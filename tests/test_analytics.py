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


# --- IMP-007: by-entry-extension breakdown --------------------------------
#
# Regression anchor: 2026-06-29 closed 4W/1L for +$126.49. The single loser was
# AAPL (BOTH, conf 81.5), which filled at 286.37 — 1.62% ABOVE its broken level
# (281.81) — and reversed straight to its stop (-$116.55), while the two winning
# breakout trades filled tight to their levels (TSLA 0.30% -> +$106.87 TP, INTC
# 0.13% -> +$85.79). That anecdote suggests "cap entry extension to stop chasing,"
# but the full book refutes it: the tightest (<=0.5%) bucket carries the WORST
# stop rate (67.9%), so extension is not a safety signal and a cap would not touch
# the false-breakout leak. These tests keep that evidence in the report so the
# extension-cap candidate cannot be silently reopened.

# The three real 2026-06-29 breakout-type trades (have a broke_level). The two
# MA-only trades that day (SPY/GOOG) have no broke_level and must be excluded.
TODAY_20260629 = [
    {"realized_pl": -116.55, "realized_pl_pct": -1.9371, "exit_reason": "STOP",
     "signal_type": "BOTH", "confidence": 81.52, "entry_price": 286.37, "broke_level": 281.81},
    {"realized_pl": 106.87, "realized_pl_pct": 2.4511, "exit_reason": "TAKE_PROFIT",
     "signal_type": "BOTH", "confidence": 71.39, "entry_price": 395.47, "broke_level": 394.27},
    {"realized_pl": 85.79, "realized_pl_pct": 1.1808, "exit_reason": "EOD_FLATTEN",
     "signal_type": "BOTH", "confidence": 84.05, "entry_price": 129.7407, "broke_level": 129.5767},
    # MA-only — no broken level, so it must not appear in the extension breakdown.
    {"realized_pl": 40.90, "realized_pl_pct": 1.9776, "exit_reason": "EOD_FLATTEN",
     "signal_type": "MA", "confidence": 61.34, "entry_price": 344.70, "broke_level": None},
]


def test_entry_extension_buckets_today():
    m = analytics.compute_metrics(TODAY_20260629)
    ext = m["by_entry_extension"]
    # AAPL filled 1.62% above its level -> the >1.0% band, and it was the loser.
    assert ext[">1.0%"]["trades"] == 1
    assert ext[">1.0%"]["win_rate"] == 0.0
    # TSLA (0.30%) + INTC (0.13%) filled tight -> the <=0.5% band, both winners.
    assert ext["<=0.5%"]["trades"] == 2
    assert ext["<=0.5%"]["win_rate"] == 100.0


def test_entry_extension_excludes_rows_without_broke_level():
    """MA-only signals have no broke_level and must not land in any extension band."""
    m = analytics.compute_metrics(TODAY_20260629)
    total_in_bands = sum(s["trades"] for s in m["by_entry_extension"].values())
    assert total_in_bands == 3  # the 3 breakout trades, not the MA-only GOOG


def test_entry_extension_cap_does_not_address_the_leak():
    """All-time shape: the tightest entries stop out at least as often as the
    extended ones, so an extension cap would not remove the false-breakout leak."""
    # Real 2026-06 breakout-type trades, abbreviated to (extension band) members.
    rows = [
        # Tight (<=0.5%) entries that STILL stopped out — the bulk of the bleed.
        {"realized_pl": -73.00, "realized_pl_pct": -1.0, "exit_reason": "STOP",
         "signal_type": "BOTH", "confidence": 80.8, "entry_price": 100.25, "broke_level": 100.0},
        {"realized_pl": -132.92, "realized_pl_pct": -2.0, "exit_reason": "STOP",
         "signal_type": "BOTH", "confidence": 86.0, "entry_price": 100.12, "broke_level": 100.0},
        {"realized_pl": -119.17, "realized_pl_pct": -2.0, "exit_reason": "STOP",
         "signal_type": "BOTH", "confidence": 86.0, "entry_price": 100.21, "broke_level": 100.0},
        {"realized_pl": 106.87, "realized_pl_pct": 2.4, "exit_reason": "TAKE_PROFIT",
         "signal_type": "BOTH", "confidence": 71.4, "entry_price": 100.30, "broke_level": 100.0},
        # Extended (>1.0%) entries — far fewer, and not uniformly losers.
        {"realized_pl": -116.55, "realized_pl_pct": -1.9, "exit_reason": "STOP",
         "signal_type": "BOTH", "confidence": 81.5, "entry_price": 101.62, "broke_level": 100.0},
        {"realized_pl": 19.61, "realized_pl_pct": 1.9, "exit_reason": "EOD_FLATTEN",
         "signal_type": "BREAKOUT", "confidence": 60.8, "entry_price": 101.00, "broke_level": 100.0},
    ]
    m = analytics.compute_metrics(rows)
    ext = m["by_entry_extension"]
    # The tight bucket stops out at least as often as the extended bucket, so the
    # leak is not concentrated in "chased" entries — an extension cap is refuted.
    assert ext["<=0.5%"]["win_rate"] <= ext[">1.0%"]["win_rate"]


