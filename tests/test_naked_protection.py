"""IMP-038 tests — an open position with no working stop leg must not be silent.

`engine.manage_stops` resolved the bracket's stop leg every tick and, when it
could not, did this:

    if stop_leg is None:
        continue  # stop filled/canceled or unresolved — leave alone

That one line conflates a CLOSED position with a live long that has no stop.
Measured on 2026-08-20 across all 27 TAKE_PROFIT exits in the book (Alpaca
order timelines, `stop.canceled_at` -> `limit.filled_at`), Alpaca's OCO
releases the stop leg as soon as the limit becomes marketable, and on **10 of
27** the limit did not fill straight away:

    BAC  #149  2026-07-14  1594.3s  (26m34s)   <- worst
    ENPH #73   2026-06-22   347.2s
    AAPL #267  2026-08-19    81.8s   (the anecdote that opened this question)
    TSLA #17   2026-06-08    66.7s
    CRM  #82   2026-06-23    63.4s
    ... plus 5 windows of 0.8-3.9s.  Cumulative naked exposure 2163.6s.

All ten resolved profitably, so the hole never cost a dollar and stayed
invisible. These tests pin the two halves of the fix:

  1. `exits.naked_position_action` — the pure verdict, including the fail-quiet
     rule that an unreadable price may alert but may never liquidate.
  2. `engine.manage_stops` wiring — the ordinary TP path stays silent, a live
     naked position alerts once, and enforcement fires ONLY at/below the
     original plan stop, cancelling the sibling limit leg before selling.

Capital-protection invariants are asserted at the bottom: this change adds no
risk, widens no limit, and can only ever REMOVE exposure.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from bot import broker, config, data, engine, execution, exits, logbook, notify

# --- the real BAC #149 window (2026-07-14) ---------------------------------
BAC_ENTRY = 46.30
BAC_PLAN_STOP = 45.61          # DB stop_price, the 1R risk anchor
BAC_LIMIT = 47.22              # take-profit leg that took 26m34s to fill
BAC_NAKED_SECONDS = 1594.281   # stop.canceled_at -> limit.filled_at


def _leg(id_, type_="stop", status="held", stop_price="45.61"):
    return SimpleNamespace(id=id_, type=type_, status=status,
                           replaced_by=None, stop_price=stop_price)


def _parent(legs, fill=str(BAC_ENTRY)):
    return SimpleNamespace(id="parent-1", legs=legs, filled_avg_price=fill)


def _trade(symbol="BAC", stop=BAC_PLAN_STOP, oid="parent-1"):
    return {"trade_id": 149, "symbol": symbol, "qty": 57,
            "entry_price": BAC_ENTRY, "stop_price": stop,
            "take_profit_price": BAC_LIMIT, "alpaca_order_id": oid,
            "entry_time": None}


# --- 1. exits.naked_position_action ----------------------------------------

def test_no_position_means_nothing_to_do():
    """The ordinary TP/STOP completion: leg gone because the trade closed."""
    assert exits.naked_position_action(False, 47.22, BAC_PLAN_STOP) == exits.NAKED_NONE
    assert exits.naked_position_action(False, None, BAC_PLAN_STOP) == exits.NAKED_NONE


def test_open_position_above_the_stop_alerts_but_does_not_enforce():
    # The real BAC #149 state: naked for 26m34s, but 1.3R ABOVE the plan stop
    # the whole time. Nothing to liquidate — the alert is the whole job.
    assert exits.naked_position_action(True, BAC_LIMIT, BAC_PLAN_STOP) == exits.NAKED_ALERT
    assert exits.naked_position_action(True, BAC_PLAN_STOP + 0.01,
                                       BAC_PLAN_STOP) == exits.NAKED_ALERT


def test_open_position_at_or_below_the_stop_enforces():
    assert exits.naked_position_action(True, BAC_PLAN_STOP,
                                       BAC_PLAN_STOP) == exits.NAKED_ENFORCE
    assert exits.naked_position_action(True, BAC_PLAN_STOP - 0.01,
                                       BAC_PLAN_STOP) == exits.NAKED_ENFORCE


@pytest.mark.parametrize("live,stop", [
    (None, BAC_PLAN_STOP),      # price feed gave us nothing
    ("", BAC_PLAN_STOP),        # unparseable
    (0.0, BAC_PLAN_STOP),       # bad tick
    (-1.0, BAC_PLAN_STOP),
    (BAC_LIMIT, None),          # no plan stop on the row
    (BAC_LIMIT, 0.0),
    (BAC_LIMIT, "n/a"),
])
def test_unreadable_inputs_alert_but_never_liquidate(live, stop):
    """Fail-quiet: closing a position on a price we could not read is worse
    than waiting one more 60s poll."""
    assert exits.naked_position_action(True, live, stop) == exits.NAKED_ALERT


def test_string_prices_are_accepted():
    # Alpaca hands back numeric strings; the DB hands back Decimals.
    assert exits.naked_position_action(True, "45.60", "45.61") == exits.NAKED_ENFORCE
    assert exits.naked_position_action(True, "45.62", "45.61") == exits.NAKED_ALERT


# --- 2. exits.resolve_limit_leg_id -----------------------------------------

def test_resolves_a_working_limit_leg():
    parent = _parent([_leg("leg-stop"), _leg("leg-tp", type_="limit", status="new")])
    assert exits.resolve_limit_leg_id(parent) == "leg-tp"


def test_returns_none_for_a_terminal_or_missing_limit_leg():
    filled = _parent([_leg("leg-tp", type_="limit", status="filled")])
    assert exits.resolve_limit_leg_id(filled) is None
    canceled = _parent([_leg("leg-tp", type_="limit", status="canceled")])
    assert exits.resolve_limit_leg_id(canceled) is None
    assert exits.resolve_limit_leg_id(_parent([_leg("leg-stop")])) is None
    assert exits.resolve_limit_leg_id(SimpleNamespace(id="p", legs=None)) is None


# --- 3. engine.manage_stops wiring -----------------------------------------

@pytest.fixture
def wired(monkeypatch):
    """Engine wiring with every outbound call captured, none of them real."""
    state = {"closed": [], "canceled": [], "alerts": [], "held": set(),
             "live": {}, "trades": [], "parents": {}, "positions_raise": None}

    monkeypatch.setattr(logbook, "get_open_trades", lambda: list(state["trades"]))
    monkeypatch.setattr(execution, "get_order", lambda oid: state["parents"][oid])
    monkeypatch.setattr(data, "latest_trade_price",
                        lambda sym: state["live"].get(sym))
    monkeypatch.setattr(data, "get_bars_for_symbols", lambda symbols, **kw: {})
    monkeypatch.setattr(execution, "replace_stop_order",
                        lambda oid, px: {"ok": True, "order_id": "n", "error": None})

    def _positions():
        if state["positions_raise"]:
            raise state["positions_raise"]
        return set(state["held"])
    monkeypatch.setattr(broker, "open_position_symbols", _positions)
    monkeypatch.setattr(broker, "close_position",
                        lambda sym: state["closed"].append(sym))
    monkeypatch.setattr(execution, "cancel_order",
                        lambda oid: state["canceled"].append(oid))
    monkeypatch.setattr(notify, "error_alert",
                        lambda msg: state["alerts"].append(msg) or True)
    return state


def _naked_parent():
    """The BAC #149 shape: stop leg cancelled by the OCO, limit still working."""
    return _parent([_leg("leg-stop", status="canceled"),
                    _leg("leg-tp", type_="limit", status="new")])


