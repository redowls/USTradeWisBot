"""Phase 9 check (todo.md Phase 9 "Done when").

Sends one of each alert type (heartbeat / entry / exit / daily summary / error)
to the configured Telegram chat and confirms the API accepted each. You should
see five messages on your phone.

Run:  python -m scripts.check_notify
"""

from __future__ import annotations

import sys
from datetime import date

from bot import notify, secrets
from bot.sizing import PositionPlan


def main() -> int:
    print("=" * 64)
    print("USTradeWisBot — Phase 9: Telegram alerts")
    print("=" * 64)

    if not secrets.telegram_configured():
        print("FAIL: Telegram not configured (need TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env)")
        return 1
    print(f"chat id: {secrets.TELEGRAM_CHAT_ID}\n")

    plan = PositionPlan(
        symbol="AAPL", confidence=85.0, tradable=True, skip_reason=None,
        entry_price=307.50, risk_fraction_pct=1.5, stop_distance=3.0, shares=10,
        stop_price=304.50, take_profit_price=313.50, dollar_risk=30.0,
        dollar_risk_pct=1.5, notional=3075.0,
    )
    evaluation = {"symbol": "AAPL", "signal_type": "BOTH"}
    exit_record = {"symbol": "AAPL", "qty": 10, "exit_price": 313.50,
                   "realized_pl": 60.0, "realized_pl_pct": 1.95, "exit_reason": "TAKE_PROFIT"}
    summary = {"trade_date": date(2026, 6, 8), "num_buys": 2, "num_sells": 2,
               "wins": 1, "losses": 1, "gross_pl": 50.0, "realized_pl_pct": 0.5,
               "equity_open": 10000.0, "equity_close": 10050.0, "symbols_traded": "AAPL,NVDA"}

    results = {
        "heartbeat": notify.heartbeat("USTradeWisBot Phase 9 test — bot is alive"),
        "entry_alert": notify.entry_alert(plan, evaluation, confidence=85.0),
        "exit_alert": notify.exit_alert(exit_record),
        "daily_summary": notify.daily_summary_alert(summary),
        "error_alert": notify.error_alert("This is a test error alert (ignore)."),
    }

    ok = True
    for name, sent in results.items():
        print(f"  {name:16} {'sent ✅' if sent else 'FAILED ❌'}")
        ok = ok and sent

    print("\n" + "=" * 64)
    print("RESULT:", "ALL SENT ✅ (check your phone)" if ok else "FAILURES ❌")
    print("=" * 64)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
