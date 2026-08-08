"""Tests for bot/exit_sim.py — the two-stage stop ratchet replay (IMP-028).

The regression fixtures are the two REAL trades that motivated the module:
2026-08-07 META #233 and NVDA #232. Both armed the live break-even stop, both
gave back their entire open profit, and the pre-IMP-028 static-bracket model in
bot/replay.py scores both as full-1R losses. Bar paths below are the actual
5-minute highs/lows for each trade's session window (Alpaca IEX bars).
"""

from __future__ import annotations

import pandas as pd
import pytest

from bot import config, exits
from bot.exit_sim import (
    ExitGeometry,
    giveback_rows,
    ratchet_stop,
    replay_geometry,
    simulate_exit,
)


def _bars(pairs: list[tuple[float, float]]) -> pd.DataFrame:
    """(high, low) pairs -> the DataFrame shape simulate_exit consumes."""
    return pd.DataFrame({"high": [p[0] for p in pairs],
                         "low": [p[1] for p in pairs]})


LIVE = ExitGeometry.from_config()

# --- 2026-08-07 META #233: entry 590.40, plan stop 582.73 (1R = 7.67) --------
# Peak 598.64 at 10:59 ET = +1.07R, i.e. it CLEARED the 1.0R trail trigger.
# Exited 14:46 via the break-even stop for -$0.08 on qty 4.
META_ENTRY, META_STOP, META_QTY = 590.40, 582.73, 4
META_TP = 604.91
META_BARS = _bars([
    (590.48, 589.96), (590.42, 589.45), (592.70, 589.71), (594.15, 591.73),
    (593.61, 592.33), (595.05, 592.52), (596.39, 594.63), (597.66, 595.93),
    (597.85, 596.23), (597.78, 596.09), (598.64, 597.30), (598.56, 596.99),
    (597.54, 596.61), (597.73, 596.59),
    (594.00, 590.30),          # the 14:46 fade back through the entry-level stop
])

# --- 2026-08-07 NVDA #232: entry 221.82, plan stop 218.46 (1R = 3.36) -------
# Peak 224.76 at 11:34 ET = +0.88R — never reached the 1.0R trail trigger.
# Exited 13:00 via the break-even stop for -$0.11 on qty 11.
NVDA_ENTRY, NVDA_STOP, NVDA_QTY = 221.82, 218.46, 11
NVDA_TP = 226.78
NVDA_BARS = _bars([
    (221.93, 221.57), (222.53, 221.32), (222.60, 221.81), (223.17, 222.21),
    (222.83, 221.77), (222.78, 221.93), (222.80, 221.75), (222.31, 220.94),
    (222.34, 221.22), (222.44, 221.86), (223.45, 221.99), (223.58, 222.78),
    (223.46, 222.80), (224.76, 223.90),
    (222.50, 221.72),          # the 13:00 fade back through the entry-level stop
])


# --- The ratchet must not drift away from the live implementation -----------

@pytest.mark.parametrize("live_price", [218.00, 221.82, 223.00, 223.50, 224.76,
                                        225.50, 228.00, 232.00])
def test_ratchet_matches_live_compute_trailed_stop(live_price):
    """ExitGeometry.from_config() must reproduce exits.compute_trailed_stop exactly.

    exit_sim re-implements the ratchet with explicit parameters (the live one
    reads config globals, so it cannot answer "what would a different trail have
    done?"). This is the guard that keeps the two from silently diverging.
    """
    assert ratchet_stop(NVDA_ENTRY, NVDA_STOP, NVDA_STOP, live_price, LIVE) == \
        exits.compute_trailed_stop(NVDA_ENTRY, NVDA_STOP, NVDA_STOP, live_price)


def test_ratchet_disabled_returns_none():
    geo = ExitGeometry(0.5, 1.0, 1.0, 0.10, trailing_enabled=False)
    assert ratchet_stop(NVDA_ENTRY, NVDA_STOP, NVDA_STOP, 230.0, geo) is None


def test_ratchet_rejects_non_positive_risk():
    assert ratchet_stop(100.0, 100.0, 100.0, 120.0, LIVE) is None


# --- The structural defect this module was built to measure -----------------

