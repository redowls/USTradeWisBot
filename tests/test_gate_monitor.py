"""Tests for scripts/gate_monitor.py — the IMP-021/022 gate-performance monitor.

Covers the pure aggregation + formatting helpers (no DB) against the REAL
2026-07-28 session that motivated IMP-023's cumulative `--since` view:
GOOG +25.90 (EOD), AAPL +6.22 (EOD), MSFT -0.48 (STOP break-even scratch),
all pure-MA (breakout_score 0) → 2W/1L, +$31.64. Plus the two-session
post-gate window (07-27 -$72.52 + 07-28 +$31.64).
"""

import pytest

from bot import config
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


# ---------------------------------------------------------------------------
# IMP-025 — VWAP-gate opportunity cost (blocked-candidate counterfactual)
#
# Built on the REAL 2026-08-03 session: 172 skip attempts across 17 distinct
# symbols, exactly 1 entry (AMZN 14:57, EOD_FLATTEN -$5.09). The replay of that
# session found the blocked set would have been mildly PROFITABLE (9W/8L,
# +0.22%/trade, ZERO stop-outs, META and NVDA reaching target) — the opposite of
# the 07-31 replay, which is the tape-dependence the audit exists to measure.
# ---------------------------------------------------------------------------

REAL_LOG_20260803 = [
    "2026-08-03 09:30:08 EDT | ENTRY SKIPPED META: entry 556.60 is +1.25% above session VWAP 549.72 (>0.25% — stretched fill, fades)",
    "2026-08-03 10:01:15 EDT | ENTRY SKIPPED NVDA: entry 202.47 is +1.33% above session VWAP 199.81 (>0.25% — stretched fill, fades)",
    "2026-08-03 10:10:44 EDT | ENTRY SKIPPED TSLA: entry 317.63 is +0.25% above session VWAP 316.84 (>0.25% — stretched fill, fades)",
    "2026-08-03 13:26:29 EDT | ENTRY SKIPPED AAPL: entry 307.47 is +0.58% above session VWAP 305.71 (>0.25% — stretched fill, fades)",
    # same candidate re-firing ~60s later, chased higher — must NOT become a 2nd candidate
    "2026-08-03 13:27:31 EDT | ENTRY SKIPPED AAPL: entry 307.36 is +0.54% above session VWAP 305.71 (>0.25% — stretched fill, fades)",
    "2026-08-03 13:28:35 EDT | ENTRY SKIPPED AAPL: entry 307.31 is +0.52% above session VWAP 305.72 (>0.25% — stretched fill, fades)",
    "2026-08-03 14:57:41 EDT | ENTRY 9 AMZN @ 284.52 (conf 61) order=b8fbc8b2-d397-41ee-86d9-a3ac1f69c2f9",
    # prior session must not leak across the rotation boundary
    "2026-07-31 09:39:48 EDT | ENTRY SKIPPED MSFT: entry 459.03 is +0.42% above session VWAP 457.11 (>0.25% — stretched fill, fades)",
]


def test_first_blocked_dedupes_refires_to_one_candidate_per_symbol():
    c = gm._first_blocked(REAL_LOG_20260803, "2026-08-03")
    assert [x["symbol"] for x in c] == ["AAPL", "META", "NVDA", "TSLA"]
    aapl = next(x for x in c if x["symbol"] == "AAPL")
    # the FIRST attempt (13:26:29 @ 307.47), not the later chased-higher re-fires
    assert aapl["time"] == "13:26:29"
    assert aapl["price"] == 307.47
    assert aapl["stretch_pct"] == 0.58
    assert aapl["vwap"] == 305.71


def test_first_blocked_excludes_other_sessions_and_entries():
    assert gm._first_blocked(REAL_LOG_20260803, "2026-07-31") == [
        {"symbol": "MSFT", "time": "09:39:48", "price": 459.03,
         "stretch_pct": 0.42, "vwap": 457.11}
    ]
    assert gm._first_blocked([], "2026-08-03") == []


