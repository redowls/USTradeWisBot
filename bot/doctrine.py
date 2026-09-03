"""Stop-exit doctrine — a stop is a failed trade, whatever the P&L sign.

Standing user directive (2026-09-01), applied to USTradeWisBot and its sibling
USTradeBot: **any exit caused by a stop being touched is a FAILED trade,
whatever the sign of its realized P&L.** A break-even stop that books +$0.02 is
not a win — IMP-013 (2026-07-08) raises the broker stop to entry at +0.5R and
IMP-040 (2026-08-24) arms it at +0.25R, so such a trade went green, armed the
ratchet, and then handed back every cent of it. Scoring it a win because
``realized_pl > 0`` is how a strategy with no edge keeps reporting a respectable
win rate, and ending that reporting failure is the whole point of this module.

Why a module and not another band table in ``bot.analytics``:
``by_stop_protection`` already splits STOP exits into full-1R / break-even /
trailed, but its ``trailed`` band (ratio > 1.05) **blends scratched trails with
real winners** — on 2026-09-01 the day's only trade (WMT #314, +$15.33) lands in
``trailed`` and reads as an unqualified success, when it banked +0.44R and never
came close to the +1R bar. The doctrine needs one classifier that every reader
(the daily review, the weekly review, ``scripts/report``) shares, so the WIN /
SCRATCH / FAIL split cannot drift between them.

The buckets (verbatim from the directive):

======  =========================================================  ==========
bucket  definition                                                 counts as
======  =========================================================  ==========
WIN     a TAKE_PROFIT fill, or any exit with profit_R >= +1.0      success
SCRATCH a STOP exit with +0.25 < profit_R < +1.0, or an            NOT a win
        EOD_FLATTEN between -0.25R and +1.0R
FAIL    any STOP exit with profit_R <= +0.25 (full-1R AND          failure
        break-even), or any exit below -0.25R
======  =========================================================  ==========

``profit_R`` is ``analytics.stop_protection_ratio(row) - 1``: the ratio is
anchored to the ORIGINAL 1R stop, which ``trades.stop_price`` keeps by IMP-013
design (the raised stop lives only at the broker, and is mirrored into
``trades.final_stop_price`` by IMP-041). ratio 1.0 = break-even = +0R banked.

Anti-gaming, restated here because this file is where the numbers come from:
the doctrine says a break-even stop **scores** as a failure, not that break-even
stops should be abolished. IMP-013's protection is capital protection and it
works. Never lower the stop rate by widening or removing the stop, and judge
every change on expectancy and payoff first, stop rate second.

Pure — no DB, no network, no config reads. Callers pass rows shaped like
``analytics.load_closed_trades`` output.
"""

from __future__ import annotations

from bot.analytics import _f, stop_protection_ratio

WIN = "WIN"
SCRATCH = "SCRATCH"
FAIL = "FAIL"

#: profit_R at or below which a STOP exit is a FAIL (full-1R *and* break-even).
FAIL_MAX_R = 0.25
#: profit_R at or above which any exit is a WIN regardless of its exit reason.
WIN_MIN_R = 1.0
#: profit_R below which a non-stop exit (EOD_FLATTEN) is a FAIL rather than a
#: SCRATCH — a flatten that gave back more than a quarter of 1R lost real money.
FLATTEN_MIN_R = -0.25
#: profit_R at or below which a FAIL is a *full* 1R loss rather than a stop that
#: armed and gave the move back. -1.0 is a clean stop fill; the 0.25R of slack
#: absorbs stop slippage (2026-08-28 TSM #307 filled at -1.01R).
FULL_STOP_MAX_R = -0.75


def profit_r(row: dict) -> float | None:
    """R banked at exit, anchored to the ORIGINAL 1R stop. None when unusable.

    +1.0 = one full R banked, 0.0 = break-even, -1.0 = the full plan stop.
    Returns None for rows missing entry/stop/exit or whose stop is not below
    entry, exactly as ``stop_protection_ratio`` does — such rows are still
    classified (see ``classify``) but can never score a WIN on geometry alone.
    """
    ratio = stop_protection_ratio(row)
    return None if ratio is None else ratio - 1.0