def test_trail_stage_is_inert_at_its_own_trigger():
    """With TRAIL_TRIGGER_R == TRAIL_DISTANCE_R == 1.0 the trail is a no-op.

    At exactly +1R the candidate is `live - 1.0R` == the entry price, which the
    break-even stage already set, so the ratchet min-step blocks it. The stop is
    therefore pinned at entry across the whole +0.5R..~+1.08R band and captures
    nothing — the dead zone that produced today's give-backs.
    """
    assert config.TRAIL_TRIGGER_R == config.TRAIL_DISTANCE_R == 1.0
    risk = META_ENTRY - META_STOP
    at_one_r = META_ENTRY + 1.0 * risk
    # Stop already at break-even (the +0.5R stage moved it there).
    assert ratchet_stop(META_ENTRY, META_STOP, META_ENTRY, at_one_r, LIVE) is None
    # META's real +1.07R peak was still blocked — by two cents.
    assert ratchet_stop(META_ENTRY, META_STOP, META_ENTRY, 598.64, LIVE) is None


def test_meta_233_replays_to_breakeven_not_a_full_loss():
    """The recorded 2026-08-07 META #233 outcome: STOP at the entry price, ~$0."""
    result = simulate_exit(META_BARS, META_ENTRY, META_STOP, META_TP,
                           fallback_exit_price=590.38, geometry=LIVE)
    assert result.exit_reason == "STOP"
    assert result.exit_price == pytest.approx(META_ENTRY)
    assert result.armed_breakeven is True
    assert result.armed_trail is False          # the trail stage never fired
    assert result.mfe / (META_ENTRY - META_STOP) == pytest.approx(1.07, abs=0.01)


def test_nvda_232_replays_to_breakeven_not_a_full_loss():
    """The recorded 2026-08-07 NVDA #232 outcome: STOP at the entry price, ~$0."""
    result = simulate_exit(NVDA_BARS, NVDA_ENTRY, NVDA_STOP, NVDA_TP,
                           fallback_exit_price=221.81, geometry=LIVE)
    assert result.exit_reason == "STOP"
    assert result.exit_price == pytest.approx(NVDA_ENTRY)
    assert result.armed_breakeven is True
    assert result.mfe / (NVDA_ENTRY - NVDA_STOP) == pytest.approx(0.88, abs=0.01)


def test_static_bracket_model_launders_the_recorded_exit_instead_of_modelling_it():
    """Proves the defect the module exists to fix, on META #233.

    META's *moved* stop (590.40, the entry) was hit; its ORIGINAL 582.73 stop
    never was. A static bracket therefore sees no stop leg fire and falls through
    to ``fallback_exit_price`` — which bot/replay.py sets to the trade's ACTUAL
    exit price, so the recorded outcome is handed back out as if it had been
    modelled. The exit REASON gives the game away (EOD_FLATTEN for a trade that
    really stopped), and swapping the fallback breaks the illusion. The faithful
    ratchet model is indifferent to the fallback because it finds the stop itself.
    """
    static = ExitGeometry(0.5, 1.0, 1.0, 0.10, trailing_enabled=False)

    handed_the_answer = simulate_exit(META_BARS, META_ENTRY, META_STOP, META_TP,
                                      fallback_exit_price=590.38, geometry=static)
    assert handed_the_answer.exit_reason == "EOD_FLATTEN"    # reality was STOP
    assert handed_the_answer.exit_price == pytest.approx(590.38)

    neutral = simulate_exit(META_BARS, META_ENTRY, META_STOP, META_TP,
                            fallback_exit_price=594.00, geometry=static)
    assert neutral.exit_price == pytest.approx(594.00)       # $14.40 off on qty 4

    faithful = simulate_exit(META_BARS, META_ENTRY, META_STOP, META_TP,
                             fallback_exit_price=594.00, geometry=LIVE)
    assert faithful.exit_reason == "STOP"
    assert faithful.exit_price == pytest.approx(META_ENTRY)  # fallback irrelevant


def test_tighter_trail_would_have_captured_meta_profit():
    """A 0.5R trail distance locks part of META's +1.07R run instead of all-or-nothing."""
    tighter = ExitGeometry(0.5, 0.5, 0.5, 0.10)
    result = simulate_exit(META_BARS, META_ENTRY, META_STOP, META_TP,
                           fallback_exit_price=590.38, geometry=tighter)
    assert result.exit_reason == "STOP"
    assert result.armed_trail is True
    assert result.exit_price > META_ENTRY
    assert (result.exit_price - META_ENTRY) * META_QTY > 10.0


# --- Simulation-core semantics ----------------------------------------------