# --- Market-regime tagging (IMP-011) -----------------------------------------
#
# Regression anchor: 2026-07-06 closed 2W/3L for -$70.51; the entire loss was two
# false-breakout STOPs (SE -55.64, INTC -74.16), while the two winners (GOOGL
# +44.62, META +22.48) and the small COST drift (-7.81) held. Every per-trade
# discriminator is already refuted, so IMP-011 measures the MARKET-LEVEL lever:
# tag each entry with the SPY intraday regime and bucket P&L. These tests pin the
# pure tagging/bucketing math (the live SPY fetch lives in scripts/regime_analysis
# and is not exercised here — offline only).

TODAY_20260706 = [
    {"trade_id": 115, "realized_pl": 44.62, "exit_reason": "TAKE_PROFIT", "signal_type": "MA"},
    {"trade_id": 116, "realized_pl": -7.81, "exit_reason": "EOD_FLATTEN", "signal_type": "MA"},
    {"trade_id": 117, "realized_pl": -55.64, "exit_reason": "STOP", "signal_type": "MA"},
    {"trade_id": 118, "realized_pl": -74.16, "exit_reason": "STOP", "signal_type": "BOTH"},
    {"trade_id": 119, "realized_pl": 22.48, "exit_reason": "EOD_FLATTEN", "signal_type": "MA"},
]


def test_classify_index_regime_price_vs_ema():
    assert analytics.classify_index_regime(100.0, 99.0) == analytics.REGIME_BULLISH
    assert analytics.classify_index_regime(99.0, 100.0) == analytics.REGIME_BEARISH
    # At/above the EMA counts as bullish (>=), boundary is inclusive.
    assert analytics.classify_index_regime(100.0, 100.0) == analytics.REGIME_BULLISH


def test_classify_index_regime_missing_data_is_unknown():
    # A data gap (no aligned index bar) must never fabricate a regime.
    assert analytics.classify_index_regime(None, 100.0) == analytics.REGIME_UNKNOWN
    assert analytics.classify_index_regime(100.0, None) == analytics.REGIME_UNKNOWN
    assert analytics.classify_index_regime(None, None) == analytics.REGIME_UNKNOWN


def test_by_market_regime_buckets_and_skip_bearish_whatif():
    # Hypothetical tag: the two STOP losers hit while SPY was below its EMA
    # (bearish); the winners while above (bullish); COST drift left untagged.
    regime = {
        115: analytics.REGIME_BULLISH,   # GOOGL +44.62
        119: analytics.REGIME_BULLISH,   # META  +22.48
        117: analytics.REGIME_BEARISH,   # SE    -55.64
        118: analytics.REGIME_BEARISH,   # INTC  -74.16
        # 116 (COST) intentionally absent -> defaults to 'unknown'
    }
    res = analytics.by_market_regime(TODAY_20260706, regime)
    b = res["buckets"]
    assert b[analytics.REGIME_BULLISH]["trades"] == 2
    assert b[analytics.REGIME_BULLISH]["total_pl"] == 67.10
    assert b[analytics.REGIME_BEARISH]["trades"] == 2
    assert b[analytics.REGIME_BEARISH]["total_pl"] == -129.80
    assert b[analytics.REGIME_UNKNOWN]["trades"] == 1  # COST, defaulted

    # Skip-bearish what-if: drop the two bearish STOPs, keep bullish + unknown.
    sk = res["skip_bearish"]
    assert sk["skipped_trades"] == 2
    assert sk["skipped_total_pl"] == -129.80
    assert sk["kept_trades"] == 3
    assert sk["kept_total_pl"] == 59.29  # 44.62 + 22.48 - 7.81


