"""Break-even trigger sweep (IMP-032) — scripts/exit_geometry.breakeven_candidates.

The sweep exists because the post-gate stop loss is concentrated in trades that
peaked BELOW the +0.5R break-even trigger and were never armed. These tests pin
it to the two 2026-08-12 trades that frame the question, using that session's
real IEX 1-min bars so the sweep cannot start reporting rescues it cannot deliver.
"""

import pandas as pd
import pytest

from bot.exit_sim import ExitGeometry, simulate_exit
from bot import config
from scripts import exit_geometry
from scripts.exit_geometry import BREAKEVEN_SWEEP, breakeven_candidates

LIVE = ExitGeometry(breakeven_trigger_r=0.5, trail_trigger_r=0.5,
                    trail_distance_r=0.5, ratchet_min_pct=0.10)

# --- QCOM #249, 2026-08-12 ---------------------------------------------------
# Filled 164.6573 at 09:56:02 ET, plan stop 162.07 (1R = 2.5873), take-profit
# 168.24, stopped out 10:43 at 161.94 for -$40.76. Every 1-min bar from the entry
# minute to the stop, (high, low), exactly as the IEX feed printed them. The
# session high over the whole hold is 164.53 — BELOW the fill — so the trade
# never once traded green.
QCOM_BARS = [
    (164.53, 164.53), (164.30, 164.17), (164.17, 164.16), (164.14, 163.73),
    (163.57, 163.28), (163.18, 162.97), (163.23, 163.23), (163.30, 163.25),
    (163.37, 163.16), (163.57, 163.47), (163.50, 163.45), (163.59, 163.47),
    (163.82, 163.62), (163.77, 163.63), (163.66, 163.47), (163.72, 163.63),
    (163.54, 163.44), (163.53, 163.43), (163.79, 163.68), (163.79, 163.79),
    (164.00, 163.82), (164.03, 164.03), (163.78, 163.68), (164.02, 163.89),
    (164.22, 163.90), (163.95, 163.95), (163.99, 163.88), (163.98, 163.94),
    (163.96, 163.96), (163.73, 163.51), (163.51, 163.41), (163.26, 162.81),
    (162.97, 162.97), (163.01, 163.01), (162.76, 162.76), (162.31, 162.15),
    (162.56, 162.56), (162.60, 162.52), (162.56, 162.56), (162.36, 162.36),
    (162.65, 162.59), (162.51, 162.49), (162.38, 162.25), (162.00, 162.00),
]
QCOM = dict(entry=164.6573, stop=162.07, tp=168.24, fallback=163.22)

# --- WMT #247, 2026-08-12 ----------------------------------------------------
# Filled 113.4943 at 09:43:41 ET, plan stop 111.78 (1R = 1.7143), take-profit
# 116.03, flattened 15:57 at 115.84 for +$49.26 — the day's best trade. Reduced
# to that session's real HOURLY (high, low) extremes from the entry hour to the
# 15:55 flatten; the reduction preserves what the ratchet reads (the running high
# and every low that could take the stop out) without carrying 372 rows.
WMT_BARS = [
    (114.85, 113.40),   # 09:43-09:59, low = the 09:43 entry bar
    (115.39, 114.51),   # 10:xx
    (115.28, 114.64),   # 11:xx
    (115.20, 114.81),   # 12:xx
    (115.59, 115.05),   # 13:xx
    (115.74, 115.24),   # 14:xx
    (115.91, 115.25),   # 15:00-15:55
]
WMT = dict(entry=113.4943, stop=111.78, tp=116.03, fallback=115.86)


def _frame(bars: list[tuple[float, float]]) -> pd.DataFrame:
    return pd.DataFrame(bars, columns=["high", "low"])


def _run(trade: dict, bars: list[tuple[float, float]], geometry: ExitGeometry):
    return simulate_exit(_frame(bars), trade["entry"], trade["stop"],
                         trade["tp"], trade["fallback"], geometry)