def test_replay_geometry_uses_the_floor_stop_and_rr_ratio():
    stop, tp = gm._replay_geometry()
    assert stop == -config.MIN_STOP_PCT
    assert tp == pytest.approx(config.MIN_STOP_PCT * config.RR_RATIO)
    assert stop < 0 < tp  # sign convention the replay depends on


def _bars(*rows):
    return [{"time": t, "high": h, "low": lo, "close": c} for t, h, lo, c in rows]


def test_replay_blocked_reproduces_the_real_20260803_outcomes():
    """NVDA reached target, AAPL faded to the flatten, neither hit the stop."""
    cands = gm._first_blocked(REAL_LOG_20260803, "2026-08-03")
    cands = [c for c in cands if c["symbol"] in ("NVDA", "AAPL")]
    bars = {
        # NVDA 202.47 -> +2.23% (207.00) reached at 11:04, as it really did
        "NVDA": _bars(("10:02:00", 203.10, 202.20, 202.90),
                      ("11:04:00", 207.50, 202.90, 207.20),
                      ("15:55:00", 207.60, 206.90, 207.10)),
        # AAPL 307.47 -> drifts down, no stop touched, exits on the 15:55 flatten
        "AAPL": _bars(("13:27:00", 307.50, 306.90, 307.00),
                      ("15:55:00", 303.30, 302.99, 303.05)),
    }
    g = gm._replay_blocked(cands, bars, -1.5, 2.25)
    out = {r["symbol"]: r for r in g["results"]}
    assert out["NVDA"]["outcome"] == "TP"
    assert out["NVDA"]["exit_time"] == "11:04:00"
    assert out["NVDA"]["ret_pct"] == pytest.approx(2.25)
    assert out["AAPL"]["outcome"] == "EOD"
    assert out["AAPL"]["ret_pct"] == pytest.approx(-1.44, abs=0.01)
    assert g["by_outcome"] == {"EOD": 1, "TP": 1}
    assert g["wins"] == 1 and g["losses"] == 1
    # the day's real signature: a blocked set that would have MADE money
    assert g["avg_ret_pct"] > 0
    assert g["gate_paid"] is False


def test_replay_blocked_flags_gate_paid_when_blocked_set_would_have_lost():
    cands = [{"symbol": "XYZ", "time": "10:00:00", "price": 100.0,
              "stretch_pct": 2.0, "vwap": 98.0}]
    bars = {"XYZ": _bars(("10:01:00", 100.2, 98.4, 98.5))}  # low pierces the -1.5% stop
    g = gm._replay_blocked(cands, bars, -1.5, 2.25)
    assert g["results"][0]["outcome"] == "STOP"
    assert g["results"][0]["ret_pct"] == pytest.approx(-1.5)
    assert g["gate_paid"] is True
    assert g["by_outcome"] == {"STOP": 1}


def test_replay_blocked_takes_the_stop_when_one_bar_spans_both_legs():
    """Pessimistic tie-break — keeps the 'gate cost money' verdict a lower bound."""
    cands = [{"symbol": "XYZ", "time": "10:00:00", "price": 100.0,
              "stretch_pct": 1.0, "vwap": 99.0}]
    bars = {"XYZ": _bars(("10:01:00", 103.0, 98.0, 101.0))}  # spans stop AND target
    g = gm._replay_blocked(cands, bars, -1.5, 2.25)
    assert g["results"][0]["outcome"] == "STOP"


def test_replay_blocked_ignores_bars_before_the_skip_and_is_empty_safe():
    cands = [{"symbol": "XYZ", "time": "12:00:00", "price": 100.0,
              "stretch_pct": 1.0, "vwap": 99.0}]
    # a pre-skip crash must not be counted against a trade that did not exist yet
    bars = {"XYZ": _bars(("09:31:00", 100.0, 90.0, 95.0), ("12:01:00", 100.5, 99.9, 100.4))}
    g = gm._replay_blocked(cands, bars, -1.5, 2.25)
    assert g["results"][0]["outcome"] == "EOD"
    assert g["results"][0]["ret_pct"] == pytest.approx(0.4)

    empty = gm._replay_blocked([], {}, -1.5, 2.25)
    assert empty["candidates"] == 0 and empty["avg_ret_pct"] is None
    assert empty["gate_paid"] is None


