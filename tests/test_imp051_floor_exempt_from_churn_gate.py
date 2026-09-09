"""IMP-051 tests — the fill-anchored floor is exempt from the churn gate.

IMP-050 (2026-09-08) added the fill-anchored stop floor: while a trade is open
the stop may never sit further than the PLANNED risk below the REAL fill. Its
first live session was 2026-09-08, and it fired **zero times**.

The cause is arithmetic, not a bug in the floor. ``compute_trailed_stop`` ends in
a churn gate — ``candidate <= current_stop + entry * STOP_RATCHET_MIN_PCT/100``
— that exists because the TRAIL re-prices off a moving tape every 60s and Alpaca
rotates the stop-leg order id on every replace. But the floor's size is, by
identity, the adverse slippage::

    floor - initial_stop == fill - plan_entry

and slippage is small. Measured over the post-gate book (114 closed trades,
2026-07-25 onward): **68 filled adverse (60%), and the floor clears the 0.10%
gate on only 21 of them — it is BLOCKED on 47 (69%)**. Median adverse slip is
0.044% of the fill, less than half the gate. So the gate did not tidy the floor
away at the margins; it removed it on the large majority of the trades it was
built for, and IMP-050's own "$34.99 saved over 99 trades" counterfactual — which
computed the floor directly, without the gate — overstated what actually shipped.

2026-09-08's four trades, every one of them (the fixtures below):

    #330 META  favourable -0.1043%  -> no floor, correctly
    #331 XOM   adverse    +0.0841%  -> floor 159.276 vs gate 0.1617  BLOCKED
    #332 TSM   adverse    +0.0480%  -> floor 430.730 vs gate 0.4373  BLOCKED
    #333 XOM   adverse    +0.0199%  -> floor 158.132 vs gate 0.1605  BLOCKED

XOM #331 then rode to the plan stop 159.14 for -$38.40 — the day's whole loss —
having never traded above its fill (0/133 green minutes). Its floor sat at
159.276, 0.136/share above the price its stop actually filled at.

IMP-051 exempts the floor from the gate and leaves the gate governing the two
tape-driven stages. **This cannot churn, and that is the property these tests
pin instead of the old size-based one**: ``entry_price``, ``plan_entry`` and
``initial_stop`` are all fixed for the life of the trade, so once the stop sits
at the floor the candidate can never again beat ``current_stop``. The floor
fires exactly once per trade.

Counterfactual over the 47 blocked trades, replayed against real 1-min bars:
**+$4.13 net, and not one trade is made worse** — 1 exits above the plan stop it
hit anyway (XOM #331, +$2.04), 2 are newly stopped inside the slippage band and
both were headed to the plan stop regardless so both improve (META #195 +$1.54,
WMT #326 +$0.55), 44 unaffected. It is ~$0.09/trade: a correctness fix that
makes ``MAX_RISK_PCT`` mean what it says on the 60% of trades that fill adverse.
No edge is claimed.

These tests pin, in both directions:
  1. every real 2026-09-08 adverse fill now lifts the stop, to the cent;
  2. the raise is SMALLER than the churn gate — i.e. the motivating fact;
  3. the favourable fill still never moves the stop down;
  4. the gate still governs the break-even and trail stages, unchanged;
  5. idempotence — the floor fires once, so the exemption cannot churn;
  6. the capital-protection invariants and IMP-040's geometry are untouched.
"""

import pytest

from bot import config, exits


# --- the real 2026-09-08 session, from the `trades` table ----------------------
# fill = trades.entry_price (corrected to the broker fill at close, and verified
# against the broker's filled_avg_price for all four); plan_entry recovered as
# plan_stop + (tp - plan_stop)/(1 + RR_RATIO), the identity sizing.plan_position
# writes. slip_pct is (fill - plan_entry)/fill * 100.
XOM_331 = dict(fill=161.7000, plan_entry=161.5640, plan_stop=159.1400, qty=15,
               floor=159.2760, slip_pct=+0.0841, exit_price=159.1400)
TSM_332 = dict(fill=437.2860, plan_entry=437.0760, plan_stop=430.5200, qty=5,
               floor=430.7300, slip_pct=+0.0480, exit_price=439.8840)
XOM_333 = dict(fill=160.5400, plan_entry=160.5080, plan_stop=158.1000, qty=15,
               floor=158.1320, slip_pct=+0.0199, exit_price=160.5300)
# the negative control: META #330 filled 0.646 BELOW its signal close
META_330 = dict(fill=619.0800, plan_entry=619.7260, plan_stop=610.4300, qty=4,
                slip_pct=-0.1043)

ADVERSE_0908 = [XOM_331, TSM_332, XOM_333]
IDS_0908 = ["XOM331", "TSM332", "XOM333"]


