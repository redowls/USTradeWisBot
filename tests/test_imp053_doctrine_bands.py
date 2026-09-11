"""IMP-053 (2026-09-11, reviewing 2026-09-10) — stop-protection bands speak the doctrine.

``analytics.by_stop_protection`` used to cut STOP exits at ratio edges chosen
before ``bot/doctrine.py`` existed (0.5 and 1.05), and ``scripts/report`` printed
a ``pl > 0`` win rate beside them. On the whole book that made the report claim:

    trailed        23  100.0     263.36    11.45    n/a

Not one of those 23 trades ever banked +1R. Nine are doctrine FAILs (ratio
<= 1.25 — the break-even stop the 2026-09-01 user directive was written about)
and fourteen are SCRATCHes. 2026-09-10 AAPL #340 is the live case that surfaced
it: it stopped out at +$5.32 / ratio 1.151, ``doctrine.classify`` says FAIL, and
the same repo's report counted it toward a 100% win rate.

The second, quieter edge was wrong too: ``full-1R`` ended at ratio 0.5 while
``doctrine.FULL_STOP_MAX_R`` puts the boundary at -0.75R (ratio 0.25). TSLA #139
(2026-07-10, -$119.38) sits in that gap.

These tests pin both edges against the doctrine's own constants, pin the six
real trades that motivated the change, and pin that the fix is a *labelling*
change — the set of rows counted is byte-for-byte what it was.
"""

from __future__ import annotations

import pytest

from bot import analytics, doctrine


# --- Real rows, straight out of the WisBot `trades` table -------------------
# Every one of these was reported under the OLD bands as `trailed` at a 100%
# win rate, except #341 (full-1R) and #139 (the misaligned-zone trade).
AAPL_340 = {"trade_id": 340, "realized_pl": 5.32, "exit_reason": "STOP",
            "entry_price": 320.9133, "stop_price": 315.05, "exit_price": 321.8}
UNH_341 = {"trade_id": 341, "realized_pl": -33.78, "exit_reason": "STOP",
           "entry_price": 396.81, "stop_price": 391.11, "exit_price": 391.18}
TSLA_336 = {"trade_id": 336, "realized_pl": 2.35, "exit_reason": "STOP",
            "entry_price": 372.25, "stop_price": 366.32, "exit_price": 372.6417}
XOM_313 = {"trade_id": 313, "realized_pl": 3.0, "exit_reason": "STOP",
           "entry_price": 159.64, "stop_price": 157.21, "exit_price": 159.84}
GOOG_306 = {"trade_id": 306, "realized_pl": 24.59, "exit_reason": "STOP",
            "entry_price": 340.15, "stop_price": 334.74, "exit_price": 343.6629}
BAC_317 = {"trade_id": 317, "realized_pl": 27.72, "exit_reason": "STOP",
           "entry_price": 62.45, "stop_price": 61.4, "exit_price": 63.22}
TSLA_139 = {"trade_id": 139, "realized_pl": -119.38, "exit_reason": "STOP",
            "entry_price": 411.079, "stop_price": 402.91, "exit_price": 405.11}

REAL_STOPS = [AAPL_340, UNH_341, TSLA_336, XOM_313, GOOG_306, BAC_317, TSLA_139]


def _row_at_ratio(ratio: float, pl: float = 1.0) -> dict:
    """A synthetic STOP exit whose stop_protection_ratio is exactly `ratio`."""
    entry, stop = 100.0, 90.0          # risk = 10.0
    return {"trade_id": 0, "realized_pl": pl, "exit_reason": "STOP",
            "entry_price": entry, "stop_price": stop,
            "exit_price": stop + ratio * (entry - stop)}


# --- The band table is the doctrine's, not a copy of it --------------------

