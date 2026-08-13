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


def test_trail_tracks_price_minus_trail_distance():
    # +2R (103.00) — stop trails TRAIL_DISTANCE_R (0.5R = 0.75) below live: 102.25.
    # Was 101.50 under the pre-IMP-029 1.0R distance.
    assert exits.compute_trailed_stop(100.0, 98.5, 100.0, 103.00) == 102.25


def test_trail_arms_at_the_breakeven_trigger_no_dead_band():
    """IMP-029: at +0.5R..+1R the stop must ratchet, not sit pinned at entry.

    Pre-IMP-029 the trail armed only at +1R and its candidate there was exactly
    the entry price, so this whole band captured nothing. +0.8R (101.20) now
    trails to 101.20 - 0.75 = 100.45, above the entry-level stop of 100.00.
    """
    moved = exits.compute_trailed_stop(100.0, 98.5, 100.0, 101.20)
    assert moved == 100.45
    assert moved > 100.0


def test_ratchet_never_lowers_stop():
    # Price fell back: trail candidate (100.0) is below the current stop.
    assert exits.compute_trailed_stop(100.0, 98.5, 101.5, 101.50) is None


def test_ratchet_ignores_tiny_improvements():
    # Candidate (102.21 = 102.96 - 0.5R) beats the current stop by 5 cents on a
    # $100 stock — below the 0.10% (=$0.10) minimum step, so no replace spam on
    # every 60s tick.
    assert exits.compute_trailed_stop(100.0, 98.5, 102.16, 102.96) is None


def test_guards_zero_risk_and_missing_price():
    assert exits.compute_trailed_stop(100.0, 100.0, 100.0, 105.0) is None  # risk 0
    assert exits.compute_trailed_stop(100.0, 101.0, 101.0, 105.0) is None  # risk < 0
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, None) is None     # no live px


def test_disabled_via_config(monkeypatch):
    monkeypatch.setattr(config, "TRAILING_STOP_ENABLED", False)
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 103.0) is None


# --- 1b. IMP-031 — break-even arms off the PRINTED high, not the 60s sample ----
# The loop polls latest_trade_price once per POLL_INTERVAL_SEC, so before this
# the break-even stage tested a point sample and any excursion that lived and
# died between two ticks was invisible. Real case: NFLX #244 on 2026-08-11.

NFLX_ENTRY = 76.19          # broker fill, 09:39:23 ET
NFLX_STOP = 74.84           # original plan stop -> 1R = 1.35
NFLX_BE_TRIGGER = 76.865    # entry + 0.5R
NFLX_PRINTED_HIGH = 76.89   # the 09:56 1-min bar's high — the only bar to reach it
NFLX_TICK_PRICE = 76.815    # that bar's close, i.e. what a poll plausibly saw


def test_imp031_breakeven_arms_on_a_high_the_tick_price_missed():
    """The regression: NFLX #244 must reach break-even instead of a full -1R.

    The tape printed 76.89 against a 76.865 trigger; every 1-min CLOSE in the
    trade stayed below it, so the polled price never armed anything and the
    trade ran to its original stop for -$44.55 (85% of the day's net loss).
    With the printed high the stop moves to entry and the loss becomes a scratch.
    """
    # What the bot did: the sampled price alone never triggers.
    assert exits.compute_trailed_stop(
        NFLX_ENTRY, NFLX_STOP, NFLX_STOP, NFLX_TICK_PRICE) is None
    # What it does now: the printed high arms break-even at the entry price.
    assert exits.compute_trailed_stop(
        NFLX_ENTRY, NFLX_STOP, NFLX_STOP, NFLX_TICK_PRICE,
        NFLX_PRINTED_HIGH) == NFLX_ENTRY
    assert NFLX_PRINTED_HIGH >= NFLX_BE_TRIGGER > NFLX_TICK_PRICE


