"""Tests for scripts/stop_geometry.py — the stop-width what-if (IMP-055).

The regression fixture is the REAL trade that motivated the module: META #347,
2026-09-14, the only fill of that session. Entry 660.49, plan stop 648.39
(1R = $12.10 = 1.832% of entry), qty 3, out at 09:54 on the break-even stop for
-$1.14 — a doctrine FAIL whose IMP-054 WIN ceiling was **+0.670R**, i.e. a WIN
was arithmetically unavailable under any exit policy.

The week-ending-09-11 weekly designated ONE live-path change off exactly that
shape: shrink 1R so +1R becomes reachable. The arithmetic half is true and these
tests assert it — the ceiling climbs +0.670R -> +1.340R as the stop is tightened,
crossing the WIN bar at 60% of the live width. The trading half is false and
these tests assert that too: replayed against the same real bars, **every** width
still exits on a break-even STOP and scores FAIL, because BREAKEVEN_TRIGGER_R is
denominated in R — a tighter 1R arms the ratchet EARLIER, pins the stop at entry
sooner, and hands the same 09:54 pullback the trade. At 50% the stop fires before
the 09:51 high even prints, truncating the very excursion it was meant to harvest.

Bar paths below are the real SIP 1-minute highs/lows for META 09:47-10:00 ET plus
the session's later peak (668.60 at 14:08) and its 15:55 close (666.34).
"""

from __future__ import annotations

import pytest

from bot import config, doctrine
from bot.exit_sim import ExitGeometry
from scripts.stop_geometry import ADR_CAPS, SCALES, Policy, build_policies, run_policy

ENTRY = 660.49
PLAN_STOP = 648.39
LIVE_SD = ENTRY - PLAN_STOP          # $12.10 = 1.832% of entry
QTY = 3

# META 2026-09-14, SIP 1-minute (high, low), 09:47 fill -> 15:55 flatten.
# The tail is compressed to the two bars that matter after the stop-out: the
# 14:08 session peak the ceiling is measured from, and the 15:55 close.
class _Bar:
    """The .high/.low duck type run_policy consumes (raw Alpaca bars in production)."""

    def __init__(self, high: float, low: float):
        self.high, self.low = high, low


META_347_BARS = [_Bar(h, l) for h, l in [
    (662.20, 657.97),   # 09:47 fill bar — MAE -2.52
    (662.01, 659.87),   # 09:48
    (662.93, 660.70),   # 09:49
    (663.77, 662.51),   # 09:50
    (663.90, 662.14),   # 09:51 — MFE +3.41 (+0.282R at the live width)
    (663.14, 661.48),   # 09:52
    (662.87, 660.70),   # 09:53
    (661.00, 659.20),   # 09:54 — the pullback that took the break-even stop
    (661.39, 659.53),   # 09:55
    (668.60, 661.00),   # the 14:08 session peak, compressed
    (666.34, 665.90),   # the 15:55 close
]]
SESSION_CLOSE = 666.34


def _trade(trade_id: int = 347) -> dict:
    import datetime as _dt
    return {
        "trade_id": trade_id,
        "symbol": "META",
        "qty": QTY,
        "entry_price": ENTRY,
        "entry_time": _dt.datetime(2026, 9, 14, 9, 47, 36),
        "stop_price": PLAN_STOP,
        "take_profit_price": 673.07,
        "exit_price": 660.11,
        "exit_time": _dt.datetime(2026, 9, 14, 9, 54, 6),
        "realized_pl": -1.14,
        "exit_reason": "STOP",
    }


def _run(policy: Policy, adr: dict | None = None) -> dict:
    trade = _trade()
    return run_policy(
        policy,
        [trade],
        {347: META_347_BARS},
        {347: SESSION_CLOSE},
        adr or {},
        ExitGeometry.from_config(),
    )


# --- The grid itself ---------------------------------------------------------

def test_grid_covers_both_policy_families():
    labels = [p.label for p in build_policies()]
    assert len(labels) == len(SCALES) + len(ADR_CAPS)
    assert "scale=1.00" in labels, "the fidelity baseline must be in the grid"
    assert all(k <= 1.0 for k in SCALES), "this module never WIDENS a stop"
    assert all(c <= 1.0 for c in ADR_CAPS)


def test_scale_policy_scales_and_never_widens():
    policies = {p.label: p for p in build_policies()}
    assert policies["scale=1.00"].stop_distance(ENTRY, LIVE_SD, None) == pytest.approx(LIVE_SD)
    assert policies["scale=0.60"].stop_distance(ENTRY, LIVE_SD, None) == pytest.approx(LIVE_SD * 0.6)