def test_by_market_regime_empty_and_all_unknown_safe():
    # No rows -> empty buckets, zeroed what-if (no crash).
    empty = analytics.by_market_regime([], {})
    assert empty["buckets"] == {}
    assert empty["skip_bearish"]["kept_trades"] == 0
    # All trades unknown (no regime map) -> nothing skipped, book fully kept.
    allu = analytics.by_market_regime(TODAY_20260706, {})
    assert allu["skip_bearish"]["skipped_trades"] == 0
    assert allu["skip_bearish"]["kept_trades"] == 5


# --- IMP-012: proxy cross-check + the 2026-07-07 counterexample ---------------
#
# 2026-07-07 (6 trades, 1W/5L, -$8.22) is a clean counterexample to the naive
# "skip bearish" market-regime gate: the only winner (META +85.74 TAKE_PROFIT)
# was tagged BEARISH under BOTH SPY and QQQ, while the worst loser (AMZN -43.97
# STOP) was tagged BULLISH. SPY and QQQ agree on 5 of 6 trades (they differ only
# on AAPL). These fixtures keep that evidence visible so a naive skip-bearish
# gate can't be shipped as a "win".
TODAY_20260707 = [
    {"trade_id": 120, "symbol": "TSLA", "realized_pl": -20.23, "exit_reason": "STOP"},
    {"trade_id": 121, "symbol": "GOOGL", "realized_pl": -2.22, "exit_reason": "EOD_FLATTEN"},
    {"trade_id": 122, "symbol": "META", "realized_pl": 85.74, "exit_reason": "TAKE_PROFIT"},
    {"trade_id": 123, "symbol": "AMZN", "realized_pl": -43.97, "exit_reason": "STOP"},
    {"trade_id": 124, "symbol": "AAPL", "realized_pl": -16.56, "exit_reason": "EOD_FLATTEN"},
    {"trade_id": 125, "symbol": "AMZN", "realized_pl": -10.98, "exit_reason": "EOD_FLATTEN"},
]
# Real intraday regime at each entry, measured off SPY and QQQ EMA9 (5-min bars).
REGIME_SPY_20260707 = {
    120: analytics.REGIME_BEARISH, 121: analytics.REGIME_BEARISH,
    122: analytics.REGIME_BEARISH, 123: analytics.REGIME_BULLISH,
    124: analytics.REGIME_BEARISH, 125: analytics.REGIME_BULLISH,
}
REGIME_QQQ_20260707 = {
    120: analytics.REGIME_BEARISH, 121: analytics.REGIME_BEARISH,
    122: analytics.REGIME_BEARISH, 123: analytics.REGIME_BULLISH,
    124: analytics.REGIME_BULLISH, 125: analytics.REGIME_BULLISH,  # AAPL flips
}


def test_regime_proxy_agreement_today():
    agr = analytics.regime_proxy_agreement(REGIME_SPY_20260707, REGIME_QQQ_20260707)
    assert agr["trades"] == 6
    assert agr["agree"] == 5
    assert agr["disagree"] == 1
    assert agr["agree_pct"] == 83.3
    # The single disagreement is AAPL (124): SPY bearish, QQQ bullish.
    assert agr["disagreements"] == [
        (124, analytics.REGIME_BEARISH, analytics.REGIME_BULLISH)
    ]


def test_regime_proxy_agreement_empty_and_partial_overlap():
    assert analytics.regime_proxy_agreement({}, {})["trades"] == 0
    assert analytics.regime_proxy_agreement({}, {})["agree_pct"] == 0.0
    # Only trade_ids present in BOTH maps are compared.
    a = {1: analytics.REGIME_BULLISH, 2: analytics.REGIME_BEARISH}
    b = {2: analytics.REGIME_BEARISH, 3: analytics.REGIME_BULLISH}
    agr = analytics.regime_proxy_agreement(a, b)
    assert agr["trades"] == 1 and agr["agree"] == 1


