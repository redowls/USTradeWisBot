"""IMP-037 — sizing must key off the risk the trade ACTUALLY takes.

`plan_position` anchors entry/stop/take-profit to the signal-bar close and sizes
with ``floor(budget / stop_distance)``, but the order is a MARKET buy filling at
the live price. When the market has run up since the signal bar the stop does
not follow it, so real risk per share is ``stop_distance + move`` while the share
count still divides by ``stop_distance``.

IMP-008 (2026-06-30) named this defect exactly — "the stop now sits that much
further from the real fill, silently inflating per-share risk above the plan" —
and then fixed only the extreme case, skipping gaps beyond
MAX_ENTRY_SLIPPAGE_PCT. The accepted band 0..1.0% kept sizing off a risk it does
not take. Measured over all 253 closed trades on 2026-08-19: 106 (41.9%) risked
more than budget, mean overshoot +8.6%, worst SE 2026-07-02 at +72.5%.

The scenarios below are the real recorded trades that motivated the fix, so the
failure becomes a regression test. Note the direction of the money: on 08-19 the
correction would have REDUCED a winner (CRM +$49.20 -> +$41.00). It ships because
the bot must risk what it says it risks, not because it pays on the day.
"""

from __future__ import annotations

import math

import pytest

from bot import config, sizing
from bot.sizing import PositionPlan


def _plan(**over) -> PositionPlan:
    """A tradable plan shaped like the ones plan_position emits."""
    base = dict(
        symbol="CRM", confidence=60.45, tradable=True, skip_reason=None,
        entry_price=199.98, risk_fraction_pct=0.5, stop_distance=3.0,
        shares=12, stop_price=196.98, take_profit_price=204.48,
        dollar_risk=36.0, dollar_risk_pct=0.486, notional=2399.76,
    )
    base.update(over)
    return PositionPlan(**base)


# --- the trade that exposed it: CRM, 2026-08-19 --------------------------------

def test_crm_2026_08_19_is_resized_to_its_real_risk():
    """Fill 0.21% above the signal close turned a $36.00 budget into $41.04."""
    equity = 7406.92
    plan = _plan()
    # What actually happened: 12 shares against a real 3.42 risk/share.
    assert plan.shares * (200.40 - plan.stop_price) == pytest.approx(41.04, abs=0.01)
    assert 41.04 / (equity * 0.005) > 1.10          # >10% over the 0.5% budget

    out = sizing.resize_for_live_risk(plan, 200.40, equity)

    assert out.shares == 10
    assert out.shares * (200.40 - out.stop_price) == pytest.approx(34.20, abs=0.01)
    # ...which is now INSIDE the budget it was sized against.
    assert out.shares * (200.40 - out.stop_price) <= equity * 0.005


def test_crm_resize_leaves_the_bracket_geometry_alone():
    """Only share count and its derived $ fields move: 1R must stay comparable."""
    plan = _plan()
    out = sizing.resize_for_live_risk(plan, 200.40, 7406.92)

    assert out.stop_price == plan.stop_price
    assert out.take_profit_price == plan.take_profit_price
    assert out.stop_distance == plan.stop_distance
    assert out.entry_price == plan.entry_price
    assert out.risk_fraction_pct == plan.risk_fraction_pct
    assert out.tradable is True and out.skip_reason is None
    assert out.notional == pytest.approx(out.shares * plan.entry_price, abs=0.01)


def test_aapl_2026_08_19_favourable_fill_is_untouched():
    """AAPL #267 filled 0.005% BELOW its signal close — nothing to correct."""
    plan = _plan(symbol="AAPL", entry_price=311.636, stop_price=306.96,
                 take_profit_price=318.65, stop_distance=4.676, shares=7)
    out = sizing.resize_for_live_risk(plan, 311.62, 7406.92)
    assert out.shares == 7
    assert out is plan


# --- the invariant that makes this safe to ship --------------------------------

@pytest.mark.parametrize("live_offset_pct", [-2.0, -1.0, -0.5, -0.1, 0.0])
def test_favourable_or_flat_fills_never_buy_more_size(live_offset_pct):
    """A fill at or below the signal close must NEVER increase the share count."""
    plan = _plan()
    live = plan.entry_price * (1 + live_offset_pct / 100.0)
    out = sizing.resize_for_live_risk(plan, live, 7406.92)
    assert out.shares <= plan.shares