def test_bands_are_the_four_doctrine_verdicts_and_labels_are_unique():
    labels = [label for label, _, _ in analytics.STOP_PROTECTION_BANDS]
    assert labels == ["full-1R", "break-even", "trailed-scratch", "banked"]
    assert len(set(labels)) == len(labels)
    # The old single blended band is gone.
    assert "trailed" not in labels
    verdicts = {v for _, v, _ in analytics.STOP_PROTECTION_BANDS}
    assert verdicts == {doctrine.FAIL, doctrine.SCRATCH, doctrine.WIN}
    # Only FAIL bands name a fail_kind, and both kinds doctrine can return for a
    # STOP exit are covered exactly once.
    kinds = [k for _, v, k in analytics.STOP_PROTECTION_BANDS if v == doctrine.FAIL]
    assert sorted(kinds) == ["break-even", "full-1R"]
    assert all(k is None for _, v, k in analytics.STOP_PROTECTION_BANDS
               if v != doctrine.FAIL)


@pytest.mark.parametrize("ratio,band", [
    # full-1R | break-even edge == doctrine.FULL_STOP_MAX_R (-0.75R -> ratio 0.25).
    (0.20, "full-1R"),
    (1.0 + doctrine.FULL_STOP_MAX_R, "full-1R"),          # exactly 0.25 -> still full-1R
    (0.30, "break-even"),
    # break-even | trailed-scratch edge == doctrine.FAIL_MAX_R (+0.25R -> ratio 1.25).
    (1.20, "break-even"),
    (1.0 + doctrine.FAIL_MAX_R, "break-even"),            # exactly 1.25 -> still a FAIL
    (1.30, "trailed-scratch"),
    # trailed-scratch | banked edge == doctrine.WIN_MIN_R (+1R -> ratio 2.0).
    (1.99, "trailed-scratch"),
    (1.0 + doctrine.WIN_MIN_R, "banked"),                 # exactly 2.0 -> a WIN
    (2.50, "banked"),
])
def test_band_edges_track_the_doctrine_constants(ratio, band):
    """Edges are derived from doctrine's constants, so they cannot drift apart.

    Written against the constants rather than the literals 0.25/1.25/2.0 on
    purpose: if the doctrine ever re-tunes a threshold, these move with it and a
    stale hard-coded band edge in analytics fails here instead of silently
    mis-reporting for weeks (the IMP-049 failure mode).
    """
    sp = analytics.by_stop_protection([_row_at_ratio(ratio)])
    assert sp[band]["trades"] == 1
    assert sum(b["trades"] for b in sp.values()) == 1


def test_every_band_agrees_with_doctrine_classify_on_synthetic_sweep():
    """No ratio anywhere on the line can land in a band the doctrine disagrees with."""
    verdict_of = {label: v for label, v, _ in analytics.STOP_PROTECTION_BANDS}
    kind_of = {label: k for label, _, k in analytics.STOP_PROTECTION_BANDS}
    for i in range(-40, 320):
        ratio = i / 100.0
        row = _row_at_ratio(ratio)
        sp = analytics.by_stop_protection([row])
        landed = [label for label, b in sp.items() if b["trades"] == 1]
        assert len(landed) == 1, f"ratio {ratio} landed in {landed}"
        band = landed[0]
        assert verdict_of[band] == doctrine.classify(row), f"ratio {ratio}"
        if kind_of[band] is not None:
            assert kind_of[band] == doctrine.fail_kind(row), f"ratio {ratio}"


# --- The real trades that motivated IMP-053 --------------------------------

def test_aapl_340_the_2026_09_10_trade_is_not_reported_as_a_win():
    """AAPL #340: +$5.32 on a ratcheted stop. Green P&L, doctrine FAIL.

    Under the old bands this was `trailed`, and scripts/report rendered that band
    at win% 100.0. It is a break-even stop: it armed at +0.25R, peaked +0.419R,
    and handed back every cent but $5.32 — the exact trade the standing directive
    says must never be scored a win.
    """
    assert round(analytics.stop_protection_ratio(AAPL_340), 4) == 1.1512
    assert doctrine.classify(AAPL_340) == doctrine.FAIL
    assert doctrine.fail_kind(AAPL_340) == "break-even"
    sp = analytics.by_stop_protection([AAPL_340])
    assert sp["break-even"]["trades"] == 1
    assert sp["break-even"]["total_pl"] == 5.32
    assert sp["trailed-scratch"]["trades"] == 0
    assert sp["banked"]["trades"] == 0