def test_imp031_high_water_mark_only_moves_the_stop_up():
    """Capital-protection invariant: a printed high can never widen risk.

    The break-even candidate is the ENTRY price and nothing above it, so the
    worst this stage can do is scratch a trade — it can never place the stop
    below where it already sits, and it can never move a trail down.
    """
    # A huge high cannot push the break-even stop above entry...
    assert exits.compute_trailed_stop(
        NFLX_ENTRY, NFLX_STOP, NFLX_STOP, NFLX_TICK_PRICE, 999.0) == NFLX_ENTRY
    # ...and cannot pull an already-higher stop back down.
    assert exits.compute_trailed_stop(
        NFLX_ENTRY, NFLX_STOP, 76.50, NFLX_TICK_PRICE, NFLX_PRINTED_HIGH) is None
    # A high BELOW the live price is ignored (max of the two is used).
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 100.75, 99.0) == 100.0


def test_imp031_trail_still_follows_the_live_price_not_the_high():
    """Scope guard: only the BREAK-EVEN stage reads the high.

    Trailing off the running high tightens the trail, and tightening is what
    sparse IEX bars bias optimistic (bot/exit_sim.py). Measured on the recorded
    book it also cut two winners (AMD #179 -$48.06, BAC #189 -$9.23), so the
    trail deliberately still tracks the live price.
    """
    # Live at +0.5R (trail candidate == entry) with the high far above: the stop
    # is the entry price, NOT high - 0.5R (which would be 101.75).
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, 100.75, 103.0) == 100.0
    # Live at +2R trails off live (102.25), unaffected by an even higher print.
    assert exits.compute_trailed_stop(100.0, 98.5, 100.0, 103.0, 110.0) == 102.25


def test_imp031_defaults_and_guards_are_unchanged():
    """Omitting high_price must reproduce the pre-IMP-031 behaviour exactly."""
    for live in (100.60, 100.75, 101.20, 103.00):
        assert (exits.compute_trailed_stop(100.0, 98.5, 98.5, live)
                == exits.compute_trailed_stop(100.0, 98.5, 98.5, live, None))
    # Guards still bite even with a high present.
    assert exits.compute_trailed_stop(100.0, 100.0, 100.0, 105.0, 110.0) is None
    assert exits.compute_trailed_stop(100.0, 98.5, 98.5, None, 110.0) is None


# --- 1c. IMP-031 — peak_high_since ---------------------------------------------

def _bars(rows):
    """rows = [(ET 'YYYY-MM-DD HH:MM', high)] -> a tz-aware ET OHLC frame."""
    import pandas as pd
    idx = pd.DatetimeIndex([pd.Timestamp(t) for t, _ in rows]).tz_localize(
        config.MARKET_TZ)
    return pd.DataFrame({"high": [h for _, h in rows],
                         "low": [h - 1 for _, h in rows],
                         "close": [h for _, h in rows]}, index=idx)


def test_peak_high_since_windows_to_this_session_after_entry():
    from datetime import datetime
    bars = _bars([
        ("2026-08-10 15:00", 99.0),   # yesterday — must be excluded
        ("2026-08-11 09:31", 80.0),   # today but BEFORE entry — excluded
        ("2026-08-11 09:39", 76.30),  # the entry minute — included
        ("2026-08-11 09:56", 76.89),  # the print that matters
        ("2026-08-11 13:00", 75.10),
    ])
    entry = datetime(2026, 8, 11, 9, 39, 23)   # naive ET, as the DB stores it
    assert exits.peak_high_since(bars, entry) == 76.89


def test_peak_high_since_fails_open():
    from datetime import datetime
    entry = datetime(2026, 8, 11, 9, 39, 23)
    assert exits.peak_high_since(None, entry) is None
    assert exits.peak_high_since(_bars([]), entry) is None
    assert exits.peak_high_since(_bars([("2026-08-11 09:39", 76.3)]), None) is None
    # A session with no bars at/after the entry minute yields nothing.
    assert exits.peak_high_since(_bars([("2026-08-11 09:31", 80.0)]), entry) is None


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

