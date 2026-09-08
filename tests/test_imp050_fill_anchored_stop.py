"""IMP-050 tests — the fill-anchored stop floor.

The bracket is sited from the SIGNAL-BAR CLOSE (``bot/sizing.py`` prices entry,
stop and take-profit off it), but the order is a MARKET buy that fills at the
live price. ``trades.stop_price`` therefore stays a planned ``d`` below a price
the bot never paid, while ``trades.entry_price`` is corrected to the real fill
when the trade closes — so a trade that filled ``slip`` above the signal close
carries ``d + slip`` of risk per share against a stop the plan sited at ``d``.

Measured over the 110 post-gate closed trades (2026-09-08 daily review):

    44 (40%) filled adverse; worst +0.266R (WMT #243)
    25 (23%) carried >5% more per-share risk than planned, max 1.266x
    true reward:risk (tp - fill)/(fill - stop): median 1.478 vs RR_RATIO 1.5,
        65 of 110 below the configured ratio, 1 below 1.0
    META #315's +0.211R adverse fill made its take-profit a +1.072R exit

IMP-037 already clamps the SHARE COUNT against this, but it clamps on the
pre-submit ``live`` quote and it never moves the stop, so the residual fill gap
and the bracket's geometry stay uncorrected. IMP-050 adds a floor: while a trade
is open the stop may never sit further than the PLANNED risk below the REAL
fill.

Strictly tightening by construction — ``floor - initial_stop == fill -
plan_entry`` — so the floor is above the plan stop only on an adverse fill and a
favourable fill leaves the plan stop untouched. Replayed over the 99 post-gate
trades with 1-min bar coverage: 0 additional stop-outs, $34.99 saved on the 10
that hit the plan stop anyway.

These tests pin, in both directions:
  1. the floor fires on real recorded adverse fills, to the cent;
  2. it does NOT fire on real recorded favourable fills (never widens risk);
  3. omitting ``plan_entry`` reproduces the pre-IMP-050 behaviour exactly;
  4. the guards — below the live price, above the current stop, min-step;
  5. the armed ratchet stages still win, and the result is still monotonic;
  6. the capital-protection invariants.
"""

import pytest

from bot import config, exits


# --- real recorded trades, from the `trades` table -----------------------------
# fill = trades.entry_price (corrected to the broker fill at close)
# plan_entry / plan_stop / tp = the plan legs the bracket was submitted with,
# with plan_entry recovered exactly as plan_stop + (tp - plan_stop)/(1+RR_RATIO).
META_315 = dict(fill=587.6300, plan_entry=585.7740, plan_stop=576.9900, qty=3)
WMT_243 = dict(fill=112.9264, plan_entry=112.4780, plan_stop=110.7900, qty=22)
NFLX_244 = dict(fill=76.1900, plan_entry=75.9760, plan_stop=74.8400, qty=33)
MU_273 = dict(fill=978.7000, plan_entry=976.2340, plan_stop=961.5900, qty=2)
# favourable fills — the negative controls
INTC_298 = dict(fill=89.6029, plan_entry=89.8800, plan_stop=88.1400, qty=21)
WMT_320 = dict(fill=106.4300, plan_entry=106.4900, plan_stop=104.8900, qty=23)

ADVERSE = [META_315, WMT_243, NFLX_244, MU_273]
FAVOURABLE = [INTC_298, WMT_320]


def _floor(t):
    """The planned-risk stop measured from the real fill."""
    return t["fill"] - (t["plan_entry"] - t["plan_stop"])


# --- 1. the floor fires on real adverse fills ---------------------------------

def test_meta_315_adverse_fill_lifts_the_stop_to_the_planned_risk():
    """META #315 filled +1.856 (+0.211R) above the signal close.

    Its stop sat 10.64 below the fill against a planned 8.784, so it carried
    21% more risk per share than the sizer chose. The floor restores it.
    """
    t = META_315
    got = exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live_price=586.00,
        plan_entry=t["plan_entry"],
    )
    assert got == pytest.approx(578.85, abs=0.01)   # 587.63 - 8.784
    assert got > t["plan_stop"]
    # risk per share falls from 10.64 back to the planned 8.784
    assert t["fill"] - got == pytest.approx(8.784, abs=0.01)
    assert t["fill"] - t["plan_stop"] == pytest.approx(10.64, abs=0.01)


