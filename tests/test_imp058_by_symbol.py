"""IMP-058 — scripts/feasibility --by-symbol: per-symbol ceiling vs the board.

The fixtures below are REAL post-gate fills. #352 (MSFT) and #353 (NVDA) are the
two trades of 2026-09-17, the session that motivated the change: both closed
GREEN (+$1.05 / +$1.72), both scored SCRATCH, and both were win-INFEASIBLE with
ceilings of +0.231R and +0.168R measured off that day's SIP 1-minute bars. The
rest are the symbols whose per-symbol record two earlier routines had to
hand-roll, which is the defect this instrument closes.

The load-bearing assertion is `test_board_median_matches_summarize`: the board
median a symbol's watchlist trigger is judged against must be the SAME number
the headline prints. IMP-049 and IMP-053 were both two-instruments-one-verdict
defects; this test exists so a third cannot be introduced silently.
"""

from __future__ import annotations

import pytest

from bot import doctrine
from scripts import feasibility as F


def _rec(trade_id, symbol, day, ceiling, pl, verdict=doctrine.SCRATCH,
         range_r=None, exit_reason="EOD_FLATTEN"):
    """A build_records()-shaped record, so the summaries test offline."""
    return {
        "trade_id": trade_id, "symbol": symbol, "day": day,
        "ceiling": ceiling, "range_r": range_r, "doctrine": verdict,
        "profit_r": None, "pl": pl, "exit_reason": exit_reason,
    }


# --- The two real fills of 2026-09-17 ---------------------------------------
MSFT_352 = _rec(352, "MSFT", "2026-09-17", 0.231, 1.05, range_r=1.12)
NVDA_353 = _rec(353, "NVDA", "2026-09-17", 0.168, 1.72, range_r=0.83)

# --- Supporting post-gate fills, so each symbol has a record to summarise ----
MSFT_WIN = _rec(300, "MSFT", "2026-08-20", 1.295, 78.40, doctrine.WIN,
                exit_reason="TAKE_PROFIT")
MSFT_MID = _rec(310, "MSFT", "2026-08-28", 1.000, 12.10, doctrine.SCRATCH)
MSFT_LOW = _rec(320, "MSFT", "2026-09-04", 0.300, -9.00, doctrine.FAIL,
                exit_reason="STOP")
NVDA_LOW1 = _rec(330, "NVDA", "2026-09-08", 0.210, -14.00, doctrine.FAIL,
                 exit_reason="STOP")
NVDA_LOW2 = _rec(340, "NVDA", "2026-09-10", 0.140, -21.00, doctrine.FAIL,
                 exit_reason="STOP")
NVDA_MID = _rec(344, "NVDA", "2026-09-11", 0.521, -6.00, doctrine.SCRATCH)

BOOK = [MSFT_352, NVDA_353, MSFT_WIN, MSFT_MID, MSFT_LOW,
        NVDA_LOW1, NVDA_LOW2, NVDA_MID]


# --- _median is one function, used by both summaries ------------------------

def test_median_is_the_upper_median():
    assert F._median([0.1, 0.2, 0.3]) == 0.2
    assert F._median([0.4, 0.1, 0.3, 0.2]) == 0.3     # n//2 on a sorted copy
    assert F._median([0.5]) == 0.5


def test_median_does_not_mutate_its_argument():
    values = [0.3, 0.1, 0.2]
    F._median(values)
    assert values == [0.3, 0.1, 0.2]


def test_board_median_matches_summarize():
    """THE point of the change: one median, two readers, identical number."""
    board = F.board_baseline(BOOK)
    assert board["median_ceiling"] == F.summarize(BOOK)["median_ceiling"]


def test_board_feasible_rate_matches_summarize_reachable():
    board = F.board_baseline(BOOK)
    s = F.summarize(BOOK)
    assert board["feasible"] == s["reachable"]
    assert board["feasible_rate"] == s["reachable_share"]


