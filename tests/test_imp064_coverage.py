"""IMP-064 — review-coverage detection (weekly, 2026-09-26).

The regression these tests exist for: 2026-09-22, 09-23 and 09-24 all completed
with no daily-review entry, 09-24 had a fill (META +$23.20), and nothing noticed
for four days. The core test replays the real week evening by evening and pins
that the detector fires on exactly the three nights it should have and is silent
on the others.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from bot import config, coverage


def _summary(day: str, *, sells: int = 0, pl: float = 0.0,
             equity: float = 7_250.0) -> dict:
    return {"trade_date": date.fromisoformat(day), "num_sells": sells,
            "gross_pl": pl, "equity_open": equity, "equity_close": equity + pl}


# The real week, as `daily_summary` recorded it (scripts.report, 2026-09-26).
REAL_WEEK = [
    _summary("2026-09-16", sells=4, pl=-47.85),
    _summary("2026-09-17", sells=2, pl=2.77),
    _summary("2026-09-18", sells=0, pl=0.0),
    _summary("2026-09-21", sells=3, pl=62.59),
    _summary("2026-09-22", sells=0, pl=0.0),
    _summary("2026-09-23", sells=0, pl=0.0),
    _summary("2026-09-24", sells=1, pl=23.20),
    _summary("2026-09-25", sells=0, pl=0.0),
]

# memory/daily-review.md as it stood BEFORE the 09-25 run recovered the backlog:
# the headings jump 09-21 -> (nothing).
REVIEW_TEXT_WITH_GAP = """## 2026-09-16 — Daily Review
body
## 2026-09-17 — Daily Review
body
## 2026-09-18 — Daily Review
body
## 2026-09-21 — Daily Review
body
"""

# ...and as it stands now, after the 09-25 entry landed (09-22/23/24 still have
# no entries of their own; the 09-25 entry recovered them in prose).
REVIEW_TEXT_AFTER_0925 = REVIEW_TEXT_WITH_GAP + """## 2026-09-25 — Daily Review
body
"""


# --- the regression itself ---

@pytest.mark.parametrize("as_of,expect_gap,expect_stale", [
    ("2026-09-22", False, None),          # 09-21 is reviewed; 09-22 is exempt (today)
    ("2026-09-23", True, "2026-09-22"),   # ALARM: 09-22 completed unreviewed
    ("2026-09-24", True, "2026-09-23"),   # ALARM
    ("2026-09-25", True, "2026-09-24"),   # ALARM, and this one had a fill
])
def test_replays_the_real_gap_evening_by_evening(as_of, expect_gap, expect_stale):
    """Fires on exactly the three nights the live bot stayed silent."""
    result = coverage.check(REAL_WEEK, REVIEW_TEXT_WITH_GAP,
                            today=date.fromisoformat(as_of))
    assert result["ok"] is True
    assert result["gapped"] is expect_gap
    if expect_stale is None:
        assert result["stale"] is None
    else:
        assert str(result["stale"]["date"]) == expect_stale


def test_the_missed_session_with_a_fill_is_flagged_as_having_traded():
    """09-24 booked +$23.20 and was never reviewed — the alert must say so."""
    result = coverage.check(REAL_WEEK, REVIEW_TEXT_WITH_GAP,
                            today=date(2026, 9, 25))
    assert result["stale"]["had_fills"] is True
    assert result["stale"]["net_pl"] == 23.20
    assert "23.20" in coverage.describe(result)
    assert "GAP" in coverage.describe(result)


def test_backlog_is_reported_but_only_the_newest_session_alarms():
    """Self-clearing: once 09-25's review lands, the older hole stops paging."""
    result = coverage.check(REAL_WEEK, REVIEW_TEXT_AFTER_0925,
                            today=date(2026, 9, 26))
    assert result["gapped"] is False          # newest eligible (09-25) is reviewed
    assert result["reason"] == "newest session reviewed"
    missing = [str(s["date"]) for s in result["missing"]]
    assert missing == ["2026-09-22", "2026-09-23", "2026-09-24"]   # still surfaced
    described = coverage.describe(result)
    assert "ok" in described and "2026-09-24*" in described  # * marks a traded session


def test_todays_session_is_exempt_so_it_cannot_alarm_every_evening():
    """post_close runs at the close; that night's review is written hours later."""
    result = coverage.check(REAL_WEEK, REVIEW_TEXT_AFTER_0925,
                            today=date(2026, 9, 25))
    # 09-25 is `today` here, so it is not judged even though its review exists.
    assert all(str(s["date"]) != "2026-09-25" for s in result["missing"])
    assert result["stale"]["date"] == date(2026, 9, 24)


def test_fully_covered_history_is_silent():
    text = "".join(f"## {s['trade_date']} — Daily Review\nbody\n" for s in REAL_WEEK)
    result = coverage.check(REAL_WEEK, text, today=date(2026, 9, 26))
    assert result["gapped"] is False
    assert result["missing"] == []
    assert result["reviewed"] == result["sessions"] == len(REAL_WEEK)
    assert "ok" in coverage.describe(result)


# --- "never report fine when you do not know" (IMP-061's rule, reused) ---

