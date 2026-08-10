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

# The geometry that was live from IMP-013 (2026-07-08) until IMP-029 (2026-08-08).
# The tests below that reproduce RECORDED outcomes are pinned to it on purpose:
# they document what the bot really did on those dates, so they must not follow
# config forward. New behaviour is asserted against LIVE.
PRE_IMP029 = ExitGeometry(0.5, 1.0, 1.0, 0.10)

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

def test_trail_stage_was_inert_at_its_own_trigger_before_imp029():
    """Historical: with TRAIL_TRIGGER_R == TRAIL_DISTANCE_R == 1.0 the trail was a no-op.

    At exactly +1R the candidate was `live - 1.0R` == the entry price, which the
    break-even stage had already set, so the ratchet min-step blocked it. The stop
    stayed pinned at entry across the whole +0.5R..~+1.08R band and captured
    nothing — the dead zone that produced the 2026-08-07 give-backs and the
    defect IMP-029 removed.
    """
    risk = META_ENTRY - META_STOP
    at_one_r = META_ENTRY + 1.0 * risk
    # Stop already at break-even (the +0.5R stage moved it there).
    assert ratchet_stop(META_ENTRY, META_STOP, META_ENTRY, at_one_r,
                        PRE_IMP029) is None
    # META's real +1.07R peak was still blocked — by two cents.
    assert ratchet_stop(META_ENTRY, META_STOP, META_ENTRY, 598.64,
                        PRE_IMP029) is None


# --- IMP-029: the dead zone must stay closed --------------------------------

def test_trail_is_not_inert_at_the_trigger():
    """The live trail must lift the stop ABOVE entry as soon as price runs past it.

    This is the regression guard for IMP-029. The failure mode it locks out is
    arithmetic, not statistical: whenever TRAIL_DISTANCE_R >= TRAIL_TRIGGER_R the
    candidate at the trigger is `live - distance*R` <= entry, i.e. no better than
    the break-even stop, and STOP_RATCHET_MIN_PCT then blocks every replace until
    price has run a further ratchet-min-step. Setting TRAIL_DISTANCE_R back to
    1.0 (or above TRAIL_TRIGGER_R) reopens the dead band and fails this test.
    """
    risk = META_ENTRY - META_STOP
    # Comfortably past the trigger, break-even already set: the stop MUST move up.
    well_past = META_ENTRY + (config.TRAIL_TRIGGER_R + 0.5) * risk
    moved = ratchet_stop(META_ENTRY, META_STOP, META_ENTRY, well_past, LIVE)
    assert moved is not None, "trail is inert — the IMP-029 dead zone is back"
    assert moved > META_ENTRY

    # META's real +1.07R peak — blocked by two cents before IMP-029 — now trails.
    at_real_peak = ratchet_stop(META_ENTRY, META_STOP, META_ENTRY, 598.64, LIVE)
    assert at_real_peak is not None
    assert at_real_peak > META_ENTRY


def test_trail_distance_stays_below_the_trigger():
    """Config invariant: distance >= trigger is what made the trail inert."""
    assert config.TRAIL_DISTANCE_R < 1.0
    assert config.TRAIL_DISTANCE_R <= config.TRAIL_TRIGGER_R
    assert config.TRAIL_TRIGGER_R <= config.BREAKEVEN_TRIGGER_R, \
        "the trail must arm no later than break-even, or a dead band reopens"


def test_imp029_geometry_captures_both_of_the_weeks_giveback_trades():
    """The two 2026-08-07 give-backs must now bank real money, not ~$0.

    META #233 peaked +1.07R and NVDA #232 peaked +0.88R; both returned 100% of
    the move under the old geometry (recorded: -$0.08 and -$0.11). NVDA is the
    reason the trigger moved to 0.5R as well as the distance — it never reached
    +1R, so a distance-only fix would have left it untouched.
    """
    meta = simulate_exit(META_BARS, META_ENTRY, META_STOP, META_TP,
                         fallback_exit_price=590.38, geometry=LIVE)
    assert meta.armed_trail is True
    assert (meta.exit_price - META_ENTRY) * META_QTY > 10.0

    nvda = simulate_exit(NVDA_BARS, NVDA_ENTRY, NVDA_STOP, NVDA_TP,
                         fallback_exit_price=221.81, geometry=LIVE)
    assert nvda.armed_trail is True, "NVDA peaked +0.88R — needs the 0.5R trigger"
    assert nvda.exit_price > NVDA_ENTRY
    assert (nvda.exit_price - NVDA_ENTRY) * NVDA_QTY > 5.0


