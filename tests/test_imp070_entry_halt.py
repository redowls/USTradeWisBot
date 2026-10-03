"""IMP-070 tests — ENTRY_MODE "none" halts NEW ENTRIES and nothing else.

The pre-registered kill criterion fired on the ORB signal (week ending
2026-10-03: escalation_by_regime['orb'] escalated on a pure 3-session window,
F+S 100%, true win rate 0%, n=7, avg -0.289R; F+S >= 60% for two consecutive
weeks). These tests pin the three things that must all be true at once:

  1. a bar that WOULD have been a perfect ORB entry is refused, and the refusal
     is RECORDED (``entry_halted``) so the evidence stream keeps accruing;
  2. the engine places no order for it, in any mode;
  3. the halt touches NO exit, ratchet, flatten or risk surface — a halted bot
     must still manage and close an open position, and the capital-protection
     invariants are unchanged.
"""

from __future__ import annotations

import ast
import pathlib

import numpy as np
import pandas as pd
import pytest

from bot import broker, config, confidence, data, engine, exits, logbook, signals


def _session(day: str, closes, highs=None, lows=None, vols=None) -> pd.DataFrame:
    n = len(closes)
    idx = pd.date_range(start=f"{day} 09:30", periods=n, freq="5min", tz=config.MARKET_TZ)
    closes = np.asarray(closes, dtype=float)
    highs = closes + 0.2 if highs is None else np.asarray(highs, dtype=float)
    lows = closes - 0.2 if lows is None else np.asarray(lows, dtype=float)
    vols = np.full(n, 1000.0) if vols is None else np.asarray(vols, dtype=float)
    return pd.DataFrame({"open": closes, "high": highs, "low": lows,
                         "close": closes, "volume": vols}, index=idx)


def _two_days(today_closes, today_vols=None):
    prev = _session("2026-09-16", [100.0] * 78)
    today = _session("2026-09-17", today_closes, vols=today_vols)
    return pd.concat([prev, today])


# The exact fixture test_imp059 uses for a CLEAN signal: bar 8 closes above the
# 6-bar range high on double volume, above VWAP, before the cutoff.
CLEAN_BREAK_CLOSES = [100.0] * 8 + [101.0, 101.5]
CLEAN_BREAK_VOLS = [1000.0] * 8 + [2000.0, 2000.0]


@pytest.fixture
def halted(monkeypatch):
    monkeypatch.setattr(config, "ENTRY_MODE", "none")
    monkeypatch.setattr(config, "ORB_RANGE_BARS", 6)
    monkeypatch.setattr(config, "ORB_CUTOFF_ET", "11:30")
    monkeypatch.setattr(config, "ORB_MIN_REL_VOL", 1.3)
    monkeypatch.setattr(config, "ORB_BUFFER_PCT", 0.0)
    monkeypatch.setattr(config, "ORB_REQUIRE_ABOVE_VWAP", True)
    monkeypatch.setattr(config, "ORB_MARKET_FILTER_SYMBOL", "SPY")


# --- the mode predicates ------------------------------------------------------------

def test_entries_halted_only_for_none(monkeypatch):
    for mode, expected in (("none", True), ("NONE", True), ("None", True),
                           ("orb", False), ("ma", False), ("", False)):
        monkeypatch.setattr(config, "ENTRY_MODE", mode)
        assert signals.entries_halted() is expected, mode


def test_orb_path_is_taken_by_both_orb_and_none(monkeypatch):
    # "none" must keep taking the ORB path, otherwise the refusal ledger goes
    # dark and a halt would also destroy the evidence a replacement needs.
    for mode, expected in (("orb", True), ("none", True), ("ma", False)):
        monkeypatch.setattr(config, "ENTRY_MODE", mode)
        assert signals.uses_orb_path() is expected, mode


# --- 1. the signal is refused, and the refusal is recorded ---------------------------

def test_a_clean_orb_break_is_refused_under_the_halt(halted):
    df = _two_days(CLEAN_BREAK_CLOSES, CLEAN_BREAK_VOLS)
    ev = signals.evaluate("AAPL", df=df.iloc[:-1])     # the bar that WAS a signal
    assert ev["signal_type"] is None                    # no entry
    orb = ev["orb"]
    assert orb["candidate"] is True                     # still measured
    assert orb["signal"] is False                       # but never actionable
    assert "entry_halted" in orb["blocks"]              # and auditable
    assert orb["or_high"] == pytest.approx(100.2)       # features still populated
    assert orb["rel_vol"] is not None


def test_the_same_bar_is_a_signal_when_not_halted(monkeypatch):
    """Guards against a false pass: the fixture really is a clean entry."""
    monkeypatch.setattr(config, "ENTRY_MODE", "orb")
    monkeypatch.setattr(config, "ORB_RANGE_BARS", 6)
    monkeypatch.setattr(config, "ORB_MIN_REL_VOL", 1.3)
    monkeypatch.setattr(config, "ORB_BUFFER_PCT", 0.0)
    monkeypatch.setattr(config, "ORB_REQUIRE_ABOVE_VWAP", True)
    df = _two_days(CLEAN_BREAK_CLOSES, CLEAN_BREAK_VOLS)
    ev = signals.evaluate("AAPL", df=df.iloc[:-1])
    assert ev["signal_type"] == "ORB" and ev["orb"]["signal"] is True
    assert "entry_halted" not in ev["orb"]["blocks"]