@pytest.mark.parametrize("t", ADVERSE, ids=["META315", "WMT243", "NFLX244", "MU273"])
def test_every_adverse_fill_is_pulled_back_to_exactly_the_planned_risk(t):
    live = t["fill"] + 0.01          # just above the fill: nothing else arms
    got = exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live, plan_entry=t["plan_entry"],
    )
    assert got is not None, "an adverse fill must lift the stop"
    assert got == pytest.approx(_floor(t), abs=0.01)
    planned_risk = t["plan_entry"] - t["plan_stop"]
    assert t["fill"] - got == pytest.approx(planned_risk, abs=0.01)


def test_nflx_244_would_have_exited_above_the_plan_stop_it_actually_hit():
    """NFLX #244 rode to a full -1R and filled its stop at 74.84 for -$44.55.

    It is the cost-free half of the change: the floor sits at 75.054, ABOVE the
    stop the trade hit anyway, so the same loss is booked 0.214/share smaller.
    """
    t = NFLX_244
    got = exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live_price=76.20,
        plan_entry=t["plan_entry"],
    )
    assert got == pytest.approx(75.05, abs=0.01)
    assert got > 74.84                       # the price the real stop filled at
    saved = (got - 74.84) * t["qty"]            # 33 shares x 0.21 after rounding
    assert saved == pytest.approx(6.93, abs=0.05)


# --- 2. favourable fills are left alone — the change can never widen risk ------

@pytest.mark.parametrize("t", FAVOURABLE, ids=["INTC298", "WMT320"])
def test_favourable_fill_never_moves_the_stop_down(t):
    """A fill BELOW the signal close means the plan stop is already tighter than
    the planned risk. The floor must not reach down to it and hand risk back."""
    assert _floor(t) < t["plan_stop"], "fixture must be a favourable fill"
    live = t["fill"] + 0.01
    got = exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live, plan_entry=t["plan_entry"],
    )
    assert got is None


def test_favourable_fill_floor_is_rejected_even_when_a_lower_leg_would_accept_it():
    """The `initial_stop < floor` guard, pinned where the downstream min-step
    check cannot stand in for it.

    `current_stop` is read from the BROKER leg, not from the plan. If that leg
    ever sits below the plan stop, a floor computed from a FAVOURABLE fill is
    both below the plan stop and above the broker leg — so the monotonic check
    would happily return it. It must still be refused: on a favourable fill
    there is no excess risk to correct, and the plan stop is the anchor.
    """
    t = INTC_298
    floor = _floor(t)                                   # 87.8629
    assert floor < t["plan_stop"], "fixture must be a favourable fill"
    stale_broker_leg = 87.00
    assert stale_broker_leg < floor < t["plan_stop"]
    got = exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], stale_broker_leg, live_price=t["fill"] + 0.01,
        plan_entry=t["plan_entry"],
    )
    assert got is None, "a favourable fill must never produce a floor at all"


def test_intc_298_the_book_s_best_trade_is_untouched():
    """INTC #298 (+$60.84, the only +1.98R in the book) filled 0.277 BELOW its
    signal close. Nothing about it may change."""
    t = INTC_298
    for live in (89.61, 90.50, 91.00):
        got = exits.compute_trailed_stop(
            t["fill"], t["plan_stop"], t["plan_stop"], live,
            plan_entry=t["plan_entry"],
        )
        without = exits.compute_trailed_stop(
            t["fill"], t["plan_stop"], t["plan_stop"], live,
        )
        assert got == without


@pytest.mark.parametrize("slip", [-0.50, -0.10, -0.01, 0.0, 0.01, 0.10, 0.50, 1.00])
def test_stop_is_monotone_non_decreasing_in_slippage_and_never_below_plan(slip):
    """Sweep the fill across the plan price: the returned stop is never BELOW
    the plan stop, at any slippage, in either direction."""
    plan_entry, plan_stop = 100.0, 98.5
    fill = plan_entry + slip
    got = exits.compute_trailed_stop(
        fill, plan_stop, plan_stop, live_price=fill + 0.01, plan_entry=plan_entry,
    )
    if got is not None:
        assert got >= plan_stop
        assert got <= fill        # a stop at/above the fill is not a stop


# --- 3. backward compatibility -------------------------------------------------

