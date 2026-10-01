"""IMP-067 — a 'break-even' FAIL must not claim capital protection it never got.

``doctrine.fail_kind`` splits FAIL on ``profit_R`` alone, so every STOP loss in
``(FULL_STOP_MAX_R, FAIL_MAX_R]`` is named 'break-even' — a label whose meaning
is "IMP-013/040 armed the stop to the fill and the trade came back to it". Since
IMP-050/051 shipped (2026-09-08) that inference is unsafe: the fill-anchored
floor raises the stop on an **adverse fill alone**, with the trade never going
green, writing a ``final_stop_price`` above the plan stop but far below entry.

The anchor case is **AAPL #358 (2026-09-30)**: one raise, a +0.36 floor lift
(0.066R — exactly its adverse slippage), MFE +0.176R so the 0.5R break-even
stage never came within a third of arming, stopped at -0.719R for -$23.42 — and
it reported as 'break-even'. Its sibling **AMZN #359** that same session is the
genuine article: the ratchet armed to 250.27 against a 250.2722 fill at 10:56
and price came back to it 3h28m later for -$0.16.

``stop_was_armed`` answers the mechanism question from the recorded stop, and
returns None rather than False when there is nothing recorded to check. These
tests pin that it changes no verdict: every WIN/SCRATCH/FAIL label and every
``fail_kind`` must be exactly what it was before.

Pure: no DB, no network. Rows are verbatim from the live `trades` table.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from bot import analytics, doctrine

# --- the 2026-09-30 session, verbatim from dbo.trades ----------------------
# All three entered within 4 seconds at 10:06 ET on ORB conf 70 and all three
# exited on a stop. stop_raises/final_stop_price are the recorded values.

AAPL_358 = dict(trade_id=358, symbol="AAPL", qty=6,
                entry_price=338.5217, stop_price=333.09, take_profit=345.77,
                exit_price=334.6183, realized_pl=-23.42, exit_reason="STOP",
                stop_raises=1, final_stop_price=333.45,
                entry_time=datetime(2026, 9, 30, 10, 6, 7),
                exit_time=datetime(2026, 9, 30, 15, 50, 7))      # -0.719R
AMZN_359 = dict(trade_id=359, symbol="AMZN", qty=9,
                entry_price=250.2722, stop_price=246.40, take_profit=255.78,
                exit_price=250.2544, realized_pl=-0.16, exit_reason="STOP",
                stop_raises=2, final_stop_price=250.27,
                entry_time=datetime(2026, 9, 30, 10, 6, 9),
                exit_time=datetime(2026, 9, 30, 14, 24, 10))     # -0.005R
GOOG_360 = dict(trade_id=360, symbol="GOOG", qty=6,
                entry_price=347.8033, stop_price=342.43, take_profit=355.47,
                exit_price=342.1783, realized_pl=-33.75, exit_reason="STOP",
                stop_raises=1, final_stop_price=342.59,
                entry_time=datetime(2026, 9, 30, 10, 6, 11),
                exit_time=datetime(2026, 9, 30, 15, 52, 52))     # -1.047R

SESSION_0930 = [AAPL_358, AMZN_359, GOOG_360]

# 2026-07-10 TSLA #139: the known un-checkable row. IMP-053's own docstring
# records that its stop HAD been raised, but final_stop_price is NULL and
# stop_raises is 0 because IMP-043 recovered raises from a rotating log that had
# already dropped the line. This must read "unknown", never "unarmed".
TSLA_139 = dict(trade_id=139, symbol="TSLA", entry_price=411.079,
                stop_price=402.91, exit_price=405.1, realized_pl=-119.38,
                exit_reason="STOP", stop_raises=0, final_stop_price=None,
                exit_time=datetime(2026, 7, 10, 14, 30, 0))      # -0.731R


# --- the anchor case ------------------------------------------------------

def test_aapl_358_reports_break_even_but_its_stop_never_armed():
    """The trade that motivated IMP-067, pinned end to end."""
    assert doctrine.classify(AAPL_358) == doctrine.FAIL
    assert doctrine.fail_kind(AAPL_358) == "break-even"       # unchanged label
    assert doctrine.stop_was_armed(AAPL_358) is False         # the correction
    # It is nowhere near the break-even trigger: the whole lift is the slippage.
    lift = AAPL_358["final_stop_price"] - AAPL_358["stop_price"]
    risk = AAPL_358["entry_price"] - AAPL_358["stop_price"]
    assert lift / risk == pytest.approx(0.0666, abs=0.001)
    # IMP-051's identity: the floor's size IS the adverse slippage (the fill
    # minus the 338.16 signal-bar close the bracket was sited from), to the cent
    # `compute_trailed_stop` rounds it to.
    assert lift == pytest.approx(AAPL_358["entry_price"] - 338.16, abs=0.005)
    assert doctrine.profit_r(AAPL_358) == pytest.approx(-0.719, abs=0.005)


def test_amzn_359_is_the_genuine_break_even_and_the_cent_rounding_still_counts():
    """The sibling that DID arm — and whose armed stop sits $0.0022 below the fill.

    ``exits.compute_trailed_stop`` returns ``round(candidate, 2)``, so a stop
    armed to the fill is persisted up to half a cent under it. Without
    ARMED_STOP_EPSILON this genuinely-armed stop would read as never armed,
    which would be the same error in the opposite direction.
    """
    assert AMZN_359["final_stop_price"] < AMZN_359["entry_price"]
    assert doctrine.stop_was_armed(AMZN_359) is True
    assert doctrine.fail_kind(AMZN_359) == "break-even"
    assert doctrine.classify(AMZN_359) == doctrine.FAIL


def test_goog_360_is_a_full_1r_loss_and_also_never_armed():
    assert doctrine.fail_kind(GOOG_360) == "full-1R"
    assert doctrine.stop_was_armed(GOOG_360) is False


def test_unrecorded_final_stop_is_unknown_not_unarmed():
    assert doctrine.stop_was_armed(TSLA_139) is None
    assert doctrine.stop_was_armed({"entry_price": 100.0}) is None
    assert doctrine.stop_was_armed({"final_stop_price": 99.0}) is None
    # a zero/absurd fill is unanswerable, not False
    assert doctrine.stop_was_armed({"entry_price": 0.0,
                                    "final_stop_price": 1.0}) is None


@pytest.mark.parametrize("final, expected", [
    (100.0, True),                                   # exactly the fill
    (100.0 - doctrine.ARMED_STOP_EPSILON, True),     # the rounding slack edge
    (100.0 - doctrine.ARMED_STOP_EPSILON - 0.001, False),
    (101.0, True),                                   # trailed above the fill
    (98.5, False),                                   # still the plan stop
])
def test_armed_boundary_is_the_fill_minus_the_cent_rounding_slack(final, expected):
    row = dict(entry_price=100.0, stop_price=98.5, exit_price=99.0,
               realized_pl=-1.0, exit_reason="STOP", final_stop_price=final)
    assert doctrine.stop_was_armed(row) is expected


# --- it must change no verdict -------------------------------------------

def test_the_0930_session_verdicts_are_untouched():
    """IMP-067 is additive: the mandated split is exactly what it was."""
    d = doctrine.summarize(SESSION_0930)
    assert d["trades"] == 3
    assert (d["win"], d["scratch"], d["fail"]) == (0, 0, 3)
    assert d["fail_kinds"] == {"full-1R": 1, "break-even": 2, "faded": 0}
    assert d["stops"] == 3 and d["stop_rate"] == 100.0
    assert d["true_win_rate"] == 0.0 and d["headline_win_rate"] == 0.0
    assert d["fail_scratch_share"] == 100.0
    assert d["total_pl"] == -57.33


def test_summarize_audits_the_break_even_count_against_the_recorded_stop():
    d = doctrine.summarize(SESSION_0930)
    assert d["break_even_armed"] == {"armed": 1, "unarmed": 1, "unknown": 0}
    # the audit only ever covers the 'break-even' rows
    assert (sum(d["break_even_armed"].values())
            == d["fail_kinds"]["break-even"] == 2)


def test_unrecorded_rows_land_in_unknown_not_in_armed_or_unarmed():
    d = doctrine.summarize([TSLA_139])
    assert d["fail_kinds"]["break-even"] == 1
    assert d["break_even_armed"] == {"armed": 0, "unarmed": 0, "unknown": 1}


def test_empty_input_still_reports_the_audit_shape():
    d = doctrine.summarize([])
    assert d["break_even_armed"] == {"armed": 0, "unarmed": 0, "unknown": 0}


def test_rows_without_the_column_at_all_are_unknown_and_do_not_raise():
    """Every pre-IMP-067 caller passes rows with no final_stop_price key."""
    legacy = dict(entry_price=100.0, stop_price=98.5, exit_price=100.02,
                  realized_pl=0.02, exit_reason="STOP")
    assert doctrine.fail_kind(legacy) == "break-even"
    assert doctrine.stop_was_armed(legacy) is None
    assert doctrine.summarize([legacy])["break_even_armed"]["unknown"] == 1


def test_the_bands_and_the_stop_protection_report_are_unchanged():
    """by_stop_protection asks doctrine directly — it must see no difference."""
    sp = analytics.by_stop_protection(SESSION_0930)
    assert sp["full-1R"]["trades"] == 1
    assert sp["full-1R"]["total_pl"] == -33.75
    assert sp["break-even"]["trades"] == 2
    assert sp["break-even"]["total_pl"] == -23.58
    assert sp["trailed-scratch"]["trades"] == 0
    assert sp["banked"]["trades"] == 0


def test_stop_was_armed_does_not_mutate_its_input():
    before = [dict(r) for r in SESSION_0930]
    for r in SESSION_0930:
        doctrine.stop_was_armed(r)
    doctrine.summarize(SESSION_0930)
    assert [dict(r) for r in SESSION_0930] == before


# --- the measured population this was built from -------------------------

def test_a_floor_only_lift_is_tiny_by_construction_so_it_can_never_be_armed():
    """The 9 raised-but-never-armed rows lifted 0.002R..0.092R of a 1R stop.

    The floor's size is by identity the adverse slippage (IMP-051), which is why
    it can restore planned risk and still leave the stop a long way under the
    fill. A lift that small must never be read as break-even protection.
    """
    for lift_r in (0.002, 0.030, 0.066, 0.092):
        risk = 5.0
        row = dict(entry_price=100.0, stop_price=100.0 - risk,
                   exit_price=96.0, realized_pl=-20.0, exit_reason="STOP",
                   stop_raises=1,
                   final_stop_price=100.0 - risk + lift_r * risk)
        assert doctrine.stop_was_armed(row) is False


def test_the_loader_selects_the_column_the_audit_depends_on():
    """Without it the audit degrades to "unknown" and IMP-067 ships INERT.

    That is exactly how STOP_RATCHET_MIN_PCT silently neutered IMP-050 until
    IMP-051 found it, so the SELECT list is pinned rather than trusted. Source
    inspection, not a DB call — this file stays pure.
    """
    import inspect

    src = inspect.getsource(analytics.load_closed_trades)
    assert "t.final_stop_price" in src
    assert "t.stop_raises" in src


def test_risk_invariants_are_untouched_by_this_change():
    from bot import config
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.BREAKEVEN_TRIGGER_R == 0.5      # IMP-013 protection intact
    assert config.TRAIL_TRIGGER_R == 1.0
    assert config.TRAIL_DISTANCE_R == 1.0
    assert config.TRAILING_STOP_ENABLED is True
    assert doctrine.FAIL_MAX_R == 0.25            # IMP-053 taxonomy untouched
    assert doctrine.WIN_MIN_R == 1.0
    assert doctrine.FULL_STOP_MAX_R == -0.75
