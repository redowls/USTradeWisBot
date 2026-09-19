"""DB <-> broker daily reconciliation — "equity moved but the ledger is empty".

IMP-061 (weekly, 2026-09-19). On 2026-09-18 the account lost **$290.16 (-3.88%)
on a day the strategy took zero trades**: an unguarded pytest run placed fourteen
real 1-share META bracket orders on the live paper account (IMP-060 has the full
root cause and shipped the guard that makes *that* vector impossible). This
module addresses the second half of the same failure — **nobody noticed for a
day.**

The reason nobody noticed is structural, and it is worth stating plainly because
it will recur in some other shape: every instrument this bot owns reads the
`trades` table, and the `trades` table only ever learns about orders the bot
itself placed. `daily_summary` duly recorded "0 buys / 0 sells / $0.00" beside a
$290.16 equity drop and raised nothing, because **no code anywhere compared the
two numbers.** IMP-043's conftest guard (which blocks live DB writes from tests)
is what kept the accidental fills out of the ledger, so a guard built to protect
the trade history is precisely what made the loss silent.

The check here is deliberately the dumbest one that would have caught it:

    divergence = (equity_close - equity_open) - gross_pl

``equity_close - equity_open`` is what the *broker* says the day did.
``gross_pl`` is what the *bot's ledger* says the day did. On a normal session
the bot is flat at 15:55 (the no-overnight invariant), so the two should agree to
within fees and stop slippage. When they do not, something moved money that the
bot did not record — an untracked fill, a position that survived the flatten and
is still marked to market, a manual order, or a corporate action. **Any of those
is worth an alert the same evening rather than at the weekly review.**

Why a tolerance rather than an exact match: the two quantities are not identical
by construction even on a clean day (Alpaca's paper equity carries pennies of
drift, and a position closed at 15:55 can settle a cent off its fill), and an
alarm that cries wolf gets ignored — which is the failure mode this module
exists to prevent. The tolerance is ``max(RECONCILE_TOLERANCE_USD,
RECONCILE_TOLERANCE_PCT% x equity_open)`` so that it scales with the account
instead of needing a re-tune every time equity moves. At the 2026-09-19 equity of
$7,192.26 that is ``max($25.00, $17.98) = $25.00``, and the 09-18 incident
(-$290.16 against a $0.00 ledger) clears it **11.6x over**.

⚠️ **This module changes no trading behaviour and touches no risk invariant.** It
places no orders, cancels nothing, sizes nothing, and cannot halt the bot. It
reads two numbers that ``post_close_summary`` already has in hand and decides
whether to send a Telegram message. It is detection, not control — deliberately,
because a reconciliation mismatch has too many benign causes to justify
automatically flattening or halting on one, and the capital-protection
invariants (paper endpoint, MAX_RISK_PCT 2.0, DAILY_LOSS_HALT_PCT 8.0,
MAX_CONCURRENT_POSITIONS 3, 15:30/15:55) are untouched by it.

Pure — no DB, no network, no clock. ``check()`` takes the ``daily_summary`` row
that ``logbook.write_daily_summary`` already returns.
"""

from __future__ import annotations

from . import config


def _f(value, default: float = 0.0) -> float:
    """Float or ``default`` — Decimals from pyodbc, None from an empty column."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def tolerance(equity_open: float) -> float:
    """Dollars of divergence tolerated before an alert fires.

    ``max(flat floor, percentage of session-open equity)`` — the floor stops a
    small account from alarming on pennies, the percentage stops a large one from
    silently tolerating a real loss. Never negative: a missing or nonsensical
    ``equity_open`` degrades to the flat floor rather than to zero tolerance
    (which would alarm on every session) or to infinity (which would alarm on
    none).
    """
    eq = _f(equity_open)
    pct_component = eq * _f(config.RECONCILE_TOLERANCE_PCT) / 100.0 if eq > 0 else 0.0
    return max(_f(config.RECONCILE_TOLERANCE_USD), pct_component)


def divergence(equity_open, equity_close, gross_pl) -> float:
    """Broker-reported move minus ledger-reported move, in dollars.

    Negative = the account lost money the ledger cannot account for (the 09-18
    shape). Positive = it gained money the ledger cannot account for, which is
    **equally a defect** — an unrecorded winning fill is still an unrecorded
    fill, and scoring it would flatter the strategy's book with P&L it did not
    earn. The sign is reported; the alarm is on magnitude.
    """
    return (_f(equity_close) - _f(equity_open)) - _f(gross_pl)


def check(summary: dict | None) -> dict:
    """Reconcile one ``daily_summary`` row. Never raises, never has a side effect.

    Returns a dict that is always safe to read:

    ``ok``          the check ran (both equity endpoints were usable)
    ``diverged``    the alarm condition — only ever True when ``ok``
    ``divergence``  dollars unexplained by the ledger (signed)
    ``tolerance``   the bar it was judged against
    ``reason``      why the check could not run, when ``ok`` is False

    A missing summary or a missing equity endpoint returns ``ok=False`` rather
    than a divergence, because ``0 - 0 = 0`` would read as a *clean*
    reconciliation and this check's entire purpose is to not report "fine" when
    it does not know. ``equity_open`` is None on any session the bot did not see
    the open (a mid-session restart), which is common and benign.
    """
    if not summary:
        return {"ok": False, "diverged": False, "divergence": 0.0,
                "tolerance": 0.0, "reason": "no daily_summary row"}

    equity_open = summary.get("equity_open")
    equity_close = summary.get("equity_close")
    if equity_open is None or equity_close is None:
        return {"ok": False, "diverged": False, "divergence": 0.0,
                "tolerance": 0.0, "reason": "missing equity_open/equity_close"}

    gross_pl = summary.get("gross_pl")
    delta = divergence(equity_open, equity_close, gross_pl)
    tol = tolerance(equity_open)
    return {
        "ok": True,
        "diverged": abs(delta) > tol,
        "divergence": round(delta, 2),
        "tolerance": round(tol, 2),
        "equity_open": _f(equity_open),
        "equity_close": _f(equity_close),
        "gross_pl": _f(gross_pl),
        "num_sells": summary.get("num_sells"),
        "trade_date": summary.get("trade_date"),
        "reason": None,
    }


def describe(result: dict) -> str:
    """One-line human summary of a `check()` result, for the log and the alert."""
    if not result.get("ok"):
        return f"reconciliation skipped — {result.get('reason')}"
    verdict = "DIVERGED" if result.get("diverged") else "ok"
    return (
        f"reconciliation {verdict} — broker moved "
        f"${result['equity_close'] - result['equity_open']:+,.2f}, ledger recorded "
        f"${result['gross_pl']:+,.2f} over {result.get('num_sells')} exits, "
        f"unexplained ${result['divergence']:+,.2f} "
        f"(tolerance ${result['tolerance']:,.2f})"
    )
