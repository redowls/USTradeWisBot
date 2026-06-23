"""Tests for bot/analytics.py — profit-factor per signal type and the
confidence-band breakdown (IMP-004).

Regression anchor: 2026-06-23 closed 4W/0L and *every* winner was an MA-only
signal scored conf 60-62 (XOM 62.0, BAC 60.96, CRM 61.53, WMT 60.22). That day
refuted the standing "raise the MA confidence floor to ~65" candidate: no trade
in the book has ever scored >=64, so lifting the floor would disable the entire
(least-bad) MA bucket and would have killed all four of that day's winners.
These tests keep that evidence visible in the report so the candidate can't be
silently reinstated.
"""

from bot import analytics

# The four real 2026-06-23 winners (symbol, realized_pl, realized_pl_pct, signal_type, confidence).
TODAY_20260623 = [
    {"realized_pl": 19.57, "realized_pl_pct": 0.7405, "exit_reason": "EOD_FLATTEN", "signal_type": "MA", "confidence": 62.00},
    {"realized_pl": 16.56, "realized_pl_pct": 0.6255, "exit_reason": "EOD_FLATTEN", "signal_type": "MA", "confidence": 60.96},
    {"realized_pl": 57.69, "realized_pl_pct": 2.2362, "exit_reason": "TAKE_PROFIT", "signal_type": "MA", "confidence": 61.53},
    {"realized_pl": 1.98, "realized_pl_pct": 0.0752, "exit_reason": "EOD_FLATTEN", "signal_type": "MA", "confidence": 60.22},
]


def test_signal_type_buckets_carry_profit_factor():
    m = analytics.compute_metrics(TODAY_20260623)
    ma = m["by_signal_type"]["MA"]
    assert "profit_factor" in ma
    # All four were winners -> no gross loss -> PF is undefined (None), not a crash.
    assert ma["profit_factor"] is None
    assert ma["trades"] == 4
    assert ma["win_rate"] == 100.0


def test_today_winners_land_in_low_confidence_bands():
    m = analytics.compute_metrics(TODAY_20260623)
    bands = m["by_confidence_band"]
    # 60.96 / 61.53 / 60.22 -> "60-62"; 62.00 -> "62-64".
    assert bands["60-62"]["trades"] == 3
    assert bands["62-64"]["trades"] == 1
    assert bands["60-62"]["expectancy"] > 0
    # The refutation: nothing scored at/above the proposed 65 floor.
    assert bands["64-66"]["trades"] == 0
    assert bands["66+"]["trades"] == 0


def test_raising_floor_to_65_would_drop_every_trade():
    """No trade scores >=64, so a 'MIN_CONFIDENCE -> 65' change disables the book."""
    m = analytics.compute_metrics(TODAY_20260623)
    above_64 = sum(s["trades"] for label, s in m["by_confidence_band"].items()
                   if label in ("64-66", "66+"))
    assert above_64 == 0
    # Everything we actually traded is below the proposed floor.
    assert sum(s["trades"] for s in m["by_confidence_band"].values()) == 4


def test_profit_factor_distinguishes_ma_from_both():
    """MA-only is the least-bad bucket; BOTH carries the big losses (all-time shape)."""
    rows = [
        {"realized_pl": 57.69, "realized_pl_pct": 2.2, "exit_reason": "TAKE_PROFIT", "signal_type": "MA", "confidence": 61.5},
        {"realized_pl": 19.57, "realized_pl_pct": 0.7, "exit_reason": "EOD_FLATTEN", "signal_type": "MA", "confidence": 62.0},
        {"realized_pl": -10.0, "realized_pl_pct": -0.5, "exit_reason": "STOP", "signal_type": "MA", "confidence": 60.5},
        {"realized_pl": -120.0, "realized_pl_pct": -3.0, "exit_reason": "STOP", "signal_type": "BOTH", "confidence": 63.0},
        {"realized_pl": -90.0, "realized_pl_pct": -2.5, "exit_reason": "STOP", "signal_type": "BOTH", "confidence": 62.0},
        {"realized_pl": 30.0, "realized_pl_pct": 1.0, "exit_reason": "TAKE_PROFIT", "signal_type": "BOTH", "confidence": 60.0},
    ]
    m = analytics.compute_metrics(rows)
    ma_pf = m["by_signal_type"]["MA"]["profit_factor"]
    both_pf = m["by_signal_type"]["BOTH"]["profit_factor"]
    assert ma_pf is not None and both_pf is not None
    assert ma_pf > both_pf  # MA edge > BOTH, the opposite of the old "BOTH is the edge" read


def test_empty_input_has_no_bands():
    assert analytics.compute_metrics([]) == {"trades": 0}
