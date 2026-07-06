"""Market-regime entry analysis (todo.md backlog ★ — the top strategy lever).

The entire all-time bleed lives in STOP exits / false breakouts (PF ~0.01) and no
pre-trade SCORE discriminates them (confidence IMP-004, volume 2026-06-26,
entry-extension IMP-007 all refuted). The one lever left is MARKET-LEVEL: only
take longs when the index (SPY) is itself trending up intraday. This script is the
FIRST measurement of that hypothesis (the measurement-first pattern of
IMP-004/006/007, before any engine change): it fetches the SPY 5-min series,
tags every closed trade with the index regime at its entry minute (SPY close vs a
short intraday EMA), and reports P&L by regime plus a "skip bearish entries"
what-if.

This is a STANDALONE analysis tool — it is deliberately NOT wired into
`scripts/report.py`, so its network dependency (fetching SPY bars) can never break
the always-on incubation report.

Caveat: the tag uses the index bar whose start <= entry time (the "current" 5-min
bar), so on the first bar of the session it reads a not-yet-complete bar — a small
lookahead acceptable for a directional regime read, not a live gate. A live gate
(a future IMP) must use only completed bars.

Usage:
  python -m scripts.regime_analysis            # all-time
  python -m scripts.regime_analysis --days 30  # last 30 days
"""

from __future__ import annotations

import sys

import pandas as pd

from bot import analytics, config
from bot.indicators import ema


def _index_regime_by_trade(rows: list[dict]) -> dict[int, str]:
    """Tag each closed trade with the SPY intraday regime at its entry minute."""
    if not rows:
        return {}

    # One continuous SPY 5-min RTH series covering the whole trade window. ~78
    # bars/day; fetch generously so the earliest trade date is covered.
    span_days = 1
    try:
        first = min(r["entry_time"] for r in rows if r.get("entry_time"))
        last = max(r["entry_time"] for r in rows if r.get("entry_time"))
        span_days = max(1, (last.date() - first.date()).days + 3)
    except (ValueError, TypeError):
        pass
    n_bars = min(10000, span_days * 80 + 200)

    from bot import data
    spy = data.get_bars(
        analytics.INDEX_REGIME_SYMBOL, n_bars=n_bars,
        timeframe=config.BAR_TIMEFRAME, regular_hours_only=True,
    )
    if spy is None or spy.empty:
        print(f"WARNING: no {analytics.INDEX_REGIME_SYMBOL} bars returned — "
              "every trade tagged 'unknown' (fail-open).")
        return {}

    spy = spy.sort_index()
    spy_ema = ema(spy["close"], analytics.INDEX_REGIME_EMA_SPAN)
    idx = spy.index

    regime: dict[int, str] = {}
    for r in rows:
        et = r.get("entry_time")
        tid = r.get("trade_id")
        if et is None or tid is None:
            continue
        ts = pd.Timestamp(et)
        if ts.tzinfo is None:
            ts = ts.tz_localize(config.MARKET_TZ)
        # last SPY bar whose start <= entry time
        pos = idx.searchsorted(ts, side="right") - 1
        if pos < 0:
            regime[tid] = analytics.REGIME_UNKNOWN
            continue
        price = spy["close"].iloc[pos]
        ema_val = spy_ema.iloc[pos]
        regime[tid] = analytics.classify_index_regime(
            None if pd.isna(price) else float(price),
            None if pd.isna(ema_val) else float(ema_val),
        )
    return regime


def _print(since=None) -> int:
    label = "all time" if since is None else f"since {since}"
    rows = analytics.load_closed_trades(since=since)
    print("=" * 72)
    print(f"USTradeWisBot — market-regime entry analysis ({label})")
    print(f"(SPY close vs EMA{analytics.INDEX_REGIME_EMA_SPAN} on "
          f"{config.BAR_TIMEFRAME} bars, at each entry)")
    print("=" * 72)
    if not rows:
        print("\nNo closed trades logged yet.")
        print("=" * 72)
        return 0

    regime = _index_regime_by_trade(rows)
    res = analytics.by_market_regime(rows, regime)
    buckets = res["buckets"]

    print(f"\n{'regime':9} {'trades':>6} {'win%':>6} {'total$':>10} {'exp$':>8} {'PF':>6}")
    for lbl in (analytics.REGIME_BULLISH, analytics.REGIME_BEARISH,
                analytics.REGIME_UNKNOWN):
        s = buckets.get(lbl)
        if not s:
            continue
        pf = "n/a" if s["profit_factor"] is None else f"{s['profit_factor']:.2f}"
        print(f"{lbl:9} {s['trades']:6d} {s['win_rate']:6.1f} "
              f"{s['total_pl']:+10.2f} {s['expectancy']:+8.2f} {pf:>6}")

    sk = res["skip_bearish"]
    print("\nWhat-if — skip every BEARISH-regime entry (keep bullish + unknown):")
    print(f"  kept    : {sk['kept_trades']:3d} trades, ${sk['kept_total_pl']:+.2f}")
    print(f"  skipped : {sk['skipped_trades']:3d} trades, ${sk['skipped_total_pl']:+.2f} "
          "(P&L removed if the gate were live)")
    print("\nRead: the gate has signal only if BEARISH is materially worse than")
    print("BULLISH and 'skipped' P&L is net-negative. This is measurement, not a")
    print("code change — a live gate is a separate, replay-validated IMP.")
    print("=" * 72)
    return 0


def main(argv: list[str]) -> int:
    since = None
    if "--days" in argv:
        i = argv.index("--days")
        try:
            since = analytics.since_days(int(argv[i + 1]))
        except (IndexError, ValueError):
            print("usage: python -m scripts.regime_analysis [--days N]")
            return 2
    return _print(since=since)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