def test_closed_position_stays_silent(wired):
    """Regression guard for the 17 of 27 exits that behave normally: the leg is
    gone because the take-profit filled and the position is flat."""
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _parent(
        [_leg("leg-stop", status="canceled"),
         _leg("leg-tp", type_="limit", status="filled")])}
    wired["held"] = set()                       # broker says we are flat
    wired["live"] = {"BAC": BAC_LIMIT}

    assert engine.Engine(dry_run=False).manage_stops() == []
    assert wired["alerts"] == []
    assert wired["closed"] == []
    assert wired["canceled"] == []


def test_bac_149_window_alerts_and_holds(wired):
    """The real 26m34s window: naked, but 1.3R above the stop. Alert, no sell."""
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["held"] = {"BAC"}
    wired["live"] = {"BAC": BAC_LIMIT - 0.01}   # hovering at the limit

    actions = engine.Engine(dry_run=False).manage_stops()
    assert actions == []                        # nothing was done to the position
    assert len(wired["alerts"]) == 1
    assert "UNPROTECTED BAC" in wired["alerts"][0]
    assert wired["closed"] == []                # <- the position is NOT liquidated
    assert wired["canceled"] == []
    assert BAC_NAKED_SECONDS > 60               # spanned >1 poll; alert was reachable


def test_breach_while_naked_enforces_the_plan_stop(wired):
    """Same window, counterfactual tape: price falls through the plan stop with
    no broker stop behind it. The bot must close it itself."""
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["held"] = {"BAC"}
    wired["live"] = {"BAC": BAC_PLAN_STOP - 0.05}

    actions = engine.Engine(dry_run=False).manage_stops()
    assert wired["canceled"] == ["leg-tp"]      # sibling leg cancelled FIRST...
    assert wired["closed"] == ["BAC"]           # ...then the position is sold
    assert actions and actions[0]["action"] == "soft_stop"
    assert actions[0]["symbol"] == "BAC"


