"""IMP-068: ORB refusal attribution — by-reason vs ANY vs EXCLUSIVE.

The regression this file exists for is the 2026-10-01 session: a zero-trade day
whose ledger, grouped by ``entry_refusals.reason``, reads "the 11:30 cutoff
turned away 107 of 131 rows (82%)" when only **23 rows across 3 symbols** were
refused by the clock ALONE. The other 84 also failed the volume floor and/or the
SPY market filter, so moving the cutoff would not have recruited one of them.
That 4.65x overstatement is pinned below against the real block-set census.
"""
from __future__ import annotations

import pytest

from bot import analytics

# --- The real 2026-10-01 census, read off dbo.entry_refusals -----------------
# 131 rows / 8 symbols. Five distinct block sets; the engine joins blocks in a
# fixed order (cutoff, volume, market filter), which is why `market_filter` is
# never blocks[0] unless it is alone.
SESSION_1001 = {
    ("after_cutoff", "low_volume"): 55,
    ("low_volume", "market_filter"): 24,
    ("after_cutoff", "low_volume", "market_filter"): 24,
    ("after_cutoff",): 23,
    ("after_cutoff", "market_filter"): 5,
}
# The 23 clock-only rows, by symbol (MRVL 10 / TSM 5 / WMT 8).
CLOCK_ONLY_SYMBOLS = {"MRVL": 10, "TSM": 5, "WMT": 8}


def _row(blocks, symbol="MRVL"):
    """One ledger row exactly as the engine writes it (IMP-059 shape)."""
    return {
        "symbol": symbol,
        "reason": f"orb_{blocks[0]}"[:24],
        "detail": ("orb_blocked_" + "+".join(blocks))[:64],
    }


def _session_rows():
    rows = []
    for blocks, n in SESSION_1001.items():
        if blocks == ("after_cutoff",):
            for sym, count in CLOCK_ONLY_SYMBOLS.items():
                rows.extend(_row(blocks, sym) for _ in range(count))
            continue
        rows.extend(_row(blocks, "INTC") for _ in range(n))
    return rows


# --- Parsing ----------------------------------------------------------------

def test_refusal_blocks_parses_the_full_set_not_just_the_first():
    row = _row(("after_cutoff", "low_volume", "market_filter"))
    assert analytics.refusal_blocks(row) == (
        "after_cutoff", "low_volume", "market_filter")
    # ...while `reason` — what the naive grouping uses — sees only the first.
    assert row["reason"] == "orb_after_cutoff"


@pytest.mark.parametrize("detail", [
    None, "", "underlying_held_TSM", "vwap_extended", 42, "orb_blocked_",
])
def test_refusal_blocks_returns_none_for_non_orb_rows(detail):
    """Non-ORB refusals must pass through, never be mis-parsed into a block."""
    assert analytics.refusal_blocks({"detail": detail}) is None


def test_non_orb_rows_are_counted_in_rows_but_not_in_orb_rows():
    rows = [_row(("after_cutoff",)), {"symbol": "TSM", "detail": "underlying_held_TSM"}]
    rb = analytics.by_refusal_block(rows)
    assert rb["rows"] == 2
    assert rb["orb_rows"] == 1
    assert set(rb["blocks"]) == {"after_cutoff"}


def test_empty_and_all_non_orb_input_is_safe():
    assert analytics.by_refusal_block([])["blocks"] == {}
    rb = analytics.by_refusal_block([{"detail": "underlying_held_X"}])
    assert rb["orb_rows"] == 0 and rb["blocks"] == {}
    assert rb["multi_block_pct"] == 0.0


# --- The 2026-10-01 regression ----------------------------------------------

def test_the_1001_session_cutoff_is_overstated_by_reason():
    """★ The defect: `reason` credits the clock with 107 rows; 23 were clock-only."""
    rb = analytics.by_refusal_block(_session_rows())
    assert rb["rows"] == rb["orb_rows"] == 131

    cutoff = rb["blocks"]["after_cutoff"]
    assert cutoff["reason_attributed"] == 107   # what grouping by reason reports
    assert cutoff["any"] == 107                 # 55 + 24 + 23 + 5
    assert cutoff["exclusive"] == 23            # ...only these could be recruited
    assert cutoff["reason_over_exclusive"] == pytest.approx(4.65, abs=0.01)
    assert cutoff["symbols_exclusive"] == 3     # MRVL, TSM, WMT


def test_the_1001_session_volume_and_market_filter_are_understated_by_reason():
    """The mirror defect: conditions that are never first vanish from `reason`."""
    rb = analytics.by_refusal_block(_session_rows())

    vol = rb["blocks"]["low_volume"]
    assert vol["any"] == 103                    # 55 + 24 + 24
    assert vol["reason_attributed"] == 24       # only when it is blocks[0]
    assert vol["exclusive"] == 0                # nothing failed volume ALONE

    mkt = rb["blocks"]["market_filter"]
    assert mkt["any"] == 53                     # 24 + 24 + 5
    assert mkt["reason_attributed"] == 0        # never first -> invisible
    assert mkt["exclusive"] == 0
    # An infinite overstatement is reported as unknown, never as a number.
    assert mkt["reason_over_exclusive"] is None


def test_the_1001_session_multi_block_share():
    rb = analytics.by_refusal_block(_session_rows())
    assert rb["multi_block"] == 108             # 131 - 23 clock-only
    assert rb["multi_block_pct"] == 82.4


# --- Invariants that must hold on any ledger --------------------------------

def test_exclusive_never_exceeds_any_and_reason_sums_to_orb_rows():
    rb = analytics.by_refusal_block(_session_rows())
    blocks = rb["blocks"]
    for name, s in blocks.items():
        assert 0 <= s["exclusive"] <= s["any"], name
        assert 0 <= s["symbols_exclusive"] <= s["symbols_any"], name
    # Every row is credited to exactly one block by the by-reason view...
    assert sum(s["reason_attributed"] for s in blocks.values()) == rb["orb_rows"]
    # ...and the exclusive rows are a strict subset of the ledger.
    assert sum(s["exclusive"] for s in blocks.values()) <= rb["orb_rows"]


def test_blocks_are_ordered_by_descending_involvement():
    order = list(analytics.by_refusal_block(_session_rows())["blocks"])
    assert order == ["after_cutoff", "low_volume", "market_filter"]


def test_single_block_ledger_has_no_distortion():
    """Control: when nothing is multi-block, by-reason and exclusive agree."""
    rb = analytics.by_refusal_block([_row(("low_volume",), "TSLA")] * 7)
    vol = rb["blocks"]["low_volume"]
    assert vol["reason_attributed"] == vol["any"] == vol["exclusive"] == 7
    assert vol["reason_over_exclusive"] == 1.0
    assert rb["multi_block"] == 0 and rb["multi_block_pct"] == 0.0