def test_a_non_candidate_is_not_labelled_entry_halted(halted):
    """Only a candidate the halt actually refused carries the block, so the
    ledger does not fill with 'entry_halted' on every quiet bar."""
    ev = signals.evaluate("AAPL", df=_two_days([100.0] * 8))
    assert ev["orb"]["candidate"] is False
    assert "entry_halted" not in ev["orb"]["blocks"]


# --- 2. the engine places nothing ---------------------------------------------------

def _drive(monkeypatch, ev: dict, dry_run: bool = True):
    now = exits.now_et().replace(hour=10, minute=7, second=0, microsecond=0)
    monkeypatch.setattr(exits, "entries_allowed", lambda _now: True)
    monkeypatch.setattr(broker, "account_summary",
                        lambda: {"equity": 7_183.70, "buying_power": 14_367.40})
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set())
    monkeypatch.setattr(logbook, "open_trade_symbols", lambda: set())
    monkeypatch.setattr(logbook, "get_today_realized_pl", lambda _d: 0.0)
    monkeypatch.setattr(logbook, "get_symbol_activity_today", lambda _d: {})
    monkeypatch.setattr(signals, "evaluate_watchlist", lambda: [ev])
    monkeypatch.setattr(data, "latest_trade_price", lambda _s: None)
    monkeypatch.setattr(logbook, "record_entry_refusals", lambda rows: len(rows))
    eng = engine.Engine(dry_run=dry_run)
    monkeypatch.setattr(eng, "_log", lambda _m: None)
    return eng.consider_entries(now=now)


def test_engine_never_buys_a_halted_candidate(halted, monkeypatch):
    ev = {"symbol": "AAPL", "signal_type": None, "close": 101.0, "atr": 0.3,
          "session_vwap": 100.1,
          "orb": {"candidate": True, "signal": False, "blocks": ["entry_halted"]}}
    actions = _drive(monkeypatch, ev)
    assert [a["action"] for a in actions] == ["skip"]
    assert actions[0]["detail"] == "orb_blocked_entry_halted"
    assert not any(a["action"] in ("buy", "would_buy") for a in actions)


def test_engine_submits_no_order_even_outside_dry_run(halted, monkeypatch):
    """The real protection: with dry_run False, nothing reaches execution."""
    from bot import execution
    calls: list = []
    monkeypatch.setattr(execution, "submit_bracket_order",
                        lambda *a, **k: calls.append((a, k)))
    ev = {"symbol": "AAPL", "signal_type": None, "close": 101.0, "atr": 0.3,
          "session_vwap": 100.1,
          "orb": {"candidate": True, "signal": False, "blocks": ["entry_halted"]}}
    actions = _drive(monkeypatch, ev, dry_run=False)
    assert calls == []                                  # no broker call at all
    assert all(a["action"] == "skip" for a in actions)


# --- 3. nothing else moved ----------------------------------------------------------

def _shipped_constant(name: str):
    """The module-level value in bot/config.py AS SHIPPED.

    tests/conftest.py has an autouse fixture that forces ENTRY_MODE to "ma" for
    every test (so the pre-IMP-059 suite keeps pinning MA behaviour), so reading
    config.ENTRY_MODE here would measure the fixture, not the deployment.
    """
    src = (pathlib.Path(__file__).resolve().parents[1] / "bot" / "config.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in bot/config.py")


def test_the_shipped_config_is_halted():
    """Pins the deployed state this review shipped."""
    assert _shipped_constant("ENTRY_MODE") == "none"


def test_the_shipped_config_is_not_silently_returned_to_a_refuted_signal():
    """Both entry rules are refuted; re-enabling either needs a gate PASS."""
    assert _shipped_constant("ENTRY_MODE") not in ("orb", "ma")


def test_the_halt_does_not_touch_the_exit_or_ratchet_surface():
    # IMP-013's break-even/1R protection is capital protection; the doctrine
    # scores a break-even stop as a FAIL, it does not ask for the ratchet to go.
    assert config.TRAILING_STOP_ENABLED is True
    assert config.BREAKEVEN_TRIGGER_R == 0.5
    assert config.TRAIL_TRIGGER_R == 1.0
    assert config.TRAIL_DISTANCE_R == 1.0
    assert config.RR_RATIO == 1.5


def test_capital_protection_invariants_unchanged():
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"


def test_no_exit_path_consults_the_entry_halt():
    """A halted bot must still manage and close an open position, so no exit
    module may branch on ENTRY_MODE or the halt predicate."""
    root = pathlib.Path(__file__).resolve().parents[1] / "bot"
    for name in ("exits.py", "execution.py", "sizing.py"):
        src = (root / name).read_text()
        tree = ast.parse(src)
        names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        assert "ENTRY_MODE" not in names, name
        assert "entries_halted" not in names, name
        assert "uses_orb_path" not in names, name
