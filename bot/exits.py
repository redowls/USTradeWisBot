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

import time as wallclock
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


# --- Break-even + trailing stop (IMP-013) -----------------------------------

_STOP_LEG_TYPES = {"STOP", "STOP_LIMIT", "TRAILING_STOP"}
# Statuses in which Alpaca will accept a PATCH on the leg. A bracket's stop leg
# sits HELD while the take-profit limit is the working OCO order.
_REPLACEABLE = {"NEW", "ACCEPTED", "HELD", "PENDING_NEW"}
# Terminal-ish statuses that mean the stop leg SOLD (or is selling) the shares,
# as opposed to being cancelled out from under the position. IMP-039.
_STOP_LEG_FILLED = {"FILLED", "PARTIALLY_FILLED"}


def peak_high_since(bars, since) -> float | None:
    """Highest price the tape PRINTED for this trade since ``since``, or None.

    ``bars`` is an intraday OHLC frame with a tz-aware ET index (what
    ``data.get_bars_for_symbols`` returns); ``since`` is the trade's entry time
    (naive ET, as stored in the DB). Both sides are compared as ``YYYY-MM-DD`` /
    ``HH:MM`` strings so a naive DB timestamp can never trip over the frame's
    tz-awareness — the same dodge ``scripts/exit_geometry.bars_by_trade`` uses,
    which keeps the live bot and the simulator reading the identical window.

    Returns None for a missing/empty frame or an empty window so the caller can
    fail open onto the previous last-trade-only behaviour. IMP-031.
    """
    if bars is None or since is None or len(bars) == 0:
        return None
    if "high" not in getattr(bars, "columns", []):
        return None
    idx = bars.index
    window = bars[(idx.strftime("%Y-%m-%d") == since.strftime("%Y-%m-%d"))
                  & (idx.strftime("%H:%M") >= since.strftime("%H:%M"))]
    if len(window) == 0:
        return None
    high = float(window["high"].max())
    return high if high > 0 else None


def compute_trailed_stop(
    entry_price: float,
    initial_stop: float,
    current_stop: float,
    live_price: float | None,
    high_price: float | None = None,
) -> float | None:
    """New (higher) stop price for a long, or None when the stop should not move.

    R is anchored to the ORIGINAL plan stop (entry - initial_stop), never the
    already-moved stop — anchoring to the moved stop would shrink 1R on every
    ratchet and chase the price straight into noise.
      * >= BREAKEVEN_TRIGGER_R printed -> stop to entry.
      * >= TRAIL_TRIGGER_R live -> stop trails TRAIL_DISTANCE_R below the live price.
    Monotonic: only returns a stop ABOVE the current one, and only when the
    improvement clears STOP_RATCHET_MIN_PCT of entry (no 60s replace churn).

    ``high_price`` (IMP-031) is the highest price the tape printed since entry.
    The engine polls ``latest_trade_price`` once per POLL_INTERVAL_SEC, so
    without it the break-even stage tests a ~60s point SAMPLE and misses any
    excursion that happened between two ticks — NFLX #244 (2026-08-11) printed
    76.89 against a 76.865 trigger for part of one minute, never armed, and rode
    to a full -1R for -$44.55 (85% of that day's loss). Only the BREAK-EVEN
    stage reads it: moving the stop to entry on a price the market really traded
    is pure loss-avoidance, whereas trailing off the running high tightens the
    trail, and tightening is exactly what sparse IEX bars bias optimistic (see
    bot/exit_sim.py). Defaults to ``live_price``, so every existing caller keeps
    its previous behaviour.
    """
    if not config.TRAILING_STOP_ENABLED or live_price is None:
        return None
    risk = entry_price - initial_stop
    if risk <= 0 or entry_price <= 0:
        return None
    peak = live_price if high_price is None else max(live_price, high_price)
    candidate: float | None = None
    if (live_price - entry_price) / risk >= config.TRAIL_TRIGGER_R:
        candidate = live_price - config.TRAIL_DISTANCE_R * risk
    if (peak - entry_price) / risk >= config.BREAKEVEN_TRIGGER_R:
        # A ratchet takes the best of the two stages; with TRAIL_DISTANCE_R <=
        # TRAIL_TRIGGER_R (the shipped 0.5R/0.5R) the trail candidate is already
        # >= entry, so this max() is a no-op today and a guard if either moves.
        candidate = entry_price if candidate is None else max(candidate, entry_price)
    if candidate is None:
        return None
    min_step = entry_price * config.STOP_RATCHET_MIN_PCT / 100.0
    if candidate <= current_stop + min_step:
        return None
    return round(candidate, 2)