def is_stop_exit(row: dict) -> bool:
    """True when the exit was caused by a stop being touched, at any level.

    Covers the plan stop and every ratcheted descendant of it — the DB records
    them all as ``STOP`` (the engine's ``PLAN_STOP`` / ``RATCHET_STOP`` prose
    distinction lives in the log, not in ``trades.exit_reason``), so match on
    the substring rather than on equality.
    """
    reason = (row.get("exit_reason") or "").upper()
    return "STOP" in reason and "TAKE_PROFIT" not in reason


def classify(row: dict) -> str:
    """Bucket one closed trade as WIN / SCRATCH / FAIL per the doctrine.

    A TAKE_PROFIT fill is a WIN by definition (the +1.5R target paid). Anything
    else is judged on ``profit_r``. When the geometry is unusable the row falls
    back to the sign of realized P&L and is capped at SCRATCH: without a stop
    anchor there is no evidence a full R was banked, and the one thing this
    module must never do is award an unverifiable WIN.
    """
    reason = (row.get("exit_reason") or "").upper()
    if "TAKE_PROFIT" in reason:
        return WIN

    r = profit_r(row)
    if r is None:
        return SCRATCH if _f(row.get("realized_pl")) > 0 else FAIL
    if r >= WIN_MIN_R:
        return WIN
    if is_stop_exit(row):
        return FAIL if r <= FAIL_MAX_R else SCRATCH
    return FAIL if r < FLATTEN_MIN_R else SCRATCH


def fail_kind(row: dict) -> str | None:
    """Sub-classify a FAIL: 'full-1R', 'break-even', or 'faded'. None if not FAIL.

    'full-1R'    — stopped at (or through) the original plan stop: the real
                   false-breakout loss.
    'break-even' — the stop armed and the trade came back to it: IMP-013/040
                   protected the capital, the thesis still did not pay.
    'faded'      — no stop was touched; the trade drifted below -0.25R and the
                   15:55 flatten closed it. The open-fade leak ``analytics.
                   by_flatten_outcome`` was built for (2026-08-31 COST #312).
    """
    if classify(row) != FAIL:
        return None
    r = profit_r(row)
    if r is None:
        return "faded"
    if not is_stop_exit(row):
        return "faded"
    return "full-1R" if r <= FULL_STOP_MAX_R else "break-even"


def summarize(rows: list[dict]) -> dict:
    """Doctrine accounting over closed trades — the daily review's mandatory block.

    Returns stop rate, the WIN/SCRATCH/FAIL split with FAIL broken down by
    ``fail_kind``, and **true win rate beside headline win rate** (the latter
    being the ``realized_pl > 0`` count the doctrine exists to distrust). When
    the two diverge, the true one governs the verdict. Empty input returns a
    zeroed dict rather than raising, so a no-trade session still reports.
    """
    rows = [r for r in rows if r.get("realized_pl") is not None]
    n = len(rows)
    if n == 0:
        return {"trades": 0, "stops": 0, "stop_rate": 0.0,
                "win": 0, "scratch": 0, "fail": 0,
                "fail_kinds": {"full-1R": 0, "break-even": 0, "faded": 0},
                "true_win_rate": 0.0, "headline_win_rate": 0.0,
                "fail_scratch_share": 0.0, "total_pl": 0.0, "avg_r": None}

    labels = [classify(r) for r in rows]
    kinds = {"full-1R": 0, "break-even": 0, "faded": 0}
    for r in rows:
        kind = fail_kind(r)
        if kind is not None:
            kinds[kind] += 1
    stops = sum(1 for r in rows if is_stop_exit(r))
    win = labels.count(WIN)
    scratch = labels.count(SCRATCH)
    fail = labels.count(FAIL)
    headline = sum(1 for r in rows if _f(r["realized_pl"]) > 0)
    rs = [x for x in (profit_r(r) for r in rows) if x is not None]

    return {
        "trades": n,
        "stops": stops,
        "stop_rate": round(100.0 * stops / n, 1),
        "win": win,
        "scratch": scratch,
        "fail": fail,
        "fail_kinds": kinds,
        "true_win_rate": round(100.0 * win / n, 1),
        "headline_win_rate": round(100.0 * headline / n, 1),
        "fail_scratch_share": round(100.0 * (fail + scratch) / n, 1),
        "total_pl": round(sum(_f(r["realized_pl"]) for r in rows), 2),
        "avg_r": round(sum(rs) / len(rs), 3) if rs else None,
    }


