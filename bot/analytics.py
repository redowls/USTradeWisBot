"""Incubation analytics (todo.md Phase 12).

Reads the logged trades/signals/daily_summary from SQL Server and computes the
metrics that decide whether the strategy is worth taking live (summary.md §10,
todo Phase 12): win rate, average P&L %, expectancy, profit factor, performance
by signal type, and the false-breakout rate.

`compute_metrics()` is a pure function (testable without a database); the load_*
helpers read from bot.db.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from statistics import mean

from . import config, db

# Minimum closed trades before results mean much (summary.md §10 / §12).
MIN_SAMPLE = 50
# A false-breakout rate at/above this is a red flag (todo Phase 12).
FALSE_BREAKOUT_LIMIT = 40.0


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Confidence bands for the by-confidence breakdown. The live scoring distribution
# tops out around the low-60s, so the bands deliberately span the actual range and
# expose that nothing scores >=64 — a "raise the floor to 65" change would disable
# the entire book (see daily-review 2026-06-23 / refuted improvement candidate).
CONFIDENCE_BANDS: tuple[tuple[float, float, str], ...] = (
    (0.0, 60.0, "<60"),
    (60.0, 62.0, "60-62"),
    (62.0, 64.0, "62-64"),
    (64.0, 66.0, "64-66"),
    (66.0, float("inf"), "66+"),
)

# Entry-extension bands for breakout-driven trades: how far ABOVE the broken
# level (broke_level) the bot actually filled, as a % of the level. The
# 2026-06-29 review proposed "cap extension to avoid chasing" after AAPL stopped
# out having filled 1.62% above its level — but the full book refutes it: the
# tightest bucket (<=0.5%) carries the WORST stop rate, so extension is not a
# safety signal and a cap would not touch the false-breakout leak (see
# daily-review 2026-06-29 / refuted improvement candidate). Only trades with a
# non-null broke_level (BREAKOUT/BOTH signals) land here.
EXTENSION_BANDS: tuple[tuple[float, float, str], ...] = (
    (float("-inf"), 0.5, "<=0.5%"),
    (0.5, 1.0, "0.5-1.0%"),
    (1.0, float("inf"), ">1.0%"),
)

# Stop-protection bands — split STOP exits by the fraction of the ORIGINAL 1R
# risk retained at the stop (see stop_protection_ratio). Since IMP-013
# (2026-07-08) raises the broker stop to break-even at +0.5R and trails it at
# +1R, the "STOP" exit_reason no longer means one thing: a full-1R stop is a real
# false-breakout loss (the PF~0.01 leak), while a break-even/trailed stop is a
# trade IMP-013 rescued. These bands de-blend the two so the residual real-STOP
# leak and IMP-013's effect can be judged separately. full-1R = stopped at/below
# the original 1R; break-even ~= stop raised to entry (small slippage/ratchet
# drift allowed up to +0.05R); trailed = stopped materially above entry (in
# profit).
STOP_PROTECTION_BANDS: tuple[tuple[float, float, str], ...] = (
    (float("-inf"), 0.5, "full-1R"),
    (0.5, 1.05, "break-even"),
    (1.05, float("inf"), "trailed"),
)


def _bucket(pls: list[float]) -> dict:
    """Win-rate / total / expectancy / profit-factor over one slice of P&Ls."""
    n = len(pls)
    if n == 0:
        return {"trades": 0, "win_rate": 0.0, "total_pl": 0.0,
                "expectancy": 0.0, "profit_factor": None}
    wins = [p for p in pls if p > 0]
    losses = [p for p in pls if p <= 0]
    gross_loss = sum(losses)  # <= 0
    return {
        "trades": n,
        "win_rate": round(100 * len(wins) / n, 1),
        "total_pl": round(sum(pls), 2),
        "expectancy": round(mean(pls), 2),
        "profit_factor": round(sum(wins) / abs(gross_loss), 2) if gross_loss else None,
    }


def _entry_date(row: dict) -> date | None:
    """Calendar date of a trade's entry fill, or None when missing/unparseable.

    Used to split a cohort into pre- and post-veto eras (IMP-047). Pure.
    """
    et = row.get("entry_time")
    if isinstance(et, str):
        try:
            et = datetime.fromisoformat(et)
        except ValueError:
            return None
    if isinstance(et, datetime):
        return et.date()
    if isinstance(et, date):
        return et
    return None


def _extension_pct(row: dict) -> float | None:
    """How far above the broken level a breakout filled, as a % of the level.

    Returns None for trades with no broke_level (MA-only signals) or no usable
    entry price, so those rows are simply excluded from the extension breakdown.
    """
    bl = row.get("broke_level")
    ep = row.get("entry_price")
    if bl is None or ep is None:
        return None
    bl_f = _f(bl, default=0.0)
    ep_f = _f(ep, default=0.0)
    if bl_f <= 0:
        return None
    return (ep_f - bl_f) / bl_f * 100.0


def stop_protection_ratio(row: dict) -> float | None:
    """Fraction of the ORIGINAL 1R risk retained at a STOP exit (long).

    (exit_price - orig_stop) / (entry_price - orig_stop): 0.0 = stopped at the
    original 1R stop (a full false-breakout loss), 1.0 = stopped at break-even
    (IMP-013 raised the stop to entry), >1.0 = trailed into profit before
    stopping. Anchored to the ORIGINAL plan stop, which trades.stop_price keeps
    by IMP-013 design (the raised stop lives only at the broker). Returns None
    when entry/stop/exit are missing or the stop is not below entry (non-long or
    a bad row), so such rows are simply excluded. Pure — no DB, no network.
    """
    entry = row.get("entry_price")
    stop = row.get("stop_price")
    exit_price = row.get("exit_price")
    if entry is None or stop is None or exit_price is None:
        return None
    risk = _f(entry) - _f(stop)
    if risk <= 0:
        return None
    return (_f(exit_price) - _f(stop)) / risk


def by_stop_protection(rows: list[dict]) -> dict:
    """Bucket STOP-exit P&L by how much of the original 1R was retained.

    Only rows whose exit_reason is STOP and that have a usable
    stop_protection_ratio are counted; returns {band: _bucket(...)} for every
    STOP_PROTECTION_BANDS label (empty dict when no STOP exit has a usable
    ratio). Pure.
    """
    pairs = [(r, stop_protection_ratio(r)) for r in rows
             if r.get("realized_pl") is not None and r.get("exit_reason") == "STOP"]
    pairs = [(r, rf) for r, rf in pairs if rf is not None]
    if not pairs:
        return {}
    out: dict[str, dict] = {}
    for lo, hi, label in STOP_PROTECTION_BANDS:
        sub = [_f(r["realized_pl"]) for r, rf in pairs if lo <= rf < hi]
        out[label] = _bucket(sub)
    return out


def by_flatten_outcome(rows: list[dict]) -> dict:
    """Split EOD_FLATTEN-exit P&L into faded (net loss) vs drifted-up (net gain).

    The EOD_FLATTEN twin of by_stop_protection. IMP-013's break-even/trail only
    arms once a trade first reaches +0.5R green, so a breakout/MA entry that fades
    from the open but whose wide 3xATR stop is never hit escapes into an
    EOD_FLATTEN exit, NOT a STOP — invisible to by_stop_protection (STOP-only).
    Because the up-drift cohort makes the EOD_FLATTEN bucket net-positive overall
    (all-time PF ~1.6), that faded sub-population is masked in the by_exit_reason
    headline. Splitting by the sign of realized P&L surfaces the residual
    open-fade leak that leaks into the flatten bucket — first clearly seen
    2026-07-14 (XOM: conf-78 BOTH breakout, filled 0.65% above its level, faded
    straight to a -$49.78 flatten with its stop never hit). Measurement-only, the
    refuted-candidate-made-visible pattern of IMP-004/007/014/015/016. Returns
    {"faded": _bucket, "drifted-up": _bucket} over EOD_FLATTEN exits (empty dict
    when there are none). Pure — no DB, no network.
    """
    flat = [_f(r["realized_pl"]) for r in rows
            if r.get("realized_pl") is not None and r.get("exit_reason") == "EOD_FLATTEN"]
    if not flat:
        return {}
    return {
        "faded": _bucket([p for p in flat if p < 0]),
        "drifted-up": _bucket([p for p in flat if p >= 0]),
    }


# Time-of-day bands — minutes AFTER the 09:30 ET open at which the entry filled.
# Motivated by the recurring high-confidence "open-drive fade": on 2026-07-10
# (TSLA conf-82 BOTH, entered 09:31) and 2026-07-13 (NVDA conf-94 BOTH, entered
# 09:30) the day's whole loss was a breakout that filled in the first minutes and
# faded straight to its full 1R stop. That pattern invites a "skip the first N
# minutes after the open" entry gate (a backlog ★ regime proxy). These bands make
# the hypothesis checkable BEFORE any engine change: bucketing the book by entry
# minute shows the false-breakout STOP bleed is spread across the WHOLE session
# (all-time STOP $ by band 0-5m/5-15m/15-30m/30-60m/60m+ ≈ -1211/-611/-409/-395/
# -964 — no early band is distinctly worse), and the earliest band also holds the
# day's BIGGEST winners (2026-07-13 MSFT +$78.39 entered 09:34; 2026-07-09 SE
# +$228.54 TP entered 09:31), so an open-skip gate would forgo winners without
# isolating the leak. Measurement-only — the refuted-candidate-made-visible
# pattern of IMP-004/007/015. Entries only land in 0-360 min (ENTRY_CUTOFF_ET).
MARKET_OPEN_ET_MINUTES = 9 * 60 + 30      # 09:30 ET regular-session open
TIME_OF_DAY_BANDS: tuple[tuple[float, float, str], ...] = (
    (float("-inf"), 5.0, "0-5m"),
    (5.0, 15.0, "5-15m"),
    (15.0, 30.0, "15-30m"),
    (30.0, 60.0, "30-60m"),
    (60.0, float("inf"), "60m+"),
)


def _minutes_after_open(row: dict) -> float | None:
    """Minutes from the 09:30 ET open to this trade's entry fill.

    Reads entry_time (a datetime, or an ISO string from the DB driver); returns
    None when it is missing/unparseable so such rows are simply excluded. The ET
    wall-clock of entry_time is used directly (trades are logged in market time),
    so no timezone conversion is needed. Pure — no DB, no network.
    """
    et = row.get("entry_time")
    if et is None:
        return None
    if isinstance(et, str):
        try:
            et = datetime.fromisoformat(et)
        except ValueError:
            return None
    try:
        return (et.hour * 60 + et.minute + et.second / 60.0) - MARKET_OPEN_ET_MINUTES
    except AttributeError:
        return None


def by_time_of_day(rows: list[dict]) -> dict:
    """Bucket closed-trade P&L by minutes-after-open at entry (TIME_OF_DAY_BANDS).

    Returns {band: _bucket(...)} for every band, over all closed trades with a
    usable entry_time (empty dict when none have one). Surfaces whether the loss /
    false-breakout bleed is concentrated near the open — the evidence a "skip the
    first N minutes" entry gate would need before any engine change. Pure.
    """
    pairs = [(r, _minutes_after_open(r)) for r in rows
             if r.get("realized_pl") is not None]
    pairs = [(r, mao) for r, mao in pairs if mao is not None]
    if not pairs:
        return {}
    out: dict[str, dict] = {}
    for lo, hi, label in TIME_OF_DAY_BANDS:
        sub = [_f(r["realized_pl"]) for r, mao in pairs if lo <= mao < hi]
        out[label] = _bucket(sub)
    return out


# --- Market-regime tagging (todo.md backlog ★ — the top strategy lever) --------
#
# Every per-trade discriminator is refuted (confidence IMP-004, volume 2026-06-26,
# entry-extension IMP-007): no pre-trade SCORE separates a false breakout from a
# real one, so the entire STOP-exit bleed (all-time PF ~0.01) is not a scoring
# problem. The one lever left is MARKET-LEVEL — only take longs when the index
# (SPY) is itself trending up intraday. These pure helpers are the FIRST
# measurement of that hypothesis: tag each closed trade with the index regime at
# its entry minute (SPY close vs a short intraday EMA) and bucket realized P&L,
# so the gate can be judged on evidence before any engine change (the
# measurement-first pattern of IMP-004/006/007). Offline/pure — the SPY series is
# fetched by the standalone scripts/regime_analysis.py, never by the always-on
# report, so a data hiccup can never break the incubation report.

INDEX_REGIME_SYMBOL = "SPY"
INDEX_REGIME_EMA_SPAN = 9          # 9 × 5-min ≈ 45-min intraday trend filter

REGIME_BULLISH = "bullish"
REGIME_BEARISH = "bearish"
REGIME_UNKNOWN = "unknown"


def classify_index_regime(index_price, index_ema) -> str:
    """Tag the intraday market regime from the index price vs its short EMA.

    bullish = index at/above its intraday EMA (take longs); bearish = below it;
    unknown when either input is missing (no index bar aligned to the entry) so a
    data gap never fabricates a regime. Pure — no network, no DB.
    """
    if index_price is None or index_ema is None:
        return REGIME_UNKNOWN
    return REGIME_BULLISH if _f(index_price) >= _f(index_ema) else REGIME_BEARISH


def by_market_regime(rows: list[dict], regime_by_trade_id: dict) -> dict:
    """Bucket closed-trade P&L by the index regime tagged at each entry.

    `regime_by_trade_id` maps trade_id -> a REGIME_* label (from
    classify_index_regime). Returns a `buckets` dict {label: _bucket(...)} for the
    labels present, plus a `skip_bearish` what-if: what the book becomes if every
    BEARISH-regime entry had been skipped (the gate's effect), keeping bullish AND
    unknown trades (never skip on missing data — fail open). Lets the lever be
    valued without touching the engine. Pure.
    """
    closed = [r for r in rows if r.get("realized_pl") is not None]
    buckets: dict[str, dict] = {}
    for label in (REGIME_BULLISH, REGIME_BEARISH, REGIME_UNKNOWN):
        sub = [_f(r["realized_pl"]) for r in closed
               if regime_by_trade_id.get(r.get("trade_id"), REGIME_UNKNOWN) == label]
        if sub:
            buckets[label] = _bucket(sub)

    kept = [_f(r["realized_pl"]) for r in closed
            if regime_by_trade_id.get(r.get("trade_id"), REGIME_UNKNOWN) != REGIME_BEARISH]
    skipped = [_f(r["realized_pl"]) for r in closed
               if regime_by_trade_id.get(r.get("trade_id"), REGIME_UNKNOWN) == REGIME_BEARISH]
    return {
        "buckets": buckets,
        "skip_bearish": {
            "kept_trades": len(kept),
            "kept_total_pl": round(sum(kept), 2),
            "skipped_trades": len(skipped),
            "skipped_total_pl": round(sum(skipped), 2),
        },
    }


def regime_proxy_agreement(regime_a: dict, regime_b: dict) -> dict:
    """Compare two index-regime proxy tags (e.g. SPY-EMA9 vs QQQ-EMA9).

    Each arg maps trade_id -> a REGIME_* label. Over the trade_ids present in
    BOTH maps, report how often the two proxies agree — a robustness check on the
    regime definition before any engine gate relies on it (IMP-011's queued
    "compare EMA9 vs QQQ/VWAP" step). If flipping the proxy can flip a trade's
    regime, the gate's edge is proxy-dependent and not yet trustworthy. Pure —
    no network, no DB.
    """
    tids = sorted(set(regime_a) & set(regime_b))
    disagreements = [(t, regime_a[t], regime_b[t]) for t in tids
                     if regime_a[t] != regime_b[t]]
    n = len(tids)
    agree = n - len(disagreements)
    return {
        "trades": n,
        "agree": agree,
        "disagree": len(disagreements),
        "agree_pct": round(100 * agree / n, 1) if n else 0.0,
        "disagreements": disagreements,
    }


# Per-proxy bearish trades needed before the skip-bearish gate can be ruled IN.
# A thin bearish sample (IMP-011 shipped at n=13) can flip sign as it grows, so a
# gate must not earn SUPPORTED on a handful of trades.
MIN_BEARISH_SAMPLE_FOR_GATE = 20


def skip_bearish_gate_verdict(results_by_proxy: dict) -> dict:
    """Machine verdict on the skip-bearish market-regime gate across proxies.

    `results_by_proxy` maps a proxy label (e.g. "SPY", "QQQ") to a
    `by_market_regime()` result. Encodes the analysis's prose "Read:" rule as a
    checkable verdict: skipping every BEARISH-regime entry is SUPPORTED only
    when, under EVERY proxy, all three hold —
      (1) the bearish bucket has >= MIN_BEARISH_SAMPLE_FOR_GATE trades (a thin
          sample can't rule the gate in),
      (2) skipping bearish removes net-NEGATIVE P&L (`skipped_total_pl` < 0, so
          the removed trades were a net loss and the book improves), AND
      (3) the bearish profit factor is below the bullish one (bearish is the
          worse regime).
    If any proxy fails any test the gate is REFUTED with the reason — its edge is
    proxy-fragile, the bearish sample is thin, or (the 2026-07-09 case) the
    bearish bucket is actually profitable so skipping would remove profit. The
    default is REFUTED (empty input, missing buckets): a gate must earn SUPPORTED
    under every proxy, a capital-protective bias so a harmful entry filter can't
    ship on a cherry-picked window. Pure — no network, no DB.
    """
    per_proxy: dict[str, dict] = {}
    reasons: list[str] = []
    for proxy, res in results_by_proxy.items():
        buckets = (res or {}).get("buckets", {})
        sk = (res or {}).get("skip_bearish", {})
        bear = buckets.get(REGIME_BEARISH) or {}
        bull = buckets.get(REGIME_BULLISH) or {}
        n_bear = bear.get("trades", 0)
        skipped_pl = sk.get("skipped_total_pl", 0.0)
        bear_pf = bear.get("profit_factor")
        bull_pf = bull.get("profit_factor")
        p = {"bearish_trades": n_bear, "skipped_total_pl": skipped_pl,
             "bearish_pf": bear_pf, "bullish_pf": bull_pf, "ok": True}
        if n_bear < MIN_BEARISH_SAMPLE_FOR_GATE:
            p["ok"] = False
            reasons.append(f"insufficient bearish sample under {proxy} "
                           f"(n={n_bear}<{MIN_BEARISH_SAMPLE_FOR_GATE})")
        elif skipped_pl >= 0:
            p["ok"] = False
            reasons.append(f"skipping bearish removes net-positive P&L under "
                           f"{proxy} (${skipped_pl:+.2f})")
        elif bear_pf is not None and bull_pf is not None and bear_pf >= bull_pf:
            p["ok"] = False
            reasons.append(f"bearish not worse than bullish under {proxy} "
                           f"(PF {bear_pf:.2f} >= {bull_pf:.2f})")
        per_proxy[proxy] = p
    supported = bool(results_by_proxy) and all(p["ok"] for p in per_proxy.values())
    if supported:
        reason = "all proxies support skip-bearish"
    elif reasons:
        reason = "; ".join(reasons)
    else:
        reason = "no proxy data"
    return {"supported": supported, "reason": reason, "per_proxy": per_proxy}


def load_closed_trades(since: date | None = None) -> list[dict]:
    """Closed trades joined to their signal (signal_type/confidence/broke_level)."""
    sql = (
        "SELECT t.trade_id, t.symbol, t.realized_pl, t.realized_pl_pct, "
        "t.exit_reason, t.entry_time, t.exit_time, t.entry_price, "
        "t.stop_price, t.exit_price, "
        "s.signal_type, s.confidence, s.broke_level "
        "FROM trades t LEFT JOIN signals s ON s.trade_id = t.trade_id "
        "WHERE t.status = 'CLOSED' AND t.realized_pl IS NOT NULL"
    )
    params: list = []
    if since is not None:
        sql += " AND CAST(t.entry_time AS DATE) >= ?"
        params.append(since)
    sql += " ORDER BY t.entry_time"
    return db.query(sql, params)


def load_daily_summaries(since: date | None = None) -> list[dict]:
    sql = "SELECT * FROM daily_summary"
    params: list = []
    if since is not None:
        sql += " WHERE trade_date >= ?"
        params.append(since)
    sql += " ORDER BY trade_date"
    return db.query(sql, params)


def compute_metrics(rows: list[dict]) -> dict:
    """Pure metric computation over closed-trade rows."""
    closed = [r for r in rows if r.get("realized_pl") is not None]
    n = len(closed)
    if n == 0:
        return {"trades": 0}

    pls = [_f(r["realized_pl"]) for r in closed]
    pcts = [_f(r["realized_pl_pct"]) for r in closed if r.get("realized_pl_pct") is not None]
    wins = [p for p in pls if p > 0]
    losses = [p for p in pls if p <= 0]

    gross_win = sum(wins)
    gross_loss = sum(losses)  # <= 0
    by_type: dict[str, dict] = {}
    for st in sorted({(r.get("signal_type") or "UNKNOWN") for r in closed}):
        sub = [_f(r["realized_pl"]) for r in closed if (r.get("signal_type") or "UNKNOWN") == st]
        by_type[st] = _bucket(sub)

    # By confidence band — exposes the actual scoring distribution so a "raise the
    # MIN_CONFIDENCE floor" candidate is judged against where trades really land.
    by_band: dict[str, dict] = {}
    for lo, hi, label in CONFIDENCE_BANDS:
        sub = [_f(r["realized_pl"]) for r in closed
               if r.get("confidence") is not None and lo <= _f(r["confidence"]) < hi]
        by_band[label] = _bucket(sub)

    # By exit reason — separates WHERE the P&L actually comes from. The all-time
    # shape (2026-06-25): STOP exits carry the entire bleed (PF ~0.01, the
    # false-breakout losses), while EOD_FLATTEN is net positive (PF ~1.3). This
    # keeps the queued "convert EOD_FLATTEN drift via breakeven/trailing" candidate
    # honest — it targets the one already-profitable bucket, not the real leak.
    by_exit: dict[str, dict] = {}
    for er in sorted({(r.get("exit_reason") or "UNKNOWN") for r in closed}):
        sub = [_f(r["realized_pl"]) for r in closed if (r.get("exit_reason") or "UNKNOWN") == er]
        by_exit[er] = _bucket(sub)

    # By entry extension — for breakout-driven trades (those with a broke_level),
    # how far above the broken level the fill landed. Surfaces that "chasing"
    # (large extension) is NOT what drives the stop-outs: the tightest bucket
    # carries the worst stop rate, so an extension cap is a refuted candidate.
    by_extension: dict[str, dict] = {}
    ext_pairs = [(r, _extension_pct(r)) for r in closed]
    ext_pairs = [(r, e) for r, e in ext_pairs if e is not None]
    if ext_pairs:
        for lo, hi, label in EXTENSION_BANDS:
            sub = [_f(r["realized_pl"]) for r, e in ext_pairs if lo <= e < hi]
            by_extension[label] = _bucket(sub)

    # By stop protection — de-blend the STOP exit_reason now that IMP-013
    # (2026-07-08) raises stops to break-even (+0.5R) and trails them (+1R). A
    # STOP exit is either a full original-1R loss (the real false-breakout leak,
    # all-time PF ~0.01) or a trade IMP-013 rescued to ~break-even / trailed
    # profit. Splitting by the retained fraction of the original 1R keeps the
    # by_exit_reason STOP bucket honest and measures IMP-013's effect over time.
    by_stop_prot = by_stop_protection(closed)

    # By flatten outcome — the EOD_FLATTEN twin of by_stop_protection. An
    # open-fade whose wide stop is never hit exits via EOD_FLATTEN (not STOP), so
    # the by_stop_protection scorecard misses it; and the profitable up-drift
    # cohort makes the EOD_FLATTEN bucket net-positive overall, masking the faded
    # losers. Splitting by the sign of realized P&L surfaces that faded slice
    # (2026-07-14 XOM: BOTH breakout faded to a -$49.78 flatten, no stop hit).
    by_flatten = by_flatten_outcome(closed)

    # By time of day — minutes-after-open at entry. Tests the "skip the first N
    # minutes" open-fade gate candidate (see TIME_OF_DAY_BANDS): the STOP/loss
    # bleed is spread across the whole session and the earliest band also holds
    # the biggest winners, so an open-skip gate is not the lever.
    by_tod = by_time_of_day(closed)

    # False-breakout rate: of breakout-driven trades, the share that stopped out.
    #
    # ERA-SPLIT (IMP-047, 2026-09-03). IMP-021's BREAKOUT_FADE_CEILING (0.5) sits
    # BELOW the analytic floor of signals.breakout_score: a level carrying the
    # MIN_LEVEL_TOUCHES touches levels.py clusters for scores at least
    # 0.45 + 0.20*(2/3) = 0.583, and the lowest of the 74 breakout-bearing signals
    # ever recorded was 0.5611. The veto therefore removes 100% of breakouts, not
    # the worst of them — IMP-021's own 2026-08-01 note said so and told the next
    # run to re-scope the report verdict around the MA/VWAP system that actually
    # trades. The last breakout-bearing signal was 2026-07-24, so this cohort is
    # frozen: the rate can never move again, and gating the verdict on it made
    # "NEEDS WORK" unfalsifiable regardless of live performance. Keep the all-time
    # figure (it is real history, and the evidence the veto rests on) but publish
    # whether the leg can still trade, so incubation_verdict only judges on it
    # while it is live.
    bo = [r for r in closed if (r.get("signal_type") in ("BREAKOUT", "BOTH"))]
    fb_rate = (round(100 * sum(1 for r in bo if r.get("exit_reason") == "STOP") / len(bo), 1)
               if bo else None)
    bo_live = [r for r in bo
               if (ed := _entry_date(r)) is not None
               and ed >= config.BREAKOUT_VETO_LIVE_FROM]

    # Stop-exit doctrine numbers, so the verdict can be judged on the true win
    # rate the standing directive says governs it. Imported here rather than at
    # module scope because bot.doctrine imports from bot.analytics.
    from . import doctrine  # noqa: PLC0415 — deliberate, breaks the import cycle
    dsum = doctrine.summarize(closed)

    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(100 * len(wins) / n, 1),
        "total_pl": round(sum(pls), 2),
        "expectancy": round(mean(pls), 2),            # expected $ per trade
        "avg_pl_pct": round(mean(pcts), 4) if pcts else 0.0,
        "avg_win": round(mean(wins), 2) if wins else 0.0,
        "avg_loss": round(mean(losses), 2) if losses else 0.0,
        "profit_factor": round(gross_win / abs(gross_loss), 2) if gross_loss else None,
        "by_signal_type": by_type,
        "by_confidence_band": by_band,
        "by_exit_reason": by_exit,
        "by_stop_protection": by_stop_prot,
        "by_flatten_outcome": by_flatten,
        "by_time_of_day": by_tod,
        "by_entry_extension": by_extension,
        "false_breakout_rate": fb_rate,
        "breakout_leg_active": bool(bo_live),
        "true_win_rate": dsum["true_win_rate"] if dsum["trades"] else None,
        "breakeven_true_win_rate": doctrine.breakeven_true_win_rate(closed),
        "exit_reasons": dict(Counter(r.get("exit_reason") for r in closed)),
    }


def incubation_verdict(metrics: dict) -> str:
    """A blunt readiness check — never a recommendation to go live by itself."""
    n = metrics.get("trades", 0)
    if n < MIN_SAMPLE:
        return f"INSUFFICIENT DATA — {n}/{MIN_SAMPLE}+ closed trades needed"
    issues: list[str] = []
    notes: list[str] = []
    if metrics.get("expectancy", 0) <= 0:
        issues.append("expectancy not positive")

    # IMP-047: only judge the breakout leg while it can still trade. Under
    # IMP-021's total veto this cohort is frozen history, so citing it as a live
    # red flag pinned the verdict to "NEEDS WORK" on evidence that can never
    # change — say so in a note instead of scoring it.
    fb = metrics.get("false_breakout_rate")
    if metrics.get("breakout_leg_active"):
        if fb is not None and fb >= FALSE_BREAKOUT_LIMIT:
            issues.append(f"false-breakout rate {fb}% >= {FALSE_BREAKOUT_LIMIT}%")
    elif fb is not None:
        notes.append(f"breakout leg vetoed since {config.BREAKOUT_VETO_LIVE_FROM}"
                     f" — false-breakout {fb}% is frozen history, not a live gate")

    # ...and in its place, the gate that does describe the system that trades: the
    # doctrine's true win rate against the break-even bar this book's own payoff
    # implies. A stop is a failed trade whatever its P&L sign, so a headline win
    # rate cannot carry this check (standing directive, 2026-09-01).
    twr = metrics.get("true_win_rate")
    bar = metrics.get("breakeven_true_win_rate")
    if twr is not None and bar is not None and twr < bar:
        issues.append(f"true win rate {twr}% < {bar}% needed to break even "
                      f"at its own payoff")

    verdict = ("PROMISING — review by-signal-type before any live decision"
               if not issues else "NEEDS WORK — " + "; ".join(issues))
    return verdict if not notes else f"{verdict}  [{'; '.join(notes)}]"


def since_days(days: int) -> date:
    return (datetime.now(config.MARKET_TZ) - timedelta(days=days)).date()
