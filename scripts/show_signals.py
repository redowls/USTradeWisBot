"""Phase 4 check (todo.md Phase 4 "Done when").

Part 1 — synthetic scenarios with known answers that prove the engine flags
breakout / MA / over-extension correctly.
Part 2 — evaluate the live watchlist and print each symbol's component scores +
signal classification.

Run from the project root:  python -m scripts.show_signals
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from bot import config, indicators, signals


def make_df(closes, volumes=None, spread=0.25) -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame with an ET index from a close series."""
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    if volumes is None:
        volumes = np.full(n, 1000.0)
    idx = pd.date_range("2026-06-01 09:30", periods=n, freq="5min", tz=config.MARKET_TZ)
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes + spread,
            "low": closes - spread,
            "close": closes,
            "volume": np.asarray(volumes, dtype=float),
        },
        index=idx,
    )


def _scenarios() -> bool:
    print("[1] Synthetic scenarios (known answers)")
    ok = True

    # (a) Fresh resistance breakout: oscillate under ~100, then close above on volume.
    osc = 98 + 2 * np.sin(np.arange(60) * 2 * np.pi / 8)
    ramp = [98.0, 98.5, 99.5, 100.0, 102.0]
    closes = np.concatenate([osc, ramp])
    vols = np.concatenate([np.full(64, 1000.0), [3500.0]])
    res = signals.evaluate("TEST_BO", df=make_df(closes, vols))
    if not (res["breakout_score"] > 0 and res["signal_type"] in ("BREAKOUT", "BOTH")
            and res["broke_level"] and abs(res["broke_level"] - 100) < 1.0):
        print(f"  FAIL: breakout not detected -> {res}"); ok = False
    else:
        print(f"  OK breakout: score={res['breakout_score']} type={res['signal_type']} "
              f"level={res['broke_level']}")

    # (b) Clean uptrend -> short EMA set stacked -> high ma_score.
    up = make_df(np.linspace(90, 110, 60))
    comp_up = indicators.compute(up)
    ma = signals.ma_score(comp_up)
    if not ma > 0.8:
        print(f"  FAIL: uptrend ma_score too low ({ma})"); ok = False
    else:
        print(f"  OK MA alignment: ma_score={ma:.2f}")

    # (c) Downtrend -> no MA signal, no buy classification.
    down = signals.evaluate("TEST_DN", df=make_df(np.linspace(110, 90, 60)))
    if not (down["ma_score"] == 0.0 and down["signal_type"] is None):
        print(f"  FAIL: downtrend produced a signal -> {down}"); ok = False
    else:
        print(f"  OK downtrend: ma_score=0, signal_type=None")

    # (d) Over-extension: consolidation near the EMA (moderate RSI, small
    # distance) is better value than a vertical spike far above it (high RSI).
    base = 100 + 0.5 * np.sin(np.arange(56) * 2 * np.pi / 8)
    consolidating = make_df(base)
    extended = make_df(np.concatenate([base, [103, 107, 113, 121]]))
    v_consol = signals.value_score(indicators.compute(consolidating), consolidating)
    v_ext = signals.value_score(indicators.compute(extended), extended)
    if not (v_consol > v_ext and 0 <= v_ext <= 1 and 0 <= v_consol <= 1):
        print(f"  FAIL: value scoring off (consol={v_consol:.2f} extended={v_ext:.2f})"); ok = False
    else:
        print(f"  OK over-extension: value consol={v_consol:.2f} > extended={v_ext:.2f}")

    print("  ALL OK" if ok else "  FAILURES above")
    return ok


def _live() -> bool:
    print("\n[2] Live watchlist evaluation")
    results = signals.evaluate_watchlist()
    if not results:
        print("  no watchlist data"); return False

    header = f"  {'SYM':6} {'bo':>5} {'ma':>5} {'val':>5} {'mom':>5} {'reg':>4} {'mult':>4}  {'type':8} broke"
    print(header)
    print("  " + "-" * (len(header) - 2))
    signals_fired = 0
    for r in sorted(results, key=lambda x: x["symbol"]):
        if r["signal_type"]:
            signals_fired += 1
        broke = f"{r['broke_level']:.2f}" if r["broke_level"] else "—"
        print(f"  {r['symbol']:6} {r['breakout_score']:5.2f} {r['ma_score']:5.2f} "
              f"{r['value_score']:5.2f} {r['momentum_score']:5.2f} "
              f"{('Y' if r['regime_ok'] else 'N'):>4} {r['regime_multiplier']:4.1f}  "
              f"{str(r['signal_type'] or '—'):8} {broke}")
    print(f"\n  {signals_fired}/{len(results)} symbols currently flag a signal "
          f"(data is last session; market may be closed).")
    return True


def main() -> int:
    print("=" * 72)
    print("USTradeWisBot — Phase 4: signal engine")
    print("=" * 72)
    ok = _scenarios()
    ok = _live() and ok
    print("\n" + "=" * 72)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
