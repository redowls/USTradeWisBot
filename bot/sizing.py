"""Position sizing & stop/target levels (todo.md Phase 5).

Sizing (summary.md §5.9, as amended by IMP-035 on 2026-08-15):
  1. Confidence -> risk fraction of equity, from CONFIDENCE_RISK_TABLE.
  2. Risk fraction + stop distance -> share count, so dollar risk stays constant
     regardless of price: shares = floor(equity * risk_frac / stop_distance).

§5.9's original rule was "more confidence = more money". **That rule is
withdrawn.** Over the whole 244-trade book the confidence score is monotonically
ANTI-predictive (conf <65 avg -$3.03/trade; >=85 avg -$42.28), so the ladder was
committing up to 4x the capital to the trades most likely to lose. The table is
now flat and `ladder_risk_is_non_increasing()` keeps it that way: risk may never
again rise with confidence without evidence that confidence predicts P&L with
the correct sign. See bot/config.py:CONFIDENCE_RISK_TABLE for the full record.

MAX_RISK_PCT (2%) is a HARD ceiling enforced here regardless of the table, and
the result is additionally capped by available buying power. Sizing keys off
buying_power, never the deprecated PDT fields (summary.md §10).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, replace

from . import config


@dataclass
class PositionPlan:
    symbol: str
    confidence: float
    tradable: bool
    skip_reason: str | None
    entry_price: float
    risk_fraction_pct: float        # % of equity intended at risk
    stop_distance: float            # per-share distance to stop
    shares: int
    stop_price: float
    take_profit_price: float
    dollar_risk: float              # actual $ at risk = shares * stop_distance
    dollar_risk_pct: float          # actual risk as % of equity
    notional: float                 # shares * entry_price

    def to_dict(self) -> dict:
        return asdict(self)


def ladder_risk_is_non_increasing(table=None) -> bool:
    """True when CONFIDENCE_RISK_TABLE never buys MORE risk for MORE confidence.

    The guard IMP-027's diagnostics were missing. Confidence is anti-predictive
    on this book, so a rung that rises with confidence is a capital-protection
    defect, not a feature — and it can be re-introduced silently by a scorer
    change, a weight renormalization (see tests/test_sizing_ladder.py) or an
    innocent-looking edit to the table. Pure function, no side effects.
    """
    rungs = config.CONFIDENCE_RISK_TABLE if table is None else table
    pcts = [pct for _min_conf, pct in rungs]
    return all(later <= earlier for earlier, later in zip(pcts, pcts[1:]))


def risk_fraction_for_confidence(confidence: float) -> float:
    """Map confidence -> risk % of equity via the table, hard-capped at MAX_RISK_PCT.

    Returns 0.0 below MIN_CONFIDENCE (no trade). Since IMP-035 the table is flat,
    so every permitted trade sizes at the floor rung regardless of confidence.
    """
    if confidence < config.MIN_CONFIDENCE:
        return 0.0
    frac = 0.0
    for min_conf, pct in config.CONFIDENCE_RISK_TABLE:
        if confidence >= min_conf:
            frac = pct
    return min(frac, config.MAX_RISK_PCT)


def _round_tick(price: float) -> float:
    """Round to the $0.01 tick used by US equities."""
    return round(price, 2)


def entry_slippage_pct(live_price: float | None, entry_price: float | None) -> float | None:
    """Percent the live price sits relative to the signal-bar entry, or None if unknown.

    Positive = the market ran up since the signal (a chase); negative = it pulled
    back / gapped down below the level. The engine's stale-signal guard skips an
    entry when the MAGNITUDE exceeds MAX_ENTRY_SLIPPAGE_PCT in EITHER direction
    (IMP-008 up-side, IMP-009 down-side), because the bracket's stop/take-profit
    are anchored to the signal close while the order fills live — a large gap
    mis-prices the bracket (a big up-gap 422s the take-profit; a big down-gap 422s
    the stop). Returns None when either price is missing/invalid so the guard
    fails open (no skip).
    """
    if live_price is None or entry_price is None or entry_price <= 0:
        return None
    return (live_price - entry_price) / entry_price * 100.0


def resize_for_live_risk(
    plan: PositionPlan, live_price: float | None, equity: float,
) -> PositionPlan:
    """Re-derive the share count against the LIVE per-share risk. NEVER increases it.

    Closes the hole IMP-008 named on 2026-06-30 and did not fix. `plan_position`
    anchors entry/stop/take-profit to the SIGNAL-BAR CLOSE and sizes with
    ``shares = floor(budget / stop_distance)``, but the order is a MARKET buy
    that fills at the LIVE price. When the market has run up by `d` since the
    signal bar, the stop does not move with it, so the real risk per share is
    ``stop_distance + d`` while the share count still assumes `stop_distance`.
    IMP-008 recorded this exactly — *"the stop now sits that much further from
    the real fill, silently inflating per-share risk above the plan"* — then
    shipped only the guard that SKIPS gaps beyond MAX_ENTRY_SLIPPAGE_PCT (1.0%),
    leaving the whole accepted band 0..1.0% sizing off a risk it does not take.

    Measured over all 253 closed trades (2026-08-19 review):

        106 trades (41.9%) risked MORE than their budget; mean overshoot +8.6%
        worst: SE 2026-07-02 risked $144.54 against an $83.81 budget (+72.5%)
        post-gate: 34 of 64 (53.1%) over budget
        2026-08-19 CRM: fill 0.21% above the signal close turned a $36.00
                        budget into $41.04 at risk (+14.0%)

    The ceiling is structural, not incidental: MAX_ENTRY_SLIPPAGE_PCT (1.0%) over
    a MIN_STOP_PCT (1.5%) stop admits up to **+67%** more risk than budgeted, so
    a trade sized at the ladder's 0.5% floor can quietly risk ~0.83% of equity.

    Strictly RISK-REDUCING by construction: the result is ``min`` of the planned
    share count and the live-risk share count, so a FAVOURABLE fill (live below
    the signal close) can never buy extra size — it just leaves the plan alone.
    Stop, take-profit and the risk fraction are untouched: `stop_distance` still
    defines 1R, so every downstream R-multiple stays comparable across the book.
    Fails open (returns the plan unchanged) when the live price is unknown, so a
    data hiccup can never block or resize an entry unpredictably.
    """
    if not plan.tradable or live_price is None or equity <= 0:
        return plan
    if live_price <= 0 or plan.stop_price <= 0 or plan.shares < 1:
        return plan

    live_risk_per_share = live_price - plan.stop_price
    # A live price at/below the stop is the down-gap case IMP-009 already skips
    # upstream; never divide by it, and never let it inflate the share count.
    if live_risk_per_share <= 0:
        return plan
    if live_risk_per_share <= plan.stop_distance:
        return plan  # favourable/neutral fill — size never grows

    budget = equity * (plan.risk_fraction_pct / 100.0)
    shares = min(plan.shares, math.floor(budget / live_risk_per_share))
    if shares >= plan.shares:
        return plan
    if shares < 1:
        return _skip(plan.symbol, plan.confidence, plan.entry_price,
                     "live_risk_size<1_share")

    actual_risk = shares * plan.stop_distance
    return replace(
        plan,
        shares=shares,
        dollar_risk=round(actual_risk, 2),
        dollar_risk_pct=round(100.0 * actual_risk / equity, 4) if equity > 0 else 0.0,
        notional=round(shares * plan.entry_price, 2),
    )


def vwap_distance_pct(entry_price: float | None, session_vwap: float | None) -> float | None:
    """Percent the entry sits ABOVE the symbol's session VWAP, or None if unknown.

    Positive = filled above the volume-weighted fair-value line (a stretched
    chase that tends to fade); negative = filled at/below it. The engine's VWAP
    entry-quality gate (IMP-022) skips an entry when this exceeds
    VWAP_MAX_DIST_PCT. Returns None when either price is missing/invalid so the
    gate fails open (no skip) — matching the live behavior on a thin/zero-volume
    session where session_vwap is undefined.
    """
    if entry_price is None or session_vwap is None or session_vwap <= 0:
        return None
    return (entry_price - session_vwap) / session_vwap * 100.0


def _skip(symbol: str, confidence: float, entry: float, reason: str) -> PositionPlan:
    return PositionPlan(
        symbol=symbol, confidence=confidence, tradable=False, skip_reason=reason,
        entry_price=_round_tick(entry), risk_fraction_pct=0.0, stop_distance=0.0,
        shares=0, stop_price=0.0, take_profit_price=0.0, dollar_risk=0.0,
        dollar_risk_pct=0.0, notional=0.0,
    )


def plan_position(
    symbol: str,
    confidence: float,
    entry_price: float,
    atr: float,
    equity: float,
    buying_power: float,
    *,
    held_symbols: set[str] | None = None,
    open_positions_count: int = 0,
) -> PositionPlan:
    """Produce a sized, risk-capped position plan (or a skip with a reason)."""
    held_symbols = held_symbols or set()
    symbol = symbol.strip().upper()

    # --- Funnel of skip conditions (summary.md §5.9) ---
    if confidence < config.MIN_CONFIDENCE:
        return _skip(symbol, confidence, entry_price, f"confidence<{config.MIN_CONFIDENCE}")
    if symbol in held_symbols:
        return _skip(symbol, confidence, entry_price, "already_held")
    if open_positions_count >= config.MAX_CONCURRENT_POSITIONS:
        return _skip(symbol, confidence, entry_price, "max_concurrent_positions")
    if atr is None or atr <= 0 or entry_price <= 0:
        return _skip(symbol, confidence, entry_price, "invalid_atr_or_price")

    # --- Sizing ---
    risk_pct = risk_fraction_for_confidence(confidence)   # already <= MAX_RISK_PCT
    # Stop distance = ATR-based, but floored at MIN_STOP_PCT of price so low-ATR
    # names don't get a sub-0.3% stop that lives inside intraday noise/spread.
    atr_distance = atr * config.ATR_STOP_MULT
    min_distance = entry_price * (config.MIN_STOP_PCT / 100.0)
    stop_distance = max(atr_distance, min_distance)
    dollar_risk_budget = equity * (risk_pct / 100.0)
    shares = math.floor(dollar_risk_budget / stop_distance)

    # Never exceed available buying power.
    max_affordable = math.floor(buying_power / entry_price) if buying_power > 0 else 0
    shares = min(shares, max_affordable)

    if shares < 1:
        return _skip(symbol, confidence, entry_price, "size<1_share")

    actual_risk = shares * stop_distance
    return PositionPlan(
        symbol=symbol,
        confidence=confidence,
        tradable=True,
        skip_reason=None,
        entry_price=_round_tick(entry_price),
        risk_fraction_pct=risk_pct,
        stop_distance=round(stop_distance, 4),
        shares=shares,
        stop_price=_round_tick(entry_price - stop_distance),
        take_profit_price=_round_tick(entry_price + stop_distance * config.RR_RATIO),
        dollar_risk=round(actual_risk, 2),
        dollar_risk_pct=round(100.0 * actual_risk / equity, 4) if equity > 0 else 0.0,
        notional=round(shares * entry_price, 2),
    )
