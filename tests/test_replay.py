"""Unit tests for bot/replay.py — the pure simulation core, on synthetic bars
and on today's recorded WMT scenario (trade 54, 2026-06-11)."""

import pandas as pd

from bot.replay import simulate_bracket


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