def test_sweep_varies_only_the_breakeven_trigger():
    cands = breakeven_candidates(LIVE, [0.3, 0.25])
    assert [c.breakeven_trigger_r for c in cands] == [0.5, 0.3, 0.25]
    for c in cands:
        assert c.trail_trigger_r == LIVE.trail_trigger_r
        assert c.trail_distance_r == LIVE.trail_distance_r
        assert c.ratchet_min_pct == LIVE.ratchet_min_pct
        assert c.trailing_enabled is LIVE.trailing_enabled


def test_sweep_always_carries_the_live_trigger_as_its_baseline():
    """Without the live row the sweep would have no reference to be judged against."""
    assert LIVE.breakeven_trigger_r not in BREAKEVEN_SWEEP
    triggers = [c.breakeven_trigger_r for c in breakeven_candidates(LIVE, BREAKEVEN_SWEEP)]
    assert triggers[0] == LIVE.breakeven_trigger_r
    assert triggers == sorted(triggers, reverse=True)
    assert len(triggers) == len(set(triggers))       # live value not duplicated
    dupe = [c.breakeven_trigger_r for c in breakeven_candidates(LIVE, [0.5, 0.5, 0.3])]
    assert dupe == [0.5, 0.3]


@pytest.mark.parametrize("trigger", [0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.05])
def test_no_breakeven_trigger_can_rescue_qcom_249(trigger):
    """QCOM never printed above its fill, so NO trigger can arm — it is not a
    break-even failure and the sweep must never claim it as a rescue.

    This is the 2026-08-12 loss (-$40.76, MFE -0.05R) that motivated IMP-032:
    it is an ENTRY-quality loss, and lowering the exit trigger is not its fix.
    """
    res = _run(QCOM, QCOM_BARS, ExitGeometry(trigger, 0.5, 0.5, 0.10))
    assert res.exit_reason == "STOP"
    assert res.exit_price == pytest.approx(QCOM["stop"])
    assert res.armed_breakeven is False
    assert res.armed_trail is False
    # ExitSimResult.mfe is floored at 0.0 by simulate_exit, so "no favorable
    # excursion was ever recorded" is the strongest statement available here.
    # The raw-bar MFE is -0.05R (session high 164.53 vs the 164.6573 fill).
    assert res.mfe == 0.0
    assert max(h for h, _ in QCOM_BARS) < QCOM["entry"]


@pytest.mark.parametrize("trigger", [0.5, 0.4, 0.35, 0.3, 0.25, 0.2])
def test_lowering_the_trigger_does_not_scratch_wmt_247(trigger):
    """The day's winner must survive every trigger in the sweep.

    WMT's lowest print after the ratchet first armed was 114.39, comfortably
    above the 113.4943 entry, so an earlier break-even stop is never touched and
    the trade still runs to the flatten. This is the cost side the raw
    'stops rescued' count ignores — the sweep has to keep pricing it.
    """
    res = _run(WMT, WMT_BARS, ExitGeometry(trigger, 0.5, 0.5, 0.10))
    assert res.exit_reason == "EOD_FLATTEN"
    assert res.exit_price == pytest.approx(WMT["fallback"])
    assert res.final_stop > WMT["entry"]     # trail carried it above entry
    assert res.armed_breakeven is True


# --- IMP-044: candidates are scored against the LIVE geometry, not the book ---
#
# The what-if grid used to score every candidate against the ACTUAL book. The
# simulator does not reproduce the book exactly, so that handed every row the
# same bias: the live geometry's own "delta" is pure reproduction error, and the
# candidates inherited it before being compared against the noise budget.
#
# The numbers below are the real 2026-08-28 reading of the IMP-040 era
# (`scripts/exit_geometry --since 2026-08-25`, 17 trades). They are the recorded
# scenario that motivated the change: a candidate whose true effect is +$55.00
# was reported as +$14.36 and dismissed as "within noise" against a $75.34
# budget, while the geometry the bot was actually running scored -$40.64
# against itself.

