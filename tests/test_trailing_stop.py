"""IMP-013 tests — break-even + trailing stop management.

The 06-08..07-07 audit (123 closed trades): STOP exits -$3,266 (56 trades,
1 winner), TAKE_PROFIT +$1,577 (only 20 trades ever reached the 1.5R target),
EOD_FLATTEN +$206 with 23/47 green at the close but most open profit given
back intraday. Realized payoff ratio 1.08 vs the ~1.8 a 36% win rate needs.
Fix: once a trade is +0.5R move the stop to entry (break-even); once +1R trail
it 1R below the live price. The stop lives BROKER-SIDE (bracket leg replace),
so it survives the nightly restart; the DB stop_price stays the ORIGINAL plan
stop because it is the risk anchor that defines 1R.

These tests pin:
  1. compute_trailed_stop — trigger levels, monotonic ratchet, guards.
  2. resolve_stop_leg — finds the stop leg and follows Alpaca's rotating
     replaced_by chain (the USTradeBot 422 "order already replaced" lesson).
  3. replace_stop_order — never raises; returns ok/order_id/error.
  4. engine.manage_stops — wiring: replaces at the right price, skips when
     nothing to do, respects dry_run, one symbol's failure can't stop the rest.
"""

from types import SimpleNamespace

from bot import config, data, engine, execution, exits, logbook


# --- 1. compute_trailed_stop --------------------------------------------------
# Defaults: BREAKEVEN_TRIGGER_R=0.5, TRAIL_TRIGGER_R=1.0, TRAIL_DISTANCE_R=1.0,
# STOP_RATCHET_MIN_PCT=0.10. Base case: entry 100, initial stop 98.5 (risk 1.5).

def test_no_move_below_breakeven_trigger():
    # +0.4R (100.60) — not yet at the +0.5R trigger.
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 100.60) is None


def test_breakeven_at_half_r():
    # +0.5R (100.75) — stop moves to entry.
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 100.75) == 100.0


def test_trail_at_one_r_tracks_price_minus_risk():
    # +2R (103.00) — stop trails 1R (1.5) below live: 101.50.
    assert exits.compute_trailed_stop(100.0, 98.5, 100.0, 103.00) == 101.5


def test_ratchet_never_lowers_stop():
    # Price fell back: trail candidate (100.0) is below the current stop.
    assert exits.compute_trailed_stop(100.0, 98.5, 101.5, 101.50) is None


def test_ratchet_ignores_tiny_improvements():
    # Candidate beats the current stop by 5 cents on a $100 stock — below the
    # 0.10% (=$0.10) minimum step, so no replace spam on every 60s tick.
    assert exits.compute_trailed_stop(100.0, 98.5, 101.45, 102.96) is None


def test_guards_zero_risk_and_missing_price():
    assert exits.compute_trailed_stop(100.0, 100.0, 100.0, 105.0) is None  # risk 0
    assert exits.compute_trailed_stop(100.0, 101.0, 101.0, 105.0) is None  # risk < 0
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, None) is None     # no live px


def test_disabled_via_config(monkeypatch):
    monkeypatch.setattr(config, "TRAILING_STOP_ENABLED", False)
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 103.0) is None


# --- 2. resolve_stop_leg --------------------------------------------------------

def _leg(id_, type_="stop", status="held", replaced_by=None, stop_price="98.5"):
    return SimpleNamespace(id=id_, type=type_, status=status,
                           replaced_by=replaced_by, stop_price=stop_price)


def _parent(legs):
    return SimpleNamespace(id="parent-1", legs=legs, filled_avg_price="100.0")


def test_resolves_active_stop_leg_directly():
    stop = _leg("leg-stop")
    parent = _parent([_leg("leg-tp", type_="limit"), stop])
    assert exits.resolve_stop_leg(parent, fetch=lambda oid: None) is stop


def test_follows_replaced_by_chain():
    # Alpaca rotates the order id on every replace; the ORIGINAL leg goes
    # status=replaced and points at the successor. Two hops here.
    current = _leg("leg-3", status="new")
    chain = {
        "leg-2": _leg("leg-2", status="replaced", replaced_by="leg-3"),
        "leg-3": current,
    }
    original = _leg("leg-1", status="replaced", replaced_by="leg-2")
    parent = _parent([_leg("leg-tp", type_="limit"), original])
    assert exits.resolve_stop_leg(parent, fetch=lambda oid: chain[oid]) is current


def test_returns_none_when_stop_leg_terminal_or_missing():
    filled = _parent([_leg("leg-stop", status="filled")])
    assert exits.resolve_stop_leg(filled, fetch=lambda oid: None) is None
    canceled = _parent([_leg("leg-stop", status="canceled")])
    assert exits.resolve_stop_leg(canceled, fetch=lambda oid: None) is None
    no_legs = SimpleNamespace(id="p", legs=None)
    assert exits.resolve_stop_leg(no_legs, fetch=lambda oid: None) is None


def test_replace_chain_hop_limit():
    # A pathological self-referencing chain must terminate, not loop forever.
    loop = _leg("leg-x", status="replaced", replaced_by="leg-x")
    parent = _parent([loop])
    assert exits.resolve_stop_leg(parent, fetch=lambda oid: loop) is None


