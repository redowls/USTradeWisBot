"""IMP-039 tests — a stop leg that FILLED is not a missing stop leg.

IMP-038 (shipped 2026-08-20) taught `engine.manage_stops` that an unresolvable
bracket stop leg might mean a live long with no protection. It fired for the
first time on 2026-08-21 and it fired on the wrong thing:

    12:04:22 EDT | UNPROTECTED UNH: position open with no working bracket
                   stop leg (live 390.61, plan stop 384.09)
    12:05:40 EDT | EXIT UNH STOP pl=$3.98 (0.1701%)

UNH #275 was not unprotected. Its stop leg was working, it had been trailed to
390.55 by the IMP-013 ratchet, and it was in the act of SELLING the position.
The Alpaca order record (read back through the `alpaca` MCP) times it exactly:

    limit leg 52f81840  canceled_at  2026-08-21T16:04:19.610486Z
    stop  leg c3e90c63  submitted_at 2026-08-21T16:04:19.672162Z
    stop  leg c3e90c63  filled_at    2026-08-21T16:04:22.502483Z  @ 390.523333

The 12:04:22 poll landed inside that second: `resolve_stop_leg` returned None
(FILLED is not a PATCHable status) while `GET /v2/positions` still listed UNH,
so the engine concluded "position open, no stop" and raised an alert about a
trade the broker had already flattened.

The false alarm is the cheap half. The expensive half is that
`naked_position_action` enforces at/below the trade's ORIGINAL plan stop, and
**every ordinary stop-out satisfies that by construction** — the stop fills at
or through its own price. 111 of the book's 261 closed trades exited on STOP.
MU #273 stopped out the same morning at 961.31 against a 961.59 plan stop and
missed the identical window by 53 seconds:

    stop leg ccaa9487  filled_at 2026-08-21T14:19:01.365898Z @ 961.31
    next engine poll             2026-08-21T14:19:54Z  (position already gone)

Had that poll landed where UNH's did, IMP-038 would have cancelled the sibling
leg and sent `DELETE /v2/positions/MU` against a position the stop had already
sold — a second sell on a flat book, i.e. a naked short, which is the exact
failure `_handle_naked_position`'s own docstring says it rules out.

So the guard is narrow by design: FILLED (or PARTIALLY_FILLED, where the same
order is still working for the remainder) means "exit in progress, leave it to
`check_exits`". CANCELED — which is what the OCO does to the stop leg on the
take-profit path, and therefore what all ten of IMP-038's measured naked
windows actually looked like — still alerts and still enforces. Every test
below that asserts silence has a CANCELED control asserting the opposite.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot import broker, data, engine, execution, exits, logbook, notify

# --- UNH #275, 2026-08-21: the trade that produced the false alarm ----------
UNH_ENTRY = 389.86          # parent e71f017d, filled 14:27:41.631527Z
UNH_QTY = 6
UNH_PLAN_STOP = 384.09      # DB stop_price, the 1R risk anchor (never moved)
UNH_LIMIT = 398.71
UNH_TRAILED_STOP = 390.55   # leg c3e90c63, after two IMP-013 ratchets
UNH_STOP_FILL = 390.523333  # what it actually sold at
UNH_LIVE_AT_POLL = 390.61   # the price in the 12:04:22 log line

# --- MU #273, 2026-08-21: the same race, but at the plan stop ---------------
MU_ENTRY = 978.70
MU_QTY = 2
MU_PLAN_STOP = 961.59       # leg ccaa9487, never trailed
MU_STOP_FILL = 961.31       # filled THROUGH the stop, as stops do
MU_LIMIT = 998.20


def _leg(id_, type_="stop", status="held", stop_price="384.09", replaced_by=None):
    return SimpleNamespace(id=id_, type=type_, status=status,
                           replaced_by=replaced_by, stop_price=stop_price)


def _parent(legs, fill=str(UNH_ENTRY), id_="parent-unh"):
    return SimpleNamespace(id=id_, legs=legs, filled_avg_price=fill)


def _unh_trade():
    return {"trade_id": 275, "symbol": "UNH", "qty": UNH_QTY,
            "entry_price": UNH_ENTRY, "stop_price": UNH_PLAN_STOP,
            "take_profit_price": UNH_LIMIT, "alpaca_order_id": "parent-unh",
            "entry_time": None}


def _mu_trade():
    return {"trade_id": 273, "symbol": "MU", "qty": MU_QTY,
            "entry_price": MU_ENTRY, "stop_price": MU_PLAN_STOP,
            "take_profit_price": MU_LIMIT, "alpaca_order_id": "parent-mu",
            "entry_time": None}


def _unh_chain(final_status):
    """UNH #275's real two-ratchet replace chain, terminating in ``final_status``.

    leg-0 384.09 -> leg-1 390.12 (10:53:27 ET) -> leg-2 390.55 (10:58:56 ET).
    Returns (parent, {id: leg}) so the engine's ``get_order`` can follow it.
    """
    leg2 = _leg("c3e90c63", status=final_status, stop_price=str(UNH_TRAILED_STOP))
    leg1 = _leg("e71a689b", status="replaced", stop_price="390.12",
                replaced_by="c3e90c63")
    leg0 = _leg("52f81840-stop", status="replaced", stop_price=str(UNH_PLAN_STOP),
                replaced_by="e71a689b")
    parent = _parent([leg0, _leg("52f81840", type_="limit", status="canceled")])
    return parent, {"e71a689b": leg1, "c3e90c63": leg2}


def _mu_parent(stop_status):
    """MU #273: a plain, never-trailed bracket whose stop reached ``stop_status``."""
    return _parent([_leg("ccaa9487", status=stop_status,
                         stop_price=str(MU_PLAN_STOP)),
                    _leg("dc7dc9ac", type_="limit", status="canceled")],
                   fill=str(MU_ENTRY), id_="parent-mu")