def test_skip_bearish_gate_is_harmful_on_2026_07_07():
    """The counterexample: skip-bearish removes NET-POSITIVE P&L today (bad gate)."""
    res = analytics.by_market_regime(TODAY_20260707, REGIME_SPY_20260707)
    b = res["buckets"]
    # The winner (META +85.74) sits in the BEARISH bucket, so bearish is net POSITIVE.
    assert b[analytics.REGIME_BEARISH]["total_pl"] == 46.73  # -20.23 -2.22 +85.74 -16.56
    assert b[analytics.REGIME_BULLISH]["total_pl"] == -54.95  # -43.97 -10.98
    sk = res["skip_bearish"]
    # Skipping bearish would REMOVE +$46.73 of net-positive P&L and KEEP -$54.95
    # -> the naive gate is harmful on today's tape. Guard against shipping it as a win.
    assert sk["skipped_total_pl"] == 46.73
    assert sk["skipped_total_pl"] > 0
    assert sk["kept_total_pl"] == -54.95


# --- IMP-014 (2026-07-08): stop-protection split of the STOP bucket ------------
#
# First live session under IMP-013 (break-even@+0.5R / trail@+1R). All four STOP
# exits that day (entry/orig_stop/exit are the real Alpaca fills; trades.stop_price
# keeps the ORIGINAL 1R anchor by IMP-013 design):
#   NVDA #127  e197.3592 s194.51  x197.42    pl +0.79  -> rf 1.021 break-even
#   QCOM #129  e185.19   s182.12  x182.10    pl -37.08 -> rf 0.00  full-1R
#   XOM  #126  e141.68   s139.88  x141.67    pl -0.19  -> rf 0.994 break-even
#   AVGO #130  e390.04   s383.68  x390.0314  pl -0.12  -> rf 0.999 break-even
# Three IMP-013 break-even rescues (~scratch, +0.48 combined) vs one real full-1R
# false-breakout loss (QCOM -37.08). Without the split the by_exit_reason STOP
# bucket blends the two and misreads both IMP-013's benefit and the residual leak.
STOP_EXITS_20260708 = [
    {"trade_id": 127, "realized_pl": 0.79, "exit_reason": "STOP",
     "entry_price": 197.3592, "stop_price": 194.51, "exit_price": 197.42},
    {"trade_id": 129, "realized_pl": -37.08, "exit_reason": "STOP",
     "entry_price": 185.19, "stop_price": 182.12, "exit_price": 182.10},
    {"trade_id": 126, "realized_pl": -0.19, "exit_reason": "STOP",
     "entry_price": 141.68, "stop_price": 139.88, "exit_price": 141.67},
    {"trade_id": 130, "realized_pl": -0.12, "exit_reason": "STOP",
     "entry_price": 390.04, "stop_price": 383.68, "exit_price": 390.0314},
]


def test_stop_protection_ratio_classifies_today_stops():
    r = {row["trade_id"]: analytics.stop_protection_ratio(row) for row in STOP_EXITS_20260708}
    assert round(r[129], 3) == -0.007      # QCOM stopped at the original 1R
    assert 0.9 <= r[126] <= 1.05           # XOM stopped ~at break-even
    assert 0.9 <= r[130] <= 1.05           # AVGO stopped ~at break-even
    assert 1.0 <= r[127] <= 1.05           # NVDA eked just past break-even


def test_stop_protection_ratio_none_on_missing_or_non_long():
    assert analytics.stop_protection_ratio({"entry_price": None, "stop_price": 1, "exit_price": 1}) is None
    # stop not below entry (bad/non-long row) -> excluded, never a divide-by-zero.
    assert analytics.stop_protection_ratio({"entry_price": 100.0, "stop_price": 100.0, "exit_price": 99.0}) is None


def test_by_stop_protection_splits_full_loss_from_imp013_rescues():
    sp = analytics.by_stop_protection(STOP_EXITS_20260708)
    # The one full-1R stop carries the whole real loss...
    assert sp["full-1R"]["trades"] == 1
    assert sp["full-1R"]["total_pl"] == -37.08
    # ...while the three IMP-013 break-even rescues are ~scratch (+0.48 combined).
    assert sp["break-even"]["trades"] == 3
    assert sp["break-even"]["total_pl"] == 0.48
    assert sp["trailed"]["trades"] == 0