def test_stop_is_checked_before_target_within_a_bar():
    """Conservative ordering: a bar spanning both legs resolves as STOP."""
    bars = _bars([(120.0, 88.0)])
    result = simulate_exit(bars, 100.0, 90.0, 115.0,
                           fallback_exit_price=100.0, geometry=LIVE)
    assert result.exit_reason == "STOP"
    assert result.exit_price == pytest.approx(90.0)


def test_take_profit_exit():
    bars = _bars([(101.0, 99.5), (116.0, 112.0)])
    result = simulate_exit(bars, 100.0, 90.0, 115.0,
                           fallback_exit_price=100.0, geometry=LIVE)
    assert result.exit_reason == "TAKE_PROFIT"
    assert result.exit_price == pytest.approx(115.0)


def test_falls_back_to_eod_flatten_when_no_leg_triggers():
    bars = _bars([(101.0, 99.0), (102.0, 100.5)])
    result = simulate_exit(bars, 100.0, 90.0, 115.0,
                           fallback_exit_price=101.5, geometry=LIVE)
    assert result.exit_reason == "EOD_FLATTEN"
    assert result.exit_price == pytest.approx(101.5)
    assert result.armed_breakeven is False


def test_ratchet_arms_from_the_bar_after_the_trigger_not_the_same_bar():
    """A bar that spikes to +0.5R and falls back must NOT stop out at entry.

    The live bot ratchets once per ~60s tick, so arming from the same bar that is
    then tested against the new stop would be optimistic. Here the spike bar arms
    break-even and the NEXT bar's low takes it out.
    """
    bars = _bars([(105.5, 99.0), (100.5, 98.0)])
    result = simulate_exit(bars, 100.0, 90.0, 130.0,
                           fallback_exit_price=99.0, geometry=LIVE)
    assert result.exit_reason == "STOP"
    assert result.exit_price == pytest.approx(100.0)   # entry, not the 90.0 plan stop


# --- Aggregation -------------------------------------------------------------

def _trade(trade_id, symbol, qty, entry, stop, tp, exit_price, pl, reason="STOP"):
    return {
        "trade_id": trade_id, "symbol": symbol, "qty": qty,
        "entry_price": entry, "stop_price": stop, "take_profit_price": tp,
        "exit_price": exit_price, "realized_pl": pl, "exit_reason": reason,
        "entry_time": pd.Timestamp("2026-08-07 10:08:00"),
    }


def test_replay_geometry_aggregates_todays_two_giveback_trades():
    trades = [
        _trade(233, "META", META_QTY, META_ENTRY, META_STOP, META_TP, 590.38, -0.08),
        _trade(232, "NVDA", NVDA_QTY, NVDA_ENTRY, NVDA_STOP, NVDA_TP, 221.81, -0.11),
    ]
    windows = {233: META_BARS, 232: NVDA_BARS}
    out = replay_geometry(trades, windows, LIVE)

    assert out["trades"] == 2
    assert out["actual_pl"] == pytest.approx(-0.19)
    assert out["armed_breakeven"] == 2
    assert out["armed_trail"] == 0
    # Both replay to ~$0, so the model tracks reality: tiny error budget.
    assert out["abs_error"] < 1.0
    # $66 of peak open profit banked as ~nothing — the give-back this measures.
    assert out["peak_mfe_usd"] == pytest.approx(65.30, abs=0.5)
    assert out["captured_pct"] == pytest.approx(0.0, abs=1.0)


def test_replay_geometry_skips_trades_without_bars():
    trades = [_trade(233, "META", META_QTY, META_ENTRY, META_STOP, META_TP,
                     590.38, -0.08)]
    assert replay_geometry(trades, {}, LIVE)["trades"] == 0


def test_replay_geometry_empty_is_safe():
    out = replay_geometry([], {}, LIVE)
    assert out["trades"] == 0
    assert out["captured_pct"] is None


def test_giveback_rows_selects_the_dead_zone_cohort():
    rows = [
        {"mfe_r": 1.07, "actual_pl": -0.08},   # gave it all back
        {"mfe_r": 0.88, "actual_pl": -0.11},   # gave it all back
        {"mfe_r": 1.68, "actual_pl": 55.72},   # ran to target — not a give-back
        {"mfe_r": 0.03, "actual_pl": -18.78},  # never green — a different leak
    ]
    assert len(giveback_rows(rows)) == 2


def test_geometry_label_is_readable():
    assert "be=0.5R" in LIVE.label()
    assert ExitGeometry(0.5, 1.0, 1.0, 0.1,
                        trailing_enabled=False).label().startswith("no-ratchet")
