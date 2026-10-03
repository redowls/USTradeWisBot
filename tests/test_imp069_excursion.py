"""IMP-069 — entry quality must be measurable without reference to the exit.

Why this exists
---------------
Net P&L, win rate, stop rate, profit factor, expectancy and every doctrine
WIN/SCRATCH/FAIL bucket are joint functions of the signal and the exit. The
2026-10-02 review is the worked example of the damage that does: the
exit-geometry what-if grid reported four candidate configurations "clearing the
noise budget" by +$14 to +$28 on the 10-trade ORB book, which reads as a
shippable exit fix — while the same book's excursions say the entire loss is
trades that never printed enough profit for ANY ratchet to act on.

``excursion_summary`` separates the two with no tunable threshold:

  * ``edge_ratio = mean(MFE_R) / mean(|MAE_R|)``, floor 1.0 — a signal that
    predicts direction must travel further for you than against you.
  * target reachability against the ``1/(1+RR_RATIO)`` hit rate the live bracket
    needs to break even.
  * a three-way, mutually exclusive, exhaustive attribution of realized P&L:
    ``banked`` / ``no-follow-through`` (entry's fault) / ``gave-back`` (exit's).

The anchor cases are the three trades the bot really took on **2026-10-02**, a
session on which SPY closed +0.73% and the Nasdaq printed a record high:

  * **INTC #361** — filled 125.6914 at 10:05:47, 0.21% under the day's 125.96
    high; MFE +0.11R, MAE -1.06R, full-1R stop for -$32.08. No exit helps a
    trade that never goes green: ``no-follow-through``.
  * **TSLA #362** — filled 371.314, peaked +0.50R (374.33 against a 374.59 day
    high), the break-even ratchet armed, price came straight back for -$0.20.
    The one trade of the three the exit owns: ``gave-back``.
  * **DELL #363** — filled 564.99, MFE +0.26R, held 5h30m and flattened at
    563.50 for -$4.47. ``no-follow-through``.

Attribution on that day: entry -$36.55, exit -$0.20. The exit geometry owns
0.5% of the session's loss.

Pure: no DB, no network, no bars. Rows are verbatim ``replay_geometry`` output
for the live geometry over the real `trades` rows.
"""

from __future__ import annotations

import pytest

from bot import config
from bot.exit_sim import (EXCURSION_CLASSES, classify_excursion,
                          excursion_summary)


def _row(trade_id, symbol, day, pl, mfe_r, mae_r, mfe_usd, reason):
    return {"trade_id": trade_id, "symbol": symbol, "day": day,
            "actual_pl": pl, "actual_reason": reason, "sim_pl": pl,
            "sim_reason": reason, "mfe_r": mfe_r, "mae_r": mae_r,
            "mfe_usd": mfe_usd, "armed_breakeven": False, "armed_trail": False}


# The 2026-10-02 session, verbatim.
INTC_361 = _row(361, "INTC", "2026-10-02", -32.08, 0.11, -1.06, 3.48, "STOP")
TSLA_362 = _row(362, "TSLA", "2026-10-02", -0.20, 0.50, -0.09, 15.08, "STOP")
DELL_363 = _row(363, "DELL", "2026-10-02", -4.47, 0.26, -0.67, 8.46,
                "EOD_FLATTEN")
SESSION_1002 = [INTC_361, TSLA_362, DELL_363]

# The whole live ORB book, 2026-09-21..2026-10-02, same source.
ORB_BOOK = SESSION_1002 + [
    _row(354, "META", "2026-09-21", 39.11, 1.41, -0.68, 54.00, "TAKE_PROFIT"),
    _row(355, "MSFT", "2026-09-21", 15.40, 0.54, -0.71, 17.30, "EOD_FLATTEN"),
    _row(356, "INTC", "2026-09-21", 8.08, 1.31, -0.01, 24.60, "STOP"),
    _row(357, "META", "2026-09-24", 23.20, 1.03, -0.54, 26.70, "EOD_FLATTEN"),
    _row(358, "AAPL", "2026-09-30", -23.42, 0.18, -1.03, 5.90, "STOP"),
    _row(359, "AMZN", "2026-09-30", -0.16, 0.56, -0.04, 19.38, "STOP"),
    _row(360, "GOOG", "2026-09-30", -33.75, 0.23, -1.23, 10.60, "STOP"),
]


# --- classification ---------------------------------------------------------

def test_classes_match_the_1002_session():
    """The day's three trades land in the classes the review attributed them to."""
    trigger = config.BREAKEVEN_TRIGGER_R
    assert classify_excursion(INTC_361, trigger) == "no-follow-through"
    assert classify_excursion(DELL_363, trigger) == "no-follow-through"
    assert classify_excursion(TSLA_362, trigger) == "gave-back"


def test_a_profitable_trade_is_banked_whatever_its_excursion():
    """``banked`` is tested first, so a winner never lands in a blame bucket.

    A trade can bank green off an excursion below the trigger (the trail never
    armed; the 15:55 flatten simply caught it above the fill). Classifying that
    as 'no-follow-through' would charge a WINNER to the entry and break the
    invariant that the three sub-totals sum to the book.
    """
    tiny_winner = _row(999, "X", "2026-10-02", 1.23, 0.05, -0.40, 2.0,
                       "EOD_FLATTEN")
    assert classify_excursion(tiny_winner, 0.5) == "banked"


