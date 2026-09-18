"""Unit tests for bot/replay.py — the pure simulation core, on synthetic bars
and on today's recorded WMT scenario (trade 54, 2026-06-11)."""

import datetime

import pandas as pd

from bot.replay import (
    bucket_vwap_distance,
    session_vwap,
    simulate_bracket,
    vwap_distance_rows,
    vwap_skip_whatif,
    vwap_skip_whatif_split,
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


# Today's (2026-07-17, 0W/5L −$211.48) five real fills, ALL above session VWAP:
# CRM +0.68% −55.65 · MU +3.66% −0.35 · UNH +0.65% −40.02 · AMD +3.82% −115.32 ·
# AAPL +0.51% −0.14. The VWAP-skip what-if (pre-ship validation for the proposed
# ★★ gate, todo.md) must remove exactly the trades above the threshold and report
# an EXACT delta (recorded P&L of the skipped trades, no fill simulation).
TODAY_VWAP_ROWS = [
    dict(trade_id=167, symbol="CRM", dist_pct=0.68, pl=-55.65, win=False),
    dict(trade_id=168, symbol="MU", dist_pct=3.66, pl=-0.35, win=False),
    dict(trade_id=169, symbol="UNH", dist_pct=0.65, pl=-40.02, win=False),
    dict(trade_id=170, symbol="AMD", dist_pct=3.82, pl=-115.32, win=False),
    dict(trade_id=171, symbol="AAPL", dist_pct=0.51, pl=-0.14, win=False),
]


def test_vwap_skip_whatif_skips_every_above_vwap_fill_today():
    # At +0.50% every one of today's five fills is above threshold -> all skipped;
    # the book improves by the whole −$211.48 (exact recorded P&L, not a sim).
    r = vwap_skip_whatif(TODAY_VWAP_ROWS, 0.50)
    assert r["n_total"] == 5 and r["n_skipped"] == 5 and r["n_kept"] == 0
    assert r["skipped_pl"] == -211.48
    assert r["delta"] == 211.48                     # improvement from skipping
    assert abs(r["delta"]) > 55.81                  # clears the noise budget
    assert r["kept_pl"] == 0.0 and r["kept_win_pct"] == 0.0


def test_vwap_skip_whatif_partial_threshold_today():
    # At +1.0% only MU (+3.66%) and AMD (+3.82%) are skipped; CRM/UNH/AAPL kept.
    r = vwap_skip_whatif(TODAY_VWAP_ROWS, 1.0)
    assert r["n_kept"] == 3 and r["n_skipped"] == 2
    assert r["kept_pl"] == -95.81                   # CRM+UNH+AAPL
    assert r["skipped_pl"] == -115.67               # MU+AMD
    assert r["delta"] == 115.67
    assert r["skipped_win_pct"] == 0.0 and r["kept_win_pct"] == 0.0


def test_vwap_skip_whatif_empty_is_safe():
    r = vwap_skip_whatif([], 0.25)
    assert r["n_total"] == 0 and r["n_kept"] == 0 and r["n_skipped"] == 0
    assert r["delta"] == 0.0 and r["kept_win_pct"] == 0.0
    assert r["skipped_pl"] == 0.0 and r["kept_pl"] == 0.0


# --- IMP-021: held-out (out-of-sample) validation of the ★★ VWAP-skip gate -----
# Today (2026-07-20, 0W/4L −$87.86) is the first genuinely out-of-sample session
# after IMP-020's in-sample validation. Its four real fills, three of them AT or
# BELOW session VWAP (the "safe" side): QCOM −0.157% −40.32 · MU +0.035% −25.18 ·
# INTC −0.628% −22.12 · AVGO +0.27% −0.24. At the +0.25% gate only AVGO is above
# threshold, so the gate skips a −$0.24 scratch and KEEPS the three real losers —
# the held-out kept book stays net-negative. This is the step-(2) evidence the
# gate's "kept book flips positive" claim does not carry out of sample.
TODAY_20_ROWS = [
    dict(trade_id=172, symbol="QCOM", day="2026-07-20", dist_pct=-0.157, pl=-40.32, win=False),
    dict(trade_id=173, symbol="MU", day="2026-07-20", dist_pct=0.035, pl=-25.18, win=False),
    dict(trade_id=174, symbol="INTC", day="2026-07-20", dist_pct=-0.628, pl=-22.12, win=False),
    dict(trade_id=175, symbol="AVGO", day="2026-07-20", dist_pct=0.27, pl=-0.24, win=False),
]
# A couple of in-sample above-VWAP losers so the in-sample skip side is net-losing.
INSAMPLE_ROWS = [
    dict(trade_id=170, symbol="AMD", day="2026-07-17", dist_pct=3.82, pl=-115.32, win=False),
    dict(trade_id=169, symbol="UNH", day="2026-07-17", dist_pct=0.65, pl=-40.02, win=False),
    dict(trade_id=160, symbol="AAPL", day="2026-07-16", dist_pct=-0.20, pl=32.32, win=True),
]


def test_vwap_skip_whatif_split_holdout_today_kept_book_stays_negative():
    # split at today -> held-out is exactly today's four fills.
    res = vwap_skip_whatif_split(INSAMPLE_ROWS + TODAY_20_ROWS, 0.25, "2026-07-20")
    ho = res["held_out"]
    assert ho["n_total"] == 4
    assert ho["n_skipped"] == 1 and ho["n_kept"] == 3      # only AVGO (+0.27%) skipped
    assert ho["skipped_pl"] == -0.24                       # a scratch, not the losers
    assert ho["kept_pl"] == -87.62                         # QCOM+MU+INTC survive the gate
    # The skip side technically removed a (tiny) net-losing trade...
    assert res["held_out_removed_losers"] is True
    # ...but the stronger "kept book flips positive" claim FAILS out of sample.
    assert res["held_out_kept_positive"] is False
    # in-sample skip side is net-losing too, so the direction is consistent.
    assert res["generalizes"] is True


def test_vwap_skip_whatif_split_kept_book_flips_positive_when_holdout_losers_above_vwap():
    # A held-out window whose losers are all ABOVE VWAP and whose one winner is
    # below it: skipping the above-VWAP losers leaves a net-positive kept book.
    holdout = [
        dict(trade_id=200, symbol="AMD", day="2026-07-20", dist_pct=1.20, pl=-80.0, win=False),
        dict(trade_id=201, symbol="AAPL", day="2026-07-20", dist_pct=-0.10, pl=25.0, win=True),
    ]
    res = vwap_skip_whatif_split(INSAMPLE_ROWS + holdout, 0.25, "2026-07-20")
    ho = res["held_out"]
    assert ho["n_skipped"] == 1 and ho["kept_pl"] == 25.0
    assert res["held_out_kept_positive"] is True
    assert res["generalizes"] is True


def test_vwap_skip_whatif_split_empty_holdout_does_not_generalize():
    # split beyond every day -> held-out empty -> nothing removed, no generalisation.
    res = vwap_skip_whatif_split(INSAMPLE_ROWS, 0.25, "2099-01-01")
    assert res["held_out"]["n_total"] == 0
    assert res["held_out_removed_losers"] is False
    assert res["held_out_kept_positive"] is False
    assert res["generalizes"] is False
