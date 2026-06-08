"""Phase 8 check (todo.md Phase 8 "Done when").

Writes simulated trades + signals + exits to the live SQL Server, verifies the
full lifecycle and the daily_summary aggregation, prints the rows (SSMS-style),
then deletes everything it created. Uses a sentinel order-id prefix and an old
sentinel trade_date so it never touches real data.

Run:  python -m scripts.check_logging
"""

from __future__ import annotations

import sys
from datetime import date, datetime

from bot import db, logbook
from bot.sizing import PositionPlan

TEST_DATE = date(1990, 1, 2)
TAG = "TESTLOG-"


def _plan(symbol, entry, stop, tp, shares) -> PositionPlan:
    return PositionPlan(
        symbol=symbol, confidence=0.0, tradable=True, skip_reason=None,
        entry_price=entry, risk_fraction_pct=1.0, stop_distance=round(entry - stop, 2),
        shares=shares, stop_price=stop, take_profit_price=tp,
        dollar_risk=0.0, dollar_risk_pct=0.0, notional=entry * shares,
    )


def _cleanup():
    db.execute(f"DELETE FROM signals WHERE trade_id IN "
               f"(SELECT trade_id FROM trades WHERE alpaca_order_id LIKE '{TAG}%')")
    db.execute("DELETE FROM signals WHERE trade_id IS NULL AND CAST(ts AS DATE) = ?", [TEST_DATE])
    db.execute(f"DELETE FROM trades WHERE alpaca_order_id LIKE '{TAG}%'")
    db.execute("DELETE FROM daily_summary WHERE trade_date = ?", [TEST_DATE])


def main() -> int:
    print("=" * 72)
    print("USTradeWisBot — Phase 8: database logging & daily summary")
    print("=" * 72)
    _cleanup()  # start clean
    ok = True

    # --- standalone signal (didn't become a trade) ---
    sig_only = {"symbol": "AAPL", "signal_type": "BREAKOUT", "breakout_score": 0.5,
                "ma_score": 0.0, "value_score": 1.0, "momentum_score": 0.3,
                "regime_ok": True, "broke_level": 305.0}
    sid = logbook.log_signal(sig_only, confidence=40.0,
                             ts=datetime(1990, 1, 2, 9, 45))
    print(f"[1] standalone signal logged: signal_id={sid}")

    # --- trade 1: AAPL winner (take-profit) ---
    ev1 = {"symbol": "AAPL", "signal_type": "BOTH", "breakout_score": 0.9,
           "ma_score": 0.8, "value_score": 1.0, "momentum_score": 0.6,
           "regime_ok": True, "broke_level": 300.0}
    t1 = logbook.record_entry(ev1, _plan("AAPL", 300.0, 297.0, 306.0, 10),
                              {"order_id": f"{TAG}1"}, confidence=85.0,
                              entry_time=datetime(1990, 1, 2, 10, 0))
    logbook.record_exit({"entry_order_id": f"{TAG}1", "exit_price": 306.0,
                         "exit_time": datetime(1990, 1, 2, 11, 0),
                         "exit_reason": "TAKE_PROFIT", "realized_pl": 60.0,
                         "realized_pl_pct": 2.0})

    # --- trade 2: NVDA loser (stop) ---
    ev2 = {"symbol": "NVDA", "signal_type": "MA", "breakout_score": 0.0,
           "ma_score": 0.7, "value_score": 0.9, "momentum_score": 0.4,
           "regime_ok": True, "broke_level": None}
    t2 = logbook.record_entry(ev2, _plan("NVDA", 200.0, 198.0, 204.0, 5),
                              {"order_id": f"{TAG}2"}, confidence=65.0,
                              entry_time=datetime(1990, 1, 2, 10, 30))
    logbook.record_exit({"entry_order_id": f"{TAG}2", "exit_price": 198.0,
                         "exit_time": datetime(1990, 1, 2, 12, 0),
                         "exit_reason": "STOP", "realized_pl": -10.0,
                         "realized_pl_pct": -1.0})
    print(f"[2] recorded 2 trades (AAPL t={t1} TP, NVDA t={t2} STOP) + their signals")

    # --- verify trade rows ---
    tr1, tr2 = logbook.get_trade(t1), logbook.get_trade(t2)
    if not (tr1["status"] == "CLOSED" and float(tr1["realized_pl"]) == 60.0
            and tr1["exit_reason"] == "TAKE_PROFIT"):
        print(f"  FAIL: trade 1 wrong -> {tr1}"); ok = False
    if not (tr2["status"] == "CLOSED" and float(tr2["realized_pl"]) == -10.0
            and tr2["exit_reason"] == "STOP"):
        print(f"  FAIL: trade 2 wrong -> {tr2}"); ok = False

    # --- verify signals linked ---
    linked = db.query("SELECT trade_id, signal_type, confidence FROM signals "
                      "WHERE trade_id IN (?, ?) ORDER BY trade_id", [t1, t2])
    if len(linked) != 2:
        print(f"  FAIL: expected 2 linked signals, got {len(linked)}"); ok = False

    # --- daily summary ---
    summ = logbook.write_daily_summary(TEST_DATE, equity_open=10_000.0, equity_close=10_050.0)
    checks = {
        "num_buys==2": summ["num_buys"] == 2,
        "num_sells==2": summ["num_sells"] == 2,
        "wins==1": summ["wins"] == 1,
        "losses==1": summ["losses"] == 1,
        "gross_pl==50": float(summ["gross_pl"]) == 50.0,
        "pct==0.5": abs(float(summ["realized_pl_pct"]) - 0.5) < 1e-6,
        "symbols both": "AAPL" in summ["symbols_traded"] and "NVDA" in summ["symbols_traded"],
    }
    for name, passed in checks.items():
        if not passed:
            print(f"  FAIL: daily summary {name} -> {summ}"); ok = False

    # --- print SSMS-style ---
    print("\n[3] trades:")
    for t in db.query(f"SELECT trade_id, symbol, qty, entry_price, exit_price, "
                      f"realized_pl, realized_pl_pct, status, exit_reason FROM trades "
                      f"WHERE alpaca_order_id LIKE '{TAG}%' ORDER BY trade_id"):
        print(f"   {t}")
    print("\n[3] signals (linked):")
    for s in db.query("SELECT signal_id, trade_id, symbol, signal_type, confidence, "
                      "breakout_score, ma_score FROM signals WHERE trade_id IN (?, ?) "
                      "ORDER BY trade_id", [t1, t2]):
        print(f"   {s}")
    print("\n[3] daily_summary:")
    print(f"   {logbook.get_daily_summary(TEST_DATE)}")

    _cleanup()  # leave no trace
    leftover = db.query_one(f"SELECT COUNT(*) AS c FROM trades WHERE alpaca_order_id LIKE '{TAG}%'")
    if leftover["c"] != 0:
        print(f"  FAIL: cleanup left {leftover['c']} rows"); ok = False
    else:
        print("\n[4] cleanup OK — all test rows removed")

    print("\n" + "=" * 72)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