def _at_floor(t, current_stop=None):
    """compute_trailed_stop with nothing but the floor able to arm.

    ``live`` sits one cent above the fill, which is below both the break-even
    and the trail trigger (+0.25R each), so the floor is the only candidate.
    """
    return exits.compute_trailed_stop(
        t["fill"], t["plan_stop"],
        t["plan_stop"] if current_stop is None else current_stop,
        live_price=t["fill"] + 0.01, plan_entry=t["plan_entry"],
    )


# --- 1. the floor now fires on the real blocked fills -------------------------

@pytest.mark.parametrize("t", ADVERSE_0908, ids=IDS_0908)
def test_every_20260908_adverse_fill_now_lifts_the_stop(t):
    got = _at_floor(t)
    assert got is not None, "IMP-051's whole point: these three were blocked"
    assert got == pytest.approx(round(t["floor"], 2), abs=0.005)
    # and the planned per-share risk is restored exactly
    assert t["fill"] - got == pytest.approx(t["plan_entry"] - t["plan_stop"], abs=0.01)


@pytest.mark.parametrize("t", ADVERSE_0908, ids=IDS_0908)
def test_the_raise_is_smaller_than_the_churn_gate_that_blocked_it(t):
    """The motivating fact, pinned so it cannot silently change back.

    If STOP_RATCHET_MIN_PCT ever applied to the floor again, every one of these
    three would return None — which is exactly what happened on 2026-09-08.
    """
    min_step = t["fill"] * config.STOP_RATCHET_MIN_PCT / 100.0
    assert t["floor"] - t["plan_stop"] < min_step
    assert _at_floor(t) is not None


def test_xom_331_would_have_booked_the_days_loss_smaller():
    """XOM #331 is the regression test: the day's only real loss.

    Never traded above its fill (0/133 green minutes, MFE -0.027R), rode to the
    plan stop 159.14 and filled there for -$38.40 = a full -1.000R. The floor
    sits 0.136/share above that, so the same failed thesis books -$36.36.
    """
    t = XOM_331
    got = _at_floor(t)
    assert got == pytest.approx(159.28, abs=0.005)
    assert got > t["exit_price"], "the floor must clear the stop it actually hit"
    saved = (got - t["exit_price"]) * t["qty"]
    assert saved == pytest.approx(2.10, abs=0.05)
    # still a full FAIL under the doctrine — this is loss reduction, not an edge
    assert got < t["fill"]


# --- 2. the risk direction is unchanged: never wider --------------------------

def test_meta_330_favourable_fill_still_never_moves_the_stop():
    """META #330 filled 0.646 BELOW its signal close. Its floor would sit at
    609.784, UNDER the plan stop — the one-directional guard must refuse it, with
    or without the churn gate."""
    t = META_330
    assert exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"],
        live_price=t["fill"] + 0.01, plan_entry=t["plan_entry"],
    ) is None
    would_be = t["fill"] - (t["plan_entry"] - t["plan_stop"])
    assert would_be < t["plan_stop"]


@pytest.mark.parametrize("t", ADVERSE_0908, ids=IDS_0908)
def test_the_floor_is_never_below_the_plan_stop_nor_above_the_fill(t):
    got = _at_floor(t)
    assert t["plan_stop"] < got < t["fill"]


@pytest.mark.parametrize("t", ADVERSE_0908, ids=IDS_0908)
def test_floor_still_refuses_to_sit_above_the_live_price(t):
    """A sell stop at or above the market is broker-rejected, and a price already
    inside the slippage band has spent its planned risk anyway — there the
    untouched original stop is the protection. Exempting the floor from the churn
    gate must not weaken that guard. (The guard is a strict ``<``; testing
    exactly AT the floor would be decided by float representation, not by the
    rule, so these probe unambiguously below it.)"""
    for below in (0.01, 0.50, 1.00):
        assert exits.compute_trailed_stop(
            t["fill"], t["plan_stop"], t["plan_stop"],
            live_price=t["floor"] - below, plan_entry=t["plan_entry"],
        ) is None


# --- 3. idempotence: the exemption cannot churn -------------------------------

@pytest.mark.parametrize("t", ADVERSE_0908, ids=IDS_0908)
def test_the_floor_fires_exactly_once(t):
    """Every input the floor reads is fixed for the life of the trade, so the
    second poll — and every poll after it — must return None. This is what
    replaces the old size-based churn protection."""
    first = _at_floor(t)
    assert first is not None
    for _ in range(5):
        assert _at_floor(t, current_stop=first) is None


def test_a_sub_cent_floor_improvement_is_not_a_replace():
    """Rounding to the cent must not hand back a no-op. A 0.004 adverse fill
    rounds to the stop the broker already holds; that is an id rotation for
    nothing, so it must be refused."""
    plan_entry, plan_stop = 100.0, 98.5
    fill = plan_entry + 0.004               # floor 98.504 -> rounds to 98.50
    assert exits.compute_trailed_stop(
        fill, plan_stop, plan_stop, live_price=fill + 0.01, plan_entry=plan_entry,
    ) is None


# --- 4. the churn gate still governs the tape-driven stages -------------------

