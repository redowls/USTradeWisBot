"""Unit tests for bot.entry_lab — the option-B entry rebuild's backtest gate.

Pure and network-free. They pin: each candidate rule fires once per event (not
on every bar that sits above a level), the doctrine bucketing in R, the walker's
caps / cooldown / slippage / fill-anchored stop, the chronological walk-forward
split, and the gate's refusal reasons.
"""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from bot import config, entry_lab


def _session(day: str, closes, highs=None, lows=None, vols=None, opens=None) -> pd.DataFrame:
    """One RTH session of 5-min bars from 09:30; defaults derive H/L from close."""
    n = len(closes)
    idx = pd.date_range(start=f"{day} 09:30", periods=n, freq="5min", tz=config.MARKET_TZ)
    closes = np.asarray(closes, dtype=float)
    highs = closes + 0.2 if highs is None else np.asarray(highs, dtype=float)
    lows = closes - 0.2 if lows is None else np.asarray(lows, dtype=float)
    opens = closes if opens is None else np.asarray(opens, dtype=float)
    vols = np.full(n, 1000.0) if vols is None else np.asarray(vols, dtype=float)
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": vols}, index=idx)


def _flat(n: int, level: float = 100.0):
    return [level] * n


# --- rules --------------------------------------------------------------------

def test_orb_fires_once_on_the_first_close_above_the_range():
    closes = _flat(78)
    closes[5] = 101.0        # first close above the 3-bar OR high (100.2) at bar 5
    closes[6] = 101.5        # still above: must NOT re-trigger
    closes[10] = 100.0
    closes[11] = 101.0       # a fresh cross later in the session DOES trigger again
    f = entry_lab.precompute_features(_session("2026-08-03", closes))
    trig = entry_lab.rule_orb(f, {"k": 3, "cutoff": "13:00", "min_relvol": 0.0, "above_vwap": False})
    fired = list(np.flatnonzero(trig.to_numpy()))
    assert fired == [5, 11]


def test_orb_respects_bar_index_cutoff_and_relvol():
    closes = _flat(78)
    closes[2] = 105.0        # inside the 6-bar OR window: never an ORB trigger
    closes[7] = 106.0        # first bar after OR → candidate
    vols = [1000.0] * 78
    vols[7] = 1000.0         # relvol == 1.0 → fails a 1.3 floor
    f = entry_lab.precompute_features(_session("2026-08-03", closes, vols=vols))
    assert not entry_lab.rule_orb(f, {"k": 6, "min_relvol": 0.0, "above_vwap": False}).iloc[2]
    assert entry_lab.rule_orb(f, {"k": 6, "min_relvol": 0.0, "above_vwap": False}).iloc[7]
    assert not entry_lab.rule_orb(f, {"k": 6, "min_relvol": 1.3, "above_vwap": False}).iloc[7]
    late = entry_lab.rule_orb(f, {"k": 6, "cutoff": "10:00", "min_relvol": 0.0, "above_vwap": False})
    assert not late.iloc[7]  # 10:05 ET is past a 10:00 cutoff


def test_pdh_needs_a_prior_day_and_a_fresh_cross_not_a_gap():
    d1 = _session("2026-08-03", _flat(78, 100.0))          # yesterday's high = 100.2
    c2 = _flat(78, 99.0)
    c2[4] = 100.5                                           # crosses PDH at bar 4
    c2[5] = 100.6                                           # holds above: no re-trigger
    d2 = _session("2026-08-04", c2)
    c3 = _flat(78, 102.0)                                   # gaps above day-2 high, never crosses
    d3 = _session("2026-08-05", c3)
    f = entry_lab.precompute_features(pd.concat([d1, d2, d3]))
    trig = entry_lab.rule_pdh(f, {"min_relvol": 0.0, "above_vwap": False})
    fired = list(np.flatnonzero(trig.to_numpy()))
    assert fired == [78 + 4]
    assert f["pdh"].iloc[0] != f["pdh"].iloc[0]              # NaN on the first session


def test_session_high_break_requires_a_base_first():
    closes = _flat(78)
    closes[3] = 103.0            # early spike sets the session high (103.2)
    closes[20] = 104.0           # 16 bars later: new high after a base → trigger
    closes[21] = 105.0           # immediately again: no base (high moved 1 bar ago) → no trigger
    f = entry_lab.precompute_features(_session("2026-08-03", closes))
    trig = entry_lab.rule_session_high(f, {"consol_bars": 6, "min_bar_idx": 6, "min_relvol": 0.0,
                                           "above_vwap": False})
    fired = list(np.flatnonzero(trig.to_numpy()))
    assert fired == [20]