# --- 1. exits.stop_leg_filled — the pure predicate --------------------------

@pytest.mark.parametrize("status,filled", [
    ("filled", True),
    ("FILLED", True),
    ("OrderStatus.FILLED", True),
    ("partially_filled", True),      # same order still works the remainder
    ("canceled", False),             # the OCO release — IMP-038's real case
    ("expired", False),
    ("rejected", False),
    ("held", False),                 # still working
    ("new", False),
    ("accepted", False),
    ("pending_new", False),
])
def test_stop_leg_filled_reads_the_terminal_status(status, filled):
    parent = _parent([_leg("leg-stop", status=status)])
    assert exits.stop_leg_filled(parent, lambda oid: None) is filled


def test_the_real_unh_chain_ends_in_a_fill():
    parent, chain = _unh_chain("filled")
    assert exits.stop_leg_filled(parent, chain.__getitem__) is True
    # ...and the same chain cancelled out is NOT a fill.
    parent, chain = _unh_chain("canceled")
    assert exits.stop_leg_filled(parent, chain.__getitem__) is False


@pytest.mark.parametrize("parent", [
    _parent([]),                                       # no legs at all
    _parent([_leg("leg-tp", type_="limit", status="filled")]),   # no STOP leg
    _parent([_leg("leg-stop", status="replaced")]),    # dead end, no replaced_by
    _parent([_leg("self", status="replaced", replaced_by="self")]),
    SimpleNamespace(id="p", legs=None, filled_avg_price="1"),
])
def test_an_unresolvable_leg_is_never_reported_as_filled(parent):
    """Fail safe: if we cannot see the leg we must not claim the stop sold."""
    assert exits.stop_leg_filled(parent, lambda oid: None) is False


def test_a_chain_longer_than_max_hops_is_not_reported_as_filled():
    chain = {f"l{i}": _leg(f"l{i}", status="replaced", replaced_by=f"l{i + 1}")
             for i in range(12)}
    chain["l12"] = _leg("l12", status="filled")
    parent = _parent([_leg("l0", status="replaced", replaced_by="l1")])
    assert exits.stop_leg_filled(parent, chain.__getitem__) is False
    assert exits.stop_leg_filled(parent, chain.__getitem__, max_hops=15) is True


# --- 2. resolve_stop_leg is unchanged by the refactor -----------------------

@pytest.mark.parametrize("status,resolves", [
    ("held", True), ("new", True), ("accepted", True), ("pending_new", True),
    ("filled", False), ("partially_filled", False), ("canceled", False),
    ("expired", False), ("rejected", False),
])
def test_resolve_stop_leg_contract_is_untouched(status, resolves):
    parent = _parent([_leg("leg-stop", status=status)])
    leg = exits.resolve_stop_leg(parent, lambda oid: None)
    assert (leg is not None) is resolves
    if resolves:
        assert leg.id == "leg-stop"


