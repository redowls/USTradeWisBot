"""Backfill trades.stop_raises / final_stop_price from the rotating bot log (IMP-043).

IMP-043 makes the ratchet durable going forward, but every arming event ALREADY
recorded lives only in `STOP RAISED` lines inside /var/log/ustradewisbot/bot.log,
which logrotate keeps for 14 days. IMP-040's live window opened 2026-08-25 and
its verdict is due ~2026-09-08 — by which time the era's opening sessions have
rotated out. This script recovers what is still on disk before that happens.

A `STOP RAISED` line is ground truth about the past regardless of what geometry
produced it, so the whole retained window is backfilled, not just the IMP-040 era.

Idempotent: each run RECOMPUTES both columns from the logs rather than
incrementing, so running it twice cannot double-count. Trades whose arming
events have already rotated away are left untouched (not zeroed) — see
--report for how many those are.

Usage:
  python -m scripts.backfill_stop_raises --dry-run   # show what would change
  python -m scripts.backfill_stop_raises             # write
  python -m scripts.backfill_stop_raises --report    # coverage only, no writes
"""

from __future__ import annotations

import argparse
import glob
import gzip
import re
import sys
from collections import defaultdict
from datetime import datetime

from bot import db

LOG_GLOB = "/var/log/ustradewisbot/bot.log*"

# 2026-08-27 10:04:41 EDT | STOP RAISED INTC 88.14 -> 89.60 (live 89.82, ...)
LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s*\|\s*"
    r"STOP RAISED\s+(?P<symbol>[A-Z.]+)\s+"
    r"(?P<frm>\d+(?:\.\d+)?)\s*->\s*(?P<to>\d+(?:\.\d+)?)"
)


def _open(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", errors="replace")
    return open(path, "r", errors="replace")


def parse_raises(paths=None) -> list[tuple[datetime, str, float]]:
    """Every (timestamp, symbol, new_stop) STOP RAISED event on disk, deduped.

    logrotate uses copytruncate, so an event can appear in both the live file and
    a rotated one. (ts, symbol, new_stop) is the natural key: the ratchet is
    strictly monotone per trade, so two genuine raises never share both a
    timestamp and a stop price.
    """
    paths = sorted(glob.glob(LOG_GLOB)) if paths is None else list(paths)
    seen: set[tuple[str, str, float]] = set()
    out: list[tuple[datetime, str, float]] = []
    for path in paths:
        try:
            with _open(path) as fh:
                for line in fh:
                    m = LINE_RE.match(line.strip())
                    if not m:
                        continue
                    key = (m["ts"], m["symbol"], float(m["to"]))
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append((
                        datetime.strptime(m["ts"], "%Y-%m-%d %H:%M:%S"),
                        m["symbol"],
                        float(m["to"]),
                    ))
        except OSError as exc:
            print(f"  ! skipped {path}: {exc}")
    out.sort(key=lambda r: r[0])
    return out


def attribute(events, trades) -> dict[int, list[tuple[datetime, float]]]:
    """Map each raise onto the trade that was open when it happened.

    Log timestamps are ET wall clock and trades.entry_time/exit_time are stored
    naive ET, so they compare directly. A raise belongs to the trade in that
    symbol whose [entry_time, exit_time] window contains it; an unmatched event
    is reported rather than silently dropped.
    """
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        by_symbol[t["symbol"].upper()].append(t)

    matched: dict[int, list[tuple[datetime, float]]] = defaultdict(list)
    unmatched: list[tuple[datetime, str, float]] = []
    for ts, symbol, new_stop in events:
        hit = None
        for t in by_symbol.get(symbol, ()):
            entry, exit_ = t["entry_time"], t["exit_time"]
            if entry is None or ts < entry:
                continue
            if exit_ is not None and ts > exit_:
                continue
            hit = t
            break
        if hit is None:
            unmatched.append((ts, symbol, new_stop))
        else:
            matched[int(hit["trade_id"])].append((ts, new_stop))
    return matched, unmatched


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="show changes, write nothing")
    ap.add_argument("--report", action="store_true", help="coverage only, write nothing")
    args = ap.parse_args(argv)

    events = parse_raises()
    if not events:
        print("No STOP RAISED events found on disk — nothing to backfill.")
        return 0
    print(f"Parsed {len(events)} STOP RAISED events "
          f"({events[0][0].date()} .. {events[-1][0].date()})")

    trades = db.query(
        "SELECT trade_id, symbol, entry_time, exit_time, stop_price, "
        "final_stop_price, stop_raises, exit_reason FROM trades ORDER BY entry_time"
    )
    matched, unmatched = attribute(events, trades)
    print(f"Attributed to {len(matched)} trades; {len(unmatched)} unmatched events")
    for ts, symbol, new_stop in unmatched[:10]:
        print(f"  ? {ts} {symbol} -> {new_stop} (no open trade covers this instant)")

    by_id = {int(t["trade_id"]): t for t in trades}
    changes = []
    for trade_id, raises in sorted(matched.items()):
        raises.sort(key=lambda r: r[0])
        count, final = len(raises), raises[-1][1]
        cur = by_id[trade_id]
        cur_final = None if cur["final_stop_price"] is None else float(cur["final_stop_price"])
        if int(cur["stop_raises"]) == count and cur_final == final:
            continue
        changes.append((trade_id, cur["symbol"], count, final))

    if args.report:
        covered = sum(1 for t in trades if int(t["trade_id"]) in matched)
        print(f"\nCoverage: {covered}/{len(trades)} trades have retained arming events.")
        return 0

    print(f"\n{len(changes)} trades to update:")
    for trade_id, symbol, count, final in changes:
        print(f"  #{trade_id} {symbol:<5} stop_raises={count:<3} final_stop_price={final}")
    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    for trade_id, _symbol, count, final in changes:
        db.execute(
            "UPDATE trades SET stop_raises = ?, final_stop_price = ? WHERE trade_id = ?",
            [count, final, trade_id],
        )
    print(f"\nWrote {len(changes)} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