def test_by_stop_protection_only_counts_stop_exits_and_is_empty_safe():
    # A non-STOP exit (EOD_FLATTEN) with prices present must NOT be bucketed here.
    rows = STOP_EXITS_20260708 + [
        {"trade_id": 128, "realized_pl": 14.4, "exit_reason": "EOD_FLATTEN",
         "entry_price": 112.46, "stop_price": 110.68, "exit_price": 113.06},
    ]
    sp = analytics.by_stop_protection(rows)
    assert sum(b["trades"] for b in sp.values()) == 4  # only the 4 STOP exits
    assert analytics.by_stop_protection([]) == {}
    # STOP exits without usable prices contribute nothing (no crash).
    assert analytics.by_stop_protection(
        [{"trade_id": 1, "realized_pl": -5.0, "exit_reason": "STOP"}]) == {}


def test_compute_metrics_exposes_by_stop_protection():
    m = analytics.compute_metrics(STOP_EXITS_20260708)
    assert "by_stop_protection" in m
    assert m["by_stop_protection"]["full-1R"]["total_pl"] == -37.08


# --- IMP-015 (2026-07-09): machine verdict on the skip-bearish regime gate -----
#
# The ★ market-regime gate (IMP-011/012) was queued "pending a bigger post-06-15
# bearish sample." By 2026-07-09 that sample has GROWN (SPY n=23 / QQQ n=30) and
# turned NET-POSITIVE under BOTH proxies (SPY bearish PF 1.11 +$37.11; QQQ bearish
# PF 1.11 +$42.66), so skipping bearish would REMOVE profit. The verdict encodes
# the analysis's "Read:" rule so this refutation can't be silently reopened.
def _regime_result(bull_pf, bear_n, bear_pf, skipped_pl):
    """Build a by_market_regime()-shaped result with only the fields the verdict reads."""
    return {
        "buckets": {
            analytics.REGIME_BULLISH: {"trades": 50, "profit_factor": bull_pf},
            analytics.REGIME_BEARISH: {"trades": bear_n, "profit_factor": bear_pf},
        },
        "skip_bearish": {"skipped_total_pl": skipped_pl, "skipped_trades": bear_n,
                         "kept_trades": 50, "kept_total_pl": 600.0},
    }


def test_skip_bearish_gate_verdict_refuted_2026_07_09_grown_sample():
    # Real post-06-15 numbers on 2026-07-09: bearish net-positive under both proxies.
    v = analytics.skip_bearish_gate_verdict({
        "SPY": _regime_result(1.74, 23, 1.11, 37.11),
        "QQQ": _regime_result(1.78, 30, 1.11, 42.66),
    })
    assert v["supported"] is False
    assert "net-positive" in v["reason"]
    assert v["per_proxy"]["SPY"]["ok"] is False
    assert v["per_proxy"]["QQQ"]["ok"] is False


def test_skip_bearish_gate_verdict_supported_only_when_bearish_is_a_net_loss():
    # A hypothetical regime where bearish is a large net loss under BOTH proxies
    # with an adequate sample and worse PF -> the gate would be SUPPORTED.
    v = analytics.skip_bearish_gate_verdict({
        "SPY": _regime_result(1.60, 25, 0.55, -180.0),
        "QQQ": _regime_result(1.55, 26, 0.60, -150.0),
    })
    assert v["supported"] is True
    assert v["reason"] == "all proxies support skip-bearish"


def test_skip_bearish_gate_verdict_refused_on_thin_sample_or_no_data():
    # Adequate + negative under SPY, but the QQQ bearish sample is too thin -> refused.
    v = analytics.skip_bearish_gate_verdict({
        "SPY": _regime_result(1.5, 25, 0.5, -100.0),
        "QQQ": _regime_result(1.5, 8, 0.5, -50.0),
    })
    assert v["supported"] is False
    assert "insufficient bearish sample under QQQ" in v["reason"]
    # Empty input -> refused, safe (capital-protective default).
    empty = analytics.skip_bearish_gate_verdict({})
    assert empty["supported"] is False
    assert empty["reason"] == "no proxy data"


