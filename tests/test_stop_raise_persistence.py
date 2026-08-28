"""IMP-043 tests — the ratchet becomes durable ground truth.

``trades.stop_price`` is pinned to the ORIGINAL 1R plan stop by design (IMP-013:
it is the anchor that defines R), so nothing in the schema recorded where the
stop actually WAS when it fired. A break-even scratch and a full -1R loss both
landed in ``exit_reason = 'STOP'``. The only record of the arming events was the
``STOP RAISED`` lines in /var/log/ustradewisbot/bot.log, which logrotate keeps
for 14 days — shorter than the window IMP-040's verdict is judged over.

Fixtures are the REAL 2026-08-27 session:

  #298 INTC  entry 89.6029  plan stop 88.14  -> ratchet ran to 92.02 (10 raises)
             then TAKE_PROFIT at 92.50 (+$60.84)
  #297 TSM   entry 422.444  plan stop 415.20 -> ratchet ran to 425.28 (4 raises)
             then the stop leg FILLED at 425.33 (+$14.43) -- a RATCHET_STOP that
             the schema alone would have shown exiting $10.13 ABOVE its stop
  #296 SPY   entry 767.88   plan stop 756.10 -> ratchet ran to 768.70 (2 raises)
             then EOD_FLATTEN at 771.0267 (+$9.44)

92.02 / 425.28 / 768.70 are the stop prices Alpaca itself reports on those three
bracket stop legs, so these tests are pinned to broker ground truth, not to the
log they are recovered from.
"""

from datetime import datetime

import pytest

from bot import config, data, engine, execution, exits, logbook
from scripts import backfill_stop_raises as bsr


# --- the real log lines (verbatim, including the copytruncate duplicate) -----

INTC_LINES = [
    "2026-08-27 10:04:41 EDT | STOP RAISED INTC 88.14 -> 89.60 (live 89.82, peak 90.04, entry 89.60)",
    "2026-08-27 10:11:12 EDT | STOP RAISED INTC 89.60 -> 89.76 (live 90.13, peak 90.3, entry 89.60)",
    "2026-08-27 10:12:16 EDT | STOP RAISED INTC 89.76 -> 90.03 (live 90.40, peak 90.3, entry 89.60)",
    "2026-08-27 10:13:21 EDT | STOP RAISED INTC 90.03 -> 90.14 (live 90.51, peak 90.49, entry 89.60)",
    "2026-08-27 10:14:25 EDT | STOP RAISED INTC 90.14 -> 90.41 (live 90.78, peak 90.64, entry 89.60)",
    "2026-08-27 10:18:44 EDT | STOP RAISED INTC 90.41 -> 90.69 (live 91.06, peak 90.94, entry 89.60)",
    "2026-08-27 10:21:55 EDT | STOP RAISED INTC 90.69 -> 91.11 (live 91.48, peak 91.22, entry 89.60)",
    "2026-08-27 10:25:08 EDT | STOP RAISED INTC 91.11 -> 91.21 (live 91.58, peak 91.71, entry 89.60)",
    "2026-08-27 10:26:14 EDT | STOP RAISED INTC 91.21 -> 91.51 (live 91.88, peak 91.88, entry 89.60)",
    "2026-08-27 10:27:18 EDT | STOP RAISED INTC 91.51 -> 92.02 (live 92.39, peak 92.03, entry 89.60)",
]
TSM_LINES = [
    "2026-08-27 10:06:50 EDT | STOP RAISED TSM 415.20 -> 422.44 (live 423.27, peak 424.4, entry 422.44)",
    "2026-08-27 10:17:40 EDT | STOP RAISED TSM 422.44 -> 423.08 (live 424.89, peak 424.81, entry 422.44)",
    "2026-08-27 10:28:22 EDT | STOP RAISED TSM 423.08 -> 423.90 (live 425.71, peak 425.39, entry 422.44)",
    "2026-08-27 10:33:49 EDT | STOP RAISED TSM 423.90 -> 425.28 (live 427.09, peak 426.22, entry 422.44)",
]
SPY_LINES = [
    "2026-08-27 11:15:10 EDT | STOP RAISED SPY 756.10 -> 767.88 (live 770.82, peak 770.83, entry 767.88)",
    "2026-08-27 12:40:32 EDT | STOP RAISED SPY 767.88 -> 768.70 (live 771.65, peak 771.5, entry 767.88)",
]
NOISE_LINES = [
    "2026-08-27 09:36:47 EDT | ENTRY 3 SPY @ 767.61 (conf 63) order=f0249dad",
    "2026-08-27 10:30:29 EDT | EXIT INTC TAKE_PROFIT pl=$60.84 (3.2333%)",
    "2026-08-27 10:35:57 EDT | EXIT TSM STOP pl=$14.43 (0.6832%)",
    "2026-08-27 12:21:37 EDT | ENTRY SKIPPED TSM: entry 421.90 is +0.35% above session VWAP 420.43",
    "2026-08-27 14:02:11 EDT | STOP RAISE FAILED AAPL: order already replaced",
]


