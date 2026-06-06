"""Phase 1 smoke test (todo.md Phase 1 "Done when").

Verifies the full skeleton end-to-end:
  1. Secrets load from .env (fail fast if missing).
  2. Alpaca paper account is reachable -> prints equity & buying power.
  3. SQL Server is reachable and the seeded watchlist reads back.

Run from the project root:  python -m scripts.smoke_test
Exit code 0 = all green.
"""

from __future__ import annotations

import sys

from bot import broker, db, secrets


def check_alpaca() -> bool:
    print("\n[Alpaca]")
    try:
        acct = broker.account_summary()
    except Exception as exc:  # noqa: BLE001 - smoke test surfaces any failure
        print(f"  FAIL: {exc}")
        return False
    mode = "PAPER" if acct["paper"] else "LIVE"
    print(f"  mode          : {mode}")
    print(f"  account       : {acct['account_number']} ({acct['status']})")
    print(f"  equity        : {acct['currency']} {acct['equity']:,.2f}")
    print(f"  buying power  : {acct['currency']} {acct['buying_power']:,.2f}")
    if not acct["paper"]:
        print("  WARNING: not on paper. ALPACA_PAPER should be true until Phase 12.")
    return True


def check_database() -> bool:
    print("\n[SQL Server]")
    try:
        if not db.ping():
            print("  FAIL: ping did not return expected result")
            return False
        print(f"  connected     : {secrets.DB_USER}@{secrets.DB_SERVER}/{secrets.DB_NAME}")
        rows = db.get_active_watchlist()
        print(f"  watchlist     : {len(rows)} active symbols")
        if rows:
            print("    " + ", ".join(r["symbol"] for r in rows))
        else:
            print("    (empty — run: python -m scripts.seed_watchlist)")
        return len(rows) > 0
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: {exc}")
        return False


def main() -> int:
    print("=" * 60)
    print("USTradeWisBot — Phase 1 smoke test")
    print("=" * 60)
    ok = check_alpaca()
    ok = check_database() and ok
    print("\n" + "=" * 60)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
