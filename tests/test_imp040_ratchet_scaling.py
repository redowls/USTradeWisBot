"""IMP-040 — the stop ratchet moved 0.5R -> 0.25R, as one scaled geometry.

Why the change exists (2026-08-24 daily review): the breakout leg has been
dormant since 2026-07-24, so every entry is now an `MA` cross. MA crosses
mean-revert instead of following through, and their excursions die well below
0.5R — so a ratchet sited at 0.5R sat ABOVE most of this book's MFE
distribution and simply never armed. Sliding the whole ratchet to 0.25R is
exit geometry rebuilt for the signal the bot actually takes.

The fixtures below are the two REAL trades from 2026-08-24 that show both
sides of the trade-off, and they are deliberately paired against the
pre-IMP-040 geometry so the change is *proved* rather than asserted:

  * AAPL #283 — the rescue. Peaked +0.26R, never armed the 0.5R ratchet, and
    drifted to the 15:55 flatten for -$10.45. Under 0.25R it arms and scratches.
  * MSFT #282 — the COST. Ran to +0.80R and banked +$17.34 at the flatten.
    Under 0.25R the tighter trail takes it out far earlier for a fraction of
    that. This test exists so no future run can pretend IMP-040 was free.

Bar paths are the real Alpaca IEX session windows for each trade, compressed
to 15-minute highs/lows (entry -> 15:55 flatten).
"""

from __future__ import annotations

import pandas as pd
import pytest

from bot import config, exits
from bot.exit_sim import ExitGeometry, ratchet_stop, simulate_exit


def _bars(pairs: list[tuple[float, float]]) -> pd.DataFrame:
    return pd.DataFrame({"high": [p[0] for p in pairs],
                         "low": [p[1] for p in pairs]})


LIVE = ExitGeometry.from_config()

# The geometry that was live from IMP-029 (2026-08-08) until IMP-040. Pinned as
# a literal so these paired controls keep documenting what the bot really did on
# 2026-08-24 instead of drifting forward with config.
PRE_IMP040 = ExitGeometry(0.5, 0.5, 0.5, 0.10)

# --- 2026-08-24 AAPL #283: entry 312.0829, plan stop 307.28 (1R = 4.8029) ----
# Peak 313.34 = +0.26R, below the old 0.5R trigger, so nothing ever armed.
# Recorded exit: EOD_FLATTEN 310.59 on qty 7 = -$10.45.
AAPL_ENTRY, AAPL_STOP, AAPL_QTY = 312.0829, 307.28, 7
AAPL_TP, AAPL_FLATTEN = 318.98, 310.57
AAPL_BARS = _bars([
    (312.25, 312.03), (313.19, 312.13), (313.30, 312.82), (313.25, 312.51),
    (313.13, 311.55), (312.44, 311.69), (312.34, 311.72), (312.30, 311.59),
    (311.86, 311.36), (312.01, 311.43), (312.30, 311.87), (313.34, 312.22),
    (312.94, 312.18), (312.46, 311.90), (312.36, 311.75), (312.26, 311.76),
    (312.10, 311.52), (311.88, 311.63), (311.84, 310.73), (311.79, 310.94),
    (311.65, 311.05), (311.55, 311.19), (311.26, 310.68), (311.01, 310.19),
])

# --- 2026-08-24 MSFT #282: entry 484.682, plan stop 477.34 (1R = 7.342) ------
# Peak 490.56 = +0.80R. Armed both stages under the OLD geometry too, but the
# 0.5R trail never caught it, so it rode to the flatten for +$17.34.
MSFT_ENTRY, MSFT_STOP, MSFT_QTY = 484.682, 477.34, 5
MSFT_TP, MSFT_FLATTEN = 495.51, 487.99
MSFT_BARS = _bars([
    (486.70, 483.93), (487.86, 484.70), (486.45, 485.12), (488.12, 485.28),
    (488.70, 486.83), (489.46, 486.59), (489.46, 487.22), (489.35, 488.45),
    (489.86, 488.51), (490.56, 488.59), (489.15, 488.57), (489.35, 488.75),
    (489.23, 488.56), (489.50, 487.85), (489.37, 488.43), (488.94, 487.80),
    (488.20, 487.40), (488.29, 487.29), (488.73, 487.50), (488.90, 487.51),
    (488.43, 487.61), (488.46, 487.38), (489.14, 488.33), (489.06, 488.20),
    (489.00, 487.99),
])