def test_resolve_stop_leg_still_follows_the_replace_chain():
    parent, chain = _unh_chain("held")
    leg = exits.resolve_stop_leg(parent, chain.__getitem__)
    assert leg is not None and leg.id == "c3e90c63"
    assert float(leg.stop_price) == UNH_TRAILED_STOP


# --- 3. engine.manage_stops wiring ------------------------------------------

@pytest.fixture
def wired(monkeypatch):
    """Every outbound call captured, none of them real."""
    state = {"closed": [], "canceled": [], "alerts": [], "held": set(),
             "live": {}, "trades": [], "orders": {}, "position_calls": 0}

    # These fixtures carry REAL trade ids, so the IMP-043 arming write would land
    # on live rows. Stubbed here instead (tests/conftest.py blocks it anyway).
    monkeypatch.setattr(logbook, "record_stop_raise", lambda _tid, _stop: True)
    monkeypatch.setattr(logbook, "get_open_trades", lambda: list(state["trades"]))
    monkeypatch.setattr(execution, "get_order", lambda oid: state["orders"][oid])
    monkeypatch.setattr(data, "latest_trade_price", lambda sym: state["live"].get(sym))
    monkeypatch.setattr(data, "get_bars_for_symbols", lambda symbols, **kw: {})
    monkeypatch.setattr(execution, "replace_stop_order",
                        lambda oid, px: {"ok": True, "order_id": "n", "error": None})

    def _positions():
        state["position_calls"] += 1
        return set(state["held"])
    monkeypatch.setattr(broker, "open_position_symbols", _positions)
    monkeypatch.setattr(broker, "close_position", lambda sym: state["closed"].append(sym))
    monkeypatch.setattr(execution, "cancel_order", lambda oid: state["canceled"].append(oid))
    monkeypatch.setattr(notify, "error_alert",
                        lambda msg: state["alerts"].append(msg) or True)
    return state


def _load_unh(wired, final_status):
    parent, chain = _unh_chain(final_status)
    wired["trades"] = [_unh_trade()]
    wired["orders"] = {"parent-unh": parent, **chain}
    wired["held"] = {"UNH"}                 # the stale position list, as observed
    wired["live"] = {"UNH": UNH_LIVE_AT_POLL}


def test_imp039_the_2026_08_21_unh_poll_is_silent(wired):
    """THE REGRESSION. Same instant, same stale position list, no false alarm."""
    _load_unh(wired, "filled")

    assert engine.Engine(dry_run=False).manage_stops() == []
    assert wired["alerts"] == []            # <- the 12:04:22 UNPROTECTED line
    assert wired["closed"] == []
    assert wired["canceled"] == []


def test_imp039_without_the_guard_that_same_state_alerted(wired):
    """THE CONTROL. Flip only the leg status to CANCELED — a genuinely naked
    long — and IMP-038 must still do its job, unchanged."""
    _load_unh(wired, "canceled")

    assert engine.Engine(dry_run=False).manage_stops() == []
    assert len(wired["alerts"]) == 1
    assert "UNPROTECTED UNH" in wired["alerts"][0]


def test_imp039_a_filled_stop_at_the_plan_stop_is_not_liquidated_again(wired):
    """THE ONE THAT MATTERS: MU #273's window, which the poll missed by 53s.

    Stop filled at 961.31, plan stop 961.59, so `naked_position_action` would
    return ENFORCE — and enforcement on an already-sold position is a short.
    """
    wired["trades"] = [_mu_trade()]
    wired["orders"] = {"parent-mu": _mu_parent("filled")}
    wired["held"] = {"MU"}                  # position list has not caught up
    wired["live"] = {"MU": MU_STOP_FILL}    # at/below the plan stop

    assert engine.Engine(dry_run=False).manage_stops() == []
    assert wired["closed"] == []            # <- no second sell
    assert wired["canceled"] == []
    assert wired["alerts"] == []
    # The verdict itself is unchanged; only whether we ever ask for it.
    assert exits.naked_position_action(True, MU_STOP_FILL,
                                       MU_PLAN_STOP) == exits.NAKED_ENFORCE


