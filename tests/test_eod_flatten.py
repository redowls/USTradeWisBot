"""IMP-002 regression tests — verified, retried end-of-day flatten.

2026-06-16 C/AMZN/BAC were opened and then held for TWO overnights (06-16 ->
06-18) because the bulk close_all_positions(cancel_orders=True) raced the async
order-cancel (held_for_orders) and silently left positions open, while the
engine unconditionally marked the day flattened. These tests pin:
  1. flatten_all cancels working orders BEFORE closing each position.
  2. eod_flatten leaves a trade OPEN (and alerts + returns False) when its
     broker position did not liquidate — so the next tick retries.
  3. eod_flatten marks a trade CLOSED only once its broker position is gone,
     using the recorded exit price (C +$20.25 / 143.765 on 06-18).
  4. tick() does not set flattened_on until eod_flatten confirms the book flat.
"""

from bot import broker, engine, exits, logbook, notify


# --- 1. cancel-before-close ordering (the held_for_orders fix) ---------------

def test_flatten_all_cancels_orders_before_closing_positions(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(exits, "_position_snapshot",
                        lambda reason: [{"symbol": "C", "market_value": 2587.77},
                                        {"symbol": "BAC", "market_value": 2585.20}])
    monkeypatch.setattr(broker, "cancel_all_orders", lambda: calls.append("cancel"))
    monkeypatch.setattr(broker, "close_position", lambda s: calls.append(f"close_{s}"))
    snap = exits.flatten_all("EOD_FLATTEN")
    assert calls[0] == "cancel", "orders must be canceled before any position close"
    assert set(calls[1:]) == {"close_C", "close_BAC"}
    assert {s["symbol"] for s in snap} == {"C", "BAC"}


def test_flatten_all_closes_every_position_even_if_one_raises(monkeypatch):
    closed: list[str] = []
    monkeypatch.setattr(exits, "_position_snapshot",
                        lambda reason: [{"symbol": "C", "market_value": 1.0},
                                        {"symbol": "BAC", "market_value": 1.0}])
    monkeypatch.setattr(broker, "cancel_all_orders", lambda: None)

    def _close(sym):
        if sym == "C":
            raise RuntimeError("held_for_orders")  # must not stop BAC
        closed.append(sym)
    monkeypatch.setattr(broker, "close_position", _close)
    exits.flatten_all("EOD_FLATTEN")
    assert closed == ["BAC"]


# --- 2/3. eod_flatten verification --------------------------------------------

def _eng_with_open_trades(monkeypatch, open_trades, flatten_snapshot, remaining):
    closed: dict[int, float] = {}
    alerts: list[str] = []
    monkeypatch.setattr(logbook, "get_open_trades", lambda: list(open_trades))
    monkeypatch.setattr(exits, "flatten_all", lambda reason: list(flatten_snapshot))
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set(remaining))
    monkeypatch.setattr(logbook, "update_trade_exit",
                        lambda tid, price, *a, **k: closed.__setitem__(tid, price))
    monkeypatch.setattr(notify, "exit_alert", lambda rec: None)
    monkeypatch.setattr(notify, "error_alert", lambda msg: alerts.append(msg))
    return engine.Engine(dry_run=False), closed, alerts


def test_eod_flatten_leaves_unconfirmed_position_open(monkeypatch):
    """06-16 replay: BAC did not liquidate -> stays OPEN, alert fires, retry."""
    open_trades = [
        {"trade_id": 70, "symbol": "C", "qty": 18, "entry_price": 142.64},
        {"trade_id": 72, "symbol": "BAC", "qty": 46, "entry_price": 56.53},
    ]
    snapshot = [{"symbol": "C", "market_value": 2587.77},
                {"symbol": "BAC", "market_value": 2585.20}]
    eng, closed, alerts = _eng_with_open_trades(
        monkeypatch, open_trades, snapshot, remaining={"BAC"})
    result = eng.eod_flatten()
    assert result is False                       # broker not flat -> caller retries
    assert 70 in closed and 72 not in closed     # C closed, BAC left OPEN
    assert alerts and "BAC" in alerts[0]


def test_eod_flatten_marks_closed_when_broker_flat(monkeypatch):
    """06-18 replay: C flattened at 143.765 (recorded +$20.25)."""
    open_trades = [{"trade_id": 70, "symbol": "C", "qty": 18, "entry_price": 142.64}]
    snapshot = [{"symbol": "C", "market_value": 2587.77}]
    eng, closed, alerts = _eng_with_open_trades(
        monkeypatch, open_trades, snapshot, remaining=set())
    assert eng.eod_flatten() is True
    assert closed[70] == round(2587.77 / 18, 4) == 143.765
    assert not alerts


def test_eod_flatten_dry_run_is_noop(monkeypatch):
    monkeypatch.setattr(logbook, "get_open_trades", lambda: [{"trade_id": 1}])
    assert engine.Engine(dry_run=True).eod_flatten() is True


# --- 4. tick gating: retry until flat ----------------------------------------

def test_tick_retries_flatten_until_broker_flat(monkeypatch):
    now = exits.now_et().replace(hour=15, minute=56, second=0, microsecond=0)
    eng = engine.Engine(dry_run=False)
    monkeypatch.setattr(eng, "manage_exits", lambda: [])

    monkeypatch.setattr(eng, "eod_flatten", lambda: False)   # incomplete
    eng.tick(now)
    assert eng.flattened_on is None                          # not marked -> retry

    monkeypatch.setattr(eng, "eod_flatten", lambda: True)    # next tick succeeds
    eng.tick(now)
    assert eng.flattened_on == now.date()