# --- The shipped geometry -----------------------------------------------------

def test_imp040_is_one_scaled_ratchet_at_the_shipped_value():
    """All three constants moved together to 0.25R — that is the whole change."""
    assert config.BREAKEVEN_TRIGGER_R == 0.25
    assert config.TRAIL_TRIGGER_R == 0.25
    assert config.TRAIL_DISTANCE_R == 0.25
    # IMP-029's shape is preserved: break-even and the trail arm at the SAME
    # point, so the two stages remain one continuous ratchet with no dead band.
    assert config.TRAIL_TRIGGER_R == config.BREAKEVEN_TRIGGER_R
    # And the IMP-029 config invariants still hold at the new scale.
    assert config.TRAIL_DISTANCE_R < 1.0
    assert config.TRAIL_DISTANCE_R <= config.TRAIL_TRIGGER_R
    assert config.TRAIL_TRIGGER_R <= config.BREAKEVEN_TRIGGER_R


def test_imp040_trail_is_not_inert_at_the_new_trigger():
    """IMP-029's arithmetic guard, re-asserted at 0.25R.

    Scaling the ratchet must not reintroduce the dead band: comfortably past
    the trigger the stop still has to lift ABOVE entry.
    """
    risk = MSFT_ENTRY - MSFT_STOP
    well_past = MSFT_ENTRY + (config.TRAIL_TRIGGER_R + 0.5) * risk
    moved = ratchet_stop(MSFT_ENTRY, MSFT_STOP, MSFT_ENTRY, well_past, LIVE)
    assert moved is not None, "trail is inert — the IMP-029 dead zone is back"
    assert moved > MSFT_ENTRY


@pytest.mark.parametrize("live_price", [305.00, 312.0829, 313.34, 314.50,
                                        316.00, 320.00])
def test_imp040_ratchet_still_matches_the_live_implementation(live_price):
    """exit_sim and exits.compute_trailed_stop must agree at the NEW constants.

    The book evidence for IMP-040 was produced by exit_sim; if it diverges from
    the code the bot actually runs, that evidence is worthless.
    """
    assert ratchet_stop(AAPL_ENTRY, AAPL_STOP, AAPL_STOP, live_price, LIVE) == \
        exits.compute_trailed_stop(AAPL_ENTRY, AAPL_STOP, AAPL_STOP, live_price)


# --- The benefit, and its paired control -------------------------------------

def test_imp040_rescues_aapl_283():
    """AAPL #283 peaked +0.26R and bled to the flatten. 0.25R scratches it."""
    sim = simulate_exit(AAPL_BARS, AAPL_ENTRY, AAPL_STOP, AAPL_TP,
                        fallback_exit_price=AAPL_FLATTEN, geometry=LIVE)
    assert sim.armed_breakeven is True, "0.25R must arm on a +0.26R excursion"
    assert sim.exit_reason == "STOP"
    # It leaves at (or a hair above) entry instead of the recorded -$10.45.
    pl = (sim.exit_price - AAPL_ENTRY) * AAPL_QTY
    assert pl > -1.0, f"expected a scratch, got ${pl:.2f}"
    assert pl > -10.45, "must beat the recorded EOD_FLATTEN loss"


