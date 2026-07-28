"""Tests for scripts/gate_monitor.py — the IMP-021/022 gate-performance monitor.

Covers the pure aggregation + formatting helpers (no DB) against the REAL
2026-07-28 session that motivated IMP-023's cumulative `--since` view:
GOOG +25.90 (EOD), AAPL +6.22 (EOD), MSFT -0.48 (STOP break-even scratch),
all pure-MA (breakout_score 0) → 2W/1L, +$31.64. Plus the two-session
post-gate window (07-27 -$72.52 + 07-28 +$31.64).
"""

from scripts import gate_monitor as gm


def _row(symbol, pl, reason, bo=0.0, date="2026-07-28"):
    return {"symbol": symbol, "status": "CLOSED", "pl": pl,
            "exit_reason": reason, "entry_date": date, "bo": bo}


# --- the real 2026-07-28 session --------------------------------------------
TODAY_ROWS = [
    _row("GOOG", 25.90, "EOD_FLATTEN"),
    _row("AAPL", 6.22, "EOD_FLATTEN"),
    _row("MSFT", -0.48, "STOP"),
]


def test_aggregate_today_scenario():
    a = gm._aggregate(TODAY_ROWS)
    assert a["taken"] == 3
    assert a["closed"] == 3
    assert a["open"] == 0
    assert a["wins"] == 2
    assert a["losses"] == 1
    assert a["win_pct"] == 66.7
    assert a["net_pl"] == 31.64
    # PF = gross win 32.12 / gross loss 0.48
    assert a["profit_factor"] == round(32.12 / 0.48, 2)
    assert a["by_reason"]["EOD_FLATTEN"] == {"n": 2, "pl": 32.12}
    assert a["by_reason"]["STOP"] == {"n": 1, "pl": -0.48}
    assert a["imp021_held"] is True
    assert a["strong_breakout_leaks"] == []
    assert a["symbols"] == ["GOOG", "AAPL", "MSFT"]


def test_aggregate_imp021_leak_detected():
    # A strong-breakout trade (bo >= BREAKOUT_FADE_CEILING) that got through =
    # the veto leaked; the monitor must flag it, never silently pass.
    rows = TODAY_ROWS + [_row("NVDA", -50.0, "STOP", bo=0.8)]
    a = gm._aggregate(rows)
    assert a["imp021_held"] is False
    assert a["strong_breakout_leaks"] == ["NVDA"]


def test_aggregate_pf_none_when_no_losses():
    a = gm._aggregate([_row("GOOG", 25.90, "EOD_FLATTEN"),
                       _row("AAPL", 6.22, "EOD_FLATTEN")])
    assert a["profit_factor"] is None  # n/a, JSON-safe (no Infinity)
    assert a["net_pl"] == 32.12


def test_aggregate_empty_safe():
    a = gm._aggregate([])
    assert a["taken"] == 0 and a["closed"] == 0
    assert a["win_pct"] == 0.0 and a["net_pl"] == 0.0
    assert a["profit_factor"] is None
    assert a["imp021_held"] is True  # nothing leaked
    assert a["by_reason"] == {}


def test_aggregate_open_trade_excluded_from_closed_stats():
    rows = TODAY_ROWS + [{"symbol": "TSLA", "status": "OPEN", "pl": None,
                          "exit_reason": None, "entry_date": "2026-07-28", "bo": 0.0}]
    a = gm._aggregate(rows)
    assert a["taken"] == 4 and a["closed"] == 3 and a["open"] == 1
    assert a["net_pl"] == 31.64  # open trade contributes no P&L


# --- window aggregation (per-session breakdown) via a stubbed fetch ----------
def test_db_window_two_session_post_gate(monkeypatch):
    window_rows = [
        _row("AAPL", -20.0, "STOP", date="2026-07-27"),
        _row("QCOM", -52.52, "STOP", date="2026-07-27"),
        _row("META", 0.0, "EOD_FLATTEN", date="2026-07-27"),
    ] + TODAY_ROWS
    monkeypatch.setattr(gm, "_fetch_rows", lambda where, params: window_rows)
    d = gm._db_window("2026-07-27", "2026-07-28")
    assert d["n_sessions"] == 2
    assert d["sessions"] == [("2026-07-27", -72.52), ("2026-07-28", 31.64)]
    assert d["net_pl"] == round(-72.52 + 31.64, 2)
    assert d["taken"] == 6


# --- formatters don't crash & carry the key facts ---------------------------
def test_format_report_renders_today():
    txt = gm.format_report("2026-07-28", {"available": True, "vwap_skips": 0,
                                          "log_entries": 0, "rejects": 0},
                           gm._aggregate(TODAY_ROWS))
    assert "gate performance 2026-07-28" in txt
    assert "net $31.64" in txt
    assert "✅ held" in txt


def test_format_window_report_renders_and_shows_sessions():
    d = gm._aggregate(TODAY_ROWS)
    d["sessions"] = [("2026-07-27", -72.52), ("2026-07-28", 31.64)]
    d["n_sessions"] = 2
    txt = gm.format_window_report("2026-07-27", "2026-07-28", d)
    assert "cumulative gate performance 2026-07-27 → 2026-07-28" in txt
    assert "2 session(s)" in txt
    assert "PF 66.92" in txt
    assert "2026-07-27 $-72.52" in txt


def test_format_window_report_pf_na_when_none():
    d = gm._aggregate([_row("GOOG", 25.90, "EOD_FLATTEN")])
    d["sessions"] = [("2026-07-28", 25.90)]
    d["n_sessions"] = 1
    txt = gm.format_window_report("2026-07-28", "2026-07-28", d)
    assert "PF n/a" in txt
