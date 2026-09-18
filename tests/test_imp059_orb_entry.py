"""IMP-059 tests — the opening-range-breakout entry, wired into the live path.

The walk-forward gate in bot/entry_lab.py chose the ORB rule; these tests pin
that the LIVE implementation judges the same bar the lab judged (a COMPLETED
bar, one trigger per fresh break), names every reason a candidate was refused,
applies the index market filter fail-closed, sizes on a constant confidence,
records blocked candidates in the refusal ledger, and does NOT run the MA-mode
VWAP-distance gate against an ORB fill.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from bot import broker, config, confidence, data, engine, entry_lab, exits, logbook, signals


def _session(day: str, closes, highs=None, lows=None, vols=None) -> pd.DataFrame:
    n = len(closes)
    idx = pd.date_range(start=f"{day} 09:30", periods=n, freq="5min", tz=config.MARKET_TZ)
    closes = np.asarray(closes, dtype=float)
    highs = closes + 0.2 if highs is None else np.asarray(highs, dtype=float)
    lows = closes - 0.2 if lows is None else np.asarray(lows, dtype=float)
    vols = np.full(n, 1000.0) if vols is None else np.asarray(vols, dtype=float)
    return pd.DataFrame({"open": closes, "high": highs, "low": lows, "close": closes, "volume": vols}, index=idx)


def _two_days(today_closes, today_vols=None, today_highs=None):
    """A full prior session (warm-up for the EMA stack) + today's bars so far."""
    prev = _session("2026-09-16", [100.0] * 78)
    today = _session("2026-09-17", today_closes, vols=today_vols, highs=today_highs)
    return pd.concat([prev, today])


@pytest.fixture
def orb_mode(monkeypatch):
    monkeypatch.setattr(config, "ENTRY_MODE", "orb")
    monkeypatch.setattr(config, "ORB_RANGE_BARS", 6)
    monkeypatch.setattr(config, "ORB_CUTOFF_ET", "11:30")
    monkeypatch.setattr(config, "ORB_MIN_REL_VOL", 1.3)
    monkeypatch.setattr(config, "ORB_BUFFER_PCT", 0.0)
    monkeypatch.setattr(config, "ORB_REQUIRE_ABOVE_VWAP", True)
    monkeypatch.setattr(config, "ORB_MARKET_FILTER_SYMBOL", "SPY")


# --- the rule on closed bars --------------------------------------------------------

def test_first_close_above_the_range_is_the_signal_and_only_once(orb_mode):
    closes = [100.0] * 8 + [101.0, 101.5]        # bars 8 and 9 above the 6-bar range high (100.2)
    vols = [1000.0] * 8 + [2000.0, 2000.0]
    df = _two_days(closes, vols)
    ev8 = signals.evaluate("AAPL", df=df.iloc[:-1])   # judged at the close of bar 8
    assert ev8["signal_type"] == "ORB"
    assert ev8["orb"]["candidate"] and ev8["orb"]["signal"] and ev8["orb"]["blocks"] == []
    assert ev8["orb"]["or_high"] == pytest.approx(100.2)
    assert ev8["broke_level"] == pytest.approx(100.2)
    assert ev8["close"] == pytest.approx(101.0)
    ev9 = signals.evaluate("AAPL", df=df)             # still above at bar 9: NOT a fresh break
    assert ev9["signal_type"] is None
    assert ev9["orb"]["candidate"] is False and ev9["orb"]["blocks"] == ["not_fresh"]


def test_break_inside_the_range_window_is_not_a_candidate(orb_mode):
    closes = [100.0, 100.0, 100.0, 105.0]            # bar 3 is still inside the 6-bar range
    df = _two_days(closes)
    ev = signals.evaluate("AAPL", df=df)
    assert ev["signal_type"] is None and ev["orb"]["blocks"] == ["range_incomplete"]