def test_imp029_never_widens_risk():
    """A ratchet may only move a stop UP — IMP-029 must not relax that."""
    risk = NVDA_ENTRY - NVDA_STOP
    # Below the break-even trigger nothing moves at all.
    assert ratchet_stop(NVDA_ENTRY, NVDA_STOP, NVDA_STOP,
                        NVDA_ENTRY + 0.2 * risk, LIVE) is None
    # A stop already above the candidate is never pulled back down.
    high_stop = NVDA_ENTRY + 0.9 * risk
    assert ratchet_stop(NVDA_ENTRY, NVDA_STOP, high_stop,
                        NVDA_ENTRY + 1.0 * risk, LIVE) is None


def test_meta_233_replays_to_breakeven_not_a_full_loss():
    """The recorded 2026-08-07 META #233 outcome under the THEN-live geometry:
    STOP at the entry price, ~$0. Pinned to PRE_IMP029 — this is history."""
    result = simulate_exit(META_BARS, META_ENTRY, META_STOP, META_TP,
                           fallback_exit_price=590.38, geometry=PRE_IMP029)
    assert result.exit_reason == "STOP"
    assert result.exit_price == pytest.approx(META_ENTRY)
    assert result.armed_breakeven is True
    assert result.armed_trail is False          # the trail stage never fired
    assert result.mfe / (META_ENTRY - META_STOP) == pytest.approx(1.07, abs=0.01)


def test_nvda_232_replays_to_breakeven_not_a_full_loss():
    """The recorded 2026-08-07 NVDA #232 outcome under the THEN-live geometry:
    STOP at the entry price, ~$0. Pinned to PRE_IMP029 — this is history."""
    result = simulate_exit(NVDA_BARS, NVDA_ENTRY, NVDA_STOP, NVDA_TP,
                           fallback_exit_price=221.81, geometry=PRE_IMP029)
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
                             fallback_exit_price=594.00, geometry=PRE_IMP029)
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
    # Bar 1 (+0.55R) arms the ratchet; bar 2 is tested against the level it set.
    # Post-IMP-029 that level is the 0.5R trail (105.5 - 0.5*10R = 100.5), not
    # the entry price — and emphatically not the 90.0 plan stop.
    assert result.exit_price == pytest.approx(100.5)


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
    out = replay_geometry(trades, windows, PRE_IMP029)   # reproduces the RECORDED day

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


# --- IMP-030: the counterfactual window must outlive the recorded exit -------
# 2026-08-10 MSFT #240: entry 504.865, plan stop 497.12 (1R = 7.745), qty 4.
# Peaked 513.72 (+1.14R) at 10:30 ET, then the IMP-029 0.5R trail took it out at
# 10:53 for +$17.54. The bars below are the REAL 5-minute highs/lows for the FULL
# session window, entry (09:40) through the 15:55 flatten -- deliberately running
# ~5 hours past the live exit, because that is the span a looser trail needs.
MSFT_ENTRY, MSFT_STOP, MSFT_QTY = 504.865, 497.12, 4
MSFT_TP = 516.05
MSFT_EXIT, MSFT_PL = 509.25, 17.54
MSFT_SESSION_CLOSE = 506.15
MSFT_BARS_FULL_SESSION = _bars([
    (505.75, 503.54), (506.85, 504.97), (506.84, 505.69), (507.70, 505.49),
    (508.33, 507.18), (509.46, 507.45), (509.77, 508.16), (510.52, 508.67),
    (511.25, 509.31), (512.75, 510.49), (513.72, 512.23), (512.65, 511.46),
    (511.73, 510.72), (510.98, 509.84), (510.50, 508.52), (509.50, 508.82),
    (510.28, 508.49), (509.16, 508.24), (509.10, 508.37), (508.86, 507.79),
    (509.31, 508.04), (509.88, 509.02), (509.70, 509.19), (509.51, 509.13),
    (509.85, 509.25), (510.11, 509.70), (510.29, 509.86), (510.68, 510.07),
    (511.06, 510.47), (511.13, 510.73), (511.09, 510.91), (511.02, 510.45),
    (510.67, 510.40), (510.61, 509.96), (510.14, 508.96), (509.29, 508.72),
    (508.75, 507.83), (508.10, 506.85), (507.22, 506.56), (508.38, 506.79),
    (509.06, 506.92), (507.91, 507.13), (507.98, 507.14), (507.88, 507.62),
    (508.18, 507.73), (508.40, 507.97), (508.59, 508.17), (508.38, 508.21),
    (508.35, 507.15), (507.19, 506.56), (506.68, 505.76), (506.30, 505.72),
    (505.62, 505.09), (505.55, 504.98), (505.42, 504.75), (505.64, 504.66),
    (505.53, 504.81), (505.32, 504.98), (505.60, 504.82), (505.72, 504.95),
    (505.84, 505.18), (505.64, 505.25), (506.13, 505.70), (506.33, 505.83),
    (506.33, 505.88), (505.87, 505.33), (505.96, 505.50), (505.75, 505.30),
    (505.39, 505.01), (505.22, 504.35), (505.27, 504.46), (505.53, 504.98),
    (505.39, 505.03), (505.39, 504.37), (505.52, 504.07), (506.93, 505.45),
])