def test_skip_bearish_gate_verdict_refused_when_bearish_pf_not_worse():
    # Skipping removes a (tiny) net loss AND sample is adequate, but bearish PF is
    # NOT below bullish -> bearish isn't the worse regime, so the gate is refused.
    v = analytics.skip_bearish_gate_verdict({
        "SPY": _regime_result(1.10, 25, 1.20, -5.0),
    })
    assert v["supported"] is False
    assert "bearish not worse than bullish under SPY" in v["reason"]


# --- IMP-016 (2026-07-13): by-time-of-day breakdown, refutes an open-skip gate --
#
# 2026-07-13 closed 2W/4L (-$85.27): the whole loss was NVDA (conf-94 BOTH, entered
# 09:30:11) fading to its full 1R stop — the SAME open-drive fade as 07-10's TSLA
# (09:31). That invites a "skip the first N minutes" entry gate. But the 0-5m band
# also holds the day's BIGGEST winner (MSFT +$78.39, entered 09:34), so skipping
# the open would forgo winners, and the all-time STOP bleed is spread across every
# band — the leak is not open-concentrated. These anchor that refutation.
from datetime import datetime

TODAY_20260713 = [
    {"trade_id": 143, "symbol": "NVDA",  "realized_pl": -129.93, "exit_reason": "STOP",
     "entry_time": datetime(2026, 7, 13, 9, 30, 11)},   # 0-5m, the day's whole loss
    {"trade_id": 144, "symbol": "GOOGL", "realized_pl": -0.78,   "exit_reason": "STOP",
     "entry_time": datetime(2026, 7, 13, 9, 30, 12)},   # 0-5m, IMP-013 break-even rescue
    {"trade_id": 145, "symbol": "MSFT",  "realized_pl": 78.39,   "exit_reason": "EOD_FLATTEN",
     "entry_time": datetime(2026, 7, 13, 9, 34, 34)},   # 0-5m, the day's BIGGEST winner
    {"trade_id": 146, "symbol": "AMZN",  "realized_pl": -0.36,   "exit_reason": "STOP",
     "entry_time": datetime(2026, 7, 13, 9, 47, 41)},   # 15-30m, break-even rescue
    {"trade_id": 147, "symbol": "SE",    "realized_pl": -41.65,  "exit_reason": "STOP",
     "entry_time": datetime(2026, 7, 13, 10, 40, 35)},  # 60m+, full-1R MA open-fade
    {"trade_id": 148, "symbol": "COST",  "realized_pl": 9.06,    "exit_reason": "EOD_FLATTEN",
     "entry_time": datetime(2026, 7, 13, 11, 47, 40)},  # 60m+, small green drift
]


def test_minutes_after_open_today():
    m = {r["symbol"]: analytics._minutes_after_open(r) for r in TODAY_20260713}
    assert round(m["NVDA"], 2) == 0.18    # 09:30:11
    assert round(m["MSFT"], 2) == 4.57    # 09:34:34 — still inside the 0-5m band
    assert round(m["AMZN"], 2) == 17.68   # 09:47:41
    assert round(m["SE"], 2) == 70.58     # 10:40:35


def test_minutes_after_open_parses_string_and_none_on_missing():
    # DB drivers may hand back an ISO string; it must parse the same way.
    assert round(analytics._minutes_after_open(
        {"entry_time": "2026-07-13 09:34:34"}), 2) == 4.57
    assert analytics._minutes_after_open({"entry_time": None}) is None
    assert analytics._minutes_after_open({"entry_time": "not-a-date"}) is None
    assert analytics._minutes_after_open({}) is None


def test_by_time_of_day_open_band_holds_both_worst_loser_and_best_winner():
    tod = analytics.by_time_of_day(TODAY_20260713)
    # NVDA (-129.93), GOOGL (-0.78) and MSFT (+78.39) all fill in the first 5 min:
    # the biggest loser AND the biggest winner share the band, so an open-skip
    # gate cannot isolate the leak without forgoing the winner.
    assert tod["0-5m"]["trades"] == 3
    assert tod["0-5m"]["total_pl"] == -52.32
    assert tod["0-5m"]["win_rate"] == 33.3
    assert tod["15-30m"]["trades"] == 1       # AMZN
    assert tod["60m+"]["trades"] == 2         # SE + COST
    assert tod["60m+"]["total_pl"] == -32.59
    # The two empty bands are still present (band coverage is complete).
    assert tod["5-15m"]["trades"] == 0
    assert tod["30-60m"]["trades"] == 0


