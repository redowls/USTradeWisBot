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

The regime is measured under TWO proxies — SPY and QQQ (both EMA9 on 5-min
bars) — so the review can see whether the gate's signal is robust to the proxy
choice or an artefact of one index (IMP-011's queued "compare EMA9 vs QQQ/VWAP
before any engine gate" step). If a single proxy swap flips a trade's regime,
the gate is not yet trustworthy.

Usage:
  python -m scripts.regime_analysis                    # all-time
  python -m scripts.regime_analysis --days 30          # last 30 days
  python -m scripts.regime_analysis --since 2026-06-15 # from a fixed date
"""

from __future__ import annotations

import sys
from datetime import date

import pandas as pd

from bot import analytics, config
from bot.indicators import ema

# Index proxies compared side by side (both EMA9 on 5-min bars). SPY is the
# primary (analytics.INDEX_REGIME_SYMBOL); QQQ cross-checks proxy-robustness.
PROXY_SYMBOLS = (analytics.INDEX_REGIME_SYMBOL, "QQQ")


def _index_regime_by_trade(rows: list[dict], symbol: str) -> dict[int, str]:
    """Tag each closed trade with `symbol`'s intraday regime at its entry minute."""
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
        symbol, n_bars=n_bars,
        timeframe=config.BAR_TIMEFRAME, regular_hours_only=True,
    )
    if spy is None or spy.empty:
        print(f"WARNING: no {symbol} bars returned — "
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


def _print_proxy(rows: list[dict], regime: dict[int, str], symbol: str) -> None:
    """Print one proxy's regime buckets + the skip-bearish what-if."""
    res = analytics.by_market_regime(rows, regime)
    buckets = res["buckets"]

    print(f"\n[{symbol} close vs EMA{analytics.INDEX_REGIME_EMA_SPAN}]")
    print(f"{'regime':9} {'trades':>6} {'win%':>6} {'total$':>10} {'exp$':>8} {'PF':>6}")
    for lbl in (analytics.REGIME_BULLISH, analytics.REGIME_BEARISH,
                analytics.REGIME_UNKNOWN):
        s = buckets.get(lbl)
        if not s:
            continue
        pf = "n/a" if s["profit_factor"] is None else f"{s['profit_factor']:.2f}"
        print(f"{lbl:9} {s['trades']:6d} {s['win_rate']:6.1f} "
              f"{s['total_pl']:+10.2f} {s['expectancy']:+8.2f} {pf:>6}")

    sk = res["skip_bearish"]
    print(f"  skip-bearish what-if: keep {sk['kept_trades']} (${sk['kept_total_pl']:+.2f}) "
          f"/ skip {sk['skipped_trades']} (${sk['skipped_total_pl']:+.2f} removed)")


def _print(since=None) -> int:
    label = "all time" if since is None else f"since {since}"
    rows = analytics.load_closed_trades(since=since)
    print("=" * 72)
    print(f"USTradeWisBot — market-regime entry analysis ({label})")
    print(f"(index close vs EMA{analytics.INDEX_REGIME_EMA_SPAN} on "
          f"{config.BAR_TIMEFRAME} bars, at each entry; proxies: "
          f"{', '.join(PROXY_SYMBOLS)})")
    print("=" * 72)
    if not rows:
        print("\nNo closed trades logged yet.")
        print("=" * 72)
        return 0

    regimes: dict[str, dict[int, str]] = {}
    for sym in PROXY_SYMBOLS:
        regimes[sym] = _index_regime_by_trade(rows, sym)
        _print_proxy(rows, regimes[sym], sym)

    # Proxy-robustness cross-check: how often SPY and QQQ agree on a trade's
    # regime. A gate whose signal survives only one proxy is not trustworthy.
    if len(PROXY_SYMBOLS) == 2:
        a, b = PROXY_SYMBOLS
        agr = analytics.regime_proxy_agreement(regimes[a], regimes[b])
        print(f"\nProxy agreement ({a} vs {b}): {agr['agree']}/{agr['trades']} "
              f"({agr['agree_pct']:.1f}%); {agr['disagree']} disagree")

    print("\nRead: the gate has signal only if BEARISH is materially worse than")
    print("BULLISH under BOTH proxies and 'skipped' P&L is net-negative. This is")
    print("measurement — a live gate is a separate, replay-validated IMP.")
    print("=" * 72)
    return 0


def main(argv: list[str]) -> int:
    usage = "usage: python -m scripts.regime_analysis [--days N | --since YYYY-MM-DD]"
    since = None
    if "--days" in argv:
        i = argv.index("--days")
        try:
            since = analytics.since_days(int(argv[i + 1]))
        except (IndexError, ValueError):
            print(usage)
            return 2
    elif "--since" in argv:
        i = argv.index("--since")
        try:
            since = date.fromisoformat(argv[i + 1])
        except (IndexError, ValueError):
            print(usage)
            return 2
    return _print(since=since)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