def test_unh_341_the_other_2026_09_10_trade_is_a_full_1r_loss():
    assert doctrine.fail_kind(UNH_341) == "full-1R"
    sp = analytics.by_stop_protection([UNH_341])
    assert sp["full-1R"]["trades"] == 1
    assert sp["full-1R"]["total_pl"] == -33.78


def test_tsla_139_moves_out_of_full_1r_where_the_old_0_5_edge_put_it():
    """The quieter misalignment: ratio 0.269 is a break-even stop, not a full 1R.

    -$119.38 is the single largest STOP loss in the book that the doctrine does
    NOT call a false-breakout full-1R loss (its stop had been raised). The old
    ratio-0.5 edge filed it under full-1R and overstated that bucket by $119.38.
    """
    ratio = analytics.stop_protection_ratio(TSLA_139)
    assert 0.25 < ratio < 0.5
    assert doctrine.fail_kind(TSLA_139) == "break-even"
    sp = analytics.by_stop_protection([TSLA_139])
    assert sp["full-1R"]["trades"] == 0
    assert sp["break-even"]["trades"] == 1


def test_no_real_stop_exit_in_the_book_has_ever_banked_a_win():
    """The headline the old `trailed` band hid: zero doctrine WINs on any stop.

    Every row here was reported as part of a 100%-win-rate band. Four are FAILs,
    two are SCRATCHes, none is a WIN. This is a regression guard on the *claim*,
    not on the sample: the day a stop finally banks >= +1R it lands in `banked`
    and this test is the thing that has to be consciously updated.
    """
    sp = analytics.by_stop_protection(REAL_STOPS)
    assert sp["banked"]["trades"] == 0
    assert sp["full-1R"]["trades"] == 1                       # UNH #341
    assert sp["break-even"]["trades"] == 4                    # AAPL, TSLA×2, XOM
    assert sp["trailed-scratch"]["trades"] == 2               # GOOG #306, BAC #317
    # ...and the SCRATCH band is where the money in the old `trailed` band was.
    assert sp["trailed-scratch"]["total_pl"] == 52.31
    assert sp["break-even"]["total_pl"] == -108.71


def test_band_counts_reconcile_with_doctrine_summarize_over_stop_exits():
    """The two instruments must agree trade-for-trade, which is the whole point."""
    sp = analytics.by_stop_protection(REAL_STOPS)
    summary = doctrine.summarize(REAL_STOPS)
    assert summary["stops"] == sum(b["trades"] for b in sp.values())
    assert summary["win"] == sp["banked"]["trades"]
    assert summary["scratch"] == sp["trailed-scratch"]["trades"]
    assert summary["fail"] == sp["full-1R"]["trades"] + sp["break-even"]["trades"]
    assert summary["fail_kinds"]["full-1R"] == sp["full-1R"]["trades"]
    assert summary["fail_kinds"]["break-even"] == sp["break-even"]["trades"]


# --- IMP-053 re-cut the labels, NOT which rows are counted ------------------

def test_row_set_is_unchanged_non_stop_and_unusable_rows_still_excluded():
    flatten = {"trade_id": 900, "realized_pl": 14.4, "exit_reason": "EOD_FLATTEN",
               "entry_price": 112.46, "stop_price": 110.68, "exit_price": 113.06}
    take_profit = {"trade_id": 901, "realized_pl": 50.0, "exit_reason": "TAKE_PROFIT",
                   "entry_price": 100.0, "stop_price": 90.0, "exit_price": 115.0}
    no_prices = {"trade_id": 902, "realized_pl": -5.0, "exit_reason": "STOP"}
    no_pl = {"trade_id": 903, "realized_pl": None, "exit_reason": "STOP",
             "entry_price": 100.0, "stop_price": 90.0, "exit_price": 95.0}
    # stop not below entry -> unusable ratio -> excluded, never a divide-by-zero.
    bad_stop = {"trade_id": 904, "realized_pl": -5.0, "exit_reason": "STOP",
                "entry_price": 100.0, "stop_price": 100.0, "exit_price": 99.0}
    sp = analytics.by_stop_protection(
        REAL_STOPS + [flatten, take_profit, no_prices, no_pl, bad_stop])
    assert sum(b["trades"] for b in sp.values()) == len(REAL_STOPS)
    # A TAKE_PROFIT is a doctrine WIN but is NOT a stop exit, so `banked` must
    # stay empty — the band table must not become a back door into this bucket.
    assert sp["banked"]["trades"] == 0
    assert analytics.by_stop_protection([]) == {}
    assert analytics.by_stop_protection([no_prices]) == {}


