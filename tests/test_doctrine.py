"""Stop-exit doctrine (IMP-046) — WIN / SCRATCH / FAIL over REAL recorded trades.

Every fixture below is a verbatim row from the live `trades` table, so these are
regression tests against the sessions that motivated the module rather than
against invented numbers. The anchor case is **WMT #314 (2026-09-01)**: the day's
only trade, +$15.33, headline win rate 100% — and a SCRATCH, because it banked
+0.44R against a +1R bar. If a future change ever lets that row score a WIN, the
doctrine has been gamed and this file fails.

Pure: no DB, no network. Rows are dicts shaped like `analytics.load_closed_trades`.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from bot import doctrine

# --- real rows, copied from the live trades table -------------------------

WMT_314 = dict(trade_id=314, symbol="WMT", entry_price=105.46, stop_price=103.94,
               exit_price=106.1265, realized_pl=15.33, exit_reason="STOP",
               exit_time=datetime(2026, 9, 1, 11, 10, 16))       # +0.438R
AAPL_267 = dict(trade_id=267, symbol="AAPL", entry_price=311.62, stop_price=306.96,
                exit_price=318.6571, realized_pl=49.26, exit_reason="TAKE_PROFIT",
                exit_time=datetime(2026, 8, 19, 14, 20, 0))      # +1.51R
INTC_298 = dict(trade_id=298, symbol="INTC", entry_price=89.6029, stop_price=88.14,
                exit_price=92.5, realized_pl=60.84, exit_reason="TAKE_PROFIT",
                exit_time=datetime(2026, 8, 27, 15, 12, 0))      # +1.98R
CRM_281 = dict(trade_id=281, symbol="CRM", entry_price=211.149, stop_price=207.51,
               exit_price=211.11, realized_pl=-0.39, exit_reason="STOP",
               exit_time=datetime(2026, 8, 24, 14, 55, 0))       # -0.01R, break-even
TSM_307 = dict(trade_id=307, symbol="TSM", entry_price=427.88, stop_price=421.64,
               exit_price=421.55, realized_pl=-31.65, exit_reason="STOP",
               exit_time=datetime(2026, 8, 28, 11, 2, 0))        # -1.01R, full stop
COST_312 = dict(trade_id=312, symbol="COST", entry_price=948.0, stop_price=933.39,
                exit_price=942.9, realized_pl=-10.2, exit_reason="EOD_FLATTEN",
                exit_time=datetime(2026, 8, 31, 15, 55, 54))     # -0.35R, faded
QQQ_294 = dict(trade_id=294, symbol="QQQ", entry_price=711.65, stop_price=701.11,
               exit_price=710.96, realized_pl=-2.07, exit_reason="EOD_FLATTEN",
               exit_time=datetime(2026, 8, 26, 15, 55, 50))      # -0.07R, scratch

ALL_ROWS = [AAPL_267, CRM_281, QQQ_294, INTC_298, TSM_307, COST_312, WMT_314]


# --- profit_R -------------------------------------------------------------

@pytest.mark.parametrize("row, expected", [
    (WMT_314, 0.438), (AAPL_267, 1.509), (INTC_298, 1.980),
    (CRM_281, -0.011), (TSM_307, -1.014), (COST_312, -0.349), (QQQ_294, -0.065),
])
def test_profit_r_matches_the_recorded_geometry(row, expected):
    assert doctrine.profit_r(row) == pytest.approx(expected, abs=0.005)


def test_profit_r_is_none_without_a_usable_stop_anchor():
    assert doctrine.profit_r({"entry_price": 100.0, "exit_price": 101.0}) is None
    # stop at/above entry is not a long's plan stop — excluded, never guessed
    assert doctrine.profit_r({"entry_price": 100.0, "stop_price": 100.0,
                              "exit_price": 101.0}) is None


# --- classification -------------------------------------------------------

def test_wmt_314_the_2026_09_01_trade_is_a_scratch_not_a_win():
    """The anchor case. +$15.33, the session's only trade, headline 100% wins.

    It banked +0.438R on a stop that ratcheted 5 times — real money, correctly
    managed, and NOT a win: the doctrine's bar is +1R and this never reached it.
    Scoring it on `realized_pl > 0` is exactly the reporting failure IMP-046
    exists to end.
    """
    assert WMT_314["realized_pl"] > 0
    assert doctrine.classify(WMT_314) == doctrine.SCRATCH
    assert doctrine.fail_kind(WMT_314) is None


@pytest.mark.parametrize("row", [AAPL_267, INTC_298])
def test_take_profit_fills_are_wins(row):
    assert doctrine.classify(row) == doctrine.WIN


def test_full_1r_stop_is_a_fail_split_as_full_1r():
    assert doctrine.classify(TSM_307) == doctrine.FAIL
    assert doctrine.fail_kind(TSM_307) == "full-1R"


def test_break_even_stop_is_a_fail_not_a_scratch():
    """CRM #281 gave back everything to the armed stop: -$0.39, ~0.00R."""
    assert doctrine.classify(CRM_281) == doctrine.FAIL
    assert doctrine.fail_kind(CRM_281) == "break-even"


def test_a_break_even_stop_that_books_a_profit_still_fails():
    """The directive's worked example: +$0.02 on a break-even stop is a FAIL.

    Sign of P&L must not rescue it — profit_R +0.013 is inside the +0.25R FAIL
    band, so the bucket is FAIL and the kind is break-even.
    """
    row = dict(entry_price=100.0, stop_price=98.5, exit_price=100.02,
               realized_pl=0.02, exit_reason="STOP")
    assert doctrine.classify(row) == doctrine.FAIL
    assert doctrine.fail_kind(row) == "break-even"


