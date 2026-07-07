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


def load_closed_trades(since: date | None = None) -> list[dict]:
    """Closed trades joined to their signal (signal_type/confidence/broke_level)."""
    sql = (
        "SELECT t.trade_id, t.symbol, t.realized_pl, t.realized_pl_pct, "
        "t.exit_reason, t.entry_time, t.exit_time, t.entry_price, "
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

    # False-breakout rate: of breakout-driven trades, the share that stopped out.
    bo = [r for r in closed if (r.get("signal_type") in ("BREAKOUT", "BOTH"))]
    fb_rate = (round(100 * sum(1 for r in bo if r.get("exit_reason") == "STOP") / len(bo), 1)
               if bo else None)

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
        "by_entry_extension": by_extension,
        "false_breakout_rate": fb_rate,
        "exit_reasons": dict(Counter(r.get("exit_reason") for r in closed)),
    }


def incubation_verdict(metrics: dict) -> str:
    """A blunt readiness check — never a recommendation to go live by itself."""
    n = metrics.get("trades", 0)
    if n < MIN_SAMPLE:
        return f"INSUFFICIENT DATA — {n}/{MIN_SAMPLE}+ closed trades needed"
    issues = []
    if metrics.get("expectancy", 0) <= 0:
        issues.append("expectancy not positive")
    fb = metrics.get("false_breakout_rate")
    if fb is not None and fb >= FALSE_BREAKOUT_LIMIT:
        issues.append(f"false-breakout rate {fb}% >= {FALSE_BREAKOUT_LIMIT}%")
    if not issues:
        return "PROMISING — review by-signal-type before any live decision"
    return "NEEDS WORK — " + "; ".join(issues)


def since_days(days: int) -> date:
    return (datetime.now(config.MARKET_TZ) - timedelta(days=days)).date()