def _ts(hhmm: str) -> datetime:
    return datetime.strptime(f"2026-08-27 {hhmm}", "%Y-%m-%d %H:%M:%S")


TRADES_0827 = [
    {"trade_id": 296, "symbol": "SPY", "entry_time": _ts("09:36:46"),
     "exit_time": _ts("15:55:42"), "stop_price": 756.10,
     "final_stop_price": None, "stop_raises": 0, "exit_reason": "EOD_FLATTEN"},
    {"trade_id": 297, "symbol": "TSM", "entry_time": _ts("09:41:02"),
     "exit_time": _ts("10:35:21"), "stop_price": 415.20,
     "final_stop_price": None, "stop_raises": 0, "exit_reason": "STOP"},
    {"trade_id": 298, "symbol": "INTC", "entry_time": _ts("09:56:02"),
     "exit_time": _ts("10:30:01"), "stop_price": 88.14,
     "final_stop_price": None, "stop_raises": 0, "exit_reason": "TAKE_PROFIT"},
]


def _write_log(tmp_path, lines, name="bot.log"):
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n")
    return str(p)


# --- the parser -------------------------------------------------------------

def test_parses_every_real_stop_raised_line(tmp_path):
    path = _write_log(tmp_path, INTC_LINES + TSM_LINES + SPY_LINES + NOISE_LINES)
    events = bsr.parse_raises([path])
    assert len(events) == 16, "10 INTC + 4 TSM + 2 SPY"
    assert {e[1] for e in events} == {"INTC", "TSM", "SPY"}


def test_parser_ignores_entries_exits_skips_and_failed_raises(tmp_path):
    """A STOP RAISE FAILED line is not an arming event and must not be counted."""
    path = _write_log(tmp_path, NOISE_LINES)
    assert bsr.parse_raises([path]) == []


def test_parser_takes_the_new_stop_not_the_old_one(tmp_path):
    """`88.14 -> 89.60` records 89.60. Reading the left number would record the
    stop the ratchet just replaced, inverting the whole measurement."""
    path = _write_log(tmp_path, [INTC_LINES[0]])
    (_ts_, symbol, new_stop), = bsr.parse_raises([path])
    assert (symbol, new_stop) == ("INTC", 89.60)


def test_copytruncate_duplicates_are_deduped(tmp_path):
    """logrotate uses copytruncate, so an event can appear in the live file AND
    the rotated one. Counting it twice would inflate every stop_raises."""
    live = _write_log(tmp_path, TSM_LINES, "bot.log")
    rotated = _write_log(tmp_path, TSM_LINES, "bot.log.1")
    assert len(bsr.parse_raises([live, rotated])) == 4


# --- attribution ------------------------------------------------------------

def test_attributes_the_real_session_with_nothing_unmatched(tmp_path):
    path = _write_log(tmp_path, INTC_LINES + TSM_LINES + SPY_LINES + NOISE_LINES)
    matched, unmatched = bsr.attribute(bsr.parse_raises([path]), TRADES_0827)
    assert unmatched == []
    assert {tid: len(v) for tid, v in matched.items()} == {296: 2, 297: 4, 298: 10}