def test_vwap_reclaim_needs_touch_then_cross_above_ema8_in_uptrend():
    # Rising tape so VWAP rises and EMA20 > EMA55; a dip touches VWAP then resumes.
    base = np.linspace(100.0, 106.0, 78)
    closes = base.copy()
    lows = closes - 0.2
    closes[30:34] -= 1.2          # pullback below the fast EMA
    lows[30:34] = closes[30:34] - 0.9   # low reaches down to VWAP
    f = entry_lab.precompute_features(_session("2026-08-03", closes, lows=lows))
    trig = entry_lab.rule_vwap_reclaim(f, {"touch_pct": 0.25, "lookback": 6, "min_relvol": 0.0})
    fired = list(np.flatnonzero(trig.to_numpy()))
    assert fired, "expected a reclaim trigger after the pullback"
    assert all(i >= 34 for i in fired), fired
    # Without any VWAP touch there is nothing to reclaim.
    g = entry_lab.precompute_features(_session("2026-08-03", base))
    assert not entry_lab.rule_vwap_reclaim(g, {"touch_pct": 0.05, "lookback": 6}).any()


def test_market_overlay_is_spy_above_its_vwap():
    closes = _flat(78, 100.0)
    closes[10] = 90.0
    spy = entry_lab.precompute_features(_session("2026-08-03", closes))
    ok = entry_lab.market_ok(spy)
    assert not ok.iloc[10] and ok.iloc[11]


# --- doctrine -------------------------------------------------------------------

@pytest.mark.parametrize("reason,r,expected", [
    ("TAKE_PROFIT", 1.5, "WIN"),
    ("EOD_FLATTEN", 1.2, "WIN"),
    ("STOP", -1.0, "FAIL"),
    ("STOP", 0.0, "FAIL"),          # break-even stop is a failed trade
    ("STOP", 0.25, "FAIL"),
    ("STOP", 0.5, "SCRATCH"),
    ("EOD_FLATTEN", 0.5, "SCRATCH"),
    ("EOD_FLATTEN", -0.25, "SCRATCH"),
    ("EOD_FLATTEN", -0.6, "FAIL"),
])
def test_doctrine_bucket(reason, r, expected):
    assert entry_lab.doctrine_bucket(reason, r) == expected


def _trade(pl, r, reason="STOP", when="2026-08-03 10:00"):
    ts = pd.Timestamp(when, tz=config.MARKET_TZ).to_pydatetime()
    return entry_lab.LabTrade("t", "X", when[:10], ts, ts, 100.0, 98.5, 102.25, 100.0 + r * 1.5,
                              10, reason, pl, r)


def test_doctrine_metrics_true_wr_payoff_and_drawdown():
    trades = [
        _trade(30.0, 1.5, "TAKE_PROFIT", "2026-08-03 10:00"),
        _trade(-15.0, -1.0, "STOP", "2026-08-03 11:00"),
        _trade(-15.0, -1.0, "STOP", "2026-08-03 12:00"),
        _trade(0.5, 0.0, "STOP", "2026-08-04 10:00"),      # break-even: sign-positive, doctrine FAIL
        _trade(7.5, 0.5, "STOP", "2026-08-04 11:00"),      # SCRATCH
    ]
    m = entry_lab.doctrine_metrics(trades)
    assert m["n"] == 5 and m["win"] == 1 and m["scratch"] == 1 and m["fail"] == 3
    assert m["true_wr"] == 20.0 and m["headline_wr"] == 60.0
    assert m["stop_rate"] == 80.0
    assert m["max_dd"] == -30.0            # +30 peak, then -15 -15
    assert m["exp_r"] == pytest.approx(0.0, abs=1e-9)
    assert m["payoff"] == pytest.approx((30 + 0.5 + 7.5) / 3 / 15.0, abs=0.01)   # rounded to 2dp
    assert entry_lab.doctrine_metrics([])["n"] == 0


# --- walker -------------------------------------------------------------------

