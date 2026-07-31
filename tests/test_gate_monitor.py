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


# --- IMP-024: the log-file skip counters ------------------------------------
# Real lines from /var/log/ustradewisbot/bot.log on 2026-07-31, the session that
# exposed the defect: the monitor read journald and reported "skipped 0" while the
# bot had actually logged 25 VWAP skips across 4 symbols that day. The unit writes
# stdout to the FILE (StandardOutput=append:), so journald only holds systemd's own
# lifecycle lines.
REAL_LOG_20260731 = [
    "2026-07-31 09:39:48 EDT | ENTRY SKIPPED MSFT: entry 459.03 is +0.42% above session VWAP 457.09 (>0.25% — stretched fill, fades)\n",
    "2026-07-31 09:50:34 EDT | ENTRY SKIPPED MSFT: entry 460.04 is +0.49% above session VWAP 457.79 (>0.25% — stretched fill, fades)\n",
    "2026-07-31 10:32:26 EDT | ENTRY 41 BAC @ 61.9 (conf 61) order=4a8b5e99-3de3-457a-87ad-acb9862de95a\n",
    "2026-07-31 10:44:12 EDT | ENTRY 12 NVDA @ 197.89 (conf 62) order=d0aecba5-70fc-491b-8ac1-0d03a2242feb\n",
    "2026-07-31 10:45:20 EDT | ENTRY SKIPPED SE: entry 106.85 is +0.75% above session VWAP 106.05 (>0.25% — stretched fill, fades)\n",
    "2026-07-31 10:47:29 EDT | ENTRY SKIPPED NVDA: entry 198.18 is +0.32% above session VWAP 197.54 (>0.25% — stretched fill, fades)\n",
    "2026-07-31 10:51:47 EDT | ENTRY SKIPPED META: entry 551.74 is +0.55% above session VWAP 548.72 (>0.25% — stretched fill, fades)\n",
    "2026-07-31 10:51:48 EDT | ENTRY 3 SPY @ 742.41 (conf 61) order=efb4f04f-9f4e-4dcf-8b91-563a31cf72f5\n",
    "2026-07-31 13:37:16 EDT | STOP RAISED NVDA 194.89 -> 198.01 (live 199.73, entry 198.01)\n",
    # prior session, must NOT leak into today's counts (rotations are read together)
    "2026-07-30 10:12:01 EDT | ENTRY SKIPPED AMD: entry 180.00 is +0.90% above session VWAP 178.40 (>0.25% — stretched fill, fades)\n",
]


def test_count_log_lines_real_20260731_session():
    c = gm._count_log_lines(REAL_LOG_20260731, "2026-07-31")
    assert c["available"] is True
    assert c["vwap_skips"] == 5          # not 0 — the defect IMP-024 fixes
    assert c["log_entries"] == 3         # BAC, NVDA, SPY
    assert c["rejects"] == 0
    assert c["by_symbol"] == {"META": 1, "MSFT": 2, "NVDA": 1, "SE": 1}
    assert c["skipped_symbols"] == 4     # attempts re-fire; opportunities is the real number


def test_count_log_lines_excludes_other_sessions():
    """Rotated files are read as one stream — only the requested day may count."""
    c = gm._count_log_lines(REAL_LOG_20260731, "2026-07-30")
    assert c["vwap_skips"] == 1
    assert c["by_symbol"] == {"AMD": 1}
    assert c["log_entries"] == 0


def test_count_log_lines_empty_safe():
    c = gm._count_log_lines([], "2026-07-31")
    assert c["vwap_skips"] == 0 and c["by_symbol"] == {} and c["skipped_symbols"] == 0


def test_count_log_lines_counts_rejects():
    lines = ["2026-07-31 11:00:00 EDT | ENTRY REJECTED AAPL: daily loss halt\n"]
    c = gm._count_log_lines(lines, "2026-07-31")
    assert c["rejects"] == 1 and c["vwap_skips"] == 0 and c["log_entries"] == 0


def test_log_counts_reads_bot_log_file(tmp_path):
    (tmp_path / "bot.log").write_text("".join(REAL_LOG_20260731[:8]))
    (tmp_path / "bot.log.1").write_text("".join(REAL_LOG_20260731[8:]))
    c = gm._log_counts("2026-07-31", log_dir=str(tmp_path))
    assert c["source"] == "bot.log"
    assert c["vwap_skips"] == 5 and c["skipped_symbols"] == 4


def test_log_counts_falls_back_when_no_log_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(gm, "_journal_lines", lambda d: ["2026-07-31 09:39:48 EDT | ENTRY SKIPPED MSFT: entry 459.03 is +0.42% above session VWAP 457.09\n"])
    c = gm._log_counts("2026-07-31", log_dir=str(tmp_path / "missing"))
    assert c["source"] == "journald" and c["vwap_skips"] == 1


def test_count_log_window_per_session():
    w = gm._count_log_window(REAL_LOG_20260731, "2026-07-30", "2026-07-31")
    assert w["vwap_skips"] == 6
    assert w["sessions"] == [("2026-07-30", 1, 1), ("2026-07-31", 5, 4)]


def test_count_log_window_respects_bounds():
    w = gm._count_log_window(REAL_LOG_20260731, "2026-07-31", "2026-07-31")
    assert w["vwap_skips"] == 5 and [d for d, _, _ in w["sessions"]] == ["2026-07-31"]


def test_format_report_shows_real_skip_counts():
    j = gm._count_log_lines(REAL_LOG_20260731, "2026-07-31")
    j["source"] = "bot.log"
    txt = gm.format_report("2026-07-31", j, gm._aggregate(TODAY_ROWS))
    assert "skipped 5 stretched-above-VWAP entry attempts across 4 symbol(s)" in txt
    assert "MSFT×2" in txt
    assert "source: bot.log" in txt


def test_format_window_report_includes_skip_series():
    d = gm._aggregate(TODAY_ROWS)
    d["sessions"] = [("2026-07-30", 62.84), ("2026-07-31", 71.17)]
    d["n_sessions"] = 2
    j = gm._count_log_window(REAL_LOG_20260731, "2026-07-30", "2026-07-31")
    j["source"] = "bot.log"
    txt = gm.format_window_report("2026-07-30", "2026-07-31", d, j)
    assert "🚫 6 skipped entry attempts" in txt
    assert "2026-07-31 5 (4 sym)" in txt


def test_format_window_report_omits_skip_series_when_log_unavailable():
    d = gm._aggregate(TODAY_ROWS)
    d["sessions"] = [("2026-07-31", 71.17)]
    d["n_sessions"] = 1
    txt = gm.format_window_report("2026-07-31", "2026-07-31", d, {"available": False})
    assert "skipped entry attempts" not in txt
