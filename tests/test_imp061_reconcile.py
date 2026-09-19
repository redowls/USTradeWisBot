"""IMP-061 — the DB <-> broker daily reconciliation alarm.

The regression these tests exist for is a real, dated, dollar-denominated event:
on **2026-09-18** an unguarded pytest run placed fourteen real 1-share META
bracket orders on the live paper account, the account fell **$7,482.42 ->
$7,192.26 (-$290.16, -3.88%)**, and `daily_summary` recorded **0 buys / 0 sells /
$0.00** beside it without raising anything. IMP-060 shipped the conftest guard
that makes that particular vector impossible; IMP-061 closes the detection gap
behind it, and `test_the_2026_09_18_incident_alarms` pins the incident itself.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from bot import config, engine, reconcile

# The 2026-09-18 incident, verbatim from daily_summary + the broker record.
INCIDENT = {
    "trade_date": date(2026, 9, 18),
    "num_buys": 0,
    "num_sells": 0,
    "gross_pl": Decimal("0.0000"),
    "equity_open": Decimal("7482.4200"),
    "equity_close": Decimal("7192.2600"),
}


def _summary(**over):
    row = {
        "trade_date": date(2026, 9, 17),
        "num_buys": 2,
        "num_sells": 2,
        "gross_pl": Decimal("2.7700"),
        "equity_open": Decimal("7479.6500"),
        "equity_close": Decimal("7482.4200"),
    }
    row.update(over)
    return row


# --- the incident itself -----------------------------------------------------

def test_the_2026_09_18_incident_alarms():
    """The $290.16 silent loss must be caught. This is the whole point of IMP-061."""
    result = reconcile.check(INCIDENT)

    assert result["ok"] is True
    assert result["diverged"] is True
    # Broker says -290.16, ledger says 0.00 -> the entire drop is unexplained.
    assert result["divergence"] == pytest.approx(-290.16, abs=0.01)
    # At $7,482.42 equity the bar is max($25.00, $18.71) = $25.00.
    assert result["tolerance"] == pytest.approx(25.0, abs=0.01)
    assert abs(result["divergence"]) > result["tolerance"] * 10  # 11.6x over


def test_incident_description_names_both_sides():
    text = reconcile.describe(reconcile.check(INCIDENT))
    assert "DIVERGED" in text
    assert "-290.16" in text
    assert "+0.00" in text  # the ledger's claim, stated beside the broker's


# --- the clean case must stay silent ----------------------------------------

def test_a_normal_session_does_not_alarm():
    """2026-09-17: two exits, +$2.77 recorded, equity +$2.77. Reconciles exactly."""
    result = reconcile.check(_summary())
    assert result["ok"] is True
    assert result["diverged"] is False
    assert result["divergence"] == pytest.approx(0.0, abs=0.01)


def test_small_drift_is_tolerated():
    """Fees and a cent of settle drift must not cry wolf."""
    row = _summary(equity_close=Decimal("7494.4200"))  # $12 unexplained, under $25
    result = reconcile.check(row)
    assert result["diverged"] is False
    assert result["divergence"] == pytest.approx(12.0, abs=0.01)


def test_a_genuinely_flat_zero_trade_session_does_not_alarm():
    """Zero trades and zero equity move is the *correct* zero-trade shape."""
    row = _summary(num_buys=0, num_sells=0, gross_pl=Decimal("0.0000"),
                   equity_open=Decimal("7527.5000"), equity_close=Decimal("7527.5000"))
    assert reconcile.check(row)["diverged"] is False


# --- sign and symmetry -------------------------------------------------------

def test_unexplained_gains_alarm_too():
    """An unrecorded winner is still an unrecorded fill — magnitude, not sign."""
    row = _summary(equity_close=Decimal("7679.6500"))  # +$200 unexplained
    result = reconcile.check(row)
    assert result["diverged"] is True
    assert result["divergence"] > 0


def test_divergence_is_broker_minus_ledger():
    assert reconcile.divergence(100.0, 90.0, -10.0) == pytest.approx(0.0)
    assert reconcile.divergence(100.0, 90.0, 0.0) == pytest.approx(-10.0)
    assert reconcile.divergence(100.0, 110.0, 0.0) == pytest.approx(10.0)


def test_a_recorded_loss_that_matches_does_not_alarm():
    """The bot losing money it correctly recorded is not a reconciliation defect."""
    row = _summary(gross_pl=Decimal("-47.8500"), equity_open=Decimal("7527.5000"),
                   equity_close=Decimal("7479.6500"))  # 2026-09-16, real session
    assert reconcile.check(row)["diverged"] is False


# --- tolerance scaling -------------------------------------------------------

def test_tolerance_is_the_greater_of_floor_and_percentage():
    assert reconcile.tolerance(7192.26) == pytest.approx(config.RECONCILE_TOLERANCE_USD)
    # A big account scales past the flat floor.
    big = reconcile.tolerance(100_000.0)
    assert big == pytest.approx(100_000.0 * config.RECONCILE_TOLERANCE_PCT / 100.0)
    assert big > config.RECONCILE_TOLERANCE_USD


def test_tolerance_degrades_to_the_floor_not_to_zero():
    """A nonsensical equity_open must not make the check alarm on everything."""
    for bad in (0.0, -5.0, None, "x"):
        assert reconcile.tolerance(bad) == pytest.approx(config.RECONCILE_TOLERANCE_USD)


# --- "don't report fine when you don't know" ---------------------------------

def test_missing_equity_endpoints_report_not_ok_rather_than_clean():
    for row in (_summary(equity_open=None), _summary(equity_close=None)):
        result = reconcile.check(row)
        assert result["ok"] is False
        assert result["diverged"] is False
        assert "missing" in result["reason"]


def test_no_summary_row_reports_not_ok():
    for empty in (None, {}):
        result = reconcile.check(empty)
        assert result["ok"] is False
        assert result["diverged"] is False
    assert reconcile.describe(reconcile.check(None)).startswith("reconciliation skipped")


def test_null_gross_pl_is_treated_as_zero_not_as_a_skip():
    """A NULL gross_pl still has an equity move to judge — that is the 09-18 shape."""
    row = _summary(gross_pl=None, equity_close=Decimal("7192.2600"))
    result = reconcile.check(row)
    assert result["ok"] is True
    assert result["diverged"] is True


# --- engine wiring -----------------------------------------------------------

class _Recorder:
    def __init__(self):
        self.alerts = []

    def __call__(self, result):
        self.alerts.append(result)
        return True


def _engine():
    eng = engine.Engine.__new__(engine.Engine)
    eng.logged = []
    eng._log = eng.logged.append
    return eng


def test_engine_alarms_on_the_incident(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(engine.notify, "reconciliation_alert", rec)
    eng = _engine()

    eng._reconcile_day(INCIDENT)

    assert len(rec.alerts) == 1
    assert rec.alerts[0]["divergence"] == pytest.approx(-290.16, abs=0.01)
    assert any("DIVERGED" in line for line in eng.logged)


def test_engine_stays_silent_on_a_clean_day(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(engine.notify, "reconciliation_alert", rec)
    eng = _engine()

    eng._reconcile_day(_summary())

    assert rec.alerts == []
    assert any("reconciliation ok" in line for line in eng.logged)


def test_engine_reconciliation_never_breaks_the_close(monkeypatch):
    """A detector that can kill the post-close path is worse than no detector."""
    def boom(_summary):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(engine.reconcile, "check", boom)
    eng = _engine()

    eng._reconcile_day(_summary())  # must not raise

    assert any("reconciliation check error" in line for line in eng.logged)


def test_alert_text_carries_the_numbers():
    sent = {}
    result = reconcile.check(INCIDENT)

    import bot.notify as notify_mod
    original = notify_mod.send
    notify_mod.send = lambda text, **kw: sent.setdefault("text", text) or True
    try:
        notify_mod.reconciliation_alert(result)
    finally:
        notify_mod.send = original

    text = sent["text"]
    assert "RECONCILIATION MISMATCH" in text
    assert "-290.16" in text
    assert "7,482.42" in text and "7,192.26" in text


# --- the invariant this change must not touch --------------------------------

def test_reconciliation_touches_no_risk_limit():
    """IMP-061 is detection only; the capital-protection invariants are unchanged."""
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