def _walk_stop_leg(entry_order, fetch, max_hops: int = 5):
    """The bracket's stop leg at the END of Alpaca's replace chain, any status.

    Every replace rotates the order id: the old leg goes status=replaced with
    ``replaced_by`` pointing at its successor (losing track of the rotation is
    USTradeBot's 422 "order already replaced" loop). ``fetch`` is an order
    lookup (execution.get_order in production, a dict in tests). Returns None
    only when there is no stop leg to speak of — no leg on the parent, or a
    replace chain that dead-ends or runs past ``max_hops``.
    """
    legs = getattr(entry_order, "legs", None) or []
    leg = next(
        (l for l in legs
         if _enum_tail(getattr(l, "type", None)) in _STOP_LEG_TYPES),
        None,
    )
    for _ in range(max_hops):
        if leg is None:
            return None
        if _enum_tail(getattr(leg, "status", "")) != "REPLACED":
            return leg
        replaced_by = getattr(leg, "replaced_by", None)
        if not replaced_by or str(replaced_by) == str(getattr(leg, "id", "")):
            return None
        leg = fetch(str(replaced_by))
    return None


def resolve_stop_leg(entry_order, fetch, max_hops: int = 5):
    """The CURRENT, still-working stop leg of a bracket, or None.

    None means "no leg the ratchet can PATCH" and lumps three broker states
    together — the stop filled, the stop was cancelled, or the leg could not be
    resolved. Callers that need to tell those apart must ask ``stop_leg_filled``
    as well; that conflation is what IMP-038 half-fixed and IMP-039 finished.
    """
    leg = _walk_stop_leg(entry_order, fetch, max_hops)
    if leg is None:
        return None
    return leg if _enum_tail(getattr(leg, "status", "")) in _REPLACEABLE else None


def stop_leg_filled(entry_order, fetch, max_hops: int = 5) -> bool:
    """True when the bracket's stop leg has (partly) FILLED. IMP-039.

    A filled stop leg is an exit in progress, not a missing stop, and the two
    are indistinguishable through ``resolve_stop_leg`` alone. Observed live on
    2026-08-21: UNH #275's trailed stop (leg c3e90c63, 390.55) filled at
    16:04:22.502Z and ``GET /v2/positions`` still listed UNH on the poll that
    landed in the same second, so IMP-038 declared a position "unprotected"
    that had already been sold. Its enforcement arm is gated on the ORIGINAL
    plan stop, which every ordinary stop-out satisfies by construction (111 of
    261 closed trades) — MU #273 stopped at 961.31 against a 961.59 plan stop
    the same morning and missed the same window by 53 seconds. Enforcing there
    would cancel the sibling leg and market-sell a position the broker had
    already flattened, i.e. open a short.

    PARTIALLY_FILLED counts as filled for this purpose: the same stop order is
    still working for the untouched remainder, so the residual long is covered.
    """
    leg = _walk_stop_leg(entry_order, fetch, max_hops)
    if leg is None:
        return False
    return _enum_tail(getattr(leg, "status", "")) in _STOP_LEG_FILLED


# --- Naked-position protection (IMP-038) ------------------------------------

