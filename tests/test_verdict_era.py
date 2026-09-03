"""IMP-047 — the incubation verdict must describe the strategy that actually trades.

The defect this locks down: ``incubation_verdict`` gated on ``false_breakout_rate``,
a statistic computed over ``signal_type in (BREAKOUT, BOTH)``. IMP-021's
``BREAKOUT_FADE_CEILING = 0.5`` sits below the analytic floor of
``signals.breakout_score`` (0.45 base + 0.20 * touches/(MIN_LEVEL_TOUCHES+1); the
lowest of 74 recorded breakout-bearing signals was 0.5611), so it vetoes 100% of
breakouts rather than the worst of them. The last breakout-bearing signal was
2026-07-24 — the cohort has been frozen ever since, and every run of
``scripts.report`` printed "false-breakout rate 52.7% >= 40.0%" as a live red flag
on evidence that can never move again.

The regression scenario is the REAL 2026-09-02 session: five fills, every one
``signal_type='MA'`` with ``breakout_score`` exactly 0.0000 — a day on which the
old verdict still cited a breakout failure rate.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from bot import analytics, config, doctrine


def _trade(trade_id, symbol, entry, stop, exit_price, reason, pl, hh, mm,
           signal_type="MA", entry_day=date(2026, 9, 2)):
    return {
        "trade_id": trade_id, "symbol": symbol,
        "entry_price": entry, "stop_price": stop, "exit_price": exit_price,
        "exit_reason": reason, "realized_pl": pl, "realized_pl_pct": 0.0,
        "signal_type": signal_type, "confidence": 61.0, "broke_level": None,
        "entry_time": datetime(entry_day.year, entry_day.month, entry_day.day, hh, mm),
        "exit_time": datetime(2026, 9, 2, 15, 55),
    }


@pytest.fixture
def session_2026_09_02():
    """The five real fills of 2026-09-02, DB values verbatim (all pure-MA)."""
    return [
        _trade(315, "META", 587.63, 576.99, 599.04, "TAKE_PROFIT", 34.23, 9, 40),
        _trade(316, "CRM", 260.91, 257.71, 260.64, "STOP", -2.43, 9, 47),
        _trade(317, "BAC", 62.45, 61.40, 63.22, "STOP", 27.72, 9, 56),
        _trade(318, "UNH", 400.15, 394.12, 399.6733, "EOD_FLATTEN", -2.86, 14, 16),
        _trade(319, "SPY", 765.3633, 754.01, 764.87, "EOD_FLATTEN", -1.48, 14, 26),
    ]


# --- the era split -----------------------------------------------------------

def test_breakout_leg_reads_inactive_on_the_real_session(session_2026_09_02):
    """Every 2026-09-02 fill was pure-MA, so the breakout leg cannot be live."""
    m = analytics.compute_metrics(session_2026_09_02)
    assert m["breakout_leg_active"] is False
    assert m["false_breakout_rate"] is None  # no breakout cohort at all


def test_breakout_leg_reads_active_only_for_a_post_veto_breakout_fill():
    """A BOTH/BREAKOUT fill dated on or after the veto means the leg leaked."""
    pre = _trade(1, "XOM", 100.0, 98.0, 97.0, "STOP", -30.0, 10, 0,
                 signal_type="BOTH", entry_day=date(2026, 7, 1))
    assert analytics.compute_metrics([pre])["breakout_leg_active"] is False

    post = _trade(2, "XOM", 100.0, 98.0, 97.0, "STOP", -30.0, 10, 0,
                  signal_type="BOTH", entry_day=config.BREAKOUT_VETO_LIVE_FROM)
    assert analytics.compute_metrics([post])["breakout_leg_active"] is True


@pytest.mark.parametrize("value,expected", [
    (datetime(2026, 9, 2, 9, 40), date(2026, 9, 2)),
    ("2026-09-02T09:40:46.210302", date(2026, 9, 2)),
    (date(2026, 9, 2), date(2026, 9, 2)),
    (None, None),
    ("not-a-date", None),
])
def test_entry_date_parses_or_declines(value, expected):
    assert analytics._entry_date({"entry_time": value}) is expected or \
        analytics._entry_date({"entry_time": value}) == expected


# --- the verdict itself ------------------------------------------------------

def _metrics(**over):
    base = {"trades": 291, "expectancy": 1.0, "false_breakout_rate": 52.7,
            "breakout_leg_active": False, "true_win_rate": 40.0,
            "breakeven_true_win_rate": 18.8}
    base.update(over)
    return base


def test_frozen_false_breakout_rate_is_not_scored_as_a_live_failure():
    """THE REGRESSION: a vetoed leg's 52.7% must not make the verdict NEEDS WORK."""
    verdict = analytics.incubation_verdict(_metrics())
    assert verdict.startswith("PROMISING")
    assert "false-breakout rate 52.7% >= 40.0%" not in verdict


def test_frozen_false_breakout_rate_is_still_disclosed():
    """Silence would read as a pass — the frozen figure must stay visible."""
    verdict = analytics.incubation_verdict(_metrics())
    assert "frozen history, not a live gate" in verdict
    assert "52.7%" in verdict
    assert str(config.BREAKOUT_VETO_LIVE_FROM) in verdict