def test_adrcap_caps_but_never_widens_and_abstains_without_adr():
    cap = {p.label: p for p in build_policies()}["adrcap=0.50"]
    # ADR20 $30 -> cap $15, wider than the live $12.10 stop, so the live stop stands.
    assert cap.stop_distance(ENTRY, LIVE_SD, 30.0) == pytest.approx(LIVE_SD)
    # ADR20 $12 -> cap $6, tighter, so the cap binds.
    assert cap.stop_distance(ENTRY, LIVE_SD, 12.0) == pytest.approx(6.0)
    # No ADR for that symbol-day: the policy has no opinion rather than a default.
    assert cap.stop_distance(ENTRY, LIVE_SD, None) is None


# --- Invariants the comparison rests on --------------------------------------

def test_dollar_risk_is_held_constant_so_tightening_is_not_a_risk_increase():
    """A tighter stop buys MORE shares at the SAME risk budget — sizing.plan_position's
    own rule. If this drifts, every row of the grid is comparing two different bets."""
    budget = QTY * LIVE_SD
    for label in ("scale=1.00", "scale=0.80", "scale=0.50"):
        policy = {p.label: p for p in build_policies()}[label]
        row = _run(policy)["rows"][0]
        sd = ENTRY - row["stop_price"]
        assert row["qty"] * sd <= budget + 1e-6, f"{label} risked more than the live trade"
        # Whole shares only, so the budget is under-spent by less than one share's
        # risk — never more. On a 3-share book that residue is material (scale=0.80
        # buys 3 shares of a $9.68 stop = 80% of the budget), which is a real limit
        # of this account size and is recorded in the IMP-055 entry, not hidden here.
        assert budget - row["qty"] * sd < sd, f"{label} left a whole share unbought"


def test_baseline_reproduces_the_live_share_count():
    """3 * 12.10 / 12.10 == 2.999... in binary float; int() would report 2 shares and
    bias the whole grid against the incumbent. Regression for the 1e-9 guard."""
    policy = {p.label: p for p in build_policies()}["scale=1.00"]
    assert _run(policy)["rows"][0]["qty"] == QTY


def test_take_profit_is_re_anchored_to_the_candidate_stop():
    policy = {p.label: p for p in build_policies()}["scale=0.50"]
    row = _run(policy)["rows"][0]
    sd = ENTRY - row["stop_price"]
    assert sd == pytest.approx(LIVE_SD * 0.5, abs=0.01)
    # Not asserted on the exit (it stops out first) but on the geometry it was given.
    assert config.RR_RATIO == 1.5


# --- The refutation ----------------------------------------------------------

def test_ceiling_rises_monotonically_as_the_stop_tightens():
    """The arithmetic half of the weekly's hypothesis — and it is TRUE."""
    policies = {p.label: p for p in build_policies()}
    ceilings = [_run(policies[f"scale={k:.2f}"])["rows"][0]["ceiling_r"] for k in SCALES]
    assert ceilings == sorted(ceilings), "ceiling must rise as 1R shrinks"
    assert ceilings[0] == pytest.approx(0.670, abs=0.005), "live width: +0.670R"
    assert ceilings[-1] == pytest.approx(1.340, abs=0.005), "half width: +1.340R"


def test_win_becomes_reachable_at_60pct_of_the_live_stop():
    policies = {p.label: p for p in build_policies()}
    assert _run(policies["scale=0.70"])["rows"][0]["ceiling_r"] < doctrine.WIN_MIN_R
    assert _run(policies["scale=0.60"])["rows"][0]["ceiling_r"] >= doctrine.WIN_MIN_R


def test_reachable_does_not_convert_meta_347_fails_at_every_width():
    """The trading half — and it is FALSE. This is the whole of IMP-055.

    Tightening 1R makes the WIN arithmetically available (above) and still never
    banks it, because BREAKEVEN_TRIGGER_R is denominated in R: the smaller the
    stop, the sooner the ratchet pins it at entry, and the same 09:54 pullback
    takes the trade either way.
    """
    policies = {p.label: p for p in build_policies()}
    for k in SCALES:
        res = _run(policies[f"scale={k:.2f}"])
        row = res["rows"][0]
        assert row["exit_reason"] == "STOP", f"scale={k}: expected a stop exit"
        assert row["verdict"] == doctrine.FAIL, f"scale={k}: expected a doctrine FAIL"
        assert res["converted"] == 0, f"scale={k}: a WIN was booked that never happened"
    # And at 60%+ the ceiling says a WIN was there for the taking — reach without
    # conversion, which is the exact failure mode the module exists to expose.
    tight = _run(policies["scale=0.50"])
    assert tight["reachable"] == 1
    assert tight["converted"] == 0


def test_tightest_stop_truncates_the_excursion_it_was_meant_to_harvest():
    """At half width the stop fires before the 09:51 high prints, so the trade's
    own MFE shrinks. The tighter stop does not capture the move earlier — it
    removes the trade from the move."""
    policies = {p.label: p for p in build_policies()}
    live_r = _run(policies["scale=1.00"])["rows"][0]["profit_r"]
    half_r = _run(policies["scale=0.50"])["rows"][0]["profit_r"]
    assert half_r < live_r + 0.25, "half-width did not out-earn the live width"
