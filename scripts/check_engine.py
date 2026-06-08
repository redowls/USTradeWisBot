"""Phase 10 check (todo.md Phase 10 "Done when").

Exercises the wired main loop safely in DRY-RUN (no orders placed, no DB writes):
  - live market clock fetch + is_market_open
  - entry-cutoff gating (no entries at/after 15:30 ET)
  - a full dry-run entry tick at a forced 10:00 ET: ingest -> evaluate -> score
    -> size, returning the actions it WOULD take
  - manage_exits() runs cleanly with no open trades
  - a dry-run flatten tick at 15:56 ET

Run:  python -m scripts.check_engine
"""

from __future__ import annotations

import sys
from datetime import datetime

from bot import broker, config
from bot.engine import Engine


def _et(h: int, m: int) -> datetime:
    return datetime(2026, 6, 8, h, m, tzinfo=config.MARKET_TZ)


def main() -> int:
    print("=" * 72)
    print("USTradeWisBot — Phase 10: scheduler / main loop (dry-run)")
    print("=" * 72)
    ok = True
    eng = Engine(dry_run=True)

    # 1. Live market clock.
    print("[1] Market clock")
    try:
        clock = broker.get_clock()
        print(f"  is_open={clock.is_open}  next_open={clock.next_open}  next_close={clock.next_close}")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: clock fetch: {exc}"); ok = False

    # 2. Entry-cutoff gating.
    print("\n[2] Entry-cutoff gating")
    after = eng.consider_entries(_et(16, 0))
    if after != []:
        print(f"  FAIL: entries returned after cutoff -> {after}"); ok = False
    else:
        print("  OK: no entries considered at 16:00 ET (past 15:30 cutoff)")

    # 3. Full dry-run entry tick at 10:00 ET.
    print("\n[3] Dry-run entry tick @ 10:00 ET (ingest->evaluate->score->size)")
    try:
        actions = eng.consider_entries(_et(10, 0))
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: consider_entries raised: {exc}"); ok = False
        actions = None
    if actions is not None:
        bad = [a for a in actions if a["action"] not in ("skip", "would_buy")]
        if bad:
            print(f"  FAIL: dry-run took live actions -> {bad}"); ok = False
        would_buy = [a for a in actions if a["action"] == "would_buy"]
        skips = [a for a in actions if a["action"] == "skip"]
        print(f"  evaluated; {len(would_buy)} would-buy, {len(skips)} skipped "
              f"(on a $0 paper account, skips are expected)")
        for a in (would_buy or skips)[:5]:
            print(f"    {a}")

    # 4. manage_exits with no open trades.
    print("\n[4] manage_exits (no open trades)")
    try:
        recs = eng.manage_exits()
        print(f"  OK: {len(recs)} exit records")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: manage_exits raised: {exc}"); ok = False

    # 5. Dry-run flatten tick at 15:56 ET.
    print("\n[5] Dry-run tick @ 15:56 ET (should attempt flatten, not entries)")
    try:
        eng.tick(_et(15, 56))
        print(f"  OK: flatten path exercised (flattened_on={eng.flattened_on})")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: flatten tick raised: {exc}"); ok = False

    print("\n" + "=" * 72)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
