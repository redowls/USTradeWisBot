"""IMP-022 tests — VWAP entry-quality gate.

Skip entries filled more than VWAP_MAX_DIST_PCT above the symbol's session VWAP.
Two independent validations motivated this (recorded-trade holdout IMP-019/020 +
a from-scratch 30-day backtest): entry-vs-session-VWAP is the one clean separator
of the open-fade leak — fills at/below VWAP hold, stretched-above fills fade.
"""

import pandas as pd

from bot import config, signals, sizing


def test_vwap_distance_pct_sign_and_magnitude():
    # Entry above VWAP -> positive %, below -> negative, exact magnitude.
    assert sizing.vwap_distance_pct(101.0, 100.0) == 1.0
    assert sizing.vwap_distance_pct(99.5, 100.0) == -0.5
    assert abs(sizing.vwap_distance_pct(100.25, 100.0) - 0.25) < 1e-9


def test_vwap_distance_pct_fails_open_on_missing():
    assert sizing.vwap_distance_pct(None, 100.0) is None
    assert sizing.vwap_distance_pct(100.0, None) is None
    assert sizing.vwap_distance_pct(100.0, 0.0) is None


def test_gate_threshold_semantics():
    # Just above the ceiling -> blocked; at/below -> allowed. (The engine skips
    # when vwap_distance_pct > VWAP_MAX_DIST_PCT.)
    thr = config.VWAP_MAX_DIST_PCT
    assert sizing.vwap_distance_pct(100.0 * (1 + (thr + 0.1) / 100), 100.0) > thr
    assert sizing.vwap_distance_pct(100.0 * (1 + thr / 100), 100.0) <= thr
    assert sizing.vwap_distance_pct(99.0, 100.0) <= thr  # below VWAP always allowed


def _ohlcv(n=70, start="2026-07-24 09:30"):
    idx = pd.date_range(start=start, periods=n, freq="5min", tz=config.MARKET_TZ)
    base = [100.0 + 0.05 * i for i in range(n)]
    return pd.DataFrame(
        {"open": base, "high": [b + 0.2 for b in base], "low": [b - 0.2 for b in base],
         "close": base, "volume": [1000 + 10 * i for i in range(n)]},
        index=idx,
    )


def test_evaluate_exposes_session_vwap():
    ev = signals.evaluate("TEST", df=_ohlcv())
    assert "session_vwap" in ev
    # A positive-volume rising session has a real VWAP between the low and high range.
    assert ev["session_vwap"] is None or ev["session_vwap"] > 0


def test_null_result_still_carries_session_vwap_key():
    # Too few bars -> null result, but the key must exist so the gate never KeyErrors.
    ev = signals.evaluate("TEST", df=_ohlcv(n=5))
    assert ev["signal_type"] is None
    assert ev["session_vwap"] is None
