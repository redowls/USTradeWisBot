"""Print review coverage — which recent sessions have a daily-review entry.

IMP-064. The instrument the 2026-09-26 weekly review did not have: it found the
09-22/23/24 gap only because the 09-25 daily review happened to notice it, four
days late. Run this to audit coverage directly.

    .venv/bin/python -m scripts.check_coverage [--lookback N] [--as-of YYYY-MM-DD]

`--as-of` replays any evening in the history (it is the `today` that `check()`
treats as not-yet-reviewable), which is how the alarm's behaviour on 09-22→09-25
was verified. Read-only: no DB writes, no orders, no Telegram.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime

from bot import coverage


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lookback", type=int, default=None,
                    help="completed sessions to audit (default: config)")
    ap.add_argument("--as-of", default=None,
                    help="replay a past evening, YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    today = (datetime.strptime(args.as_of, "%Y-%m-%d").date()
             if args.as_of else date.today())
    result = coverage.check(coverage.load_sessions(args.lookback),
                            coverage.read_review_text(),
                            today=today, lookback=args.lookback)

    print(f"as of {today}  (sessions dated {today} are exempt — that review is "
          f"written later the same night)")
    print(coverage.describe(result))
    if not result["ok"]:
        print("\nVERDICT: CANNOT CHECK — reporting 'covered' here would be a lie.")
        return 0

    # The table must show EXACTLY the window the verdict was computed over.
    # Printing every fetched session beside a windowed verdict is this repo's
    # recurring "two instruments, one verdict" defect (IMP-049/053/058/062), so
    # the window is derived here the same way `check()` derives it.
    print(f"\n{'session':<12}{'fills':>7}{'net $':>11}  review"
          f"   (window: last {result['sessions']} completed sessions)")
    reviewed = coverage.parse_reviewed_dates(coverage.read_review_text())
    missing_dates = {s["date"] for s in result["missing"]}
    completed = [s for s in coverage.sessions_from_summaries(
        coverage.load_sessions(args.lookback)) if s["date"] < today]
    for s in completed[-result["sessions"]:]:
        has = s["date"] in reviewed
        flag = "MISSING" if s["date"] in missing_dates else ("ok" if has else "?")
        print(f"{str(s['date']):<12}{'yes' if s['had_fills'] else '-':>7}"
              f"{s['net_pl']:>11.2f}  {flag}")

    print()
    if result["gapped"]:
        print(f"VERDICT: GAP — {result['stale']['date']} needs a review entry.")
    elif result["missing"]:
        print("VERDICT: COVERED at the newest session; older gaps listed above "
              "are backlog (they do not alarm).")
    else:
        print("VERDICT: FULLY COVERED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