def _open_trade(symbol="NVDA", stop=98.5, oid="parent-1", entry_time=None):
    return {"trade_id": 1, "symbol": symbol, "qty": 10, "entry_price": 100.0,
            "stop_price": stop, "take_profit_price": 102.25,
            "alpaca_order_id": oid, "entry_time": entry_time}


def _wire(monkeypatch, trades, parents, live, replace_results=None, bars=None):
    replaced: list[tuple[str, float]] = []
    monkeypatch.setattr(logbook, "get_open_trades", lambda: list(trades))
    monkeypatch.setattr(execution, "get_order", lambda oid: parents[oid])
    monkeypatch.setattr(data, "latest_trade_price", lambda sym: live.get(sym))
    # IMP-031: manage_stops batches a 1-min bar pull for the break-even
    # high-water mark. Stub it so no test reaches the network; the default {}
    # is the fail-open path (no bars -> previous last-trade-only behaviour).
    monkeypatch.setattr(data, "get_bars_for_symbols",
                        lambda symbols, **kw: dict(bars or {}))

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
    assert replaced == [("leg-stop", 102.25)]
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
    monkeypatch.setattr(data, "get_bars_for_symbols", lambda symbols, **kw: {})
    replaced = []
    monkeypatch.setattr(execution, "replace_stop_order",
                        lambda oid, px: (replaced.append((oid, px)),
                                         {"ok": True, "order_id": "n", "error": None})[1])
    engine.Engine(dry_run=False).manage_stops()
    assert replaced == [("leg-stop", 102.25)]


def test_manage_stops_arms_breakeven_off_the_session_high(monkeypatch):
    """IMP-031 wiring: the batched 1-min pull feeds the break-even stage.

    Replays NFLX #244 (2026-08-11) through the engine: the polled price is the
    09:56 bar CLOSE, which never reached the +0.5R trigger, while that bar's
    HIGH did. The stop must be replaced at the entry price.
    """
    from datetime import datetime
    entry_time = datetime(2026, 8, 11, 9, 39, 23)
    trade = {"trade_id": 244, "symbol": "NFLX", "qty": 33,
             "entry_price": NFLX_ENTRY, "stop_price": NFLX_STOP,
             "take_profit_price": 77.68, "alpaca_order_id": "parent-1",
             "entry_time": entry_time}
    parent = SimpleNamespace(id="parent-1", filled_avg_price=str(NFLX_ENTRY),
                             legs=[_leg("leg-stop", stop_price=str(NFLX_STOP))])
    bars = {"NFLX": _bars([("2026-08-11 09:39", 76.235),
                           ("2026-08-11 09:56", NFLX_PRINTED_HIGH),
                           ("2026-08-11 10:30", 76.26)])}
    replaced = _wire(monkeypatch, [trade], {"parent-1": parent},
                     {"NFLX": NFLX_TICK_PRICE}, bars=bars)
    actions = engine.Engine(dry_run=False).manage_stops()
    assert replaced == [("leg-stop", NFLX_ENTRY)]
    assert actions and actions[0]["to"] == NFLX_ENTRY

    # Same tick with no bars available (the fail-open path) = what the bot did
    # before IMP-031: nothing arms and the trade keeps riding to the full stop.
    replaced = _wire(monkeypatch, [trade], {"parent-1": parent},
                     {"NFLX": NFLX_TICK_PRICE})
    assert engine.Engine(dry_run=False).manage_stops() == []
    assert replaced == []


def test_manage_stops_survives_a_bar_fetch_failure(monkeypatch):
    """A data hiccup must never stop the ratchet — it degrades, not fails."""
    parent = _parent([_leg("leg-stop")])
    replaced = _wire(monkeypatch, [_open_trade()], {"parent-1": parent},
                     {"NVDA": 103.0})

    def _boom(symbols, **kw):
        raise RuntimeError("data feed down")
    monkeypatch.setattr(data, "get_bars_for_symbols", _boom)
    actions = engine.Engine(dry_run=False).manage_stops()
    assert replaced == [("leg-stop", 102.25)]      # trail still ran off live
    assert actions and actions[0]["action"] == "stop_raised"


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