def test_walker_caps_entries_applies_cooldown_slippage_and_fill_anchored_stop(monkeypatch):
    # Every bar triggers; the tape falls 3% right after each entry so each trade
    # stops out on the next bar. The daily cap (2) and the 30-min cooldown must
    # hold, the fill must be slipped, and the stop must sit 1R below the FILL.
    monkeypatch.setattr(config, "MAX_ENTRIES_PER_SYMBOL_PER_DAY", 2)
    monkeypatch.setattr(config, "REENTRY_COOLDOWN_MIN", 30)
    closes = [100.0, 100.0, 100.0, 97.0, 97.0, 97.0, 97.0, 97.0, 97.0, 97.0, 97.0, 94.0] + [94.0] * 66
    lows = [c - 0.1 for c in closes]
    lows[3] = 96.0
    lows[11] = 93.0
    f = entry_lab.precompute_features(_session("2026-08-03", closes, lows=lows))
    f["atr"] = 0.1                                   # tiny ATR → the 1.5% floor sets 1R
    trig = pd.Series(True, index=f.index)
    trades = entry_lab.walk_symbol("t", "AAPL", f, trig, {date(2026, 8, 3)}, 10_000.0, slippage_pct=0.1)
    assert len(trades) == 2
    first, second = trades
    assert first.entry_time == f.index[1]            # bar 0 (09:30) is never an entry
    assert first.entry_price == pytest.approx(100.0 * 1.001)
    assert first.stop_price == pytest.approx(first.entry_price - first.entry_price / 1.001 * 0.015, rel=1e-6)
    # The stop fill pays the slip too: exit = stop*(1-0.001) → a hair worse than -1R.
    expected_r = (first.stop_price * (1 - 0.001) - first.entry_price) / (first.entry_price - first.stop_price)
    assert first.exit_reason == "STOP" and first.profit_r == pytest.approx(expected_r, abs=1e-3)
    assert -1.10 < first.profit_r < -1.0
    # Cooldown: exit at bar 3 (09:45) → next entry no earlier than 10:15 = bar 9.
    assert second.entry_time >= first.exit_time + pd.Timedelta(minutes=30)
    assert (second.entry_time - f.index[0]).total_seconds() / 60 >= 45


def test_run_rule_applies_max_concurrent_across_symbols(monkeypatch):
    monkeypatch.setattr(config, "MAX_CONCURRENT_POSITIONS", 1)
    feats = {}
    for sym in ("A", "B"):
        closes = [100.0] * 78
        f = entry_lab.precompute_features(_session("2026-08-03", closes))
        f["atr"] = 0.1
        feats[sym] = f
    fn = lambda f, p: pd.Series([i == 5 for i in range(len(f))], index=f.index)   # noqa: E731
    trades = entry_lab.run_rule("t", fn, {}, feats, [date(2026, 8, 3)], 10_000.0)
    assert len(trades) == 1          # both symbols trigger at 09:55; only one slot


# --- walk-forward + gate ------------------------------------------------------------

def test_split_sessions_is_chronological_and_disjoint():
    days = [date(2026, 8, d) for d in range(3, 23)]
    is_days, oos_days = entry_lab.split_sessions(days, 0.65)
    assert is_days == days[:13] and oos_days == days[13:]
    assert not set(is_days) & set(oos_days)
    assert entry_lab.split_sessions([date(2026, 8, 3)], 0.65) == ([date(2026, 8, 3)], [])


def test_param_grid_is_the_full_cartesian_product():
    g = entry_lab.param_grid({"a": [1, 2], "b": ["x", "y", "z"]})
    assert len(g) == 6 and {"a": 2, "b": "z"} in g


def test_gate_lists_every_refusal_reason():
    good = {"n": 40, "exp_r": 0.2, "pf": 1.5}
    ok, why = entry_lab.gate(good, {"exp_r": 0.1}, {"n": 50, "exp_r": -0.1})
    assert ok and why == []
    bad = {"n": 10, "exp_r": -0.05, "pf": 0.8}
    ok, why = entry_lab.gate(bad, {"exp_r": -0.2}, {"n": 50, "exp_r": 0.0})
    assert not ok and len(why) == 5
    ok, why = entry_lab.gate(good, None, {"n": 50, "exp_r": 0.3})
    assert not ok and "incumbent" in why[0]


def test_select_in_sample_prefers_expectancy_among_qualifying_sets(monkeypatch):
    monkeypatch.setattr(entry_lab, "MIN_TRADES_IS", 1)
    calls = []

    def fake_run(rule, fn, params, feats, sessions, equity, slip, mkt):
        calls.append(params["x"])
        r = {1: 0.1, 2: 0.3, 3: -0.2}[params["x"]]
        return [_trade(r * 15, r, "EOD_FLATTEN")]

    monkeypatch.setattr(entry_lab, "run_rule", fake_run)
    best, m, rows = entry_lab.select_in_sample("t", None, {"x": [1, 2, 3]}, {}, [], 1.0, 0.0, None)
    assert best == {"x": 2} and m["exp_r"] == pytest.approx(0.3) and len(rows) == 3
    assert calls == [1, 2, 3]
