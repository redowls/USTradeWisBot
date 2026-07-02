"""Unit tests for bot/exits.py — time gates, exit classification, P&L math."""

from datetime import datetime
from types import SimpleNamespace

from bot import config, exits, logbook


def _et(hour: int, minute: int) -> datetime:
    return datetime(2026, 6, 11, hour, minute, tzinfo=config.MARKET_TZ)


# --- Time rules (the no-overnight invariants) --------------------------------

def test_entries_allowed_before_cutoff():
    assert exits.entries_allowed(_et(15, 29))
    assert not exits.past_entry_cutoff(_et(9, 30))


def test_entry_cutoff_at_and_after_1530():
    assert exits.past_entry_cutoff(_et(15, 30))
    assert exits.past_entry_cutoff(_et(15, 45))
    assert not exits.entries_allowed(_et(15, 30))


def test_flatten_at_and_after_1555():
    assert not exits.past_flatten_time(_et(15, 54))
    assert exits.past_flatten_time(_et(15, 55))
    assert exits.past_flatten_time(_et(16, 0))


# --- P&L math (recorded scenario: WMT trade 54, 2026-06-11) ------------------

def test_compute_pl_matches_recorded_wmt_trade():
    pl, pl_pct = exits.compute_pl(120.56, 120.44, 23)
    assert pl == -2.76
    assert round(pl_pct, 2) == -0.10


def test_compute_pl_winner_and_zero_entry():
    pl, pl_pct = exits.compute_pl(100.0, 102.0, 10)
    assert (pl, pl_pct) == (20.0, 2.0)
    assert exits.compute_pl(0.0, 1.0, 1) == (1.0, 0.0)


# --- Exit-reason classification -----------------------------------------------

def test_reason_from_leg_type():
    assert exits.reason_from_leg_type("limit") == "TAKE_PROFIT"
    assert exits.reason_from_leg_type("OrderType.STOP") == "STOP"
    assert exits.reason_from_leg_type("stop_limit") == "STOP"
    assert exits.reason_from_leg_type("market") == "UNKNOWN"


# --- build_exit_record on fake Alpaca orders ----------------------------------

def _order(entry_filled, leg_status="filled", leg_price="98.00"):
    leg = SimpleNamespace(
        status=leg_status, filled_avg_price=leg_price, id="leg-1",
        filled_at="2026-06-11T15:00:00Z", type="stop",
    )
    return SimpleNamespace(
        symbol="TEST", id="parent-1", filled_qty="10",
        filled_avg_price=entry_filled, legs=[leg],
    )


def test_build_exit_record_none_when_entry_unfilled():
    assert exits.build_exit_record(_order(entry_filled=None)) is None


def test_build_exit_record_none_when_no_leg_filled():
    assert exits.build_exit_record(_order("100.00", leg_status="new")) is None


def test_build_exit_record_stop_leg():
    record = exits.build_exit_record(_order("100.00"))
    assert record["exit_reason"] == "STOP"
    assert record["realized_pl"] == -20.0
    assert record["qty"] == 10


# --- IMP-010: STOP/TP path corrects entry_price to the real bracket fill -------

def test_record_exit_corrects_entry_price_to_real_fill(monkeypatch):
    """IMP-010 — GOOGL 2026-07-02 replay. The OPEN row stored the plan/signal
    entry (361.19) but the bracket buy filled at 360.84; build_exit_record prices
    P&L off the real fill (STOP @355.76 -> -35.58). record_exit must forward that
    real entry into update_trade_exit so trades.entry_price reconciles with
    realized_pl (pre-IMP-010 it left the stale 361.19 → row inconsistent, and the
    by-entry-extension analytic mis-measured every slipped STOP/TP breakout)."""
    monkeypatch.setattr(logbook.db, "query_one", lambda *a, **k: {"trade_id": 111})
    captured: dict = {}
    monkeypatch.setattr(
        logbook, "update_trade_exit",
        lambda tid, **kw: captured.update({"trade_id": tid, **kw}),
    )
    exit_record = {
        "symbol": "GOOGL", "entry_order_id": "ord-googl", "qty": 7,
        "entry_price": 360.8429,          # real bracket fill (not the 361.19 plan)
        "exit_price": 355.76, "exit_reason": "STOP",
        "realized_pl": -35.58, "realized_pl_pct": -1.4086, "exit_time": None,
    }
    assert logbook.record_exit(exit_record) == 111
    assert captured["entry_price"] == 360.8429     # forwarded → column corrected
    assert captured["entry_price"] != 361.19       # never the stale plan price
    assert captured["exit_price"] == 355.76
    assert captured["realized_pl"] == -35.58