def test_empty_window_reports_cannot_check_not_covered():
    result = coverage.check([], REVIEW_TEXT_AFTER_0925, today=date(2026, 9, 26))
    assert result["ok"] is False
    assert result["gapped"] is False
    assert result["reason"] == "no completed sessions in window"
    assert "skipped" in coverage.describe(result)


def test_unreadable_review_file_cannot_manufacture_an_alarm():
    """A missing file returns None, and None must not read as 'nothing reviewed'."""
    assert coverage.read_review_text("/nonexistent/daily-review.md") is None
    # None text => no headings => everything looks unreviewed, so the detector
    # would alarm. That is acceptable ONLY because read failure is distinguishable;
    # pin that the reader itself never raises, which is the part that could break
    # the post-close path.
    assert coverage.parse_reviewed_dates(None) == set()


def test_unparseable_trade_date_drops_the_session_rather_than_raising():
    rows = REAL_WEEK + [{"trade_date": "not-a-date", "num_sells": 9, "gross_pl": 1.0}]
    sessions = coverage.sessions_from_summaries(rows)
    assert len(sessions) == len(REAL_WEEK)


def test_malformed_heading_does_not_blind_the_whole_file():
    text = "## 2026-13-45 — Daily Review\n" + REVIEW_TEXT_AFTER_0925
    assert date(2026, 9, 21) in coverage.parse_reviewed_dates(text)


# --- parsing / classification details ---

def test_only_line_anchored_headings_count():
    """A date quoted in body prose must not fake a review entry."""
    text = "## 2026-09-21 — Daily Review\nsee ## 2026-09-22 for context\n"
    assert coverage.parse_reviewed_dates(text) == {date(2026, 9, 21)}


def test_heading_counts_regardless_of_trailing_prose():
    assert coverage.parse_reviewed_dates("## 2026-09-24\n") == {date(2026, 9, 24)}


def test_had_fills_uses_sells_and_falls_back_to_gross_pl():
    assert coverage.had_fills({"num_sells": 1, "gross_pl": 0.0}) is True
    assert coverage.had_fills({"num_sells": 0, "gross_pl": -12.5}) is True
    assert coverage.had_fills({"num_sells": 0, "gross_pl": 0.0}) is False
    assert coverage.had_fills({"num_sells": None, "gross_pl": None}) is False


def test_datetime_trade_date_is_accepted():
    rows = [{"trade_date": datetime(2026, 9, 24, 16, 0), "num_sells": 1,
             "gross_pl": 23.2}]
    assert coverage.sessions_from_summaries(rows)[0]["date"] == date(2026, 9, 24)


def test_sessions_are_sorted_oldest_first_regardless_of_row_order():
    rows = list(reversed(REAL_WEEK))
    dates = [s["date"] for s in coverage.sessions_from_summaries(rows)]
    assert dates == sorted(dates)


def test_lookback_trims_to_the_most_recent_completed_sessions():
    result = coverage.check(REAL_WEEK, "", today=date(2026, 9, 26), lookback=2)
    assert result["sessions"] == 2
    assert [str(s["date"]) for s in result["missing"]] == ["2026-09-24", "2026-09-25"]


def test_zero_or_negative_lookback_degrades_to_one_session_not_zero():
    """A bad constant must not silently disable the check."""
    for bad in (0, -5):
        result = coverage.check(REAL_WEEK, "", today=date(2026, 9, 26), lookback=bad)
        assert result["ok"] is True and result["sessions"] == 1


# --- invariants: this is a detector, not control ---

FORBIDDEN_IN_DETECTOR = ("broker", "execution", "sizing", "exits", "signals",
                         "place_stock_order", "close_position", "submit")


def test_coverage_module_imports_nothing_from_the_order_path():
    """Parsed, not grepped — the docstring discusses `broker` on purpose."""
    import ast

    tree = ast.parse(open(coverage.__file__, encoding="utf-8").read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.update(a.name for a in node.names)
            if node.module:
                imported.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Import):
            imported.update(a.name.split(".")[-1] for a in node.names)
    assert not imported & set(FORBIDDEN_IN_DETECTOR), (
        f"coverage.py must not import the order path: "
        f"{sorted(imported & set(FORBIDDEN_IN_DETECTOR))}")
    # And nothing in the executable body names them either (comments/docstrings
    # are excluded by walking the AST for attribute/name nodes).
    referenced = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    referenced |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not referenced & set(FORBIDDEN_IN_DETECTOR)


def test_risk_invariants_unchanged_by_this_change():
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert str(config.ENTRY_CUTOFF_ET) == "15:30"
    assert str(config.FLATTEN_ET) == "15:55"
    assert config.COVERAGE_LOOKBACK_SESSIONS == 10


def test_engine_calls_the_detector_after_the_summary_is_written():
    """Wiring guard: post_close must reconcile AND check coverage."""
    from bot import engine
    src = open(engine.__file__, encoding="utf-8").read()
    assert "_check_review_coverage" in src
    assert "coverage.check" in src
    # Ordering: coverage runs after the day is marked summarized, like reconcile.
    assert src.index("self.summarized_on = today") < src.index(
        "self._check_review_coverage(today)")