def _msft_trade():
    return _trade(240, "MSFT", MSFT_QTY, MSFT_ENTRY, MSFT_STOP, MSFT_TP,
                  MSFT_EXIT, MSFT_PL, reason="STOP")


def test_imp030_reverted_geometry_is_not_the_live_answer():
    """The bug: a looser trail was scored as if it had exited where live did.

    Truncated at the recorded 10:53 exit, the pre-IMP-029 1R/1R trail never got
    a bar low enough to fire, fell through to the fallback, and reported MSFT's
    live +$17.54 straight back as its own counterfactual. Over the full session
    its 505.98 stop really does get hit -- for +$4.46.
    """
    trades = [_msft_trade()]
    windows = {240: MSFT_BARS_FULL_SESSION}
    fallbacks = {240: MSFT_SESSION_CLOSE}

    reverted = replay_geometry(trades, windows, PRE_IMP029, fallbacks)
    row = reverted["rows"][0]

    assert row["sim_reason"] == "STOP"
    assert row["sim_pl"] == pytest.approx(4.46, abs=0.10)
    # The whole point: it must NOT come back as the live result.
    assert row["sim_pl"] != pytest.approx(MSFT_PL, abs=1.0)
    # ...and the measured benefit of IMP-029 on this trade is the difference.
    assert MSFT_PL - row["sim_pl"] == pytest.approx(13.08, abs=0.15)


def test_imp030_live_geometry_still_reproduces_the_recorded_exit():
    """Widening the window must not disturb fidelity on the shipped geometry.

    IMP-029's trail fires at 10:53 in reality; bars after it are unreachable, so
    the extra ~5 hours are inert here and the sim still lands on the live exit.
    """
    trades = [_msft_trade()]
    out = replay_geometry(trades, {240: MSFT_BARS_FULL_SESSION}, LIVE,
                          {240: MSFT_SESSION_CLOSE})
    row = out["rows"][0]

    assert row["sim_reason"] == "STOP" == row["actual_reason"]
    assert row["sim_pl"] == pytest.approx(19.94, abs=0.10)
    assert row["armed_trail"] is True
    assert row["mfe_r"] == pytest.approx(1.14, abs=0.02)


def test_imp030_fallback_map_is_optional_and_per_trade():
    """Omitting the map keeps the old per-trade recorded-exit fallback."""
    trades = [_msft_trade()]
    # A static bracket never triggers on this path: its 497.12 stop is never hit
    # and the 516.05 target never prints, so the result IS the fallback.
    static = ExitGeometry(0.5, 1.0, 1.0, 0.10, trailing_enabled=False)

    without = replay_geometry(trades, {240: MSFT_BARS_FULL_SESSION}, static)
    with_map = replay_geometry(trades, {240: MSFT_BARS_FULL_SESSION}, static,
                               {240: MSFT_SESSION_CLOSE})

    assert without["rows"][0]["sim_reason"] == "EOD_FLATTEN"
    assert without["rows"][0]["sim_pl"] == pytest.approx(
        (MSFT_EXIT - MSFT_ENTRY) * MSFT_QTY, abs=0.01)      # legacy: live exit
    assert with_map["rows"][0]["sim_pl"] == pytest.approx(
        (MSFT_SESSION_CLOSE - MSFT_ENTRY) * MSFT_QTY, abs=0.01)   # honest: 15:55

    # An unmapped trade_id must fall back to its own recorded exit, not crash.
    partial = replay_geometry(trades, {240: MSFT_BARS_FULL_SESSION}, static, {})
    assert partial["rows"][0]["sim_pl"] == pytest.approx(
        without["rows"][0]["sim_pl"], abs=0.01)
