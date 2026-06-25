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


# --- IMP-006: by-exit-reason P&L attribution ------------------------------
#
# Regression anchor: 2026-06-25 closed 2W/1L for -$3.69, and all three exits were
# EOD_FLATTEN (QCOM +9.62, AMD +19.61, TSM -32.92). The day reignited the recurring
# "EOD_FLATTEN drift is a low-yield drag" framing. The all-time by-exit-reason split
# refutes that: STOP exits (48 trades) carry the ENTIRE bleed (-$2,739.74, PF ~0.01,
# 2.1% win — the false breakouts), while EOD_FLATTEN (27 trades) is net POSITIVE
# (+$72.53, PF ~1.29). The report previously showed only exit-reason *counts*, hiding
# this. These tests keep the attribution visible so the queued "convert EOD_FLATTEN
# drift via breakeven/trailing" candidate is judged against the real leak (STOP), not
# the bucket that already makes money.

# The three real 2026-06-25 EOD_FLATTEN trades.
TODAY_20260625 = [
    {"realized_pl": 9.62, "realized_pl_pct": 0.6743, "exit_reason": "EOD_FLATTEN", "signal_type": "BOTH", "confidence": 76.92},
    {"realized_pl": -32.92, "realized_pl_pct": -1.8597, "exit_reason": "EOD_FLATTEN", "signal_type": "BREAKOUT", "confidence": 67.98},
    {"realized_pl": 19.61, "realized_pl_pct": 1.8824, "exit_reason": "EOD_FLATTEN", "signal_type": "BREAKOUT", "confidence": 60.75},
]


def test_by_exit_reason_present_and_buckets_today():
    m = analytics.compute_metrics(TODAY_20260625)
    by_exit = m["by_exit_reason"]
    assert set(by_exit) == {"EOD_FLATTEN"}
    flat = by_exit["EOD_FLATTEN"]
    assert flat["trades"] == 3
    assert flat["total_pl"] == -3.69            # matches the broker equity move exactly
    assert flat["win_rate"] == round(100 * 2 / 3, 1)


def test_by_exit_reason_separates_stop_bleed_from_flatten():
    """All-time shape: STOP is the leak (PF < 1), EOD_FLATTEN is net positive (PF > 1)."""
    rows = [
        # EOD_FLATTEN bucket: net positive across the book despite the 06-25 trio
        # netting slightly red (these extra winners mirror the all-time +$72.53 shape).
        *TODAY_20260625,
        {"realized_pl": 19.57, "realized_pl_pct": 0.74, "exit_reason": "EOD_FLATTEN", "signal_type": "MA", "confidence": 62.0},
        {"realized_pl": 16.56, "realized_pl_pct": 0.63, "exit_reason": "EOD_FLATTEN", "signal_type": "MA", "confidence": 61.0},
        # STOP bucket: the false-breakout bleed — almost never recovers.
        {"realized_pl": -57.0, "realized_pl_pct": -1.5, "exit_reason": "STOP", "signal_type": "BOTH", "confidence": 66.0},
        {"realized_pl": -49.0, "realized_pl_pct": -1.4, "exit_reason": "STOP", "signal_type": "BREAKOUT", "confidence": 61.0},
        {"realized_pl": 2.0, "realized_pl_pct": 0.1, "exit_reason": "STOP", "signal_type": "MA", "confidence": 60.5},
        # TAKE_PROFIT bucket: pure winners.
        {"realized_pl": 81.0, "realized_pl_pct": 2.2, "exit_reason": "TAKE_PROFIT", "signal_type": "BOTH", "confidence": 70.0},
    ]
    m = analytics.compute_metrics(rows)
    be = m["by_exit_reason"]
    assert be["STOP"]["total_pl"] < 0
    assert be["STOP"]["profit_factor"] < 1.0          # the leak
    assert be["EOD_FLATTEN"]["profit_factor"] > 1.0   # already profitable
    # The queued lever targets the wrong bucket: flatten is fine, STOP is the bleed.
    assert be["STOP"]["total_pl"] < be["EOD_FLATTEN"]["total_pl"]


def test_by_exit_reason_empty_safe():
    assert analytics.compute_metrics([])["trades"] == 0  # no crash, no by_exit_reason key needed