def test_final_stop_matches_the_broker_stop_legs(tmp_path):
    """92.02 / 425.28 / 768.70 are Alpaca's own stop_price on those bracket legs."""
    path = _write_log(tmp_path, INTC_LINES + TSM_LINES + SPY_LINES)
    matched, _ = bsr.attribute(bsr.parse_raises([path]), TRADES_0827)
    finals = {tid: max(v)[1] for tid, v in matched.items()}
    assert finals == {296: 768.70, 297: 425.28, 298: 92.02}


def test_a_raise_outside_the_hold_window_is_not_attributed(tmp_path):
    """INTC exited 10:30:01. A later INTC raise belongs to no trade and must be
    reported, not silently folded into the closed one."""
    late = ("2026-08-27 11:00:00 EDT | STOP RAISED INTC 92.02 -> 93.00 "
            "(live 93.25, peak 93.1, entry 89.60)")
    path = _write_log(tmp_path, INTC_LINES + [late])
    matched, unmatched = bsr.attribute(bsr.parse_raises([path]), TRADES_0827)
    assert len(matched[298]) == 10
    assert [(u[1], u[2]) for u in unmatched] == [("INTC", 93.00)]


def test_raises_are_attributed_to_the_right_one_of_two_same_day_trades(tmp_path):
    """TSM was traded on 08-26 and again on 08-27; the windows disambiguate."""
    prior = dict(TRADES_0827[1])
    prior.update(trade_id=293, entry_time=_ts("06:00:00"), exit_time=_ts("08:00:00"))
    path = _write_log(tmp_path, TSM_LINES)
    matched, unmatched = bsr.attribute(bsr.parse_raises([path]), [prior] + TRADES_0827)
    assert unmatched == []
    assert set(matched) == {297} and len(matched[297]) == 4


# --- the live writer --------------------------------------------------------

def test_record_stop_raise_recomputes_final_and_increments_count(monkeypatch):
    seen = {}

    def fake_execute(sql, params):
        seen["sql"], seen["params"] = " ".join(sql.split()), params
        return 1

    monkeypatch.setattr(logbook.db, "execute", fake_execute)
    assert logbook.record_stop_raise(298, 92.02) is True
    assert "stop_raises = stop_raises + 1" in seen["sql"]
    assert "final_stop_price = ?" in seen["sql"]
    assert seen["params"] == [92.02, 298]


def test_record_stop_raise_never_raises_and_reports_failure(monkeypatch):
    """A database hiccup must not surface as a ratchet failure: the stop is
    already working at the broker by the time this runs."""
    def boom(_sql, _params):
        raise RuntimeError("connection reset by peer")

    monkeypatch.setattr(logbook.db, "execute", boom)
    assert logbook.record_stop_raise(298, 92.02) is False


def test_record_stop_raise_reports_false_when_no_row_matches(monkeypatch):
    monkeypatch.setattr(logbook.db, "execute", lambda _s, _p: 0)
    assert logbook.record_stop_raise(999_999, 1.0) is False


# --- the engine wiring ------------------------------------------------------

class _Leg:
    def __init__(self, stop_price):
        self.id = "leg-1"
        self.stop_price = stop_price


class _Parent:
    filled_avg_price = 89.6029