# What manage_stops should do about an open trade whose bracket stop leg has
# vanished. resolve_stop_leg() returns None for THREE different broker states —
# the stop filled (position closed), the stop was cancelled (position may still
# be OPEN and is then completely unprotected), or the leg could not be resolved
# — and the engine treated all three as "nothing to do".
NAKED_NONE = "none"        # no live position behind the missing leg
NAKED_ALERT = "alert"      # position open with no stop, but price is above it
NAKED_ENFORCE = "enforce"  # position open with no stop AND price is at/below it


def naked_position_action(position_held: bool, live_price, plan_stop) -> str:
    """Verdict for an open trade whose bracket stop leg is gone.

    Measured on 2026-08-20 over all 27 TAKE_PROFIT exits in the book: Alpaca's
    OCO releases the stop leg as soon as the limit leg becomes marketable, and
    on **10 of the 27** the limit did not fill immediately — leaving a real long
    position with no working stop for 0.8s to **1,594.3s (26m34s)** (BAC #149,
    2026-07-14: stop cancelled 14:04:30Z, limit filled 14:31:04Z). Cumulative
    naked exposure 2,163.6s. Every one of those windows resolved profitably, so
    it has never cost money — which is why it stayed invisible.

    ``execution.replace_stop_order``'s docstring claims "a failed replace leaves
    the old stop working, so the position is never unprotected". That claim is
    about the REPLACE path and it is fine; what was never true is the engine's
    inference that a missing leg means a closed position.

    Fails safe in the quiet direction: an unknown/invalid live price or plan
    stop can raise the alert but can never trigger enforcement, because closing
    a position on a price we could not read is a worse failure than waiting one
    more 60s poll.
    """
    if not position_held:
        return NAKED_NONE
    live = _to_float(live_price)
    stop = _to_float(plan_stop)
    if live is None or stop is None or stop <= 0 or live <= 0:
        return NAKED_ALERT
    return NAKED_ENFORCE if live <= stop else NAKED_ALERT


def resolve_limit_leg_id(entry_order) -> str | None:
    """Id of the bracket's take-profit leg while it is still cancellable.

    Returns None once the leg is filled/cancelled/expired, so the caller never
    tries to cancel an order that has already done its job. Mirrors
    resolve_stop_leg's status rules, minus the replace chain: the take-profit
    limit is never replaced by this bot.
    """
    for leg in getattr(entry_order, "legs", None) or []:
        if _enum_tail(getattr(leg, "type", None)) != "LIMIT":
            continue
        if _enum_tail(getattr(leg, "status", "")) not in _REPLACEABLE:
            return None
        leg_id = getattr(leg, "id", None)
        return str(leg_id) if leg_id else None
    return None


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


def _settle(check, sleep, timeout: float | None = None, poll: float | None = None) -> bool:
    """Poll ``check()`` until it is True or ``timeout`` seconds have been spent.

    Bounded and non-raising: a broker error during a probe counts as "not
    settled yet", so the caller always falls through to the next phase rather
    than letting a transient API failure abort a flatten. IMP-033.
    """
    timeout = config.FLATTEN_SETTLE_TIMEOUT_SEC if timeout is None else timeout
    poll = config.FLATTEN_SETTLE_POLL_SEC if poll is None else poll
    probes = max(1, int(timeout / poll)) if poll > 0 else 1
    for attempt in range(probes):
        try:
            if check():
                return True
        except Exception:  # noqa: BLE001 - a failed probe is just "not yet"
            pass
        if attempt < probes - 1:
            sleep(poll)
    return False


def shares_released(positions) -> bool:
    """True when no position still has shares held by a working order.

    Alpaca reports ``qty_available`` < ``qty`` while a bracket leg holds the
    shares, and DELETE /v2/positions/{sym} is rejected (held_for_orders) until
    the leg's cancel actually SETTLES — which is async and lands seconds after
    cancel_orders() has already returned. A position that does not report
    qty_available is treated as released, so a missing field can never stall
    the flatten. IMP-033.
    """
    for p in positions:
        qty = abs(_to_float(getattr(p, "qty", None)) or 0.0)
        available = _to_float(getattr(p, "qty_available", None))
        if available is None:
            continue
        if abs(available) + 1e-9 < qty:
            return False
    return True


