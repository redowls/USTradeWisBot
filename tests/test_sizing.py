"""Unit tests for bot/sizing.py — the risk caps that protect the account."""

from bot import config, sizing


def test_risk_zero_below_min_confidence():
    assert sizing.risk_fraction_for_confidence(config.MIN_CONFIDENCE - 0.01) == 0.0


def test_risk_never_exceeds_max_risk_pct():
    assert sizing.risk_fraction_for_confidence(100.0) <= config.MAX_RISK_PCT
    assert config.MAX_RISK_PCT <= 2.0  # capital-protection invariant


def test_plan_skips_when_max_positions_held():
    plan = sizing.plan_position(
        "AAPL", 90.0, 100.0, 1.0, equity=10_000, buying_power=10_000,
        open_positions_count=config.MAX_CONCURRENT_POSITIONS,
    )
    assert not plan.tradable
    assert plan.skip_reason == "max_concurrent_positions"


def test_plan_skips_already_held_and_bad_atr():
    held = sizing.plan_position(
        "AAPL", 90.0, 100.0, 1.0, equity=10_000, buying_power=10_000,
        held_symbols={"AAPL"},
    )
    assert held.skip_reason == "already_held"
    bad = sizing.plan_position(
        "AAPL", 90.0, 100.0, 0.0, equity=10_000, buying_power=10_000,
    )
    assert bad.skip_reason == "invalid_atr_or_price"


def test_stop_floor_applies_for_low_atr_names():
    """Regression for bcfdf0e: sub-noise stops must be floored at MIN_STOP_PCT."""
    plan = sizing.plan_position(
        "AAPL", 90.0, 100.0, atr=0.01, equity=10_000, buying_power=10_000,
    )
    assert plan.tradable
    assert plan.stop_distance >= 100.0 * config.MIN_STOP_PCT / 100.0


def test_dollar_risk_within_budget():
    plan = sizing.plan_position(
        "AAPL", 90.0, 100.0, atr=1.0, equity=10_000, buying_power=100_000,
    )
    assert plan.tradable
    assert plan.dollar_risk <= 10_000 * config.MAX_RISK_PCT / 100.0 + 1e-6
    assert plan.stop_price < plan.entry_price < plan.take_profit_price