def test_compute_metrics_exposes_the_new_bands():
    m = analytics.compute_metrics(REAL_STOPS)
    sp = m["by_stop_protection"]
    assert set(sp) == {"full-1R", "break-even", "trailed-scratch", "banked"}
    assert sp["full-1R"]["total_pl"] == -33.78


# --- The rendered claim, which is the thing that was actually wrong ---------

def _stop_protection_block(capsys, monkeypatch, rows) -> tuple[str, list[list[str]]]:
    """Render scripts/report over `rows`; return (caption text, table data rows).

    Both DB readers are stubbed, so this stays as hermetic as the rest of the
    suite — the renderer is the only thing under test.
    """
    from scripts import report

    monkeypatch.setattr(analytics, "load_closed_trades", lambda since=None: list(rows))
    monkeypatch.setattr(analytics, "load_daily_summaries", lambda since=None: [])
    report._print_report()
    lines = capsys.readouterr().out.splitlines()
    start = next(i for i, ln in enumerate(lines) if "By stop protection" in ln)
    header = next(i for i, ln in enumerate(lines[start:], start)
                  if ln.split()[:2] == ["band", "verdict"])
    caption = "\n".join(lines[start:header + 1])
    data = []
    for ln in lines[header + 1:]:
        if not ln.strip():
            break
        data.append(ln.split())
    return caption, data


def test_report_no_longer_prints_a_pl_sign_win_rate_for_stop_bands(capsys, monkeypatch):
    """The defect, stated as a test: this block used to read `trailed 23 100.0 263.36`."""
    caption, data = _stop_protection_block(capsys, monkeypatch, REAL_STOPS)
    assert "doctrine verdict" in caption
    # The column header no longer carries a win-rate column (the prose above it
    # does say the words "win%", explaining why it was removed).
    assert caption.splitlines()[-1].split() == [
        "band", "verdict", "trades", "total$", "exp$", "PF"]
    # Every data row is band/verdict/trades/total$/exp$/PF — no win-rate column.
    # GOOG #306 and BAC #317 are both +$ and both SCRATCH; under the old renderer
    # their band printed a win rate of 100.0.
    assert all(len(row) == 6 for row in data)
    assert all("100.0" not in cell for row in data for cell in row)
    assert [row[:3] for row in data] == [
        ["full-1R", "FAIL", "1"],
        ["break-even", "FAIL", "4"],
        ["trailed-scratch", "SCRATCH", "2"],
        ["banked", "WIN", "0"],
    ]


def test_report_always_shows_the_empty_banked_row(capsys, monkeypatch):
    """An empty WIN band is the finding, so it must not be suppressed like other zeros."""
    _, data = _stop_protection_block(capsys, monkeypatch, REAL_STOPS)
    assert ["banked", "WIN", "0", "0.00", "0.00", "n/a"] in data


def test_report_still_suppresses_other_empty_bands(capsys, monkeypatch):
    """Only the WIN band is exempt — the rest keep the report's existing behaviour."""
    _, data = _stop_protection_block(capsys, monkeypatch, [AAPL_340])
    assert [row[:3] for row in data] == [
        ["break-even", "FAIL", "1"],      # the one populated band
        ["banked", "WIN", "0"],           # empty but exempt
    ]                                     # full-1R / trailed-scratch suppressed