# --- 3. execution.replace_stop_order -------------------------------------------

def test_replace_stop_order_success(monkeypatch):
    seen = {}

    class _Client:
        def replace_order_by_id(self, order_id, order_data=None):
            seen["order_id"] = order_id
            seen["stop_price"] = order_data.stop_price
            return SimpleNamespace(id="new-leg-9")

    monkeypatch.setattr(execution.broker, "trading_client", lambda: _Client())
    res = execution.replace_stop_order("leg-1", 101.5)
    assert res["ok"] is True
    assert res["order_id"] == "new-leg-9"
    assert seen == {"order_id": "leg-1", "stop_price": 101.5}


def test_replace_stop_order_never_raises(monkeypatch):
    class _Client:
        def replace_order_by_id(self, order_id, order_data=None):
            raise RuntimeError("order already replaced")

    monkeypatch.setattr(execution.broker, "trading_client", lambda: _Client())
    res = execution.replace_stop_order("leg-1", 101.5)
    assert res["ok"] is False
    assert "order already replaced" in res["error"]


# --- 4. engine.manage_stops -----------------------------------------------------

def _open_trade(symbol="NVDA", stop=98.5, oid="parent-1"):
    return {"trade_id": 1, "symbol": symbol, "qty": 10, "entry_price": 100.0,
            "stop_price": stop, "take_profit_price": 102.25,
            "alpaca_order_id": oid}


def _wire(monkeypatch, trades, parents, live, replace_results=None):
    replaced: list[tuple[str, float]] = []
    monkeypatch.setattr(logbook, "get_open_trades", lambda: list(trades))
    monkeypatch.setattr(execution, "get_order", lambda oid: parents[oid])
    monkeypatch.setattr(data, "latest_trade_price", lambda sym: live.get(sym))

    def _replace(order_id, new_stop):
        replaced.append((order_id, new_stop))
        return (replace_results or {}).get(order_id, {"ok": True, "order_id": "n1",
                                                      "error": None})
    monkeypatch.setattr(execution, "replace_stop_order", _replace)
    return replaced


def test_manage_stops_replaces_at_one_r(monkeypatch):
    parent = _parent([_leg("leg-tp", type_="limit"), _leg("leg-stop")])
    replaced = _wire(monkeypatch, [_open_trade()], {"parent-1": parent},
                     {"NVDA": 103.0})
    actions = engine.Engine(dry_run=False).manage_stops()
    assert replaced == [("leg-stop", 101.5)]
    assert actions and actions[0]["action"] == "stop_raised"


def test_manage_stops_skips_unfilled_entry_and_flat_price(monkeypatch):
    unfilled = SimpleNamespace(id="parent-1", filled_avg_price=None,
                               legs=[_leg("leg-stop")])
    replaced = _wire(monkeypatch, [_open_trade()], {"parent-1": unfilled},
                     {"NVDA": 103.0})
    assert engine.Engine(dry_run=False).manage_stops() == []
    assert replaced == []

    # Entry filled but price still below the +0.5R trigger: no replace.
    parent = _parent([_leg("leg-stop")])
    replaced = _wire(monkeypatch, [_open_trade()], {"parent-1": parent},
                     {"NVDA": 100.2})
    assert engine.Engine(dry_run=False).manage_stops() == []
    assert replaced == []


def test_manage_stops_dry_run_does_not_replace(monkeypatch):
    parent = _parent([_leg("leg-stop")])
    replaced = _wire(monkeypatch, [_open_trade()], {"parent-1": parent},
                     {"NVDA": 103.0})
    engine.Engine(dry_run=True).manage_stops()
    assert replaced == []


def test_manage_stops_one_failure_does_not_stop_the_rest(monkeypatch):
    bad = SimpleNamespace(id="parent-1")  # get_order below raises for this one
    good = _parent([_leg("leg-stop")])
    trades = [_open_trade("AMD", oid="parent-bad"),
              _open_trade("NVDA", oid="parent-1")]

    def _get_order(oid):
        if oid == "parent-bad":
            raise RuntimeError("api down")
        return good
    monkeypatch.setattr(logbook, "get_open_trades", lambda: trades)
    monkeypatch.setattr(execution, "get_order", _get_order)
    monkeypatch.setattr(data, "latest_trade_price", lambda sym: 103.0)
    replaced = []
    monkeypatch.setattr(execution, "replace_stop_order",
                        lambda oid, px: (replaced.append((oid, px)),
                                         {"ok": True, "order_id": "n", "error": None})[1])
    engine.Engine(dry_run=False).manage_stops()
    assert replaced == [("leg-stop", 101.5)]


def test_tick_calls_manage_stops_before_entries(monkeypatch):
    calls: list[str] = []
    eng = engine.Engine(dry_run=True)
    monkeypatch.setattr(eng, "manage_exits", lambda: calls.append("exits"))
    monkeypatch.setattr(eng, "manage_stops", lambda now=None: calls.append("stops"))
    monkeypatch.setattr(eng, "consider_entries", lambda now=None: calls.append("entries"))
    import datetime as _dt
    noon = _dt.datetime(2026, 7, 8, 12, 0, tzinfo=config.MARKET_TZ)
    eng.tick(noon)
    assert calls == ["exits", "stops", "entries"]