def test_board_baseline_is_none_when_no_ceiling_is_usable():
    """An unknown board is not a board of zero — nothing may be judged on it."""
    assert F.board_baseline([]) is None
    assert F.board_baseline([{"symbol": "MSFT", "ceiling": None, "pl": 0.0}]) is None


# --- by_symbol ---------------------------------------------------------------

def test_by_symbol_partitions_the_book():
    stats = F.by_symbol(BOOK)
    assert set(stats) == {"MSFT", "NVDA"}
    assert stats["MSFT"]["fills"] + stats["NVDA"]["fills"] == len(BOOK)


def test_by_symbol_counts_the_real_0917_fills():
    stats = F.by_symbol(BOOK)
    # NVDA: 4 fills (#353 + three supporting), none reaching +1.0R.
    assert stats["NVDA"]["fills"] == 4
    assert stats["NVDA"]["feasible"] == 0
    assert stats["NVDA"]["feasible_rate"] == 0.0
    assert stats["NVDA"]["best_ceiling"] == 0.521
    # MSFT: 4 fills, two win-feasible — MSFT_MID's ceiling is exactly +1.000R,
    # which IS the WIN bar (`is_reachable` is >=, not >).
    assert stats["MSFT"]["fills"] == 4
    assert stats["MSFT"]["feasible"] == 2
    assert stats["MSFT"]["feasible_rate"] == 50.0
    assert stats["MSFT"]["median_ceiling"] == 1.000
    assert stats["MSFT"]["wins"] == 1


def test_by_symbol_net_and_wins_are_per_symbol():
    stats = F.by_symbol(BOOK)
    assert stats["NVDA"]["net"] == pytest.approx(1.72 - 14.00 - 21.00 - 6.00)
    assert stats["NVDA"]["wins"] == 0
    assert stats["MSFT"]["net"] == pytest.approx(1.05 + 78.40 + 12.10 - 9.00)


def test_by_symbol_skips_records_without_a_ceiling():
    """A trade whose ceiling is unknown must not be counted as infeasible."""
    book = BOOK + [_rec(999, "TSM", "2026-09-17", None, -5.0)]
    stats = F.by_symbol(book)
    assert "TSM" not in stats


def test_win_feasible_uses_the_imported_doctrine_bar():
    """The +1.0R bar comes from bot.doctrine — never redefined here."""
    assert F.WIN_CEILING_R == doctrine.WIN_MIN_R
    exactly_at_bar = [_rec(1, "AAA", "2026-09-17", doctrine.WIN_MIN_R, 0.0)]
    assert F.by_symbol(exactly_at_bar)["AAA"]["feasible"] == 1


# --- trigger_verdict ---------------------------------------------------------

def test_trigger_fires_only_when_both_legs_are_below_the_board():
    board = F.board_baseline(BOOK)
    stats = F.by_symbol(BOOK)
    nvda = F.trigger_verdict(stats["NVDA"], board)
    assert nvda["below_rate"] and nvda["below_median"]
    assert nvda["fires"] and nvda["verdict"] == "FIRES"


def test_trigger_holds_when_only_one_leg_is_below():
    board = {"feasible_rate": 20.0, "median_ceiling": 0.400,
             "fills": 100, "feasible": 20}
    one_leg = {"fills": 8, "feasible": 1, "feasible_rate": 12.5,
               "median_ceiling": 0.900, "best_ceiling": 1.2, "net": 0.0, "wins": 0}
    tv = F.trigger_verdict(one_leg, board)
    assert tv["below_rate"] and not tv["below_median"]
    assert not tv["fires"] and tv["verdict"] == "holds"


def test_equal_to_the_board_is_not_below_it():
    """Strict inequality on both legs — a symbol at the board does not fire."""
    board = {"feasible_rate": 15.9, "median_ceiling": 0.380,
             "fills": 126, "feasible": 20}
    at_board = {"fills": 11, "feasible": 2, "feasible_rate": 15.9,
                "median_ceiling": 0.380, "best_ceiling": 1.0, "net": 0.0, "wins": 0}
    tv = F.trigger_verdict(at_board, board)
    assert not tv["below_rate"] and not tv["below_median"]
    assert not tv["fires"]


