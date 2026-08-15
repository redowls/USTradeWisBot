"""Regression tests for the confidence -> risk-tier ladder (IMP-027).

Built on the five REAL signals recorded on 2026-08-06 (trades 223-227). Every
one of them scored breakout_score = 0.0 exactly, because IMP-021 vetoes
breakout_score >= BREAKOUT_FADE_CEILING and the score is empirically bimodal.
That pins confidence into a ~3-point band and makes the upper risk tiers
unreachable — the summary.md §5.9 "more confidence = more money" ladder is inert.

These tests lock in that the degeneracy is REAL (so it stops being an invisible
structural fact) and, more importantly, that the two ways it could turn
dangerous stay guarded:

  * a sub-veto breakout score silently buying a higher risk tier, and
  * the "just renormalize the weights" tidy-up, which would quadruple risk.
"""

import pytest

from bot import config, confidence, sizing
from scripts import check_sizing_ladder as ladder

# (symbol, breakout, ma, value, momentum, confidence recorded in dbo.signals)
TODAY_2026_08_06 = [
    ("META", 0.0, 1.0, 1.0, 0.7162, 60.74),
    ("NVDA", 0.0, 1.0, 1.0, 0.7130, 60.70),
    ("WMT", 0.0, 1.0, 1.0, 0.6704, 60.06),
    ("AMZN", 0.0, 1.0, 1.0, 0.6800, 60.20),
    ("AAPL", 0.0, 1.0, 1.0, 0.8432, 62.65),
]


def _ev(bo, ma, val, mom):
    return {
        "breakout_score": bo,
        "ma_score": ma,
        "value_score": val,
        "momentum_score": mom,
        "regime_multiplier": config.REGIME_MULT_OK,
    }


@pytest.mark.parametrize("symbol,bo,ma,val,mom,recorded", TODAY_2026_08_06)
def test_todays_real_signals_reproduce_recorded_confidence(
    symbol, bo, ma, val, mom, recorded
):
    """The scorer must still reproduce what the live bot wrote to the DB."""
    assert confidence.score(_ev(bo, ma, val, mom)) == pytest.approx(recorded, abs=0.01)


@pytest.mark.parametrize("symbol,bo,ma,val,mom,recorded", TODAY_2026_08_06)
def test_todays_real_signals_all_land_on_the_floor_risk_tier(
    symbol, bo, ma, val, mom, recorded
):
    """All five sized at 0.5% of equity — the bottom tier — as recorded live."""
    assert sizing.risk_fraction_for_confidence(recorded) == 0.5


def test_momentum_spread_does_not_move_the_risk_tier():
    """WMT (mom 0.67) and AAPL (mom 0.84) differ by 0.17 and still tie.

    Momentum is the ONLY varying input left in the blend, and its Pearson r with
    realized P&L is 0.0001 over n=145 — so the ladder has nothing to scale on.
    """
    wmt = confidence.score(_ev(0.0, 1.0, 1.0, 0.6704))
    aapl = confidence.score(_ev(0.0, 1.0, 1.0, 0.8432))
    assert aapl - wmt == pytest.approx(2.59, abs=0.01)
    assert sizing.risk_fraction_for_confidence(wmt) == sizing.risk_fraction_for_confidence(
        aapl
    )


def test_live_ceiling_is_65_and_upper_tiers_are_unreachable():
    ceiling = ladder.confidence_ceiling(0.0)
    assert ceiling == pytest.approx(65.0)
    reach = dict((min_conf, ok) for min_conf, _pct, ok in ladder.tier_reachability(ceiling))
    assert reach[60] is True
    assert reach[70] is False and reach[80] is False and reach[90] is False


def test_ceiling_still_admits_trades_at_all():
    """A ceiling below MIN_CONFIDENCE would silently stop the bot trading."""
    assert ladder.confidence_ceiling(0.0) >= config.MIN_CONFIDENCE


def test_sub_veto_breakout_no_longer_lifts_the_risk_tier():
    """The latent inverse risk this diagnostic monitored — DISARMED by IMP-035.

    breakout_score is bimodal today (0.0 or >=0.5), so this path has never
    fired — but a scorer change putting it at 0.49 used to buy the 1.5% tier,
    3x the risk of every trade the bot actually takes, on IMP-021's toxic leg.
    The scorer still lifts confidence to 82.15 (that half is unchanged and worth
    watching); what changed is that confidence no longer buys size, because the
    conf-75-85 cohort averaged -$30.25/trade over 28 trades.
    """
    ev = _ev(config.BREAKOUT_FADE_CEILING - 0.01, 1.0, 1.0, 1.0)
    assert confidence.score(ev) == pytest.approx(82.15, abs=0.01)
    assert sizing.risk_fraction_for_confidence(confidence.score(ev)) == 0.5
    assert ladder.breakout_tier_lift(ev) == pytest.approx(0.0)


def test_no_breakout_component_means_no_tier_lift():
    """Every live trade: the breakout leg contributes exactly nothing to size."""
    for _sym, bo, ma, val, mom, _rec in TODAY_2026_08_06:
        assert ladder.breakout_tier_lift(_ev(bo, ma, val, mom)) == 0.0


def test_naive_weight_renormalization_no_longer_quadruples_risk(monkeypatch):
    """IMP-021's registered follow-up WAS a capital-protection trap — now defused.

    "Down-weight WEIGHT_BREAKOUT now that its leg is gated out" sounds like
    tidy-up. Renormalizing the remaining three weights to sum to 1.0 still lifts
    today's real META signal from 60.74 to ~92 — but since IMP-035 flattened the
    ladder that no longer reaches the 2.0% cap, so the 4x risk widening this test
    was written to forbid is now structurally impossible rather than merely
    forbidden by convention. The confidence inflation is still wrong and the
    renormalization should still not ship; it just can no longer cost capital.
    """
    total = config.WEIGHT_MA + config.WEIGHT_VALUE + config.WEIGHT_MOMENTUM
    monkeypatch.setattr(config, "WEIGHT_BREAKOUT", 0.0)
    monkeypatch.setattr(config, "WEIGHT_MA", config.WEIGHT_MA / total)
    monkeypatch.setattr(config, "WEIGHT_VALUE", config.WEIGHT_VALUE / total)
    monkeypatch.setattr(config, "WEIGHT_MOMENTUM", config.WEIGHT_MOMENTUM / total)

    meta = confidence.score(_ev(0.0, 1.0, 1.0, 0.7162))
    assert meta > 90.0
    assert sizing.risk_fraction_for_confidence(meta) == 0.5
    assert sizing.risk_fraction_for_confidence(meta) != 4 * 0.5


def test_summarize_on_todays_real_set():
    rows = [(bo, ma, val, mom, rec) for _s, bo, ma, val, mom, rec in TODAY_2026_08_06]
    s = ladder.summarize(rows)
    assert s["n"] == 5
    assert s["breakout_entries"] == 0
    assert s["tiers"] == {0.5: 5}
    assert s["conf_min"] == pytest.approx(60.06)
    assert s["conf_max"] == pytest.approx(62.65)


def test_veto_live_from_marker_is_analysis_only():
    """The new config constant must not be a trading knob."""
    assert config.BREAKOUT_VETO_LIVE_FROM.isoformat() == "2026-07-25"
    # Capital-protection invariants untouched by IMP-027.
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