def test_break_even_exactly_at_the_trigger_is_the_exits_problem():
    """MFE == trigger armed the ratchet, so the give-back is real, not rounding.

    TSLA #362 peaked at exactly +0.50R against a 0.5R trigger and the broker leg
    really did move to 371.31. A ``<`` comparison on the wrong side of that
    boundary would charge the day's one genuine give-back to the entry.
    """
    assert classify_excursion(TSLA_362, 0.5) == "gave-back"
    assert classify_excursion({**TSLA_362, "mfe_r": 0.49}, 0.5) == \
        "no-follow-through"


@pytest.mark.parametrize("row", SESSION_1002 + ORB_BOOK)
def test_every_row_lands_in_exactly_one_known_class(row):
    assert classify_excursion(row, config.BREAKEVEN_TRIGGER_R) in EXCURSION_CLASSES


# --- the summary ------------------------------------------------------------

def test_attribution_is_exhaustive_and_sums_to_the_book():
    """The invariant that makes the attribution quotable: no trade double-counted."""
    s = excursion_summary(ORB_BOOK)
    assert s["trades"] == len(ORB_BOOK)
    assert sum(v["trades"] for v in s["attribution"].values()) == len(ORB_BOOK)
    total = sum(v["total_pl"] for v in s["attribution"].values())
    assert total == pytest.approx(sum(r["actual_pl"] for r in ORB_BOOK), abs=0.01)
    assert total == pytest.approx(-8.29, abs=0.01)


def test_the_1002_session_charges_the_loss_to_the_entry():
    """-$36.55 entry vs -$0.20 exit: the finding the review shipped on."""
    s = excursion_summary(SESSION_1002)
    assert s["attribution"]["no-follow-through"] == {
        "trades": 2, "total_pl": -36.55, "peak_mfe_usd": 11.94}
    assert s["attribution"]["gave-back"] == {
        "trades": 1, "total_pl": -0.2, "peak_mfe_usd": 15.08}
    assert s["attribution"]["banked"]["trades"] == 0
    assert s["entry_owned_pl"] == -36.55
    assert s["exit_owned_pl"] == -0.2
    assert abs(s["exit_owned_pl"]) < abs(s["entry_owned_pl"]) / 100.0


def test_orb_book_edge_ratio_fails_its_only_non_arbitrary_floor():
    """edge_ratio 1.012 on mean MFE +0.613R vs mean |MAE| 0.606R.

    Pinned to 3dp because the verdict string flips at exactly 1.000 and the
    whole point of the metric is that the floor is not tunable.
    """
    s = excursion_summary(ORB_BOOK)
    assert s["mean_mfe_r"] == pytest.approx(0.613, abs=0.001)
    assert s["mean_mae_r"] == pytest.approx(0.606, abs=0.001)
    assert s["edge_ratio"] == pytest.approx(1.012, abs=0.001)
    assert "NO DIRECTIONAL EDGE" not in s["verdict"]      # 1.012 > 1.0, barely


def test_an_anti_predictive_book_is_named_as_such():
    """Below 1.0 the entry is anti-predictive and no exit can rescue it."""
    s = excursion_summary([
        _row(1, "A", "d", -10.0, 0.20, -1.00, 2.0, "STOP"),
        _row(2, "B", "d", -10.0, 0.30, -1.00, 3.0, "STOP"),
    ])
    assert s["edge_ratio"] == pytest.approx(0.25, abs=0.001)
    assert s["verdict"].startswith("NO DIRECTIONAL EDGE")


def test_target_reachability_is_scored_against_the_brackets_own_break_even():
    """0/10 ever printed 1.5R against the 40% a 1.5R bracket needs."""
    s = excursion_summary(ORB_BOOK)
    assert s["target_r"] == config.RR_RATIO == 1.5
    assert s["target_reached"] == 0
    assert s["target_reach_pct"] == 0.0
    assert s["target_reach_needed_pct"] == pytest.approx(40.0, abs=0.1)


def test_trigger_and_target_are_overridable_for_what_ifs():
    """A what-if must be able to ask the question at another trigger.

    At a 0.25R trigger TSLA and DELL both clear it, so DELL's -$4.47 moves from
    the entry's column to the exit's — which is exactly the trade-off a trigger
    sweep has to be able to price.
    """
    s = excursion_summary(SESSION_1002, breakeven_trigger_r=0.25, target_r=1.0)
    assert s["breakeven_trigger_r"] == 0.25
    assert s["attribution"]["gave-back"]["trades"] == 2
    assert s["attribution"]["gave-back"]["total_pl"] == pytest.approx(-4.67, abs=0.01)
    assert s["attribution"]["no-follow-through"]["trades"] == 1
    assert s["target_reach_needed_pct"] == pytest.approx(50.0, abs=0.1)


def test_empty_book_returns_empty_not_a_crash():
    """Zero-trade sessions are the norm for this bot — four of six in late Sept."""
    assert excursion_summary([]) == {}


def test_a_book_that_never_traded_below_its_fill_leaves_the_ratio_undefined():
    """mean |MAE| == 0 has no honest quotient; None beats a fabricated infinity."""
    s = excursion_summary([_row(1, "A", "d", 5.0, 1.0, 0.0, 5.0, "TAKE_PROFIT")])
    assert s["edge_ratio"] is None
    assert s["verdict"].startswith("UNDEFINED")


def test_summary_does_not_mutate_its_input():
    before = [dict(r) for r in SESSION_1002]
    excursion_summary(SESSION_1002)
    assert SESSION_1002 == before
