"""Unit tests for bot/replay.py — the pure simulation core, on synthetic bars
and on today's recorded WMT scenario (trade 54, 2026-06-11)."""

import datetime

import pandas as pd

from bot.replay import (
    bucket_vwap_distance,
    session_vwap,
    simulate_bracket,
    vwap_distance_rows,
)


def _bars(rows):
    """rows = [(high, low), ...] -> DataFrame like data.get_bars output."""
    return pd.DataFrame(
        [{"high": h, "low": lo} for h, lo in rows],
        index=pd.date_range("2026-06-11 09:30", periods=len(rows), freq="5min"),
    )


# Recorded WMT scenario: entry 120.56, stop 118.75, tp 123.27 (R = 1.81).
# Price peaked +1.05% (121.83 = +0.70R) at 13:30, faded, EOD-flattened 120.44.
WMT = dict(entry_price=120.56, stop_price=118.75, take_profit_price=123.27,
           fallback_exit_price=120.44)
WMT_BARS = _bars([(120.90, 120.30), (121.83, 120.70), (121.10, 120.20),
                  (120.80, 120.31)])


def test_wmt_baseline_replays_to_eod_flatten():
    sim = simulate_bracket(WMT_BARS, **WMT)
    assert sim.exit_reason == "EOD_FLATTEN"
    assert sim.exit_price == 120.44
    assert round(sim.mfe / (120.56 - 118.75), 2) == 0.70  # never reached +1R


def test_wmt_breakeven_at_1r_never_arms():
    sim = simulate_bracket(WMT_BARS, **WMT, breakeven_at_r=1.0)
    assert not sim.breakeven_armed
    assert sim.exit_reason == "EOD_FLATTEN"


def test_wmt_breakeven_at_half_r_saves_the_fade():
    sim = simulate_bracket(WMT_BARS, **WMT, breakeven_at_r=0.5)
    assert sim.breakeven_armed
    assert sim.exit_reason == "STOP"
    assert sim.exit_price == 120.56  # out at entry instead of riding to EOD


def test_stop_checked_before_target_within_a_bar():
    bars = _bars([(112.0, 98.0)])  # one wide bar touches both legs
    sim = simulate_bracket(bars, 100.0, 98.0, 110.0, fallback_exit_price=100.0)
    assert sim.exit_reason == "STOP"


def test_take_profit_hit():
    bars = _bars([(101.0, 99.5), (110.5, 100.5)])
    sim = simulate_bracket(bars, 100.0, 98.0, 110.0, fallback_exit_price=100.0)
    assert sim.exit_reason == "TAKE_PROFIT"
    assert sim.exit_price == 110.0


def test_breakeven_stop_does_not_trigger_same_bar_it_arms():
    # Bar 1 arms breakeven (+1R high) but its low stays above entry; bar 2
    # dips to entry -> stopped at breakeven, not at the original stop.
    bars = _bars([(102.5, 100.5), (101.0, 99.9)])
    sim = simulate_bracket(bars, 100.0, 98.0, 110.0,
                           fallback_exit_price=100.0, breakeven_at_r=1.0)
    assert sim.breakeven_armed
    assert sim.exit_reason == "STOP"
    assert sim.exit_price == 100.0


def test_mfe_mae_tracking():
    bars = _bars([(103.0, 99.0), (104.0, 101.0)])
    sim = simulate_bracket(bars, 100.0, 95.0, None, fallback_exit_price=102.0)
    assert sim.mfe == 4.0
    assert sim.mae == -1.0
    assert sim.exit_reason == "EOD_FLATTEN"


# --- Entry-vs-VWAP diagnostic (IMP-019) --------------------------------------

def _ohlcv(rows):
    """rows = [(high, low, close, volume), ...] -> full OHLCV DataFrame (ET)."""
    return pd.DataFrame(
        [{"high": h, "low": lo, "close": c, "volume": v} for h, lo, c, v in rows],
        index=pd.date_range("2026-07-16 09:30", periods=len(rows),
                            freq="5min", tz="America/New_York"),
    )


def test_session_vwap_is_volume_weighted():
    # bar1 typical=100 (vol 100); bar2 typical=102 (vol 300)
    # VWAP = (100*100 + 102*300) / 400 = 101.5
    bars = _ohlcv([(101, 99, 100, 100), (103, 101, 102, 300)])
    assert session_vwap(bars) == 101.5


def test_session_vwap_none_without_volume():
    assert session_vwap(_ohlcv([(101, 99, 100, 0)])) is None
    assert session_vwap(None) is None


# Today's AMZN (10:26 entry 255.38, full-1R STOP -$37.25) filled above its
# session VWAP — the open-fade case IMP-019 exists to bucket. AAPL (09:46 entry
# 329.27, +$32.32) held. A flat-VWAP synthetic reproduces both signs.
def test_vwap_distance_rows_and_bucketing():
    flat = _ohlcv([(100, 100, 100, 100)] * 3)  # session VWAP == 100.0
    all_bars = {"AMZN": flat, "AAPL": flat}
    trades = [
        dict(trade_id=1, symbol="AMZN", entry_price=100.5, realized_pl=-37.25,
             entry_time=datetime.datetime(2026, 7, 16, 9, 45)),   # +0.50% above VWAP
        dict(trade_id=2, symbol="AAPL", entry_price=99.8, realized_pl=32.32,
             entry_time=datetime.datetime(2026, 7, 16, 9, 45)),   # -0.20% below VWAP
    ]
    rows = vwap_distance_rows(trades, all_bars)
    by_id = {r["trade_id"]: r for r in rows}
    assert by_id[1]["dist_pct"] == 0.5 and by_id[1]["win"] is False
    assert by_id[2]["dist_pct"] == -0.2 and by_id[2]["win"] is True

    bands = bucket_vwap_distance(rows)
    top = bands[-1]                       # ">= +0.50%" band holds the AMZN fade
    assert top["n"] == 1 and top["total"] == -37.25 and top["win_pct"] == 0.0
    near = next(b for b in bands if b["label"] == "-0.25..+0.00%")
    assert near["n"] == 1 and near["total"] == 32.32