@pytest.mark.parametrize("live_offset_pct", [0.05, 0.1, 0.25, 0.5, 0.75, 1.0])
def test_size_is_monotonically_non_increasing_in_adverse_move(live_offset_pct):
    """More adverse move => never more shares, and never above the risk budget."""
    equity = 7406.92
    plan = _plan()
    live = plan.entry_price * (1 + live_offset_pct / 100.0)
    out = sizing.resize_for_live_risk(plan, live, equity)

    assert out.shares <= plan.shares
    realised_risk = out.shares * (live - out.stop_price)
    budget = equity * plan.risk_fraction_pct / 100.0
    # Within one share of the budget (floor division leaves at most that slack).
    assert realised_risk <= budget + (live - out.stop_price)


def test_resize_is_monotone_across_the_whole_guard_band():
    """Share count must be non-increasing as the adverse move grows."""
    equity = 7406.92
    plan = _plan()
    counts = [
        sizing.resize_for_live_risk(
            plan, plan.entry_price * (1 + pct / 100.0), equity,
        ).shares
        for pct in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    ]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] == plan.shares


def test_worst_recorded_overshoot_se_2026_07_02_is_capped():
    """SE risked $144.54 against an $83.81 budget (+72.5%) — the book's worst.

    The structural ceiling: MAX_ENTRY_SLIPPAGE_PCT (1.0%) over a MIN_STOP_PCT
    (1.5%) stop admits ~+67% more risk than budgeted.
    """
    equity = 8300.0
    budget = 83.81
    stop_distance = 2.0
    planned = math.floor(budget / stop_distance)        # 41 shares
    entry = 133.0
    plan = _plan(symbol="SE", entry_price=entry, stop_price=entry - stop_distance,
                 take_profit_price=entry + stop_distance * config.RR_RATIO,
                 stop_distance=stop_distance, shares=planned,
                 risk_fraction_pct=100.0 * budget / equity)

    live = entry * 1.01                                  # the guard's outer edge
    assert planned * (live - plan.stop_price) > budget * 1.5   # the defect

    out = sizing.resize_for_live_risk(plan, live, equity)
    assert out.shares < planned
    assert out.shares * (live - out.stop_price) <= budget + (live - out.stop_price)


# --- fail-open / degenerate inputs ---------------------------------------------

@pytest.mark.parametrize("live", [None, 0.0, -5.0])
def test_unknown_or_invalid_live_price_fails_open(live):
    plan = _plan()
    assert sizing.resize_for_live_risk(plan, live, 7406.92) is plan


def test_live_price_at_or_below_the_stop_is_left_to_the_upstream_guard():
    """The down-gap case IMP-009 skips — never divide by a non-positive risk."""
    plan = _plan()
    assert sizing.resize_for_live_risk(plan, plan.stop_price, 7406.92) is plan
    assert sizing.resize_for_live_risk(plan, plan.stop_price - 1.0, 7406.92) is plan


def test_untradable_plan_is_passed_through():
    plan = _plan(tradable=False, skip_reason="already_held", shares=0)
    assert sizing.resize_for_live_risk(plan, 200.40, 7406.92) is plan


def test_zero_equity_fails_open():
    plan = _plan()
    assert sizing.resize_for_live_risk(plan, 200.40, 0.0) is plan


def test_size_below_one_share_becomes_a_skip_not_a_naked_order():
    """Degenerate case: never emit a tradable plan with <1 share."""
    plan = _plan(shares=1, stop_distance=3.0, risk_fraction_pct=0.5)
    out = sizing.resize_for_live_risk(plan, 260.0, 100.0)   # budget $0.50
    assert out.tradable is False
    assert out.skip_reason == "live_risk_size<1_share"
    assert out.shares == 0


# --- capital-protection invariants: unmoved by this change ---------------------

def test_capital_protection_invariants_untouched():
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    assert config.MAX_ENTRY_SLIPPAGE_PCT == 1.0
    assert config.MIN_STOP_PCT == 1.5
    assert sizing.ladder_risk_is_non_increasing()


def test_resize_can_only_ever_lower_realised_risk():
    """Across the whole admissible band, resized risk <= planned-share risk."""
    equity = 7406.92
    plan = _plan()
    for pct in [-1.0, -0.5, 0.0, 0.1, 0.25, 0.5, 0.75, 1.0]:
        live = plan.entry_price * (1 + pct / 100.0)
        out = sizing.resize_for_live_risk(plan, live, equity)
        assert out.shares * (live - plan.stop_price) <= plan.shares * (live - plan.stop_price)