def _drive_manage_stops(monkeypatch, *, replace_ok=True, record_ok=True):
    """Run one manage_stops tick over INTC #298 at its 10:27:18 raise."""
    recorded: list[tuple] = []
    trade = {"trade_id": 298, "symbol": "INTC", "stop_price": 88.14,
             "entry_time": _ts("09:56:02"), "alpaca_order_id": "bc055ad0"}

    monkeypatch.setattr(config, "TRAILING_STOP_ENABLED", True)
    monkeypatch.setattr(logbook, "get_open_trades", lambda: [trade])
    monkeypatch.setattr(data, "get_bars_for_symbols", lambda *a, **k: {"INTC": []})
    monkeypatch.setattr(execution, "get_order", lambda _oid: _Parent())
    monkeypatch.setattr(exits, "resolve_stop_leg", lambda _p, _f: _Leg(91.51))
    monkeypatch.setattr(data, "latest_trade_price", lambda _s: 92.39)
    monkeypatch.setattr(exits, "peak_high_since", lambda _b, _t: 92.03)
    monkeypatch.setattr(exits, "compute_trailed_stop",
                        lambda *a, **k: 92.02)
    monkeypatch.setattr(
        execution, "replace_stop_order",
        lambda _id, _stop: {"ok": replace_ok, "order_id": "leg-2",
                            "error": None if replace_ok else "already replaced"},
    )

    def fake_record(trade_id, new_stop):
        recorded.append((trade_id, new_stop))
        return record_ok

    monkeypatch.setattr(logbook, "record_stop_raise", fake_record)

    eng = engine.Engine(dry_run=False)
    logged: list[str] = []
    monkeypatch.setattr(eng, "_log", logged.append)
    return eng.manage_stops(), recorded, logged


def test_a_successful_raise_is_persisted_with_the_new_stop(monkeypatch):
    actions, recorded, logged = _drive_manage_stops(monkeypatch)
    assert recorded == [(298, 92.02)]
    assert actions[0]["action"] == "stop_raised" and actions[0]["to"] == 92.02
    assert any("STOP RAISED INTC 91.51 -> 92.02" in ln for ln in logged)


def test_a_failed_replace_is_not_persisted(monkeypatch):
    """The broker rejected the replacement, so the stop did NOT move. Recording
    it would report a ratchet that never happened."""
    actions, recorded, logged = _drive_manage_stops(monkeypatch, replace_ok=False)
    assert recorded == []
    assert actions == []
    assert any("STOP RAISE FAILED" in ln for ln in logged)


def test_a_failed_write_does_not_break_the_ratchet(monkeypatch):
    """Losing the measurement must still leave the raise done and reported."""
    actions, recorded, logged = _drive_manage_stops(monkeypatch, record_ok=False)
    assert recorded == [(298, 92.02)]
    assert actions[0]["action"] == "stop_raised", "the stop still moved"
    assert any("STOP RAISE NOT RECORDED" in ln for ln in logged)
    assert any("STOP RAISED INTC" in ln for ln in logged)


def test_dry_run_never_writes(monkeypatch):
    """A dry-run tick must not manufacture arming events in the real table."""
    recorded: list[tuple] = []
    trade = {"trade_id": 298, "symbol": "INTC", "stop_price": 88.14,
             "entry_time": _ts("09:56:02"), "alpaca_order_id": "bc055ad0"}
    monkeypatch.setattr(config, "TRAILING_STOP_ENABLED", True)
    monkeypatch.setattr(logbook, "get_open_trades", lambda: [trade])
    monkeypatch.setattr(data, "get_bars_for_symbols", lambda *a, **k: {"INTC": []})
    monkeypatch.setattr(execution, "get_order", lambda _oid: _Parent())
    monkeypatch.setattr(exits, "resolve_stop_leg", lambda _p, _f: _Leg(91.51))
    monkeypatch.setattr(data, "latest_trade_price", lambda _s: 92.39)
    monkeypatch.setattr(exits, "peak_high_since", lambda _b, _t: 92.03)
    monkeypatch.setattr(exits, "compute_trailed_stop", lambda *a, **k: 92.02)
    monkeypatch.setattr(logbook, "record_stop_raise",
                        lambda tid, s: recorded.append((tid, s)) or True)
    eng = engine.Engine(dry_run=True)
    monkeypatch.setattr(eng, "_log", lambda _m: None)
    eng.manage_stops()
    assert recorded == []


# --- what the columns are FOR ----------------------------------------------