def test_every_failed_quality_condition_is_named(orb_mode):
    # Fresh break on bar 8 but on thin volume -> candidate, blocked by low_volume.
    closes = [100.0] * 8 + [101.0]
    ev = signals.evaluate("AAPL", df=_two_days(closes, [1000.0] * 9))
    assert ev["orb"]["candidate"] and ev["signal_type"] is None
    assert ev["orb"]["blocks"] == ["low_volume"]
    # After the cutoff: bar 25 = 11:35 ET.
    closes = [100.0] * 25 + [101.0]
    vols = [1000.0] * 25 + [2000.0]
    ev = signals.evaluate("AAPL", df=_two_days(closes, vols))
    assert "after_cutoff" in ev["orb"]["blocks"] and ev["signal_type"] is None
    # Below VWAP: an early heavy-volume spike drags the session VWAP above the
    # range high, then a fresh break at 100.5 sits under it.
    closes = [100.0] * 6 + [106.0, 100.1, 100.5]
    highs = [100.2] * 6 + [106.5, 100.3, 100.7]
    vols = [1000.0] * 6 + [50_000.0, 1000.0, 2000.0]
    ev = signals.evaluate("AAPL", df=_two_days(closes, vols, highs))
    assert ev["orb"]["candidate"] and "below_vwap" in ev["orb"]["blocks"]
    assert ev["signal_type"] is None


def test_live_rule_matches_the_lab_rule_bar_for_bar(orb_mode):
    """The lab's vectorised trigger and the live per-bar evaluation must agree."""
    rng = np.random.default_rng(7)
    closes = list(100.0 + np.cumsum(rng.normal(0, 0.15, 40)))
    vols = list(rng.uniform(500, 3000, 40))
    df = _two_days(closes, vols)
    feats = entry_lab.precompute_features(df)
    lab = entry_lab.rule_orb(feats, {"k": 6, "cutoff": "11:30", "min_relvol": 1.3,
                                     "buffer_pct": 0.0, "above_vwap": True})
    today = df.index.normalize() == df.index[-1].normalize()
    for i in np.flatnonzero(np.asarray(today)):
        ev = signals.evaluate("AAPL", df=df.iloc[: i + 1])
        assert (ev["signal_type"] == "ORB") == bool(lab.iloc[i]), (i, ev["orb"])


def test_completed_bars_drops_the_forming_bar():
    df = _session("2026-09-17", [100.0] * 10)         # 09:30 .. 10:15
    now = datetime(2026, 9, 17, 10, 7, tzinfo=config.MARKET_TZ)
    kept = signals.completed_bars(df, now)
    assert kept.index[-1] == pd.Timestamp("2026-09-17 10:00", tz=config.MARKET_TZ)
    assert signals.completed_bars(df, None) is df


def test_ma_mode_is_unchanged(monkeypatch):
    monkeypatch.setattr(config, "ENTRY_MODE", "ma")
    ev = signals.evaluate("AAPL", df=_two_days([100.0] * 8 + [101.0], [1000.0] * 8 + [2000.0]))
    assert ev["signal_type"] != "ORB" and ev["orb"] is None
    assert signals._null_result("X")["orb"] is None


# --- market filter --------------------------------------------------------------------

def test_market_filter_reads_spy_closed_bar_against_its_vwap(orb_mode):
    spy_up = _session("2026-09-17", list(np.linspace(100.0, 101.0, 10)))
    spy_dn = _session("2026-09-17", list(np.linspace(101.0, 100.0, 10)))
    now = datetime(2026, 9, 17, 10, 17, tzinfo=config.MARKET_TZ)
    ok, why = signals.orb_market_ok({"SPY": spy_up}, now)
    assert ok and "above" in why
    ok, why = signals.orb_market_ok({"SPY": spy_dn}, now)
    assert not ok and "below" in why