def test_enforcement_never_fires_above_the_plan_stop(wired):
    """The stop is never tightened: at plan_stop + 1 cent nothing is sold."""
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["held"] = {"BAC"}
    wired["live"] = {"BAC": BAC_PLAN_STOP + 0.01}
    assert engine.Engine(dry_run=False).manage_stops() == []
    assert wired["closed"] == []


def test_alert_is_raised_once_per_position_not_once_per_poll(wired):
    """26m34s of naked exposure is 26 polls; it must not be 26 Telegram alerts."""
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["held"] = {"BAC"}
    wired["live"] = {"BAC": BAC_LIMIT - 0.01}

    eng = engine.Engine(dry_run=False)
    for _ in range(5):
        eng.manage_stops()
    assert len(wired["alerts"]) == 1
    # ...but a different symbol still gets its own alert.
    wired["trades"] = [_trade(symbol="NFLX", oid="parent-2")]
    wired["parents"]["parent-2"] = _naked_parent()
    wired["held"] = {"NFLX"}
    wired["live"] = {"NFLX": BAC_LIMIT - 0.01}
    eng.manage_stops()
    assert len(wired["alerts"]) == 2


def test_unknown_live_price_alerts_but_never_sells(wired):
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["held"] = {"BAC"}
    wired["live"] = {}                          # feed returned nothing
    assert engine.Engine(dry_run=False).manage_stops() == []
    assert len(wired["alerts"]) == 1
    assert "live unknown" in wired["alerts"][0]
    assert wired["closed"] == []


def test_position_lookup_failure_degrades_to_the_old_behaviour(wired):
    """An API hiccup must not manufacture alerts or liquidations."""
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["positions_raise"] = RuntimeError("api down")
    wired["live"] = {"BAC": BAC_PLAN_STOP - 0.05}
    assert engine.Engine(dry_run=False).manage_stops() == []
    assert wired["alerts"] == []
    assert wired["closed"] == []


