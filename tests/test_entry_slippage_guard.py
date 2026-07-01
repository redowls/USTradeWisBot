"""IMP-008 / IMP-009 regression tests — stale-signal / entry-slippage guard.

2026-06-30 09:30:22 ET (IMP-008): AMD was the day's first entry attempt but
Alpaca rejected the whole bracket with a 422 ("take_profit.limit_price must be
>= base_price + 0.01", base_price 554.29). The plan's entry/stop/take-profit are
anchored to the signal-bar close (~542), but the order is a MARKET buy that
filled live at 554.29 — a >2% gap up between signal and submission pushed the
take-profit (>= ~entry*1.0225) below the live price, so the entry was silently
lost and never even reached the DB.

2026-07-01 09:30:26 ET (IMP-009): NVDA was the day's first entry attempt and
Alpaca rejected the bracket with the MIRROR 422 ("stop_loss.stop_price must be
<= base_price - 0.01", base_price 195.02) — NVDA gapped DOWN between the signal
and submission, so the stop (anchored ~1.5% below the higher signal close) landed
at/above the live price. Same silent lost entry, opposite direction.

These tests pin the pre-submit guard that skips an entry when the live price has
moved more than MAX_ENTRY_SLIPPAGE_PCT from the signal close in EITHER direction
— avoiding both doomed brackets and, for smaller gaps that would be accepted, the
stop/TP mispriced against the real fill (inflated risk / hair-trigger stop).
"""

from bot import broker, config, confidence, data, engine, exits, logbook, signals, sizing


# --- pure helper -----------------------------------------------------------

def test_entry_slippage_pct_amd_gap():
    """AMD 06-30: signal ~542.10 vs live 554.29 -> ~2.25% above (a chase)."""
    slip = sizing.entry_slippage_pct(554.29, 542.10)
    assert slip is not None and 2.2 < slip < 2.3


def test_entry_slippage_pct_normal_fill_small():
    """A typical open fill (CRM-class) sits ~0.45% above the signal — under cap."""
    slip = sizing.entry_slippage_pct(155.17, 154.48)
    assert slip is not None and slip < config.MAX_ENTRY_SLIPPAGE_PCT


def test_entry_slippage_pct_pullback_is_negative():
    """Live below the signal (a dip into the level) is negative."""
    assert sizing.entry_slippage_pct(99.0, 100.0) < 0


def test_entry_slippage_pct_nvda_gap_down():
    """NVDA 07-01: signal ~198.0 vs live 195.02 -> ~-1.5% below (a gap down)."""
    slip = sizing.entry_slippage_pct(195.02, 198.0)
    assert slip is not None and -1.6 < slip < -1.4
    assert abs(slip) > config.MAX_ENTRY_SLIPPAGE_PCT


def test_entry_slippage_pct_none_when_no_live_price():
    """Missing/invalid prices -> None so the guard fails open (no skip)."""
    assert sizing.entry_slippage_pct(None, 100.0) is None
    assert sizing.entry_slippage_pct(100.0, 0.0) is None


# --- engine guard ----------------------------------------------------------

def _ev(symbol: str, close: float) -> dict:
    return {"symbol": symbol, "signal_type": "BREAKOUT", "close": close, "atr": 2.0}


def _run(monkeypatch, symbol: str, *, signal_close: float, live_price):
    """Drive Engine.consider_entries (dry-run) for one candidate with a live price."""
    now = exits.now_et().replace(hour=9, minute=30, second=22, microsecond=0)
    monkeypatch.setattr(exits, "entries_allowed", lambda _now: True)
    monkeypatch.setattr(broker, "account_summary",
                        lambda: {"equity": 10_000.0, "buying_power": 100_000.0})
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set())
    monkeypatch.setattr(logbook, "open_trade_symbols", lambda: set())
    monkeypatch.setattr(logbook, "get_today_realized_pl", lambda _d: 0.0)
    monkeypatch.setattr(logbook, "get_symbol_activity_today", lambda _d: {})
    monkeypatch.setattr(signals, "evaluate_watchlist", lambda: [_ev(symbol, signal_close)])
    monkeypatch.setattr(confidence, "score", lambda _ev: 90.0)
    monkeypatch.setattr(data, "latest_trade_price", lambda _s: live_price)
    actions = engine.Engine(dry_run=True).consider_entries(now=now)
    assert len(actions) == 1
    return actions[0]


def test_amd_gap_up_is_skipped(monkeypatch):
    """AMD 06-30 replay: signal 542.10, live 554.29 (+2.25%) -> skip, not a 422."""
    act = _run(monkeypatch, "AMD", signal_close=542.10, live_price=554.29)
    assert act["action"] == "skip"
    assert act["detail"].startswith("stale_signal_gap_")


def test_normal_open_fill_still_buys(monkeypatch):
    """A live price only ~0.3% above the signal must still trade (no false skip)."""
    act = _run(monkeypatch, "INTC", signal_close=131.69, live_price=132.10)
    assert act["action"] == "would_buy"


def test_missing_live_price_fails_open(monkeypatch):
    """No live price (data hiccup) -> guard is silent, entry proceeds as before."""
    act = _run(monkeypatch, "TSM", signal_close=455.12, live_price=None)
    assert act["action"] == "would_buy"


def test_pullback_below_signal_still_buys(monkeypatch):
    """A small dip below the signal close (<1%) is not a chase -> entry proceeds."""
    act = _run(monkeypatch, "TSLA", signal_close=411.72, live_price=409.00)  # -0.66%
    assert act["action"] == "would_buy"


def test_nvda_gap_down_is_skipped(monkeypatch):
    """NVDA 07-01 replay: signal 198.0, live 195.02 (-1.5%) -> skip, not a 422."""
    act = _run(monkeypatch, "NVDA", signal_close=198.0, live_price=195.02)
    assert act["action"] == "skip"
    assert act["detail"].startswith("stale_signal_gap_down_")
