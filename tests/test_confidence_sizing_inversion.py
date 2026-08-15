"""IMP-035 (weekly, 2026-08-15) — the confidence->risk ladder must never re-steepen.

The week ending 2026-08-15 audited the confidence score against realized P&L over
the whole 244-trade book and found it monotonically ANTI-predictive:

    conf band    n     avg P&L    avg notional
    <65        176     -$3.03        $3,763
    65-75       28    -$15.10        $5,879
    75-85       28    -$30.25        $9,254
    >=85        12    -$42.28       $11,446

The 68 trades at conf >=65 are 28% of the book and 77% of the lifetime loss.
Controlled for era (the 06-08..07-24 window where both signal families fired),
breakout-carrying signals averaged -$26.04/trade on $8,385 notional against
-$2.39/trade on $4,360 for MA-only — so this is a sizing defect, not a survivor
of a bad month.

IMP-027 diagnosed the same trap and built tests to WATCH it, but left it armed
on the reasoning that IMP-021's veto made the upper tiers unreachable. Dormant
is not disarmed: the tiers become reachable again the moment the scorer changes.
These tests are the disarm.
"""

import pytest

from bot import config, sizing


def test_the_ladder_is_flat_across_every_reachable_confidence():
    """The core IMP-035 regression: confidence must not buy size.

    Spans MIN_CONFIDENCE to 100, including every old rung boundary (70/80/90)
    where the pre-IMP-035 table stepped up to 1.0/1.5/2.0.
    """
    floor = sizing.risk_fraction_for_confidence(config.MIN_CONFIDENCE)
    assert floor == 0.5
    for conf in (60, 61.4, 65, 69.99, 70, 75, 80, 82.15, 85, 90, 95, 100):
        assert sizing.risk_fraction_for_confidence(conf) == floor, (
            f"confidence {conf} bought {sizing.risk_fraction_for_confidence(conf)}% "
            f"instead of the flat {floor}% — the anti-predictive ladder is back"
        )


def test_the_old_four_x_top_rung_is_gone():
    """conf 90+ used to size 4x a conf-60 trade. That cohort lost $42.28/trade."""
    assert sizing.risk_fraction_for_confidence(90.0) == sizing.risk_fraction_for_confidence(
        config.MIN_CONFIDENCE
    )
    assert sizing.risk_fraction_for_confidence(90.0) != 4 * 0.5


def test_guard_accepts_the_shipped_table():
    assert sizing.ladder_risk_is_non_increasing() is True


def test_guard_rejects_the_pre_imp035_ladder():
    """The exact table IMP-035 removed must fail the guard."""
    pre_imp035 = [(60, 0.5), (70, 1.0), (80, 1.5), (90, 2.0)]
    assert sizing.ladder_risk_is_non_increasing(pre_imp035) is False


def test_guard_rejects_a_single_re_steepened_rung():
    """Catches the subtle edit, not just wholesale reversion."""
    sneaky = [(60, 0.5), (70, 0.5), (80, 0.5), (90, 0.75)]
    assert sizing.ladder_risk_is_non_increasing(sneaky) is False


def test_guard_allows_de_risking_with_confidence():
    """A DECREASING ladder is permitted — the evidence points that way, if anywhere."""
    assert sizing.ladder_risk_is_non_increasing([(60, 0.5), (70, 0.4), (80, 0.25)]) is True


def test_live_config_ladder_never_re_steepens():
    """Guards the shipped config itself, so a future edit trips CI, not the account."""
    assert sizing.ladder_risk_is_non_increasing(config.CONFIDENCE_RISK_TABLE) is True


def test_capital_protection_invariants_untouched_by_imp035():
    """IMP-035 is risk-REDUCING. It must not have moved any risk limit."""
    assert config.MAX_RISK_PCT == 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS == 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    # every rung is at or below the hard cap, and none exceeds the old floor
    for _min_conf, pct in config.CONFIDENCE_RISK_TABLE:
        assert 0.0 < pct <= config.MAX_RISK_PCT
        assert pct <= 0.5


def test_this_weeks_real_confidences_size_identically():
    """The 19 trades of 08-10..08-14 ran conf 60.2-62.6; sizing must be unchanged.

    IMP-035 is deliberately INERT on the current live cohort — that is why it is
    safe to ship. It binds only if the scorer ever reaches the upper band again.
    """
    week_confidences = [60.19, 60.26, 60.31, 61.4, 62.57, 62.6]
    sizes = {sizing.risk_fraction_for_confidence(c) for c in week_confidences}
    assert sizes == {0.5}