def test_market_filter_fails_closed_without_index_bars(orb_mode, monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("no data")
    monkeypatch.setattr(data, "get_bars", _boom)
    ok, why = signals.orb_market_ok({}, datetime(2026, 9, 17, 10, 17, tzinfo=config.MARKET_TZ))
    assert not ok and "unavailable" in why
    monkeypatch.setattr(config, "ORB_MARKET_FILTER_SYMBOL", "")
    assert signals.orb_market_ok({}, None) == (True, "market filter disabled")


def test_evaluate_watchlist_applies_filter_and_records_blocked_candidates(orb_mode, monkeypatch):
    closes = [100.0] * 8 + [101.0]
    vols = [1000.0] * 8 + [2000.0]
    aapl = _two_days(closes, vols)
    spy_dn = _session("2026-09-17", list(np.linspace(101.0, 100.0, 9)))
    monkeypatch.setattr(data, "get_watchlist_bars", lambda n_bars=120: {"AAPL": aapl, "SPY": spy_dn})
    monkeypatch.setattr(signals, "completed_bars", lambda df, now: df)   # treat all bars as closed
    (ev,) = [e for e in signals.evaluate_watchlist() if e["symbol"] == "AAPL"]
    assert ev["signal_type"] is None
    assert ev["orb"]["candidate"] and ev["orb"]["blocks"] == ["market_filter"]
    assert "below" in ev["orb"]["market"]


# --- confidence + engine -----------------------------------------------------------------

def test_orb_confidence_is_the_configured_constant(orb_mode):
    assert confidence.score({"signal_type": "ORB"}) == pytest.approx(config.ORB_CONFIDENCE)
    assert confidence.score({"signal_type": "MA", "ma_score": 0.0}) == 0.0


def _drive(monkeypatch, ev: dict) -> tuple[dict, list[str]]:
    now = exits.now_et().replace(hour=10, minute=7, second=0, microsecond=0)
    monkeypatch.setattr(exits, "entries_allowed", lambda _now: True)
    monkeypatch.setattr(broker, "account_summary", lambda: {"equity": 7_500.0, "buying_power": 15_000.0})
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set())
    monkeypatch.setattr(logbook, "open_trade_symbols", lambda: set())
    monkeypatch.setattr(logbook, "get_today_realized_pl", lambda _d: 0.0)
    monkeypatch.setattr(logbook, "get_symbol_activity_today", lambda _d: {})
    monkeypatch.setattr(signals, "evaluate_watchlist", lambda: [ev])
    monkeypatch.setattr(data, "latest_trade_price", lambda _s: None)
    eng = engine.Engine(dry_run=True)
    logged: list[str] = []
    monkeypatch.setattr(eng, "_log", logged.append)
    actions = eng.consider_entries(now=now)
    assert len(actions) == 1
    return actions[0], logged


def test_engine_does_not_apply_the_vwap_distance_gate_to_an_orb_fill(orb_mode, monkeypatch):
    # A range break is by nature stretched above VWAP: +0.9% here, far past the
    # 0.25% MA-mode cap. In ORB mode it must go through to sizing, not be refused.
    ev = {"symbol": "AAPL", "signal_type": "ORB", "close": 101.0, "atr": 0.3,
          "session_vwap": 100.1, "orb": {"candidate": True, "signal": True, "blocks": []}}
    act, logged = _drive(monkeypatch, ev)
    assert act["action"] == "would_buy" and act["confidence"] == pytest.approx(config.ORB_CONFIDENCE)
    assert not any("above session VWAP" in ln for ln in logged)


def test_engine_still_applies_the_vwap_gate_in_ma_mode(monkeypatch):
    monkeypatch.setattr(config, "ENTRY_MODE", "ma")
    monkeypatch.setattr(confidence, "score", lambda _ev: 65.0)
    ev = {"symbol": "AAPL", "signal_type": "MA", "close": 101.0, "atr": 0.3, "session_vwap": 100.1}
    act, logged = _drive(monkeypatch, ev)
    assert act["action"] == "skip" and act["detail"].startswith("above_vwap_")


def test_engine_records_a_blocked_orb_candidate_in_the_refusal_ledger(orb_mode, monkeypatch):
    ev = {"symbol": "AAPL", "signal_type": None, "close": 101.0, "atr": 0.3, "session_vwap": 100.1,
          "orb": {"candidate": True, "signal": False, "blocks": ["market_filter"]}}
    act, _ = _drive(monkeypatch, ev)
    assert act["action"] == "skip"
    assert act["detail"] == "orb_blocked_market_filter"
    assert act["confidence"] == pytest.approx(config.ORB_CONFIDENCE)


def test_engine_ignores_a_plain_non_signal_in_orb_mode(orb_mode, monkeypatch):
    ev = {"symbol": "AAPL", "signal_type": None, "close": 100.0, "atr": 0.3, "session_vwap": 100.1,
          "orb": {"candidate": False, "signal": False, "blocks": ["no_break"]}}
    now = exits.now_et().replace(hour=10, minute=7, second=0, microsecond=0)
    monkeypatch.setattr(exits, "entries_allowed", lambda _now: True)
    monkeypatch.setattr(broker, "account_summary", lambda: {"equity": 7_500.0, "buying_power": 15_000.0})
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set())
    monkeypatch.setattr(logbook, "open_trade_symbols", lambda: set())
    monkeypatch.setattr(logbook, "get_today_realized_pl", lambda _d: 0.0)
    monkeypatch.setattr(logbook, "get_symbol_activity_today", lambda _d: {})
    monkeypatch.setattr(signals, "evaluate_watchlist", lambda: [ev])
    eng = engine.Engine(dry_run=True)
    monkeypatch.setattr(eng, "_log", lambda _m: None)
    assert eng.consider_entries(now=now) == []      # no fill, no refusal row: nothing happened
