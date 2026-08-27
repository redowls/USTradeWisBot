"""IMP-042 tests — eligibility is decided BEFORE entry quality.

2026-08-26 replay. TSM was entered at 09:36:31 and held until the 15:55
flatten. Between 13:57:39 and 14:25:11 the engine logged NINE
``ENTRY SKIPPED TSM: entry 418.54 is +0.35% above session VWAP 417.10`` lines
— 9 of the session's 31 refusals (29%) — for a symbol that was sitting in the
book and could not have been bought at any price. The 13:57:39 line then became
that session's ``_first_blocked`` TSM candidate, so IMP-033's refused-candidate
replay in ``scripts/gate_monitor.py`` priced a counterfactual entry the engine
was never able to take.

The bug is ordering, not logic: both branches ``continue``, so no entry is
gained or lost (:func:`test_reordering_changes_no_entry_decision` pins that,
which is what keeps IMP-040's open ratchet window uncontaminated). What changes
is attribution — the VWAP gate is now only asked about candidates that were
actually takeable, so its refusal count and its measured opportunity cost mean
what every daily review has been reading them as.
"""

from datetime import timedelta

from bot import broker, config, confidence, data, engine, exits, logbook, signals


# The real 2026-08-26 13:57:39 numbers, so the fixture is the recorded scenario.
TSM_PRICE = 418.54
TSM_VWAP = 417.10  # entry sits +0.35% above -> beyond VWAP_MAX_DIST_PCT (0.25)


def _ev(symbol: str, *, stretched: bool) -> dict:
    """One watchlist evaluation. ``stretched`` puts it beyond the VWAP gate."""
    return {
        "symbol": symbol,
        "signal_type": "MA",
        "close": TSM_PRICE,
        "atr": 6.0,
        "session_vwap": TSM_VWAP if stretched else TSM_PRICE,
    }


def _run(monkeypatch, symbol: str, *, stretched: bool, held: set[str],
         activity: dict) -> tuple[dict, list[str]]:
    """Drive Engine.consider_entries (dry-run) and capture what it logged."""
    now = exits.now_et().replace(hour=13, minute=57, second=39, microsecond=0)
    monkeypatch.setattr(exits, "entries_allowed", lambda _now: True)
    monkeypatch.setattr(broker, "account_summary",
                        lambda: {"equity": 7_428.76, "buying_power": 7_428.76})
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set(held))
    monkeypatch.setattr(logbook, "open_trade_symbols", lambda: set())
    monkeypatch.setattr(logbook, "get_today_realized_pl", lambda _d: 0.0)
    monkeypatch.setattr(logbook, "get_symbol_activity_today", lambda _d: activity)
    monkeypatch.setattr(signals, "evaluate_watchlist",
                        lambda: [_ev(symbol, stretched=stretched)])
    monkeypatch.setattr(confidence, "score", lambda _ev: 62.0)
    monkeypatch.setattr(data, "latest_trade_price", lambda _s: None)

    eng = engine.Engine(dry_run=True)
    logged: list[str] = []
    monkeypatch.setattr(eng, "_log", logged.append)
    actions = eng.consider_entries(now=now)
    assert len(actions) == 1
    return actions[0], logged


def _stale_exit():
    now_naive = exits.now_et().replace(
        hour=13, minute=57, second=39, microsecond=0,
    ).astimezone(config.MARKET_TZ).replace(tzinfo=None)
    return now_naive - timedelta(minutes=config.REENTRY_COOLDOWN_MIN + 5)


def _recent_exit():
    now_naive = exits.now_et().replace(
        hour=13, minute=57, second=39, microsecond=0,
    ).astimezone(config.MARKET_TZ).replace(tzinfo=None)
    return now_naive - timedelta(minutes=5)


def test_gate_is_not_asked_about_a_held_symbol(monkeypatch):
    """The 2026-08-26 TSM line itself: held symbol, stretched price."""
    act, logged = _run(monkeypatch, "TSM", stretched=True,
                       held={"TSM"}, activity={"TSM": {"entries": 1, "last_exit": None}})
    assert act["action"] == "skip"
    assert act["detail"] == "underlying_held_TSM"
    assert not any("above session VWAP" in ln for ln in logged), (
        "a symbol already in the book must not be recorded as a VWAP refusal"
    )


def test_gate_is_not_asked_about_a_cooldown_symbol(monkeypatch):
    act, logged = _run(monkeypatch, "TSM", stretched=True, held=set(),
                       activity={"TSM": {"entries": 1, "last_exit": _recent_exit()}})
    assert act["action"] == "skip"
    assert act["detail"].startswith("cooldown_")
    assert not any("above session VWAP" in ln for ln in logged)


def test_gate_is_not_asked_about_a_daily_capped_symbol(monkeypatch):
    act, logged = _run(
        monkeypatch, "TSM", stretched=True, held=set(),
        activity={"TSM": {"entries": config.MAX_ENTRIES_PER_SYMBOL_PER_DAY,
                          "last_exit": _stale_exit()}},
    )
    assert act["action"] == "skip"
    assert act["detail"] == "max_entries_per_symbol"
    assert not any("above session VWAP" in ln for ln in logged)


def test_gate_is_not_asked_about_a_held_share_class_sibling(monkeypatch):
    """The equivalence group blocks first too: GOOG held -> GOOGL is not a
    VWAP refusal, it is duplicate single-name exposure."""
    act, logged = _run(monkeypatch, "GOOGL", stretched=True,
                       held={"GOOG"}, activity={})
    assert act["detail"] == "underlying_held_GOOG"
    assert not any("above session VWAP" in ln for ln in logged)


def test_eligible_stretched_candidate_is_still_refused_by_the_gate(monkeypatch):
    """Non-vacuity: IMP-022 must still fire — and still log — for a real candidate."""
    act, logged = _run(monkeypatch, "TSM", stretched=True, held=set(), activity={})
    assert act["action"] == "skip"
    assert act["detail"].startswith("above_vwap_+")
    assert any("above session VWAP" in ln for ln in logged), (
        "the gate must keep logging refusals it genuinely owns — "
        "scripts/gate_monitor.py parses that exact line"
    )


def test_eligible_unstretched_candidate_still_trades(monkeypatch):
    """Control: neither guard fires -> the candidate reaches the order path."""
    act, _ = _run(monkeypatch, "TSM", stretched=False, held=set(), activity={})
    assert act["action"] == "would_buy"


def test_reordering_changes_no_entry_decision(monkeypatch):
    """The invariant that lets this ship mid-experiment.

    Across the full (held x cooldown x capped x stretched) matrix, a candidate
    is entered under the new order if and only if it was entered under the old
    one: every guard ends in ``continue``, so only the recorded reason moves.
    IMP-040's ratchet window therefore sees an identical trade population.
    """
    for held in (set(), {"TSM"}):
        for act_row in (None,
                        {"entries": 1, "last_exit": _recent_exit()},
                        {"entries": config.MAX_ENTRIES_PER_SYMBOL_PER_DAY,
                         "last_exit": _stale_exit()}):
            for stretched in (False, True):
                activity = {} if act_row is None else {"TSM": act_row}
                act, _ = _run(monkeypatch, "TSM", stretched=stretched,
                              held=held, activity=activity)
                # Old order: VWAP first, then eligibility. Same predicate set,
                # so "would_buy" requires eligible AND unstretched either way.
                eligible = not held and act_row is None
                expected = "would_buy" if (eligible and not stretched) else "skip"
                assert act["action"] == expected, (held, act_row, stretched)
