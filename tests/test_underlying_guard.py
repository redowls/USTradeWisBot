"""PHASE-002 regression tests — underlying-equivalence guard.

2026-06-12 trade #62: GOOG hit take-profit at 11:24:48 and the bot bought
GOOGL at 11:25:27 (same company, top of the move, -$128.79). 2026-06-10 it
held GOOG and GOOGL simultaneously. These tests pin the guard that makes
share classes count as one underlying for the held-skip, the cooldown and
the daily entry cap.
"""

from datetime import timedelta

from bot import broker, config, confidence, engine, exits, logbook, signals


def test_equivalent_symbols_groups_share_classes():
    assert config.equivalent_symbols("GOOG") == {"GOOG", "GOOGL"}
    assert config.equivalent_symbols("GOOGL") == {"GOOG", "GOOGL"}
    assert config.equivalent_symbols("AAPL") == {"AAPL"}


def _ev(symbol: str) -> dict:
    return {"symbol": symbol, "signal_type": "BREAKOUT", "close": 100.0, "atr": 2.0}


def _run(monkeypatch, symbol: str, *, held: set[str], activity: dict,
         open_trades: set[str] | None = None) -> dict:
    """Drive Engine.consider_entries (dry-run) for one candidate symbol."""
    now = exits.now_et().replace(hour=11, minute=25, second=27, microsecond=0)
    monkeypatch.setattr(exits, "entries_allowed", lambda _now: True)
    monkeypatch.setattr(broker, "account_summary",
                        lambda: {"equity": 10_000.0, "buying_power": 10_000.0})
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set(held))
    monkeypatch.setattr(logbook, "open_trade_symbols", lambda: set(open_trades or set()))
    monkeypatch.setattr(logbook, "get_today_realized_pl", lambda _d: 0.0)
    monkeypatch.setattr(logbook, "get_symbol_activity_today", lambda _d: activity)
    monkeypatch.setattr(signals, "evaluate_watchlist", lambda: [_ev(symbol)])
    monkeypatch.setattr(confidence, "score", lambda _ev: 90.0)
    actions = engine.Engine(dry_run=True).consider_entries(now=now)
    assert len(actions) == 1
    return actions[0]


def test_googl_blocked_by_goog_cooldown(monkeypatch):
    """Trade #62 replay: GOOG exited 39s ago -> GOOGL must sit out the cooldown."""
    now_naive = exits.now_et().replace(
        hour=11, minute=25, second=27, microsecond=0,
    ).astimezone(config.MARKET_TZ).replace(tzinfo=None)
    activity = {"GOOG": {"entries": 1, "last_exit": now_naive - timedelta(seconds=39)}}
    act = _run(monkeypatch, "GOOGL", held=set(), activity=activity)
    assert act["action"] == "skip"
    assert act["detail"].startswith("cooldown_")


def test_googl_blocked_while_goog_held(monkeypatch):
    """06-10 replay: GOOG position open -> GOOGL entry is duplicate exposure."""
    act = _run(monkeypatch, "GOOGL", held={"GOOG"}, activity={})
    assert act["action"] == "skip"
    assert act["detail"] == "underlying_held_GOOG"


def test_daily_cap_aggregates_across_share_classes(monkeypatch):
    """One entry in each class == 2 entries in the underlying -> cap reached."""
    now_naive = exits.now_et().replace(
        hour=11, minute=25, second=27, microsecond=0,
    ).astimezone(config.MARKET_TZ).replace(tzinfo=None)
    stale = now_naive - timedelta(minutes=config.REENTRY_COOLDOWN_MIN + 5)
    activity = {
        "GOOG": {"entries": 1, "last_exit": stale},
        "GOOGL": {"entries": 1, "last_exit": stale},
    }
    act = _run(monkeypatch, "GOOGL", held=set(), activity=activity)
    assert act["action"] == "skip"
    assert act["detail"] == "max_entries_per_symbol"


def test_unrelated_symbol_unaffected(monkeypatch):
    """Control: META must still trade while GOOG is held and recently active."""
    now_naive = exits.now_et().replace(
        hour=11, minute=25, second=27, microsecond=0,
    ).astimezone(config.MARKET_TZ).replace(tzinfo=None)
    activity = {"GOOG": {"entries": 1, "last_exit": now_naive - timedelta(seconds=39)}}
    act = _run(monkeypatch, "META", held={"GOOG"}, activity=activity)
    assert act["action"] == "would_buy"


def test_unfilled_open_trade_blocks_re_entry(monkeypatch):
    """IMP-001 / 2026-06-15 ENPH replay: ENPH was entered at 9:31:22 and again at
    9:32:36 because the first bracket had not filled, so it wasn't in the Alpaca
    position set when the next tick's guard ran (combined -$117.59). An OPEN
    logbook trade must now count as held even with zero filled positions."""
    activity = {"ENPH": {"entries": 1, "last_exit": None}}  # entered once, not exited
    act = _run(monkeypatch, "ENPH", held=set(), activity=activity,
               open_trades={"ENPH"})
    assert act["action"] == "skip"
    assert act["detail"] == "underlying_held_ENPH"


def test_single_symbol_cooldown_unchanged(monkeypatch):
    """Pre-existing behavior: a symbol's own recent exit still throttles it."""
    now_naive = exits.now_et().replace(
        hour=11, minute=25, second=27, microsecond=0,
    ).astimezone(config.MARKET_TZ).replace(tzinfo=None)
    activity = {"AAPL": {"entries": 1, "last_exit": now_naive - timedelta(minutes=5)}}
    act = _run(monkeypatch, "AAPL", held=set(), activity=activity)
    assert act["action"] == "skip"
    assert act["detail"].startswith("cooldown_")