def test_replay_blocked_marks_symbols_without_bars_as_no_data():
    cands = [{"symbol": "XYZ", "time": "10:00:00", "price": 100.0,
              "stretch_pct": 1.0, "vwap": 99.0}]
    g = gm._replay_blocked(cands, {}, -1.5, 2.25)
    assert g["results"][0]["outcome"] == "NO_DATA"
    assert g["replayed"] == 0 and g["no_data"] == 1
    assert g["avg_ret_pct"] is None


# ---------------------------------------------------------------------------
# IMP-045 — the counterfactual must price blocked candidates under the RATCHET
# the bot actually runs, not the static bracket it abandoned on 2026-08-24.
#
# Fixture is the REAL CRM path of 2026-08-31 (1-minute SIP bars, verbatim).
# CRM was VWAP-blocked at 11:23:49 @ 260.41 and ran to 262.19 (+0.68%, well past
# the +0.25R = +0.375% break-even trigger) before reversing to close at 257.635.
#   static bracket : never touches -1.5% or +2.25%  -> EOD  -0.89%
#   live ratchet   : break-even at 11:54, trail to 260.75 at 12:01, hit 12:33
#                    -> TRAIL +0.13%
# A 1.02pp swing on ONE name, and it moved the session verdict from
# "gate PAID -0.27%/trade" to a -0.06%/trade coin flip.
# ---------------------------------------------------------------------------

CRM_20260831 = _bars(
    ("11:24:00", 260.74, 260.4, 260.405),
    ("11:54:00", 261.705, 260.84, 261.16),    # peak 261.705 >= +0.25R -> stop to entry
    ("12:01:00", 261.8, 261.56, 261.73),      # close 261.73 -> trail to 260.75
    ("12:33:00", 260.82, 260.675, 260.82),    # low 260.675 takes the ratchet stop
    ("15:55:00", 258.48, 258.03, 258.085),    # where the static replay would have exited
    ("15:59:00", 258.07, 257.47, 257.635),
)
CRM_BLOCKED = [{"symbol": "CRM", "time": "11:23:49", "price": 260.41,
                "stretch_pct": 0.39, "vwap": 259.40}]


def test_replay_blocked_banks_crm_20260831_on_the_ratchet_not_the_eod_close():
    g = gm._replay_blocked(CRM_BLOCKED, {"CRM": CRM_20260831}, -1.5, 2.25)
    r = g["results"][0]
    assert r["outcome"] == "TRAIL"          # NOT the plan stop, and NOT EOD
    assert r["exit_time"] == "12:33:00"
    assert r["ret_pct"] == pytest.approx(0.131, abs=0.005)
    assert r["stop_raises"] == 2
    assert r["final_stop"] == pytest.approx(260.75, abs=0.01)
    # the excursion that armed it is real (+0.53% by the exit bar, past +0.375%)
    assert r["mfe_pct"] == pytest.approx(0.53, abs=0.02)
    assert g["gate_paid"] is False           # blocked set made money -> gate COST


def test_replay_blocked_static_bracket_would_have_scored_crm_as_a_loss():
    """The bug this fixes: with the ratchet off, CRM drifts to a red 15:55 close."""
    import bot.config as cfg
    prev = cfg.TRAILING_STOP_ENABLED
    cfg.TRAILING_STOP_ENABLED = False        # exits.compute_trailed_stop -> None
    try:
        g = gm._replay_blocked(CRM_BLOCKED, {"CRM": CRM_20260831}, -1.5, 2.25)
    finally:
        cfg.TRAILING_STOP_ENABLED = prev
    r = g["results"][0]
    assert r["outcome"] == "EOD"
    assert r["ret_pct"] == pytest.approx(-0.893, abs=0.005)
    assert r["stop_raises"] == 0 and r["final_stop"] is None
    assert g["gate_paid"] is True            # the inverted verdict, verbatim