def test_imp039_a_cancelled_stop_at_the_plan_stop_still_enforces(wired):
    """THE CONTROL for the above: a real naked breach must still be closed.

    MU's sibling limit leg was already canceled in the real record, so there is
    nothing for `resolve_limit_leg_id` to pull — the shares are free and the
    liquidation goes straight out. (Cancel-before-sell ordering on a still
    WORKING limit leg is pinned by `test_naked_protection`.)
    """
    wired["trades"] = [_mu_trade()]
    wired["orders"] = {"parent-mu": _mu_parent("canceled")}
    wired["held"] = {"MU"}
    wired["live"] = {"MU": MU_STOP_FILL}

    actions = engine.Engine(dry_run=False).manage_stops()
    assert wired["closed"] == ["MU"]
    assert wired["canceled"] == []
    assert actions and actions[0]["action"] == "soft_stop"
    assert len(wired["alerts"]) == 1


def test_imp039_a_partially_filled_stop_is_still_working(wired):
    """The remainder is covered by the same order — nothing to alert about."""
    wired["trades"] = [_mu_trade()]
    wired["orders"] = {"parent-mu": _mu_parent("partially_filled")}
    wired["held"] = {"MU"}
    wired["live"] = {"MU": MU_STOP_FILL}

    assert engine.Engine(dry_run=False).manage_stops() == []
    assert wired["closed"] == []
    assert wired["alerts"] == []


def test_imp039_the_filled_path_costs_no_position_lookup(wired):
    """Ordinary STOP exits are 111 of 261 trades; they must not each add a
    /v2/positions round-trip to the 60s poll."""
    _load_unh(wired, "filled")
    engine.Engine(dry_run=False).manage_stops()
    assert wired["position_calls"] == 0
    # ...whereas the genuinely-naked path does pay for one.
    _load_unh(wired, "canceled")
    engine.Engine(dry_run=False).manage_stops()
    assert wired["position_calls"] == 1


def test_imp039_a_filled_stop_does_not_block_another_symbols_ratchet(wired):
    """The guard sits inside the per-symbol loop; the rest of the tick runs."""
    protected = {"trade_id": 274, "symbol": "GOOG", "qty": 7,
                 "entry_price": 339.74, "stop_price": 334.47,
                 "take_profit_price": 347.20, "alpaca_order_id": "parent-goog",
                 "entry_time": None}
    parent, chain = _unh_chain("filled")
    wired["trades"] = [_unh_trade(), protected]
    wired["orders"] = {
        "parent-unh": parent, **chain,
        "parent-goog": _parent([_leg("goog-stop", stop_price="334.47")],
                               fill="339.74", id_="parent-goog"),
    }
    wired["held"] = {"UNH"}
    wired["live"] = {"UNH": UNH_LIVE_AT_POLL, "GOOG": 343.27}

    actions = engine.Engine(dry_run=False).manage_stops()
    assert [a["action"] for a in actions] == ["stop_raised"]
    assert actions[0]["symbol"] == "GOOG"
    assert wired["alerts"] == []


# --- 4. capital-protection invariants ---------------------------------------

def test_imp039_can_only_ever_narrow_what_gets_liquidated(wired):
    """The guard adds no code path that sells, alerts or widens risk: for every
    leg status, the set of actions is a SUBSET of the pre-IMP-039 behaviour."""
    for status in ("filled", "partially_filled", "canceled", "expired", "held"):
        wired.update(closed=[], canceled=[], alerts=[], position_calls=0)
        wired["trades"] = [_mu_trade()]
        wired["orders"] = {"parent-mu": _mu_parent(status)}
        wired["held"] = {"MU"}
        wired["live"] = {"MU": MU_STOP_FILL}
        engine.Engine(dry_run=False).manage_stops()
        if status in ("filled", "partially_filled"):
            assert wired["closed"] == [] and wired["alerts"] == []
        elif status == "held":
            assert wired["closed"] == []      # protected: ratchet territory
        else:
            assert wired["closed"] == ["MU"]  # IMP-038, untouched


def test_imp039_dry_run_still_touches_nothing(wired):
    _load_unh(wired, "filled")
    assert engine.Engine(dry_run=True).manage_stops() == []
    assert wired["closed"] == [] and wired["canceled"] == [] and wired["alerts"] == []
