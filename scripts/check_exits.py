"""Phase 7 check (todo.md Phase 7 "Done when").

Part 1 (offline) — verify the time rules (15:30 entry cutoff, 15:55 flatten),
P&L math, exit-reason classification, and exit-record building against fake
bracket orders (TP-filled, SL-filled, still-open, entry-unfilled).
Part 2 (live) — report current ET, whether entries are allowed / flatten is due,
and the live exit/position state (no side effects).

Run:  python -m scripts.check_exits
"""

from __future__ import annotations

import sys
from datetime import datetime
from types import SimpleNamespace

from bot import config, exits


def _et(h: int, m: int) -> datetime:
    return datetime(2026, 6, 8, h, m, tzinfo=config.MARKET_TZ)


def _fake_order(entry_filled=True, leg=("limit", "filled", 102.0)):
    """Build a fake parent bracket order with one TP leg + one SL leg."""
    ltype, lstatus, lprice = leg
    tp = SimpleNamespace(id="tp1", type="limit",
                         status=lstatus if ltype == "limit" else "canceled",
                         filled_avg_price=lprice if ltype == "limit" else None,
                         filled_at=_et(11, 0))
    sl = SimpleNamespace(id="sl1", type="stop",
                         status=lstatus if ltype == "stop" else "canceled",
                         filled_avg_price=lprice if ltype == "stop" else None,
                         filled_at=_et(11, 0))
    return SimpleNamespace(
        id="parent1", symbol="AAPL",
        filled_avg_price=100.0 if entry_filled else None,
        filled_qty=10.0, legs=[tp, sl],
    )


def _offline() -> bool:
    print("[1] Offline: time rules, P&L, exit-record building")
    ok = True

    # Entry cutoff (15:30) and flatten (15:55).
    time_cases = [
        ("entries_allowed 09:35", exits.entries_allowed(_et(9, 35)), True),
        ("entries_allowed 15:29", exits.entries_allowed(_et(15, 29)), True),
        ("entries_allowed 15:30", exits.entries_allowed(_et(15, 30)), False),
        ("past_entry_cutoff 15:31", exits.past_entry_cutoff(_et(15, 31)), True),
        ("past_flatten 15:54", exits.past_flatten_time(_et(15, 54)), False),
        ("past_flatten 15:55", exits.past_flatten_time(_et(15, 55)), True),
    ]
    for name, got, exp in time_cases:
        if got != exp:
            print(f"  FAIL: {name} = {got}, expected {exp}"); ok = False
    print("  OK time rules: cutoff 15:30, flatten 15:55")

    # P&L math.
    if exits.compute_pl(100, 102, 10) != (20.0, 2.0):
        print(f"  FAIL: win P&L {exits.compute_pl(100,102,10)}"); ok = False
    if exits.compute_pl(100, 98, 10) != (-20.0, -2.0):
        print(f"  FAIL: loss P&L {exits.compute_pl(100,98,10)}"); ok = False
    print("  OK P&L: +2 pts/10sh = +$20 (+2%), -2 pts = -$20 (-2%)")

    # Reason classification.
    if not (exits.reason_from_leg_type("limit") == "TAKE_PROFIT"
            and exits.reason_from_leg_type("stop") == "STOP"):
        print("  FAIL: reason classification"); ok = False
    print("  OK reasons: limit->TAKE_PROFIT, stop->STOP")

    # Exit-record building scenarios.
    tp_rec = exits.build_exit_record(_fake_order(leg=("limit", "filled", 102.0)))
    if not (tp_rec and tp_rec["exit_reason"] == "TAKE_PROFIT"
            and tp_rec["realized_pl"] == 20.0 and tp_rec["realized_pl_pct"] == 2.0):
        print(f"  FAIL: TP exit record -> {tp_rec}"); ok = False
    else:
        print(f"  OK TP exit: {tp_rec['exit_reason']} ${tp_rec['realized_pl']} "
              f"({tp_rec['realized_pl_pct']}%)")

    sl_rec = exits.build_exit_record(_fake_order(leg=("stop", "filled", 98.5)))
    if not (sl_rec and sl_rec["exit_reason"] == "STOP" and sl_rec["realized_pl"] == -15.0):
        print(f"  FAIL: SL exit record -> {sl_rec}"); ok = False
    else:
        print(f"  OK SL exit: {sl_rec['exit_reason']} ${sl_rec['realized_pl']} "
              f"({sl_rec['realized_pl_pct']}%)")

    if exits.build_exit_record(_fake_order(leg=("limit", "new", None))) is not None:
        print("  FAIL: open position should yield no exit record"); ok = False
    if exits.build_exit_record(_fake_order(entry_filled=False)) is not None:
        print("  FAIL: unfilled entry should yield no exit record"); ok = False
    print("  OK no-exit cases: still-open and entry-unfilled both -> None")

    print("  ALL OK" if ok else "  FAILURES above")
    return ok


def _live() -> None:
    print("\n[2] Live status (no side effects)")
    now = exits.now_et()
    print(f"  now (ET)         : {now:%Y-%m-%d %H:%M:%S %Z}")
    print(f"  entries allowed  : {exits.entries_allowed(now)} (cutoff {config.ENTRY_CUTOFF_ET})")
    print(f"  flatten due now  : {exits.past_flatten_time(now)} (flatten {config.FLATTEN_ET})")
    try:
        from bot import broker
        positions = broker.get_positions()
        print(f"  open positions   : {[p.symbol for p in positions] or 'none'}")
        print("  (flatten_all() would cancel orders + market-sell these as EOD_FLATTEN)")
    except Exception as exc:  # noqa: BLE001
        print(f"  could not read positions: {exc}")


def main() -> int:
    print("=" * 72)
    print("USTradeWisBot — Phase 7: exit management & end-of-day flatten")
    print("=" * 72)
    ok = _offline()
    _live()
    print("\n" + "=" * 72)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
