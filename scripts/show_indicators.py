"""Phase 3 check (todo.md Phase 3 "Done when").

Two parts:
  1. Math sanity checks on synthetic series (no network) — validates the
     indicator formulas against known-answer cases.
  2. Real data: print current EMAs, ATR, RSI, ADX, relative volume and a short
     list of S/R levels with touch counts for a few sample symbols.

Run from the project root:  python -m scripts.show_indicators
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from bot import config, data, indicators, levels


def _sanity_checks() -> bool:
    print("[1] Indicator math sanity checks")
    ok = True

    # EMA of a constant series is that constant.
    const = pd.Series([5.0] * 50)
    if not np.isclose(indicators.ema(const, 10).iloc[-1], 5.0):
        print("  FAIL: EMA of constant != constant"); ok = False

    # RSI of a strictly rising series -> 100 (no losses).
    rising = pd.Series(np.arange(1, 60, dtype=float))
    if not np.isclose(indicators.rsi(rising).iloc[-1], 100.0):
        print("  FAIL: RSI of rising series != 100"); ok = False

    # RSI of a strictly falling series -> 0 (no gains).
    falling = pd.Series(np.arange(60, 1, -1, dtype=float))
    if not np.isclose(indicators.rsi(falling).iloc[-1], 0.0, atol=1e-6):
        print(f"  FAIL: RSI of falling series != 0 (got {indicators.rsi(falling).iloc[-1]})"); ok = False

    # ATR is positive for a series with real range.
    rng = pd.DataFrame({
        "high": np.arange(10, 60, dtype=float) + 1,
        "low": np.arange(10, 60, dtype=float) - 1,
        "close": np.arange(10, 60, dtype=float),
    })
    if not indicators.atr(rng).iloc[-1] > 0:
        print("  FAIL: ATR not positive on ranging series"); ok = False

    # ADX of a clean uptrend should be high (strong trend).
    adx_val = indicators.adx(rng)[0].iloc[-1]
    if not adx_val > 20:
        print(f"  FAIL: ADX of clean trend too low ({adx_val:.1f})"); ok = False

    # Pivot detection: a single obvious peak is found as resistance.
    piv = pd.DataFrame({
        "high": [1, 2, 3, 10, 3, 2, 1],
        "low":  [1, 1, 1, 1, 1, 1, 1],
    }, index=pd.date_range("2026-01-01", periods=7, freq="5min", tz=config.MARKET_TZ))
    res, _ = levels.find_pivots(piv, lookback=3)
    if not (len(res) == 1 and np.isclose(res[0][0], 10.0)):
        print(f"  FAIL: pivot detection missed the peak ({res})"); ok = False

    print("  OK" if ok else "  FAILURES above")
    return ok


def _real_data(sample: list[str], n_bars: int = 120) -> bool:
    print(f"\n[2] Live indicators & S/R ({config.BAR_TIMEFRAME}, last {n_bars} bars)")
    bars = data.get_bars_for_symbols(sample, n_bars=n_bars)
    any_ok = False
    for symbol in sample:
        df = bars.get(symbol)
        if df is None or df.empty:
            print(f"\n{symbol}: no data"); continue
        any_ok = True
        snap = indicators.snapshot(df)
        sr = levels.support_resistance(df)
        print(f"\n{symbol}  (close {snap['close']:.2f}, {len(df)} bars)")
        print(f"  EMA short 8/10/20 : {snap['ema_8']:.2f} / {snap['ema_10']:.2f} / {snap['ema_20']:.2f}"
              f"   stacked={'Y' if snap['ema_8']>snap['ema_10']>snap['ema_20'] else 'N'}")
        print(f"  EMA long 21/34/55 : {snap['ema_21']:.2f} / {snap['ema_34']:.2f} / {snap['ema_55']:.2f}"
              f"   stacked={'Y' if snap['ema_21']>snap['ema_34']>snap['ema_55'] else 'N'}")
        print(f"  ATR={snap['atr']:.2f}  RSI={snap['rsi']:.1f}  ADX={snap['adx']:.1f}"
              f"  (+DI={snap['plus_di']:.1f}/-DI={snap['minus_di']:.1f})  relVol={snap['rel_vol']:.2f}")
        res = sr["resistance"][-4:]
        sup = sr["support"][:4]
        print("  resistance: " + (", ".join(f"{l.price:.2f}(x{l.touches})" for l in res) or "—"))
        print("  support   : " + (", ".join(f"{l.price:.2f}(x{l.touches})" for l in sup) or "—"))
    return any_ok


def main() -> int:
    print("=" * 64)
    print("USTradeWisBot — Phase 3: indicators & support/resistance")
    print("=" * 64)
    ok = _sanity_checks()
    ok = _real_data(["AAPL", "NVDA", "TSLA"]) and ok
    print("\n" + "=" * 64)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 64)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