def test_false_breakout_gate_still_bites_while_the_leg_is_live():
    """Era-gating must not disarm the check — only scope it to a live cohort."""
    verdict = analytics.incubation_verdict(_metrics(breakout_leg_active=True))
    assert verdict.startswith("NEEDS WORK")
    assert f"false-breakout rate 52.7% >= {analytics.FALSE_BREAKOUT_LIMIT}%" in verdict


def test_true_win_rate_below_its_own_break_even_bar_is_a_failure():
    """The doctrine gate that replaces it: 11.7% true wins against a 18.8% bar."""
    verdict = analytics.incubation_verdict(_metrics(true_win_rate=11.7))
    assert verdict.startswith("NEEDS WORK")
    assert "true win rate 11.7% < 18.8%" in verdict


def test_true_win_gate_is_skipped_when_the_bar_is_uncomputable():
    verdict = analytics.incubation_verdict(_metrics(breakeven_true_win_rate=None,
                                                    true_win_rate=0.0))
    assert verdict.startswith("PROMISING")


def test_insufficient_sample_still_short_circuits():
    assert "INSUFFICIENT" in analytics.incubation_verdict(_metrics(trades=3))


# --- the break-even bar ------------------------------------------------------

def test_breakeven_bar_is_none_when_the_non_win_cohort_is_not_losing(
        session_2026_09_02):
    """2026-09-02's scratches banked +0.13R on average — nothing to recover."""
    assert doctrine.breakeven_true_win_rate(session_2026_09_02) is None


def test_breakeven_bar_solves_expectancy_for_zero():
    """One +2R WIN against three -0.5R non-WINs: p = 0.5/2.5 = 20%."""
    rows = [
        _trade(1, "AAA", 100.0, 90.0, 120.0, "STOP", 200.0, 10, 0),        # +2R
        _trade(2, "BBB", 100.0, 90.0, 95.0, "STOP", -50.0, 10, 0),         # -0.5R
        _trade(3, "CCC", 100.0, 90.0, 95.0, "STOP", -50.0, 10, 0),
        _trade(4, "DDD", 100.0, 90.0, 95.0, "STOP", -50.0, 10, 0),
    ]
    assert doctrine.breakeven_true_win_rate(rows) == pytest.approx(20.0)


def test_breakeven_bar_ignores_rows_without_usable_stop_geometry():
    rows = [{"realized_pl": 10.0, "exit_reason": "TAKE_PROFIT"},
            {"realized_pl": -10.0, "exit_reason": "STOP"}]
    assert doctrine.breakeven_true_win_rate(rows) is None


def test_breakeven_bar_is_unmoved_by_widening_the_stop():
    """Anti-gaming: re-denominating R cannot lower the bar.

    Identical fills and exits in price terms, stop distance doubled. Widening
    shrinks the winner (+2R -> +1R) and the loser (-0.5R -> -0.25R) by the same
    factor, so the payoff ratio — and therefore the required win share — is
    unchanged at 20%. A wider stop buys no credit here.
    """
    tight = [
        _trade(1, "AAA", 100.0, 95.0, 110.0, "STOP", 200.0, 10, 0),
        _trade(2, "BBB", 100.0, 95.0, 97.5, "STOP", -50.0, 10, 0),
    ]
    wide = [
        _trade(1, "AAA", 100.0, 90.0, 110.0, "STOP", 200.0, 10, 0),
        _trade(2, "BBB", 100.0, 90.0, 97.5, "STOP", -50.0, 10, 0),
    ]
    assert doctrine.breakeven_true_win_rate(tight) == pytest.approx(20.0)
    assert doctrine.breakeven_true_win_rate(wide) == pytest.approx(20.0)


def test_breakeven_bar_rises_as_the_payoff_deteriorates():
    """A book that gives more back per non-WIN must win more often to survive."""
    good = [
        _trade(1, "AAA", 100.0, 90.0, 120.0, "STOP", 200.0, 10, 0),   # +2R
        _trade(2, "BBB", 100.0, 90.0, 97.5, "STOP", -25.0, 10, 0),    # -0.25R
    ]
    bad = [
        _trade(1, "AAA", 100.0, 90.0, 120.0, "STOP", 200.0, 10, 0),   # +2R
        _trade(2, "BBB", 100.0, 90.0, 90.0, "STOP", -100.0, 10, 0),   # -1R
    ]
    assert doctrine.breakeven_true_win_rate(bad) > \
        doctrine.breakeven_true_win_rate(good)


# --- doctrine numbers reach the metrics dict ---------------------------------

def test_compute_metrics_carries_the_doctrine_true_win_rate(session_2026_09_02):
    """Headline 40% (2 of 5 green) vs true 20% (only META printed +1R)."""
    m = analytics.compute_metrics(session_2026_09_02)
    assert m["win_rate"] == 40.0
    assert m["true_win_rate"] == 20.0
    assert doctrine.summarize(session_2026_09_02)["fail_kinds"]["break-even"] == 1