def test_flatten_below_minus_quarter_r_is_a_fail_and_above_it_a_scratch():
    assert doctrine.classify(COST_312) == doctrine.FAIL     # -0.35R
    assert doctrine.fail_kind(COST_312) == "faded"
    assert doctrine.classify(QQQ_294) == doctrine.SCRATCH   # -0.07R
    assert doctrine.fail_kind(QQQ_294) is None


def test_a_stop_that_banks_a_full_r_is_a_win_even_though_it_stopped():
    """The doctrine faults stops that pay nothing, not stops as a mechanism.

    A trail that rides to +1R and then stops has done the job the strategy is
    written to do, and must score as a WIN — otherwise the rule would punish the
    exact behaviour it wants more of.
    """
    row = dict(entry_price=100.0, stop_price=98.0, exit_price=102.0,
               realized_pl=40.0, exit_reason="STOP")
    assert doctrine.classify(row) == doctrine.WIN


def test_unusable_geometry_never_awards_a_win():
    """No stop anchor = no evidence a full R was banked. Cap at SCRATCH."""
    green = dict(entry_price=100.0, exit_price=140.0, realized_pl=400.0,
                 exit_reason="EOD_FLATTEN")
    red = dict(entry_price=100.0, exit_price=60.0, realized_pl=-400.0,
               exit_reason="EOD_FLATTEN")
    assert doctrine.classify(green) == doctrine.SCRATCH
    assert doctrine.classify(red) == doctrine.FAIL


def test_ratchet_stop_reasons_still_count_as_stop_exits():
    """Guards against a future exit_reason rename silently emptying the bucket."""
    assert doctrine.is_stop_exit({"exit_reason": "STOP"})
    assert doctrine.is_stop_exit({"exit_reason": "RATCHET_STOP"})
    assert doctrine.is_stop_exit({"exit_reason": "PLAN_STOP"})
    assert not doctrine.is_stop_exit({"exit_reason": "EOD_FLATTEN"})
    assert not doctrine.is_stop_exit({"exit_reason": "TAKE_PROFIT"})


# --- summarize ------------------------------------------------------------

def test_summarize_reports_true_win_rate_beside_the_headline_one():
    s = doctrine.summarize(ALL_ROWS)
    assert s["trades"] == 7
    assert s["win"] == 2 and s["scratch"] == 2 and s["fail"] == 3
    assert s["fail_kinds"] == {"full-1R": 1, "break-even": 1, "faded": 1}
    assert s["stops"] == 3                       # WMT, CRM, TSM
    assert s["stop_rate"] == pytest.approx(42.9, abs=0.1)
    assert s["true_win_rate"] == pytest.approx(28.6, abs=0.1)
    # headline counts WMT #314 and both take-profits as wins — the inflation
    assert s["headline_win_rate"] == pytest.approx(42.9, abs=0.1)
    assert s["true_win_rate"] < s["headline_win_rate"]


def test_summarize_of_the_2026_09_01_session_is_one_scratch_and_no_wins():
    """The live session this module shipped on: 1 trade, +$15.33, 0% true wins."""
    s = doctrine.summarize([WMT_314])
    assert s["trades"] == 1 and s["stop_rate"] == 100.0
    assert (s["win"], s["scratch"], s["fail"]) == (0, 1, 0)
    assert s["true_win_rate"] == 0.0 and s["headline_win_rate"] == 100.0
    assert s["total_pl"] == 15.33


def test_summarize_of_nothing_is_zeroed_not_an_exception():
    s = doctrine.summarize([])
    assert s["trades"] == 0 and s["true_win_rate"] == 0.0 and s["avg_r"] is None


def test_summarize_ignores_open_trades():
    rows = ALL_ROWS + [dict(entry_price=100.0, stop_price=98.0, realized_pl=None,
                            exit_reason=None)]
    assert doctrine.summarize(rows)["trades"] == 7


# --- sessions and escalation ---------------------------------------------

def test_by_session_groups_on_exit_date():
    per = doctrine.by_session(ALL_ROWS)
    assert list(per) == [r["exit_time"].date() for r in
                         sorted(ALL_ROWS, key=lambda r: r["exit_time"])]
    assert per[WMT_314["exit_time"].date()]["scratch"] == 1


def test_escalation_fires_on_three_sessions_of_fail_and_scratch():
    """2026-08-28 / 08-31 / 09-01 ran 100% FAIL+SCRATCH — the clause's trigger."""
    rows = [TSM_307, COST_312, WMT_314]
    v = doctrine.escalation_verdict(rows)
    assert v["escalated"] is True
    assert v["fail_scratch_share"] == 100.0
    assert v["sessions"] == ["2026-08-28", "2026-08-31", "2026-09-01"]


def test_escalation_does_not_fire_when_wins_carry_the_window():
    v = doctrine.escalation_verdict([AAPL_267, INTC_298, WMT_314])
    assert v["escalated"] is False
    assert v["fail_scratch_share"] == pytest.approx(33.3, abs=0.1)


def test_escalation_needs_three_sessions_of_evidence():
    """A short window is not evidence — never escalate on one bad session."""
    v = doctrine.escalation_verdict([TSM_307, COST_312])
    assert v["escalated"] is False
    assert v["fail_scratch_share"] == 100.0     # bad, but only two sessions


def test_escalation_window_counts_sessions_not_calendar_days():
    """A flat day has no rows, so it can neither trigger nor reset the window."""
    v = doctrine.escalation_verdict(ALL_ROWS, sessions=3)
    assert v["sessions"] == ["2026-08-28", "2026-08-31", "2026-09-01"]
    assert v["summary"]["trades"] == 3