def test_the_columns_separate_a_ratchet_stop_from_a_plan_stop():
    """The whole point. TSM #297 exited at 425.33 on exit_reason='STOP' while
    trades.stop_price still reads 415.20 — a $10.13 gap that made a +$14.43
    RATCHET_STOP indistinguishable from a full -1R loss in the exit mix."""
    tsm = {"exit_reason": "STOP", "stop_price": 415.20,
           "final_stop_price": 425.28, "stop_raises": 4, "exit_price": 425.33}
    plan_stop_loser = {"exit_reason": "STOP", "stop_price": 415.20,
                       "final_stop_price": None, "stop_raises": 0,
                       "exit_price": 415.19}

    def classify(t):
        if t["exit_reason"] != "STOP":
            return t["exit_reason"]
        return "RATCHET_STOP" if t["stop_raises"] > 0 else "PLAN_STOP"

    assert classify(tsm) == "RATCHET_STOP"
    assert classify(plan_stop_loser) == "PLAN_STOP"
    assert tsm["exit_price"] > tsm["stop_price"], (
        "without final_stop_price this trade looks like it exited above its stop"
    )


def test_the_ratchet_never_lowers_the_recorded_stop():
    """final_stop_price is only ever written from compute_trailed_stop, which is
    monotone up. Each recovered chain must be strictly increasing."""
    for lines in (INTC_LINES, TSM_LINES, SPY_LINES):
        stops = [float(ln.split("-> ")[1].split(" ")[0]) for ln in lines]
        assert stops == sorted(stops) and len(set(stops)) == len(stops)


# --- capital-protection invariants (untouched by IMP-043) -------------------

def test_imp043_touches_no_risk_limit_and_no_imp040_geometry():
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.MIN_STOP_PCT == 1.5
    assert config.ATR_STOP_MULT == 3.0
    assert config.RR_RATIO == 1.5
    # IMP-040's open experiment — an analysis change must not disturb it.
    assert config.BREAKEVEN_TRIGGER_R == 0.25
    assert config.TRAIL_TRIGGER_R == 0.25
    assert config.TRAIL_DISTANCE_R == 0.25
    from bot import secrets
    assert secrets.ALPACA_PAPER is True, "the paper endpoint is never negotiable"


@pytest.mark.parametrize("attr,expected", [("ENTRY_CUTOFF_ET", "15:30"),
                                           ("FLATTEN_ET", "15:55")])
def test_imp043_leaves_the_no_overnight_rules_alone(attr, expected):
    assert getattr(config, attr) == expected


# --- the guard that stops this measurement corrupting itself -----------------

def test_the_suite_cannot_write_to_the_live_database():
    """IMP-043's own near-miss, pinned.

    Adding one record_stop_raise() call to manage_stops silently turned three
    pre-existing test files into writers, because they drive the ratchet with
    fixtures carrying REAL trade ids (1, 149, 244, 273, 274, 275). A suite run
    incremented stop_raises on live rows #149/#244/#274 and invented arming
    events for two trades whose logs had rotated away months earlier —
    corrupting the exact column this change exists to make trustworthy.
    """
    from bot import db

    # Resolved off the raised object rather than imported, so `tests` does not
    # have to become a package (adding tests/__init__.py changes pytest's import
    # mode for the whole suite).
    with pytest.raises(BaseException) as excinfo:  # noqa: B017 - that is the point
        db.execute("UPDATE trades SET stop_raises = 999", [])

    err = excinfo.value
    assert type(err).__name__ == "LiveDatabaseWriteBlocked"
    assert not isinstance(err, Exception), (
        "must not be an Exception: record_stop_raise and manage_stops both "
        "catch Exception on purpose and would swallow the guard"
    )


def test_record_stop_raise_would_swallow_an_ordinary_guard(monkeypatch):
    """Why the guard is a BaseException — shown, not asserted in a comment."""
    def ordinary(_sql, _params):
        raise AssertionError("a normal test guard")

    monkeypatch.setattr(logbook.db, "execute", ordinary)
    assert logbook.record_stop_raise(298, 92.02) is False, (
        "an Exception-derived guard is absorbed and the test passes silently"
    )
