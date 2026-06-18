"""Exit management & end-of-day flatten (todo.md Phase 7).

Two jobs each loop:
  1. Detect filled bracket exit legs, classify the reason ('TAKE_PROFIT' /
     'STOP'), and compute realized P&L. (Persistence is Phase 8.)
  2. Enforce the two time rules near the close (summary.md §2, §5.11):
       - No new entries after ENTRY_CUTOFF_ET (15:30).
       - Force-flatten everything at FLATTEN_ET (15:55): cancel open orders and
         market-sell all positions ('EOD_FLATTEN'). No overnight holds.

All times compare in US Eastern explicitly.
"""

from __future__ import annotations

from datetime import datetime, time

from . import broker, config, execution


# --- Time rules (US Eastern) ------------------------------------------------

def _parse_hhmm(text: str) -> time:
    hours, minutes = text.split(":")
    return time(int(hours), int(minutes))


ENTRY_CUTOFF = _parse_hhmm(config.ENTRY_CUTOFF_ET)
FLATTEN_TIME = _parse_hhmm(config.FLATTEN_ET)


def now_et() -> datetime:
    """Current time in US Eastern (the market timezone)."""
    return datetime.now(config.MARKET_TZ)


def past_entry_cutoff(now: datetime | None = None) -> bool:
    """True at/after 15:30 ET — too late to open new trades."""
    return (now or now_et()).time() >= ENTRY_CUTOFF


def entries_allowed(now: datetime | None = None) -> bool:
    """True while new entries are still permitted (before the cutoff)."""
    return not past_entry_cutoff(now)


def past_flatten_time(now: datetime | None = None) -> bool:
    """True at/after 15:55 ET — force-flatten everything."""
    return (now or now_et()).time() >= FLATTEN_TIME


# --- Exit detection & P&L ---------------------------------------------------

def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _enum_tail(value) -> str:
    """'OrderStatus.FILLED' or 'filled' -> 'FILLED'."""
    return str(value).split(".")[-1].upper()


def reason_from_leg_type(leg_type) -> str:
    """Map a bracket leg's order type to an exit reason."""
    t = _enum_tail(leg_type)
    if t == "LIMIT":
        return "TAKE_PROFIT"
    if t in ("STOP", "STOP_LIMIT"):
        return "STOP"
    return "UNKNOWN"


def compute_pl(entry_price: float, exit_price: float, qty: float) -> tuple[float, float]:
    """Realized P&L (dollars) and P&L % for a long position."""
    pl = (exit_price - entry_price) * qty
    pl_pct = ((exit_price / entry_price) - 1.0) * 100.0 if entry_price else 0.0
    return round(pl, 4), round(pl_pct, 4)


def build_exit_record(entry_order) -> dict | None:
    """From a (parent) bracket order, return an exit record if a leg has filled.

    Returns None if the entry hasn't filled yet or neither exit leg has filled
    (position still open). Works on any object exposing the Alpaca Order shape,
    so it is unit-testable with a fake order.
    """
    entry_price = _to_float(getattr(entry_order, "filled_avg_price", None))
    if entry_price is None:
        return None  # entry not filled yet

    qty = _to_float(getattr(entry_order, "filled_qty", None)) or 0.0
    legs = getattr(entry_order, "legs", None) or []
    for leg in legs:
        if _enum_tail(getattr(leg, "status", "")) != "FILLED":
            continue
        exit_price = _to_float(getattr(leg, "filled_avg_price", None))
        if exit_price is None:
            continue
        pl, pl_pct = compute_pl(entry_price, exit_price, qty)
        return {
            "symbol": getattr(entry_order, "symbol", None),
            "entry_order_id": str(getattr(entry_order, "id", "")),
            "exit_order_id": str(getattr(leg, "id", "")),
            "qty": int(qty),
            "entry_price": round(entry_price, 4),
            "exit_price": round(exit_price, 4),
            "exit_time": getattr(leg, "filled_at", None),
            "exit_reason": reason_from_leg_type(getattr(leg, "type", None)),
            "realized_pl": pl,
            "realized_pl_pct": pl_pct,
        }
    return None  # still open


def detect_exits(entry_order_ids: list[str]) -> list[dict]:
    """Fetch each entry order and return exit records for those that have closed."""
    records: list[dict] = []
    for oid in entry_order_ids:
        try:
            order = execution.get_order(oid)
        except Exception:  # noqa: BLE001 - one bad id shouldn't stop the rest
            continue
        record = build_exit_record(order)
        if record is not None:
            records.append(record)
    return records


# --- End-of-day flatten -----------------------------------------------------

def _position_snapshot(reason: str) -> list[dict]:
    snapshot: list[dict] = []
    for p in broker.get_positions():
        snapshot.append({
            "symbol": p.symbol,
            "qty": int(_to_float(p.qty) or 0),
            "avg_entry_price": _to_float(getattr(p, "avg_entry_price", None)),
            "market_value": _to_float(getattr(p, "market_value", None)),
            "unrealized_pl": _to_float(getattr(p, "unrealized_pl", None)),
            "exit_reason": reason,
        })
    return snapshot


def flatten_all(reason: str = "EOD_FLATTEN") -> list[dict]:
    """Cancel all open orders and market-sell every position. No overnight holds.

    Returns a snapshot of what was flattened (taken before liquidation). The
    precise fill prices land via detect_exits() on the next loop / via Alpaca.

    Cancels working orders FIRST, then closes each position individually, so a
    still-working bracket leg can't block (held_for_orders) the liquidation of
    its own position. The bulk close_all_positions(cancel_orders=True) raced the
    async cancel and left C/AMZN/BAC stranded for two overnights (06-16 -> 06-18);
    the caller (engine.eod_flatten) re-checks positions and retries until flat. IMP-002.
    """
    snapshot = _position_snapshot(reason)
    try:
        broker.cancel_all_orders()
    except Exception:  # noqa: BLE001 - liquidation below is the priority; verified by caller
        pass
    for snap in snapshot:
        try:
            broker.close_position(snap["symbol"])
        except Exception:  # noqa: BLE001 - any failure surfaces via the caller's position re-check
            pass
    return snapshot


def maybe_flatten(now: datetime | None = None) -> list[dict]:
    """Flatten only if it's at/after the flatten time; otherwise a no-op."""
    if past_flatten_time(now):
        return flatten_all("EOD_FLATTEN")
    return []