ERA_ACTUAL = 83.35        # book P&L, 17 trades since 2026-08-25
ERA_SIM_LIVE = 42.71      # the LIVE 0.25R/0.25R geometry, replayed
ERA_REPRO_ERR = -40.64    # ERA_SIM_LIVE - ERA_ACTUAL: the simulator's own miss
ERA_SIM_HALF = 97.71      # the 0.5R-trigger / 0.25R-trail candidate, replayed
ERA_BUDGET = 75.34        # sum |sim - actual| under the live geometry


def _run_dict(sim_pl: float, per_trade: list[tuple[int, float]],
              actual: float = ERA_ACTUAL, geometry: str = "cand") -> dict:
    """The subset of a replay_geometry() result that the scorecard reads."""
    return {
        "geometry": geometry,
        "sim_pl": sim_pl,
        "actual_pl": actual,
        "delta": round(sim_pl - actual, 2),
        "trades": len(per_trade),
        "sim_wins": sum(1 for _, pl in per_trade if pl > 0),
        "captured_pct": 21.4,
        "rows": [{"trade_id": tid, "sim_pl": pl} for tid, pl in per_trade],
    }


def _spread(total: float, n: int = 17) -> list[tuple[int, float]]:
    """n trades summing to ``total``, ids 300.. — the shape rows() has."""
    each = round(total / n, 4)
    return [(300 + i, each) for i in range(n)]


def test_the_live_geometry_scores_exactly_zero_against_itself():
    """The self-check. A geometry cannot outperform or trail itself.

    This is the single assertion that would have caught the bug: before IMP-044
    the live row scored -$40.64 against the book and that number was silently
    read as a property of the geometry.
    """
    live = _run_dict(ERA_SIM_LIVE, _spread(ERA_SIM_LIVE))
    assert exit_geometry.paired_delta(live, live) == (0.0, 0)
    assert live["delta"] == pytest.approx(ERA_REPRO_ERR, abs=0.01)  # the old score


def test_paired_delta_strips_the_reproduction_error_from_a_candidate():
    """The recorded 2026-08-28 case: +$14.36 reported, +$55.00 real."""
    live = _run_dict(ERA_SIM_LIVE, _spread(ERA_SIM_LIVE))
    cand = _run_dict(ERA_SIM_HALF, _spread(ERA_SIM_HALF))
    delta, _ = exit_geometry.paired_delta(cand, live)
    assert delta == pytest.approx(55.00, abs=0.01)
    assert cand["delta"] == pytest.approx(14.36, abs=0.01)      # what it used to say
    assert delta - cand["delta"] == pytest.approx(-ERA_REPRO_ERR, abs=0.01)


@pytest.mark.parametrize("sim", [25.78, 62.57, 80.21, 112.81, 130.56, 141.46])
def test_the_bias_removed_is_the_same_constant_in_every_row(sim):
    """Why scoring against the book was wrong for the whole grid, not one cell.

    Every candidate carried the identical -$40.64, so the grid's ORDERING was
    right and its SCALE was wrong — which is exactly what makes a noise-budget
    verdict on it wrong, since the budget is an absolute dollar bar.
    """
    live = _run_dict(ERA_SIM_LIVE, _spread(ERA_SIM_LIVE))
    cand = _run_dict(sim, _spread(sim))
    delta, _ = exit_geometry.paired_delta(cand, live)
    assert delta - cand["delta"] == pytest.approx(-ERA_REPRO_ERR, abs=0.01)


def test_a_candidate_that_changes_nothing_scores_zero_however_bad_the_simulator():
    """Debiasing must not depend on the simulator being any good.

    Same per-trade exits under both geometries -> zero effect and zero support,
    even when the simulator is missing the book by $500.
    """
    rows = _spread(42.71)
    live = _run_dict(42.71, rows, actual=542.71)
    cand = _run_dict(42.71, rows, actual=542.71)
    assert live["delta"] == pytest.approx(-500.0, abs=0.01)
    assert exit_geometry.paired_delta(cand, live) == (0.0, 0)


