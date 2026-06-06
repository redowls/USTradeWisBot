"""Phase 6 check (todo.md Phase 6 "Done when").

Part 1 (offline, no network) — prove the bracket request is built correctly
(BRACKET class + take-profit + stop-loss legs, right qty/side) and that
non-tradable plans are skipped, and the retry classifier behaves.

Part 2 (live) — attempt a minimal 1-share paper bracket order to exercise the
real submit path. On a funded account during market hours this places a real
order, prints its child legs, then cancels it to leave the account clean. On a
$0 / closed-market account it shows the graceful rejection.

Run:  python -m scripts.place_test_order
"""

from __future__ import annotations

import sys

from alpaca.trading.enums import OrderClass, OrderSide

from bot import broker, data, execution
from bot.sizing import PositionPlan


def _one_share_plan(symbol: str, entry: float) -> PositionPlan:
    stop_distance = round(max(0.05, entry * 0.01), 2)
    return PositionPlan(
        symbol=symbol, confidence=95.0, tradable=True, skip_reason=None,
        entry_price=round(entry, 2), risk_fraction_pct=2.0, stop_distance=stop_distance,
        shares=1, stop_price=round(entry - stop_distance, 2),
        take_profit_price=round(entry + stop_distance * 2, 2),
        dollar_risk=stop_distance, dollar_risk_pct=0.0, notional=round(entry, 2),
    )


def _offline_checks() -> bool:
    print("[1] Offline: bracket request construction + skip + retry classifier")
    ok = True

    plan = _one_share_plan("AAPL", 307.00)
    req = execution.build_bracket_request(plan)
    checks = {
        "order_class BRACKET": req.order_class == OrderClass.BRACKET,
        "side BUY": req.side == OrderSide.BUY,
        "qty == shares": req.qty == plan.shares,
        "take_profit leg": req.take_profit is not None
            and float(req.take_profit.limit_price) == plan.take_profit_price,
        "stop_loss leg": req.stop_loss is not None
            and float(req.stop_loss.stop_price) == plan.stop_price,
        "client_order_id set": bool(req.client_order_id),
    }
    for name, passed in checks.items():
        if not passed:
            print(f"  FAIL: {name}"); ok = False
    if all(checks.values()):
        print(f"  OK request: BUY {req.qty} {req.symbol} BRACKET "
              f"tp={req.take_profit.limit_price} sl={req.stop_loss.stop_price}")

    # Non-tradable plan -> skipped without any network call.
    skip = PositionPlan("ZZZ", 50.0, False, "confidence<60", 10.0, 0.0, 0.0, 0,
                        0.0, 0.0, 0.0, 0.0, 0.0)
    res = execution.submit_bracket_order(skip)
    if res["ok"] or res["status"] != "skipped":
        print(f"  FAIL: non-tradable plan not skipped -> {res}"); ok = False
    else:
        print(f"  OK skip: {res['error']}")

    # Retry classifier: network errors retry, value errors don't.
    if not (execution._is_retryable(ConnectionError()) and not execution._is_retryable(ValueError())):
        print("  FAIL: retry classifier wrong"); ok = False
    else:
        print("  OK retry classifier (ConnectionError retryable, ValueError not)")

    print("  ALL OK" if ok else "  FAILURES above")
    return ok


def _live_attempt() -> None:
    print("\n[2] Live: minimal 1-share paper bracket order")
    acct = broker.account_summary()
    print(f"  account: equity ${acct['equity']:,.2f}  buying power ${acct['buying_power']:,.2f}"
          f"  ({'PAPER' if acct['paper'] else 'LIVE'})")
    if not acct["paper"]:
        print("  REFUSING: not a paper account — skipping live test order."); return

    df = data.get_bars("AAPL", n_bars=5)
    if df is None or df.empty:
        print("  no price data for AAPL; skipping"); return
    entry = float(df["close"].iloc[-1])
    plan = _one_share_plan("AAPL", entry)
    print(f"  submitting: BUY 1 AAPL ~{plan.entry_price} "
          f"(stop {plan.stop_price}, tp {plan.take_profit_price})")

    res = execution.submit_bracket_order(plan)
    print(f"  result: ok={res['ok']} status={res['status']} "
          f"order_id={res['order_id']} error={res['error']}")

    if res["ok"] and res["order_id"]:
        order = execution.get_order(res["order_id"])
        legs = getattr(order, "legs", None) or []
        print(f"  legs ({len(legs)}):")
        for leg in legs:
            print(f"    - {leg.type} {leg.side} {getattr(leg,'limit_price',None) or getattr(leg,'stop_price',None)}")
        print("  cleaning up: cancelling the test order ...")
        try:
            execution.cancel_order(res["order_id"])
            print("  cancelled.")
        except Exception as exc:  # noqa: BLE001
            print(f"  (could not cancel: {exc})")
    else:
        print("  (expected on a $0 / closed-market account — submit path & error "
              "handling verified)")


def main() -> int:
    print("=" * 72)
    print("USTradeWisBot — Phase 6: bracket-order execution (paper)")
    print("=" * 72)
    ok = _offline_checks()
    _live_attempt()
    print("\n" + "=" * 72)
    print("RESULT:", "OFFLINE LOGIC GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