def breakeven_true_win_rate(rows: list[dict]) -> float | None:
    """The true win rate this book must clear to break even at its OWN payoff.

    Expectancy in R is ``p * avgR(WIN) + (1 - p) * avgR(non-WIN)``; setting it to
    zero and solving for ``p`` gives the share of WINs the strategy needs at the
    payoff it actually realises. Returned as a percentage, or None when it cannot
    be computed — no usable R, an empty WIN or non-WIN cohort, or a non-WIN cohort
    that is not losing money (nothing to break even against).

    This is a *derived* bar, not a tuned one: it is expectancy re-expressed, so it
    cannot be passed by widening a stop or loosening a filter — those move
    ``avgR(non-WIN)`` and drag the bar up with it. That is exactly the property
    the doctrine's anti-gaming rules ask for, and it is why this belongs beside
    the buckets rather than as a hand-set constant. Re-derive it; never hand-tune
    it to make a verdict read better.

    Pure — no DB, no network.
    """
    wins: list[float] = []
    rest: list[float] = []
    for row in rows:
        r = profit_r(row)
        if r is None:
            continue
        (wins if classify(row) == WIN else rest).append(r)
    if not wins or not rest:
        return None
    avg_win = sum(wins) / len(wins)
    avg_rest = sum(rest) / len(rest)
    if avg_rest >= 0 or avg_win <= avg_rest:
        return None
    return round(100.0 * -avg_rest / (avg_win - avg_rest), 1)


def by_session(rows: list[dict]) -> dict:
    """{exit date -> summarize(rows of that session)}, sessions with trades only.

    Rows without a usable ``exit_time`` are dropped: a trade that cannot be
    dated cannot be attributed to a session, and silently bucketing it into
    "today" would corrupt the escalation window below.
    """
    by_date: dict = {}
    for r in rows:
        exit_time = r.get("exit_time")
        if exit_time is None or r.get("realized_pl") is None:
            continue
        by_date.setdefault(exit_time.date(), []).append(r)
    return {d: summarize(by_date[d]) for d in sorted(by_date)}


def escalation_verdict(rows: list[dict], sessions: int = 3,
                       threshold: float = 60.0) -> dict:
    """Has FAIL+SCRATCH stayed >= ``threshold``% across the last N sessions?

    The doctrine's escalation clause: when it has, stop shipping parameter
    tweaks — that is evidence the breakout signal itself, not its tuning, is the
    problem — write the verdict plainly, propose the structural change (or the
    honest "no demonstrated edge" finding), and hand it to the weekly review
    with the numbers attached.

    Counts **sessions that had trades**, so a flat day neither triggers nor
    resets the window. Returns ``escalated=False`` with the sessions it did find
    when fewer than ``sessions`` are available — an escalation needs evidence,
    and a short window is not evidence.
    """
    per = by_session(rows)
    dates = sorted(per)[-sessions:]
    window = [r for r in rows
              if r.get("exit_time") is not None and r["exit_time"].date() in dates
              and r.get("realized_pl") is not None]
    agg = summarize(window)
    share = agg["fail_scratch_share"]
    return {
        "escalated": bool(len(dates) == sessions and share >= threshold),
        "sessions": [str(d) for d in dates],
        "fail_scratch_share": share,
        "threshold": threshold,
        "summary": agg,
    }