def test_support_count_is_the_number_of_trades_whose_exit_moved():
    """A $55 delta from one trade and from twelve are different evidence."""
    live = _run_dict(42.71, [(301, 10.0), (302, 10.0), (303, 22.71)])
    one = _run_dict(97.71, [(301, 10.0), (302, 10.0), (303, 77.71)])
    many = _run_dict(97.71, [(301, 28.0), (302, 30.0), (303, 39.71)])
    assert exit_geometry.paired_delta(one, live) == (55.0, 1)
    assert exit_geometry.paired_delta(many, live) == (55.0, 3)


def test_sub_cent_wobble_is_not_counted_as_a_changed_trade():
    """Float noise in a rounded sim price must not inflate the support count."""
    live = _run_dict(42.71, [(301, 21.355), (302, 21.355)])
    cand = _run_dict(42.71, [(301, 21.3551), (302, 21.3549)])
    assert exit_geometry.paired_delta(cand, live)[1] == 0


def test_the_noise_verdict_now_answers_the_question_it_claims_to(capsys):
    """The end-to-end consequence, on the recorded numbers.

    The 0.5R/0.25R cell was printed as '+$14.36 within noise'. Its real effect
    against the running geometry is +$55.00 — still inside a $75.34 budget, so
    the verdict does NOT flip here and this change is not a licence to declare
    significance. What changes is that the number being compared is the
    geometry's effect rather than the geometry's effect minus a simulator bug.
    """
    live = _run_dict(ERA_SIM_LIVE, _spread(ERA_SIM_LIVE), geometry="live")
    cand = _run_dict(ERA_SIM_HALF, _spread(ERA_SIM_HALF), geometry="half")
    exit_geometry._print_run(cand, ERA_BUDGET, live)
    out = capsys.readouterr().out
    assert "vs live $  +55.00" in out
    assert "within noise" in out
    assert "[17/17 differ]" in out


def test_a_cell_whose_true_effect_clears_the_budget_is_no_longer_hidden(capsys):
    """The 1R-trail rows: +$98.75 real vs +$58.11 as reported before.

    Under the old scoring this sat below the $75.34 budget and was printed
    'within noise'; debiased it clears. That is the verdict the ~2026-09-08
    IMP-040 decision is scheduled to be read off.
    """
    live = _run_dict(ERA_SIM_LIVE, _spread(ERA_SIM_LIVE), geometry="live")
    cand = _run_dict(141.46, _spread(141.46), geometry="trail@1R-0.25R")
    assert cand["delta"] == pytest.approx(58.11, abs=0.01)
    assert abs(cand["delta"]) < ERA_BUDGET          # the old, wrong verdict
    exit_geometry._print_run(cand, ERA_BUDGET, live)
    out = capsys.readouterr().out
    assert "vs live $  +98.75" in out
    assert "clears noise" in out


def test_fidelity_rows_are_still_scored_against_the_book(capsys):
    """The two rows that exist to measure the SIMULATOR keep measuring it.

    Passing no baseline must still print the raw sim-vs-book delta: that is the
    reproduction error, and hiding it would remove the evidence that the
    debiasing is needed at all.
    """
    live = _run_dict(ERA_SIM_LIVE, _spread(ERA_SIM_LIVE), geometry="live")
    exit_geometry._print_run(live, None)
    out = capsys.readouterr().out
    assert "vs book $  -40.64" in out
    assert "vs live" not in out
    assert "differ]" not in out


def test_imp040_geometry_is_untouched_by_this_run():
    """IMP-044 is measurement only: the live ratchet constants must not move.

    IMP-040's window is open until ~2026-09-08 and this change exists to make
    that verdict computable, not to pre-empt it.
    """
    assert config.BREAKEVEN_TRIGGER_R == 0.25
    assert config.TRAIL_TRIGGER_R == 0.25
    assert config.TRAIL_DISTANCE_R == 0.25
    assert config.MIN_STOP_PCT == 1.5
    assert config.ATR_STOP_MULT == 3.0
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
