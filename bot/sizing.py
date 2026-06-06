"""Position sizing & stop/target levels (todo.md Phase 5).

"More confidence = more money" done safely (summary.md §5.9):
  1. Confidence -> risk fraction of equity, from CONFIDENCE_RISK_TABLE.
  2. Risk fraction + stop distance -> share count, so dollar risk stays constant
     regardless of price: shares = floor(equity * risk_frac / stop_distance).

MAX_RISK_PCT (2%) is a HARD ceiling enforced here regardless of the table, and
the result is additionally capped by available buying power. Sizing keys off
buying_power, never the deprecated PDT fields (summary.md §10).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

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


def risk_fraction_for_confidence(confidence: float) -> float:
    """Map confidence -> risk % of equity via the table, hard-capped at MAX_RISK_PCT.

    Returns 0.0 below MIN_CONFIDENCE (no trade).
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
    stop_distance = atr * config.ATR_STOP_MULT
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