def test_min_step_still_blocks_a_marginal_trail_raise():
    """The trail re-prices every 60s off a moving tape — it is what the gate is
    for, and IMP-051 must not touch it. Here the trail has armed and its
    candidate improves on the current stop by less than 0.10% of entry."""
    fill, plan_stop = 100.0, 98.5            # 1R = 1.5, min_step = 0.10
    live = fill + 0.25 * 1.5                 # exactly the +0.25R trail trigger
    trail_candidate = live - config.TRAIL_DISTANCE_R * 1.5   # == 100.00
    assert exits.compute_trailed_stop(
        fill, plan_stop, current_stop=trail_candidate - 0.05, live_price=live,
    ) is None, "a 0.05 trail improvement must not clear the 0.10 gate"
    # ...and it DOES fire once the improvement clears the gate
    assert exits.compute_trailed_stop(
        fill, plan_stop, current_stop=trail_candidate - 0.20, live_price=live,
    ) == pytest.approx(100.00, abs=0.01)


def test_min_step_still_blocks_a_marginal_breakeven_raise():
    fill, plan_stop = 100.0, 98.5
    peak = fill + 0.25 * 1.5                 # break-even armed on the peak
    assert exits.compute_trailed_stop(
        fill, plan_stop, current_stop=fill - 0.05, live_price=fill - 0.10,
        high_price=peak,
    ) is None
    assert exits.compute_trailed_stop(
        fill, plan_stop, current_stop=fill - 0.50, live_price=fill - 0.10,
        high_price=peak,
    ) == pytest.approx(fill, abs=0.01)


def test_an_armed_stage_outbids_the_floor_and_takes_the_gate_with_it():
    """When break-even or the trail arms, its candidate is at or above the fill
    and therefore above the floor — so the winning candidate is NOT the floor and
    the gate must apply to it again. Pinned on TSM #332, which armed for real."""
    t = TSM_332
    risk = t["fill"] - t["plan_stop"]
    live = t["fill"] + 2.0 * risk            # far past both triggers
    got = exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live, plan_entry=t["plan_entry"],
    )
    assert got is not None and got > t["fill"] > t["floor"]
    # the same armed stage, blocked by the gate when the improvement is marginal
    assert exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], current_stop=got - 0.01, live_price=live,
        plan_entry=t["plan_entry"],
    ) is None


def test_tsm_332_real_ratchet_walk_is_reproduced_with_the_floor_in_place():
    """TSM #332's live walk was 430.52 -> 437.56 -> 438.16 -> 438.68 -> 439.46
    -> 440.13 on five raises. With IMP-051 the floor inserts ONE extra step at
    the front (430.73) and every subsequent level is unchanged, because the
    armed stages never read the floor."""
    t = TSM_332
    assert _at_floor(t) == pytest.approx(430.73, abs=0.005)
    for live, peak, expected in ((439.25, 439.00, 437.56), (439.85, 439.61, 438.16),
                                 (440.37, 440.33, 438.68), (441.15, 440.77, 439.46),
                                 (441.82, 441.76, 440.13)):
        got = exits.compute_trailed_stop(
            t["fill"], t["plan_stop"], expected - 1.0, live, peak,
            plan_entry=t["plan_entry"],
        )
        assert got == pytest.approx(expected, abs=0.01)


# --- 5. backward compatibility and the invariants ----------------------------

@pytest.mark.parametrize("t", ADVERSE_0908, ids=IDS_0908)
def test_omitting_plan_entry_still_reproduces_pre_imp050_behaviour(t):
    """Every caller that does not pass plan_entry (bot/backtest.py, exit_sim's
    parity mirror, the whole pre-IMP-050 suite) must be untouched."""
    assert exits.compute_trailed_stop(
        t["fill"], t["plan_stop"], t["plan_stop"], live_price=t["fill"] + 0.01,
    ) is None


def test_imp051_never_widens_risk_across_a_price_sweep():
    plan_entry, plan_stop = 100.0, 98.5
    for slip in (0.0, 0.004, 0.01, 0.05, 0.10, 0.25, 0.50):
        fill = plan_entry + slip
        got = exits.compute_trailed_stop(
            fill, plan_stop, plan_stop, live_price=fill + 0.01,
            plan_entry=plan_entry,
        )
        assert got is None or got >= plan_stop, "a ratchet may never lower a stop"


def test_risk_limits_and_the_paper_endpoint_are_untouched():
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    from bot import secrets
    assert secrets.ALPACA_PAPER is True


def test_imp040_ratchet_geometry_and_the_churn_gate_value_are_untouched():
    assert config.BREAKEVEN_TRIGGER_R == 0.25
    assert config.TRAIL_TRIGGER_R == 0.25
    assert config.TRAIL_DISTANCE_R == 0.25
    assert config.STOP_RATCHET_MIN_PCT == 0.10
    assert config.MIN_STOP_PCT == 1.5
    assert config.RR_RATIO == 1.5
