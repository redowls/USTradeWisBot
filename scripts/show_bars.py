"""Phase 2 check (todo.md Phase 2 "Done when").

One call returns current 5-min bars for the whole watchlist, printed sanely.

Run from the project root:  python -m scripts.show_bars
"""

from __future__ import annotations

import sys

from bot import config, data


def main() -> int:
    print("=" * 64)
    print(f"USTradeWisBot — watchlist bars ({config.BAR_TIMEFRAME}, feed={config.DATA_FEED})")
    print("=" * 64)

    bars = data.get_watchlist_bars(n_bars=50)
    if not bars:
        print("No symbols in watchlist (run: python -m scripts.seed_watchlist)")
        return 1

    have_data = 0
    for symbol in sorted(bars):
        df = bars[symbol]
        if df.empty:
            print(f"\n{symbol:6s} — no bars returned")
            continue
        have_data += 1
        last = df.iloc[-1]
        first_ts = df.index[0].strftime("%Y-%m-%d %H:%M %Z")
        last_ts = df.index[-1].strftime("%Y-%m-%d %H:%M %Z")
        print(
            f"\n{symbol:6s} — {len(df):>3d} bars  [{first_ts} -> {last_ts}]\n"
            f"        last: O={last['open']:.2f} H={last['high']:.2f} "
            f"L={last['low']:.2f} C={last['close']:.2f} V={int(last['volume']):,}"
        )

    print("\n" + "=" * 64)
    print(f"RESULT: {have_data}/{len(bars)} symbols returned bars",
          "✅" if have_data == len(bars) else "⚠️")
    print("=" * 64)
    # Pass if every watchlist symbol returned data.
    return 0 if have_data == len(bars) else 1


if __name__ == "__main__":
    sys.exit(main())