def test_replay_blocked_labels_plan_stop_and_ratchet_stop_apart():
    """IMP-041's lesson: a -1R plan stop and a break-even scratch are not one bucket."""
    plan = gm._replay_blocked(
        [{"symbol": "P", "time": "10:00:00", "price": 100.0, "stretch_pct": 1.0, "vwap": 99.0}],
        {"P": _bars(("10:01:00", 100.1, 98.4, 98.5))}, -1.5, 2.25)
    assert plan["results"][0]["outcome"] == "STOP"
    assert plan["results"][0]["ret_pct"] == pytest.approx(-1.5)
    assert plan["results"][0]["stop_raises"] == 0
    assert plan["by_outcome"] == {"STOP": 1}


def test_replay_blocked_raise_cannot_protect_the_bar_that_produced_it():
    """No look-ahead: a bar that spikes past the trigger AND collapses is a plan stop.

    Entry 100 (1R = 1.5). The bar prints 101.0 (+0.67R, past the 0.25R trigger)
    and 98.4 in the same minute. Order within a bar is unknowable, so the stop in
    force stays the plan stop -1.5% and the exit is a full -1R, never a scratch.
    """
    g = gm._replay_blocked(
        [{"symbol": "Q", "time": "10:00:00", "price": 100.0, "stretch_pct": 1.0, "vwap": 99.0}],
        {"Q": _bars(("10:01:00", 101.0, 98.4, 98.6))}, -1.5, 2.25)
    assert g["results"][0]["outcome"] == "STOP"
    assert g["results"][0]["ret_pct"] == pytest.approx(-1.5)


def test_replay_blocked_tracks_the_live_ratchet_config():
    """Parity guard: the replay reads exits.compute_trailed_stop, so a ratchet
    config change (e.g. whatever the 09-08 IMP-040 verdict decides) propagates
    here automatically instead of silently leaving the audit on stale geometry."""
    import bot.config as cfg
    prev = (cfg.BREAKEVEN_TRIGGER_R, cfg.TRAIL_TRIGGER_R)
    # 0.9R = +1.35%; CRM's +0.53% excursion cannot arm either stage
    cfg.BREAKEVEN_TRIGGER_R = cfg.TRAIL_TRIGGER_R = 0.9
    try:
        g = gm._replay_blocked(CRM_BLOCKED, {"CRM": CRM_20260831}, -1.5, 2.25)
    finally:
        cfg.BREAKEVEN_TRIGGER_R, cfg.TRAIL_TRIGGER_R = prev
    assert g["results"][0]["outcome"] == "EOD"
    assert g["results"][0]["stop_raises"] == 0


def test_format_gate_cost_reports_the_ratchet_and_keeps_the_lower_bound_claim():
    txt = "\n".join(gm.format_gate_cost(
        gm._replay_blocked(CRM_BLOCKED, {"CRM": CRM_20260831}, -1.5, 2.25)))
    assert "ratchet" in txt                  # header names the real geometry
    assert "ratchet armed on 1/1 replayed (2 raises)" in txt
    assert "lower bound" in txt              # now actually true (IMP-045)


def test_format_gate_cost_renders_verdict_and_degrades_cleanly():
    cands = gm._first_blocked(REAL_LOG_20260803, "2026-08-03")
    bars = {"NVDA": _bars(("10:02:00", 207.50, 202.20, 207.20))}
    txt = "\n".join(gm.format_gate_cost(gm._replay_blocked(cands, bars, -1.5, 2.25)))
    assert "opportunity cost" in txt
    assert "gate COST" in txt          # NVDA made money -> gate cost money
    assert "lower bound" in txt

    assert "no candidates were blocked" in "\n".join(
        gm.format_gate_cost(gm._replay_blocked([], {}, -1.5, 2.25)))
    assert "unavailable" in "\n".join(
        gm.format_gate_cost({"available": False, "error": "boom"}))