def test_by_time_of_day_empty_safe_and_exposed_by_compute_metrics():
    assert analytics.by_time_of_day([]) == {}
    # Rows without a usable entry_time contribute nothing (no crash).
    assert analytics.by_time_of_day([{"realized_pl": -5.0}]) == {}
    m = analytics.compute_metrics(TODAY_20260713)
    assert "by_time_of_day" in m
    assert m["by_time_of_day"]["0-5m"]["total_pl"] == -52.32


# --- IMP-017 (2026-07-14): by-flatten-outcome, surfaces the fade-to-flatten leak -
#
# 2026-07-14 closed 2W/4L (-$41.14). The day's biggest loss was XOM (#150): a
# conf-78 BOTH breakout that filled 0.65% above its broken level, then faded all
# day to a -$49.78 EOD_FLATTEN — its wide 3xATR stop never hit, so it never armed
# IMP-013 and never counted as a STOP. by_stop_protection (IMP-014) is STOP-only,
# so this open-fade leak is invisible there; and the by_exit_reason EOD_FLATTEN
# bucket is net-positive overall (the up-drift cohort masks it). Splitting the
# flatten bucket by the sign of realized P&L surfaces that faded slice. Today's
# three EOD_FLATTEN exits: XOM -49.78 (faded), META -21.28 (faded), GOOG +18.18
# (drifted-up).
FLATTEN_EXITS_20260714 = [
    {"trade_id": 150, "symbol": "XOM",  "realized_pl": -49.78, "exit_reason": "EOD_FLATTEN"},
    {"trade_id": 153, "symbol": "GOOG", "realized_pl": 18.18,  "exit_reason": "EOD_FLATTEN"},
    {"trade_id": 154, "symbol": "META", "realized_pl": -21.28, "exit_reason": "EOD_FLATTEN"},
]


def test_by_flatten_outcome_splits_faded_from_drifted_up():
    fo = analytics.by_flatten_outcome(FLATTEN_EXITS_20260714)
    # The two faders (XOM, META) carry the masked leak...
    assert fo["faded"]["trades"] == 2
    assert fo["faded"]["total_pl"] == -71.06
    # ...while the single up-drift (GOOG) is the profitable cohort that hides it.
    assert fo["drifted-up"]["trades"] == 1
    assert fo["drifted-up"]["total_pl"] == 18.18
    assert fo["drifted-up"]["win_rate"] == 100.0


def test_by_flatten_outcome_only_counts_flatten_exits_and_is_empty_safe():
    # STOP / TAKE_PROFIT exits (even with a loss/gain) must NOT be bucketed here.
    rows = FLATTEN_EXITS_20260714 + [
        {"trade_id": 151, "symbol": "UNH", "realized_pl": -39.33, "exit_reason": "STOP"},
        {"trade_id": 149, "symbol": "BAC", "realized_pl": 51.47,  "exit_reason": "TAKE_PROFIT"},
    ]
    fo = analytics.by_flatten_outcome(rows)
    assert fo["faded"]["trades"] == 2          # UNH's STOP loss excluded
    assert fo["drifted-up"]["trades"] == 1     # BAC's TP win excluded
    # No EOD_FLATTEN exits at all -> empty dict, no crash.
    assert analytics.by_flatten_outcome([]) == {}
    assert analytics.by_flatten_outcome(
        [{"trade_id": 1, "realized_pl": -5.0, "exit_reason": "STOP"}]) == {}


def test_compute_metrics_exposes_by_flatten_outcome():
    m = analytics.compute_metrics(FLATTEN_EXITS_20260714)
    assert "by_flatten_outcome" in m
    assert m["by_flatten_outcome"]["faded"]["total_pl"] == -71.06
    assert m["by_flatten_outcome"]["drifted-up"]["total_pl"] == 18.18