def test_imp040_without_the_change_aapl_283_still_bled_out():
    """The paired control: under the OLD 0.5R ratchet nothing arms.

    This is what makes the test above a regression rather than a tautology —
    revert the geometry and AAPL goes back to losing real money.
    """
    sim = simulate_exit(AAPL_BARS, AAPL_ENTRY, AAPL_STOP, AAPL_TP,
                        fallback_exit_price=AAPL_FLATTEN, geometry=PRE_IMP040)
    assert sim.armed_breakeven is False, "+0.26R never reached the old 0.5R trigger"
    assert sim.exit_reason == "EOD_FLATTEN"
    assert (sim.exit_price - AAPL_ENTRY) * AAPL_QTY < -10.0


# --- The cost, pinned so it cannot be quietly forgotten ----------------------

def test_imp040_costs_msft_282_most_of_its_upside():
    """IMP-040 is NOT free: the tighter trail caps the day's best trade.

    MSFT #282 ran +0.80R and banked +$17.34 riding to the 15:55 flatten. Under
    0.25R the trail takes it out early for a fraction of that. Recorded here on
    purpose — the book-level case for IMP-040 is a NET one, and any future run
    judging it must weigh this side too. If this ever starts passing with the
    full +$17.34 intact, the geometry has silently drifted back.
    """
    sim = simulate_exit(MSFT_BARS, MSFT_ENTRY, MSFT_STOP, MSFT_TP,
                        fallback_exit_price=MSFT_FLATTEN, geometry=LIVE)
    assert sim.armed_trail is True
    assert sim.exit_reason == "STOP"
    pl = (sim.exit_price - MSFT_ENTRY) * MSFT_QTY
    assert pl > 0.0, "the trail must still bank a profit, just a smaller one"
    assert pl < 17.34, "this is the cost side — it must be smaller than the flatten"

    old = simulate_exit(MSFT_BARS, MSFT_ENTRY, MSFT_STOP, MSFT_TP,
                        fallback_exit_price=MSFT_FLATTEN, geometry=PRE_IMP040)
    assert old.exit_reason == "EOD_FLATTEN"
    assert (old.exit_price - MSFT_ENTRY) * MSFT_QTY > pl


# --- Capital protection -------------------------------------------------------

@pytest.mark.parametrize("live_price", [300.0, 307.28, 310.0, 312.0829, 313.0,
                                        313.34, 315.0, 318.0, 325.0, 340.0])
def test_imp040_never_widens_risk(live_price):
    """A tighter ratchet may only ever hold a HIGHER stop than the old one.

    The invariant that makes this change safe by construction: at every price,
    the 0.25R stop is >= the 0.5R stop, and neither is ever below the original
    1R plan stop. Max loss per trade is therefore unchanged.
    """
    new = ratchet_stop(AAPL_ENTRY, AAPL_STOP, AAPL_STOP, live_price, LIVE)
    old = ratchet_stop(AAPL_ENTRY, AAPL_STOP, AAPL_STOP, live_price, PRE_IMP040)
    new_stop = AAPL_STOP if new is None else new
    old_stop = AAPL_STOP if old is None else old
    assert new_stop >= old_stop, "IMP-040 must never sit BELOW the old stop"
    assert new_stop >= AAPL_STOP, "the ratchet must never go below the plan stop"


def test_imp040_ratchet_is_monotonic_as_price_rises():
    """Sweeping price upward, the stop may only ever move up or hold."""
    risk = AAPL_ENTRY - AAPL_STOP
    prev = AAPL_STOP
    for step in range(0, 40):
        live = AAPL_ENTRY + (step * 0.05 - 0.5) * risk
        moved = ratchet_stop(AAPL_ENTRY, AAPL_STOP, prev, live, LIVE)
        current = prev if moved is None else moved
        assert current >= prev, f"stop moved DOWN at live={live:.4f}"
        prev = current


def test_imp040_leaves_every_risk_limit_untouched():
    """IMP-040 is exit geometry only — no risk limit, no sizing, no entry rule."""
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    assert config.MIN_STOP_PCT == 1.5
    assert config.TRAILING_STOP_ENABLED is True