def test_format_report_includes_gate_cost_only_when_supplied():
    j = gm._count_log_lines(REAL_LOG_20260803, "2026-08-03")
    d = gm._aggregate([{"symbol": "AMZN", "status": "CLOSED", "pl": -5.09,
                        "exit_reason": "EOD_FLATTEN", "entry_date": "2026-08-03", "bo": 0.0}])
    assert "opportunity cost" not in gm.format_report("2026-08-03", j, d)
    g = gm._replay_blocked(gm._first_blocked(REAL_LOG_20260803, "2026-08-03"),
                           {"NVDA": _bars(("10:02:00", 207.5, 202.2, 207.2))}, -1.5, 2.25)
    assert "opportunity cost" in gm.format_report("2026-08-03", j, d, g)


def test_first_blocked_survives_newest_first_rotation_order():
    """_read_log_lines yields bot.log BEFORE bot.log.1, so a session split across a
    rotation arrives newest-chunk-first. Selecting by arrival order picks the last
    attempt of the day — the real 2026-08-03 defect (META 14:55 @ 593.53 replayed
    instead of the 09:30 @ 556.60 the bot actually wanted in at)."""
    newest_chunk = [
        "2026-08-03 14:55:33 EDT | ENTRY SKIPPED META: entry 593.53 is +1.10% above session VWAP 587.07 (>0.25% — stretched fill, fades)",
    ]
    older_chunk = [
        "2026-08-03 09:30:08 EDT | ENTRY SKIPPED META: entry 556.60 is +1.25% above session VWAP 549.72 (>0.25% — stretched fill, fades)",
    ]
    c = gm._first_blocked(newest_chunk + older_chunk, "2026-08-03")
    assert len(c) == 1
    assert c[0]["time"] == "09:30:08"
    assert c[0]["price"] == 556.60
    # and the same answer regardless of which chunk is streamed first
    assert gm._first_blocked(older_chunk + newest_chunk, "2026-08-03") == c


# --- IMP-049: the counterfactual speaks the doctrine ------------------------
# The REAL 2026-09-04 blocked set, verbatim from
# `python -m scripts.gate_monitor --date 2026-09-04 --replay-skips`.
# Five candidates the VWAP gate refused while it admitted two trades that lost
# -$40.36 between them. The sign-based count calls this set 4W/1L (80% win);
# the doctrine calls it WIN 1 / SCRATCH 2 / FAIL 2 (true win rate 20%), because
# three of the four "wins" banked between -0.11R and +0.24R.
REPLAYED_20260904 = [
    {"symbol": "TSM", "time": "09:30:10", "price": 417.01, "outcome": "TRAIL",
     "ret_pct": 1.712, "stop_raises": 4},
    {"symbol": "AMD", "time": "12:18:53", "price": 473.22, "outcome": "TRAIL",
     "ret_pct": 0.366, "stop_raises": 3},
    {"symbol": "INTC", "time": "10:20:14", "price": 94.53, "outcome": "TRAIL",
     "ret_pct": 0.360, "stop_raises": 2},
    {"symbol": "AMZN", "time": "15:07:26", "price": 257.95, "outcome": "EOD",
     "ret_pct": 0.299, "stop_raises": 1},
    {"symbol": "BAC", "time": "14:21:36", "price": 62.78, "outcome": "EOD",
     "ret_pct": -0.159, "stop_raises": 0},
]


def test_doctrine_rows_score_the_real_20260904_blocked_set():
    """The regression: 4 of 5 blocked candidates were scratches, not winners."""
    from bot import doctrine

    rows = gm._doctrine_rows(REPLAYED_20260904, -1.5)
    labels = {r["symbol"]: doctrine.classify(r) for r in rows}
    assert labels == {"TSM": "WIN",        # +1.14R — the only paid thesis
                      "AMD": "FAIL",       # ratcheted stop banking +0.24R
                      "INTC": "FAIL",      # ratcheted stop banking +0.24R
                      "AMZN": "SCRATCH",   # flatten at +0.20R
                      "BAC": "SCRATCH"}    # flatten at -0.11R
    d = doctrine.summarize(rows)
    assert (d["win"], d["scratch"], d["fail"]) == (1, 2, 2)
    assert d["fail_kinds"] == {"full-1R": 0, "break-even": 2, "faded": 0}
    assert d["true_win_rate"] == 20.0
    assert d["headline_win_rate"] == 80.0   # the number the tool used to print alone
    assert d["stop_rate"] == 60.0
    assert d["avg_r"] == pytest.approx(0.344, abs=0.002)


