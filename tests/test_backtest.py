"""Unit tests for the from-scratch backtest engine (bot.backtest).

Cover the pure, network-free pieces: the bracket exit simulation (stop-before-
target, IMP-013 breakeven→trail ratchet, EOD fallback) and the MAX_CONCURRENT
interval scheduler. The signal-generation path is exercised live by
`scripts.backtest`; here we pin the deterministic mechanics.
"""

from datetime import datetime, timedelta

import pandas as pd

from bot import backtest, config


def _bars(rows, start="2026-07-24 10:00"):
    """rows = list of (low, high, close); index = 5-min ET bars."""
    idx = pd.date_range(start=start, periods=len(rows), freq="5min", tz=config.MARKET_TZ)
    return pd.DataFrame(
        {"low": [r[0] for r in rows], "high": [r[1] for r in rows],
         "close": [r[2] for r in rows]},
        index=idx,
    )


def test_stop_is_checked_before_target_within_a_bar():
    # A bar whose range spans BOTH the stop and the target must exit STOP (conservative).
    bars = _bars([(98.0, 105.0, 100.0)])
    price, reason, _ = backtest.simulate_exit(bars, entry=100.0, initial_stop=99.0,
                                              take_profit=104.0, eod_close=101.0)
    assert reason == "STOP" and price == 99.0


def test_take_profit_when_only_target_touched():
    bars = _bars([(100.5, 104.5, 103.0)])
    price, reason, _ = backtest.simulate_exit(bars, entry=100.0, initial_stop=99.0,
                                              take_profit=104.0, eod_close=101.0)
    assert reason == "TAKE_PROFIT" and price == 104.0


def test_eod_flatten_when_neither_leg_triggers():
    bars = _bars([(100.1, 101.0, 100.5), (100.2, 101.2, 100.8)])
    price, reason, ts = backtest.simulate_exit(bars, entry=100.0, initial_stop=99.0,
                                               take_profit=110.0, eod_close=100.8)
    assert reason == "EOD_FLATTEN" and price == 100.8 and ts is not None


def test_breakeven_ratchet_locks_a_scratch_not_a_full_loss():
    # entry 100, initial stop 99 (1R = 1.0). Bar1 high 100.6 = +0.6R -> stop to entry(100).
    # Bar2 dips to 99.5: with breakeven the stop is now 100, so it exits at 100 (scratch),
    # NOT at the original 99. Confirms the IMP-013 breakeven moved the stop.
    bars = _bars([(100.1, 100.6, 100.4), (99.5, 100.2, 99.8)])
    price, reason, _ = backtest.simulate_exit(bars, entry=100.0, initial_stop=99.0,
                                              take_profit=110.0, eod_close=99.8)
    assert reason == "STOP" and price == 100.0


def _tr(sym, e_h, x_h, pl=1.0):
    """Build a BtTrade with entry/exit at given hours on the same day."""
    base = datetime(2026, 7, 24, 0, 0)
    return backtest.BtTrade(
        symbol=sym, day="2026-07-24", entry_time=base + timedelta(hours=e_h),
        exit_time=base + timedelta(hours=x_h), entry_price=100.0, exit_price=101.0,
        shares=10, confidence=70.0, exit_reason="TAKE_PROFIT", pl=pl,
    )


def test_concurrency_drops_the_fourth_overlapping_entry():
    # Four trades all open 10:00–12:00; MAX_CONCURRENT=3 admits only the first three.
    trades = [_tr("A", 10, 12), _tr("B", 10, 12), _tr("C", 10, 12), _tr("D", 10, 12)]
    kept = backtest.apply_concurrency(trades, max_concurrent=3)
    assert {t.symbol for t in kept} == {"A", "B", "C"}


def test_concurrency_admits_when_a_slot_frees_up():
    # Three overlap early; a fourth starts after one has exited -> admitted.
    trades = [_tr("A", 10, 10.5), _tr("B", 10, 12), _tr("C", 10, 12), _tr("D", 11, 12)]
    kept = backtest.apply_concurrency(trades, max_concurrent=3)
    assert "D" in {t.symbol for t in kept} and len(kept) == 4