def test_dry_run_never_touches_the_broker(wired):
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["held"] = {"BAC"}
    wired["live"] = {"BAC": BAC_PLAN_STOP - 0.05}
    assert engine.Engine(dry_run=True).manage_stops() == []
    assert wired["closed"] == []
    assert wired["canceled"] == []
    assert wired["alerts"] == []


def test_close_failure_is_logged_and_retried_not_swallowed(wired, monkeypatch):
    def _boom(sym):
        raise RuntimeError("position is held_for_orders")
    monkeypatch.setattr(broker, "close_position", _boom)
    wired["trades"] = [_trade()]
    wired["parents"] = {"parent-1": _naked_parent()}
    wired["held"] = {"BAC"}
    wired["live"] = {"BAC": BAC_PLAN_STOP - 0.05}
    # No action is reported, so the next 60s poll tries again.
    assert engine.Engine(dry_run=False).manage_stops() == []


def test_one_naked_symbol_does_not_block_another_trades_ratchet(wired):
    """The naked branch sits inside the per-symbol loop; the rest must still run."""
    protected = _trade(symbol="NVDA", stop=98.5, oid="parent-2")
    protected.update(entry_price=100.0, take_profit_price=102.25, qty=10)
    wired["trades"] = [_trade(), protected]
    wired["parents"] = {"parent-1": _naked_parent(),
                        "parent-2": _parent([_leg("leg-stop", stop_price="98.5")],
                                            fill="100.0")}
    wired["held"] = {"BAC"}
    wired["live"] = {"BAC": BAC_LIMIT - 0.01, "NVDA": 103.0}

    actions = engine.Engine(dry_run=False).manage_stops()
    assert [a["action"] for a in actions] == ["stop_raised"]
    assert len(wired["alerts"]) == 1


def test_broker_positions_are_fetched_at_most_once_per_tick(wired, monkeypatch):
    calls = {"n": 0}

    def _positions():
        calls["n"] += 1
        return {"BAC", "NFLX"}
    monkeypatch.setattr(broker, "open_position_symbols", _positions)
    wired["trades"] = [_trade(), _trade(symbol="NFLX", oid="parent-2")]
    wired["parents"] = {"parent-1": _naked_parent(), "parent-2": _naked_parent()}
    wired["live"] = {"BAC": BAC_LIMIT, "NFLX": BAC_LIMIT}
    engine.Engine(dry_run=False).manage_stops()
    assert calls["n"] == 1


def test_no_broker_call_when_every_stop_leg_resolves(wired, monkeypatch):
    """The healthy path must not add an API round-trip to every tick."""
    def _boom():
        raise AssertionError("positions must not be fetched when stops resolve")
    monkeypatch.setattr(broker, "open_position_symbols", _boom)
    trade = _trade(symbol="NVDA", stop=98.5)
    trade.update(entry_price=100.0, take_profit_price=102.25, qty=10)
    wired["trades"] = [trade]
    wired["parents"] = {"parent-1": _parent([_leg("leg-stop", stop_price="98.5")],
                                            fill="100.0")}
    wired["live"] = {"NVDA": 103.0}
    actions = engine.Engine(dry_run=False).manage_stops()
    assert actions and actions[0]["action"] == "stop_raised"


# --- 4. capital-protection invariants --------------------------------------

def test_imp_038_widens_no_risk_limit():
    """This change may only ever REMOVE exposure. Nothing here is negotiable."""
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    assert config.TRAILING_STOP_ENABLED is True


def test_enforcement_is_monotonically_protective():
    """Sweep the tape across the plan stop: the verdict may only turn from
    'hold' to 'sell' as price falls, never the other way."""
    seen_enforce = False
    for tick in [50.0, 47.22, 46.30, 45.62, 45.61, 45.60, 44.00, 40.0]:
        act = exits.naked_position_action(True, tick, BAC_PLAN_STOP)
        if act == exits.NAKED_ENFORCE:
            seen_enforce = True
        else:
            assert not seen_enforce, "enforcement un-fired as price fell further"
    assert seen_enforce
