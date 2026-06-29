"""Incubation report (todo.md Phase 12).

Prints the paper-incubation metrics from the logged trades/signals/daily_summary
so you can decide — after several weeks of paper sessions — whether the strategy
is worth taking live. Read summary.md §10/§12 first: paper overstates live, the
edge is fragile, and the base rate is humbling.

Usage:
  python -m scripts.report              # all-time
  python -m scripts.report --days 30    # last 30 days
  python -m scripts.report --selftest   # verify the metric math (no DB writes)
"""

from __future__ import annotations

import sys

from bot import analytics


def _print_report(since=None) -> int:
    label = "all time" if since is None else f"since {since}"
    print("=" * 72)
    print(f"USTradeWisBot — incubation report ({label})")
    print("=" * 72)

    rows = analytics.load_closed_trades(since)
    m = analytics.compute_metrics(rows)

    if m["trades"] == 0:
        print("\nNo closed trades logged yet.")
        print("Fund the paper account, enable the service, and let it run some "
              "sessions — then re-run this report.")
        print("=" * 72)
        return 0

    print(f"\nClosed trades : {m['trades']}  (wins {m['wins']} / losses {m['losses']})")
    print(f"Win rate      : {m['win_rate']}%")
    print(f"Total P&L     : ${m['total_pl']:+,.2f}")
    print(f"Expectancy    : ${m['expectancy']:+.2f} per trade")
    print(f"Avg P&L %     : {m['avg_pl_pct']:+.3f}%")
    print(f"Avg win/loss  : ${m['avg_win']:+.2f} / ${m['avg_loss']:+.2f}")
    print(f"Profit factor : {m['profit_factor']}")
    print(f"False-breakout: {m['false_breakout_rate']}%  (breakouts that stopped out)")
    print(f"Exit reasons  : {m['exit_reasons']}")

    def _pf(s):
        return "  n/a" if s["profit_factor"] is None else f"{s['profit_factor']:5.2f}"

    print("\nBy signal type:")
    print(f"  {'type':9} {'trades':>6} {'win%':>6} {'total$':>10} {'exp$':>8} {'PF':>6}")
    for st, s in m["by_signal_type"].items():
        print(f"  {st:9} {s['trades']:6d} {s['win_rate']:6.1f} "
              f"{s['total_pl']:10.2f} {s['expectancy']:8.2f} {_pf(s):>6}")

    print("\nBy confidence band:")
    print(f"  {'band':9} {'trades':>6} {'win%':>6} {'total$':>10} {'exp$':>8} {'PF':>6}")
    for band, s in m["by_confidence_band"].items():
        if s["trades"] == 0:
            continue
        print(f"  {band:9} {s['trades']:6d} {s['win_rate']:6.1f} "
              f"{s['total_pl']:10.2f} {s['expectancy']:8.2f} {_pf(s):>6}")

    print("\nBy exit reason:")
    print(f"  {'reason':12} {'trades':>6} {'win%':>6} {'total$':>10} {'exp$':>8} {'PF':>6}")
    for er, s in m.get("by_exit_reason", {}).items():
        print(f"  {er:12} {s['trades']:6d} {s['win_rate']:6.1f} "
              f"{s['total_pl']:10.2f} {s['expectancy']:8.2f} {_pf(s):>6}")

    ext = m.get("by_entry_extension", {})
    if ext:
        print("\nBy entry extension (breakout fills, % above broken level):")
        print(f"  {'band':9} {'trades':>6} {'win%':>6} {'total$':>10} {'exp$':>8} {'PF':>6}")
        for band, s in ext.items():
            if s["trades"] == 0:
                continue
            print(f"  {band:9} {s['trades']:6d} {s['win_rate']:6.1f} "
                  f"{s['total_pl']:10.2f} {s['expectancy']:8.2f} {_pf(s):>6}")

    summaries = analytics.load_daily_summaries(since)
    if summaries:
        print("\nDaily summaries:")
        print(f"  {'date':12} {'in':>3} {'out':>3} {'W':>3} {'L':>3} {'gross$':>10} {'day%':>7} {'equity_close':>13}")
        for d in summaries:
            print(f"  {str(d['trade_date']):12} {d['num_buys']:3d} {d['num_sells']:3d} "
                  f"{d['wins']:3d} {d['losses']:3d} {float(d['gross_pl'] or 0):10.2f} "
                  f"{float(d['realized_pl_pct'] or 0):7.3f} {float(d['equity_close'] or 0):13.2f}")

    print("\nVerdict: " + analytics.incubation_verdict(m))
    print("(Tooling only — the go-live call is yours, per summary §12.)")
    print("=" * 72)
    return 0


def _selftest() -> int:
    print("[selftest] verifying compute_metrics on synthetic trades")
    rows = [
        {"realized_pl": 60.0, "realized_pl_pct": 2.0, "exit_reason": "TAKE_PROFIT", "signal_type": "BOTH"},
        {"realized_pl": -10.0, "realized_pl_pct": -1.0, "exit_reason": "STOP", "signal_type": "MA"},
        {"realized_pl": 30.0, "realized_pl_pct": 1.0, "exit_reason": "TAKE_PROFIT", "signal_type": "BREAKOUT"},
        {"realized_pl": -20.0, "realized_pl_pct": -1.0, "exit_reason": "STOP", "signal_type": "BREAKOUT"},
    ]
    m = analytics.compute_metrics(rows)
    checks = {
        "trades==4": m["trades"] == 4,
        "win_rate==50": m["win_rate"] == 50.0,
        "total_pl==60": m["total_pl"] == 60.0,
        "expectancy==15": m["expectancy"] == 15.0,
        # breakout/both = 3 trades (BOTH, BREAKOUT, BREAKOUT); 1 stopped out -> 33.3%
        "false_breakout==33.3": m["false_breakout_rate"] == 33.3,
        "profit_factor==3": m["profit_factor"] == 3.0,  # 90 / 30
        "verdict insufficient": "INSUFFICIENT" in analytics.incubation_verdict(m),
    }
    ok = True
    for name, passed in checks.items():
        print(f"  {'OK' if passed else 'FAIL'}: {name}")
        ok = ok and passed
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    return 0 if ok else 1


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        return _selftest()
    since = None
    if "--days" in args:
        since = analytics.since_days(int(args[args.index("--days") + 1]))
    return _print_report(since)


if __name__ == "__main__":
    sys.exit(main())