def flatten_all(reason: str = "EOD_FLATTEN", sleep=None) -> list[dict]:
    """Cancel all open orders and market-sell every position. No overnight holds.

    Returns a snapshot of what was flattened (taken before liquidation). The
    precise fill prices land via detect_exits() on the next loop / via Alpaca.

    Cancels working orders FIRST, then closes each position individually, so a
    still-working bracket leg can't block (held_for_orders) the liquidation of
    its own position. The bulk close_all_positions(cancel_orders=True) raced the
    async cancel and left C/AMZN/BAC stranded for two overnights (06-16 -> 06-18);
    the caller (engine.eod_flatten) re-checks positions and retries until flat. IMP-002.

    Cancelling first was necessary but not sufficient: cancel_orders() returns
    before the cancels settle, so the closes below still raced them and EVERY
    first pass failed. On 2026-08-13 the stop legs cancelled at 19:55:23.596Z
    and the limit legs only at 19:55:26.706Z — 3.1s later — so the pass that ran
    at 19:55:23.6 submitted ZERO liquidation orders and burned a whole 60s poll;
    the same first-pass failure appears on 10 of the last 10 sessions and needed
    a SECOND retry on 6 of them, leaving the bot long at 15:57 with five minutes
    of runway to the close. So each phase now waits, bounded, for the broker
    state it depends on: shares released before closing, flat before returning.
    Both waits fail open (proceed anyway on timeout) and IMP-002's outer retry
    is untouched, so this can only shorten the exposure, never extend it. IMP-033.

    The two phases wait on different things and needed different budgets. On
    IMP-033's first live session (2026-08-14) the cancel phase settled in 5.0s
    and pass 1 did submit all three liquidations — but Alpaca then took
    12.4-15.0s to fill them, against a shared 8s budget, so the fill wait timed
    out at 19:55:25 while the sells were in flight (they filled 19:55:29-31) and
    the caller cried "EOD flatten incomplete" over a book that was about to be
    flat. That false alarm is the same message a genuine stranded position
    raises, and it also defers the exit records a whole poll (DB exit_time
    15:56:28 vs the true 15:55:29 fill). The fill phase therefore gets its own
    FLATTEN_FILL_TIMEOUT_SEC, sized off 36 measured EOD liquidations. It is a
    reporting wait, not an exposure wait: the sells are already working before
    it starts, and it is skipped entirely when no close was accepted, so a
    rejected pass still hands straight back to IMP-002's retry. IMP-034.
    """
    sleep = wallclock.sleep if sleep is None else sleep
    snapshot = _position_snapshot(reason)
    if not snapshot:
        return snapshot
    try:
        broker.cancel_all_orders()
    except Exception:  # noqa: BLE001 - liquidation below is the priority; verified by caller
        pass
    _settle(lambda: shares_released(broker.get_positions()), sleep)
    submitted = 0
    for snap in snapshot:
        try:
            broker.close_position(snap["symbol"])
            submitted += 1
        except Exception as exc:  # noqa: BLE001 - also surfaces via the caller's position re-check
            snap["flatten_error"] = f"{type(exc).__name__}: {exc}"
    if submitted:
        _settle(lambda: not broker.get_positions(), sleep,
                timeout=config.FLATTEN_FILL_TIMEOUT_SEC)
    return snapshot


def maybe_flatten(now: datetime | None = None) -> list[dict]:
    """Flatten only if it's at/after the flatten time; otherwise a no-op."""
    if past_flatten_time(now):
        return flatten_all("EOD_FLATTEN")
    return []