def test_doctrine_rows_drop_unpriced_candidates_and_are_empty_safe():
    rows = gm._doctrine_rows(
        [{"symbol": "XYZ", "price": 100.0, "outcome": "NO_DATA", "ret_pct": None}], -1.5)
    assert rows == []
    assert gm._doctrine_rows([], -1.5) == []


def test_replay_blocked_reports_the_doctrine_beside_the_headline():
    """A trailed stop that banks a fraction of 1R is headline-green, doctrine-FAIL."""
    cands = [{"symbol": "XYZ", "time": "10:00:00", "price": 100.0,
              "stretch_pct": 1.0, "vwap": 99.0}]
    # runs just past the +0.25R trigger (1R = 1.5), arms the ratchet, then gives
    # the whole excursion back to the raised stop — the live book's commonest shape
    bars = _bars(("10:01:00", 100.5, 99.9, 100.40),
                 ("10:02:00", 100.4, 99.0, 99.10))
    g = gm._replay_blocked(cands, {"XYZ": bars}, -1.5, 2.25)
    assert g["results"][0]["outcome"] == "TRAIL"
    assert g["results"][0]["ret_pct"] > 0          # headline: a "win"
    assert g["wins"] == 1
    assert g["doctrine"]["win"] == 0               # doctrine: not a win
    assert g["doctrine"]["fail"] == 1
    assert g["doctrine"]["true_win_rate"] == 0.0
    assert g["doctrine"]["headline_win_rate"] == 100.0
    assert g["avg_r"] == g["doctrine"]["avg_r"]


def test_replay_blocked_doctrine_calls_a_plan_stop_a_full_1r_fail():
    cands = [{"symbol": "XYZ", "time": "10:00:00", "price": 100.0,
              "stretch_pct": 2.0, "vwap": 98.0}]
    g = gm._replay_blocked(cands, {"XYZ": _bars(("10:01:00", 100.2, 98.4, 98.5))},
                           -1.5, 2.25)
    assert g["results"][0]["outcome"] == "STOP"
    assert g["doctrine"]["fail_kinds"]["full-1R"] == 1
    assert g["doctrine"]["true_win_rate"] == 0.0
    assert g["gate_paid"] is True                  # expectancy still sets the verdict


def test_replay_blocked_doctrine_awards_the_target_a_win():
    cands = gm._first_blocked(REAL_LOG_20260803, "2026-08-03")
    cands = [c for c in cands if c["symbol"] == "NVDA"]
    g = gm._replay_blocked(cands, {"NVDA": _bars(("10:02:00", 207.5, 202.2, 207.2))},
                           -1.5, 2.25)
    assert g["results"][0]["outcome"] == "TP"
    assert g["doctrine"]["win"] == 1
    assert g["doctrine"]["true_win_rate"] == 100.0


def test_replay_blocked_empty_and_unpriced_sets_still_carry_a_doctrine_block():
    empty = gm._replay_blocked([], {}, -1.5, 2.25)
    assert empty["doctrine"]["trades"] == 0
    assert empty["avg_r"] is None
    nodata = gm._replay_blocked(
        [{"symbol": "XYZ", "time": "10:00:00", "price": 100.0,
          "stretch_pct": 1.0, "vwap": 99.0}], {}, -1.5, 2.25)
    assert nodata["results"][0]["outcome"] == "NO_DATA"
    assert nodata["doctrine"]["trades"] == 0


def test_format_gate_cost_prints_true_win_rate_beside_headline():
    txt = "\n".join(gm.format_gate_cost(
        gm._replay_blocked(CRM_BLOCKED, {"CRM": CRM_20260831}, -1.5, 2.25)))
    assert "if taken: headline" in txt        # the sign-based count is now LABELLED
    assert "doctrine: WIN" in txt
    assert "true win rate" in txt and "headline" in txt
    assert "R" in txt
    assert "a blocked set of scratches is not a blocked set of winners" in txt