@pytest.mark.parametrize("t", ADVERSE + FAVOURABLE)
def test_omitting_plan_entry_reproduces_pre_imp050_behaviour(t):
    """Every caller that does not pass plan_entry (bot/backtest.py, exit_sim's
    parity mirror, the whole existing test suite) must be byte-identical."""
    for live in (t["fill"] - 0.50, t["fill"], t["fill"] + 0.50, t["fill"] + 5.0):
        assert exits.compute_trailed_stop(
            t["fill"], t["plan_stop"], t["plan_stop"], live,
        ) == exits.compute_trailed_stop(
            t["fill"], t["plan_stop"], t["plan_stop"], live, plan_entry=None,
        )


def test_the_classic_base_case_is_unchanged_when_the_fill_matched_the_plan():
    """entry 100 / stop 98.5 with no slippage: the floor is exactly the plan
    stop, so every pre-IMP-050 assertion still holds."""
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 100.30, plan_entry=100.0) is None
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 100.375, plan_entry=100.0) == 100.0
    assert exits.compute_trailed_stop(100.0, 98.5, 100.0, 103.00, plan_entry=100.0) == 102.62


# --- 4. guards -----------------------------------------------------------------

def test_floor_is_not_applied_at_or_above_the_live_price():
    """A sell stop at or above the market is rejected by the broker. If price has
    already fallen into the slippage band, the original stop is the protection."""
    t = META_315
    floor = _floor(t)                                   # 578.846
    assert exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live_price=floor - 0.01,
        plan_entry=t["plan_entry"],
    ) is None
    assert exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live_price=floor,
        plan_entry=t["plan_entry"],
    ) is None
    assert exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live_price=floor + 0.05,
        plan_entry=t["plan_entry"],
    ) == pytest.approx(578.85, abs=0.01)


def test_floor_respects_the_min_step_and_cannot_churn_the_broker():
    """A one-cent adverse fill is not worth a replace round-trip."""
    plan_entry, plan_stop = 100.0, 98.5
    fill = plan_entry + 0.01                # floor 98.51, min_step 0.10% = 0.10
    assert exits.compute_trailed_stop(
        fill, plan_stop, plan_stop, live_price=fill + 0.01, plan_entry=plan_entry,
    ) is None


def test_floor_never_lowers_a_stop_the_ratchet_already_raised():
    """Once break-even armed, the stop sits at the fill — far above the floor."""
    t = META_315
    already_at_breakeven = t["fill"]
    assert exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], already_at_breakeven, live_price=590.0,
        plan_entry=t["plan_entry"],
    ) is None


def test_armed_stages_still_win_over_the_floor():
    """With the trade +1R up, break-even/trail must decide the stop, not the
    floor — the floor is a starting condition, not a ceiling."""
    t = META_315
    live = t["fill"] + 2.0 * (t["fill"] - t["plan_stop"])
    got = exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live, plan_entry=t["plan_entry"],
    )
    assert got is not None
    assert got > t["fill"] > _floor(t)


def test_degenerate_plan_entry_values_are_ignored():
    for bad in (0.0, -1.0, 98.5, 90.0):     # zero, negative, at/below the stop
        got = exits.compute_trailed_stop(
            100.20, 98.5, 98.5, live_price=100.25, plan_entry=bad,
        )
        without = exits.compute_trailed_stop(100.20, 98.5, 98.5, live_price=100.25)
        assert got == without


# --- 5. capital-protection invariants -----------------------------------------

def test_imp050_never_widens_risk_across_a_price_sweep():
    """For every price and both slippage directions, the stop this function
    returns is >= the plan stop. Risk per share can only fall."""
    plan_entry, plan_stop = 250.0, 246.25          # 1.5% stop
    for slip in (-1.0, -0.25, 0.0, 0.25, 1.0, 2.0):
        fill = plan_entry + slip
        for live in [fill + i * 0.5 for i in range(0, 20)]:
            got = exits.compute_trailed_stop(
                fill, plan_stop, plan_stop, live, plan_entry=plan_entry,
            )
            if got is not None:
                assert got >= plan_stop


def test_risk_limits_and_the_paper_endpoint_are_untouched():
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    from bot import secrets
    assert secrets.ALPACA_PAPER is True


def test_imp040_ratchet_geometry_is_untouched_by_this_run():
    """IMP-050 changes where the stop STARTS, never where the ratchet arms."""
    assert config.BREAKEVEN_TRIGGER_R == 0.25
    assert config.TRAIL_TRIGGER_R == 0.25
    assert config.TRAIL_DISTANCE_R == 0.25
    assert config.RR_RATIO == 1.5