def test_short_sample_is_insufficient_never_fires():
    """Below MIN_TRIGGER_FILLS the verdict is `insufficient`, not a fire."""
    board = {"feasible_rate": 20.0, "median_ceiling": 0.400,
             "fills": 100, "feasible": 20}
    thin = {"fills": 2, "feasible": 0, "feasible_rate": 0.0,
            "median_ceiling": 0.100, "best_ceiling": 0.2, "net": -3.0, "wins": 0}
    tv = F.trigger_verdict(thin, board)
    assert tv["below_rate"] and tv["below_median"]        # both legs are below
    assert not tv["enough_fills"]
    assert not tv["fires"] and tv["verdict"] == "insufficient"


def test_min_fills_is_configurable_and_defaults_to_four():
    """META's trigger as written says '4+ fills'."""
    assert F.MIN_TRIGGER_FILLS == 4
    board = {"feasible_rate": 20.0, "median_ceiling": 0.400,
             "fills": 100, "feasible": 20}
    three = {"fills": 3, "feasible": 0, "feasible_rate": 0.0,
             "median_ceiling": 0.100, "best_ceiling": 0.2, "net": 0.0, "wins": 0}
    assert not F.trigger_verdict(three, board)["fires"]
    assert F.trigger_verdict(three, board, min_fills=3)["fires"]


def test_a_relative_comparator_cannot_park_the_whole_board():
    """The reason the test is relative: an absolute bar fires on every name.

    The post-gate book is ~94% win-infeasible, so any absolute threshold near
    +1.0R would convict every symbol it holds. Against the board, the symbol at
    the top of a bad book still holds.
    """
    board = F.board_baseline(BOOK)
    stats = F.by_symbol(BOOK)
    fired = [s for s, st in stats.items()
             if F.trigger_verdict(st, board)["fires"]]
    assert fired != list(stats)          # not everything fires
    assert "MSFT" not in fired           # the better name is not convicted


# --- CLI ---------------------------------------------------------------------

def test_cli_by_symbol_renders(monkeypatch, capsys):
    """--by-symbol prints the table without touching the network or the DB."""
    rows = [{"trade_id": 352, "symbol": "MSFT", "exit_time": _dt("2026-09-17")},
            {"trade_id": 353, "symbol": "NVDA", "exit_time": _dt("2026-09-17")}]
    monkeypatch.setattr(F.analytics, "load_closed_trades", lambda: rows)
    monkeypatch.setattr(F, "build_records", lambda r, feed: (BOOK, ["stubbed"]))
    assert F.main(["--since", "2026-07-25", "--by-symbol"]) == 0
    out = capsys.readouterr().out
    assert "PER-SYMBOL vs the board" in out
    assert "MSFT" in out and "NVDA" in out
    assert "FIRES" in out


def test_cli_without_the_flag_prints_no_symbol_table(monkeypatch, capsys):
    rows = [{"trade_id": 352, "symbol": "MSFT", "exit_time": _dt("2026-09-17")}]
    monkeypatch.setattr(F.analytics, "load_closed_trades", lambda: rows)
    monkeypatch.setattr(F, "build_records", lambda r, feed: (BOOK, ["stubbed"]))
    assert F.main(["--since", "2026-07-25"]) == 0
    assert "PER-SYMBOL vs the board" not in capsys.readouterr().out


def _dt(day: str):
    from datetime import datetime
    return datetime.strptime(day, "%Y-%m-%d")


# --- blast radius ------------------------------------------------------------

def test_module_cannot_reach_the_order_path():
    """A diagnostic that can reach execution is a diagnostic that can trade."""
    import inspect
    src = inspect.getsource(F)
    for forbidden in ("bot.execution", "bot.broker", "bot.engine",
                      "from bot import execution", "import broker"):
        assert forbidden not in src
