"""Gate-performance monitor: how the IMP-021 (breakout veto) and IMP-022 (VWAP)
entry gates performed on a given trading session.

  python -m scripts.gate_monitor                 # today (ET), print only
  python -m scripts.gate_monitor --date 2026-07-27
  python -m scripts.gate_monitor --since 2026-07-27          # cumulative post-gate scorecard
  python -m scripts.gate_monitor --since 2026-07-27 --date 2026-07-31   # bounded window
  python -m scripts.gate_monitor --telegram --out /path/result.json

Combines two sources:
  * /var/log/ustradewisbot/bot.log (+ its rotations) — counts the IMP-022 VWAP
    skips actually fired ("above session VWAP") plus entries/rejects for context.
    The unit writes stdout to that FILE (`StandardOutput=append:` in
    deploy/ustradewisbot.service), so journald only ever holds systemd's own
    lifecycle lines — reading journald reported "skipped 0" on every session
    (IMP-024). journald stays as a fallback if the log dir is missing.
  * dbo.trades / dbo.signals — the trades that got THROUGH the gates that day,
    their win/lose/exit-reason split, and a check that IMP-021 held (every taken
    trade is pure-MA, breakout_score == 0; a strong breakout would mean the veto
    leaked).

Honest limit: the IMP-021 veto suppresses a signal inside signals._classify
without a log line, so the number of breakout candidates it blocked is not
directly countable — we verify it held (nothing strong-breakout got through)
rather than count what it stopped.
"""

from __future__ import annotations

import glob
import gzip
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from bot import config, db, notify

SERVICE = "ustradewisbot.service"
LOG_DIR = "/var/log/ustradewisbot"

# "2026-07-31 09:39:48 EDT | ENTRY SKIPPED MSFT: entry 459.03 is +0.42% above ..."
_SKIP_RE = re.compile(r"ENTRY SKIPPED ([A-Z][A-Z.\-]*)\s*:")

# Same line, fully destructured — the price/VWAP are what make the skip replayable.
_SKIP_DETAIL_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) \S+ \| ENTRY SKIPPED ([A-Z][A-Z.\-]*): "
    r"entry ([\d.]+) is \+([\d.]+)% above session VWAP ([\d.]+)"
)


def _arg(argv, flag, default):
    return argv[argv.index(flag) + 1] if flag in argv else default


def _count_log_lines(lines, date_str: str) -> dict:
    """Pure: count IMP-022 VWAP skips / entries / rejects among ``lines`` for one day.

    Every bot line is prefixed ``YYYY-MM-DD HH:MM:SS TZ | ...`` (engine._log), so the
    date prefix is what selects the session — the caller may hand over several
    rotations at once. ``by_symbol`` matters more than the raw attempt count: the
    gate re-fires on the same candidate every ~60s cycle, so 25 attempts can be
    only 4 distinct opportunities skipped.
    """
    vwap = entries = rejects = 0
    by_symbol: dict[str, int] = {}
    for ln in lines:
        if not ln.startswith(date_str):
            continue
        if "above session VWAP" in ln:
            vwap += 1
            m = _SKIP_RE.search(ln)
            if m:
                by_symbol[m.group(1)] = by_symbol.get(m.group(1), 0) + 1
        elif "ENTRY REJECTED" in ln:
            rejects += 1
        elif " ENTRY " in ln and "order=" in ln:
            entries += 1
    return {"available": True, "vwap_skips": vwap, "log_entries": entries,
            "rejects": rejects, "by_symbol": dict(sorted(by_symbol.items())),
            "skipped_symbols": len(by_symbol)}


def _read_log_lines(log_dir: str = LOG_DIR):
    """Yield every line of bot.log and its rotations (plain + .gz), newest dir order."""
    paths = [os.path.join(log_dir, "bot.log")]
    paths += sorted(glob.glob(os.path.join(log_dir, "bot.log.*")))
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            opener = gzip.open if path.endswith(".gz") else open
            with opener(path, "rt", errors="replace") as fh:
                yield from fh
        except OSError:  # unreadable rotation must not kill the monitor
            continue


def _journal_lines(date_str: str):
    """Fallback source: journald (holds only lifecycle lines on a normal install)."""
    out = subprocess.run(
        ["journalctl", "-u", SERVICE, "--no-pager", "-o", "cat",
         "--since", f"{date_str} 00:00:00", "--until", f"{date_str} 23:59:59"],
        capture_output=True, text=True, timeout=60,
    ).stdout
    return out.splitlines()


def _log_counts(date_str: str, log_dir: str = LOG_DIR) -> dict:
    """Count IMP-022 VWAP skips / entries / rejects in the bot's own log for the day."""
    try:
        if os.path.isdir(log_dir):
            counts = _count_log_lines(_read_log_lines(log_dir), date_str)
            counts["source"] = "bot.log"
            return counts
        counts = _count_log_lines(_journal_lines(date_str), date_str)
        counts["source"] = "journald"
        return counts
    except Exception as exc:  # noqa: BLE001 - monitor must not crash on log access
        return {"available": False, "error": str(exc)}


def _first_blocked(lines, date_str: str) -> list[dict]:
    """Pure: the FIRST VWAP-blocked attempt per symbol on ``date_str``.

    The gate re-fires on the same candidate every ~60s cycle, so the raw attempt
    count is not a candidate count. The *first* attempt is the moment the bot
    actually wanted in, and is therefore the only honest entry price to replay
    the counterfactual from (later attempts are the same idea, chased higher).

    Selection is by TIMESTAMP, never by iteration order: ``_read_log_lines``
    yields ``bot.log`` before its older rotations, so a session split across a
    rotation arrives newest-chunk-first. Trusting arrival order silently picks
    the *last* attempt of the day and replays a price the bot never wanted in at
    (2026-08-03: META 14:55 @ 593.53 instead of 09:30 @ 556.60).
    """
    first: dict[str, dict] = {}
    for ln in lines:
        m = _SKIP_DETAIL_RE.match(ln)
        if not m or m.group(1) != date_str:
            continue
        sym, ts = m.group(3), m.group(2)
        prev = first.get(sym)
        if prev is not None and prev["time"] <= ts:
            continue
        first[sym] = {"symbol": sym, "time": ts, "price": float(m.group(4)),
                      "stretch_pct": float(m.group(5)), "vwap": float(m.group(6))}
    return [first[s] for s in sorted(first)]


def _replay_geometry() -> tuple[float, float]:
    """Bracket the blocked candidates would have been given, as (stop%, target%).

    Uses the MIN_STOP_PCT floor rather than 3xATR because ATR is not recoverable
    from the log. That is deliberately conservative *in favour of the gate*: real
    stops are >= the floor, so a floor-width stop gets hit at least as often as
    the real one, which can only make the blocked set look worse than it was.
    A verdict of "the gate cost money" computed this way is therefore a lower bound.
    """
    return -float(config.MIN_STOP_PCT), float(config.MIN_STOP_PCT) * float(config.RR_RATIO)


def _replay_blocked(candidates: list[dict], bars_by_symbol: dict, stop_pct: float,
                    tp_pct: float, flatten: str = "15:55") -> dict:
    """Pure: what the VWAP-blocked candidates WOULD have done if they'd been taken.

    ``bars_by_symbol`` maps symbol -> [{"time": "HH:MM:SS", "high", "low", "close"}]
    for the session, oldest first. Walks each candidate forward from its skip
    timestamp under the real exit structure (stop / target / 15:55 flatten).
    When a bar spans both the stop and the target the STOP is taken — pessimistic,
    matching the same bias as :func:`_replay_geometry`.
    """
    results = []
    for c in candidates:
        rows = [b for b in (bars_by_symbol.get(c["symbol"]) or []) if b["time"] >= c["time"]]
        if not rows:
            results.append({**c, "outcome": "NO_DATA", "ret_pct": None,
                            "exit_time": None, "mfe_pct": None, "mae_pct": None})
            continue
        entry = c["price"]
        stop, target = entry * (1 + stop_pct / 100.0), entry * (1 + tp_pct / 100.0)
        outcome, exit_px, exit_time = "EOD", rows[-1]["close"], rows[-1]["time"]
        mfe = mae = 0.0
        for b in rows:
            mfe = max(mfe, (b["high"] - entry) / entry * 100.0)
            mae = min(mae, (b["low"] - entry) / entry * 100.0)
            if b["low"] <= stop:
                outcome, exit_px, exit_time = "STOP", stop, b["time"]
                break
            if b["high"] >= target:
                outcome, exit_px, exit_time = "TP", target, b["time"]
                break
            if b["time"] >= flatten:
                outcome, exit_px, exit_time = "EOD", b["close"], b["time"]
                break
        results.append({**c, "outcome": outcome, "exit_time": exit_time,
                        "ret_pct": round((exit_px - entry) / entry * 100.0, 3),
                        "mfe_pct": round(mfe, 2), "mae_pct": round(mae, 2)})

    scored = [r for r in results if r["ret_pct"] is not None]
    wins = sum(1 for r in scored if r["ret_pct"] > 0)
    by_outcome: dict[str, int] = {}
    for r in results:
        by_outcome[r["outcome"]] = by_outcome.get(r["outcome"], 0) + 1
    total = round(sum(r["ret_pct"] for r in scored), 2)
    avg = round(total / len(scored), 3) if scored else None
    return {
        "available": True, "candidates": len(results), "replayed": len(scored),
        "no_data": len(results) - len(scored),
        "wins": wins, "losses": len(scored) - wins,
        "by_outcome": dict(sorted(by_outcome.items())),
        "sum_ret_pct": total, "avg_ret_pct": avg,
        # Sign convention: the gate PAID when the set it blocked would have lost.
        "gate_paid": None if avg is None else avg <= 0,
        "stop_pct": stop_pct, "tp_pct": round(tp_pct, 3),
        "results": results,
    }


def _bars_to_rows(df, date_str: str) -> list[dict]:
    """Adapter: one symbol's ET-indexed OHLCV frame -> pure-replay row dicts."""
    rows = []
    for ts, r in df.iterrows():
        if ts.strftime("%Y-%m-%d") != date_str:
            continue
        rows.append({"time": ts.strftime("%H:%M:%S"), "high": float(r["high"]),
                     "low": float(r["low"]), "close": float(r["close"])})
    return rows


def _gate_cost(date_str: str, log_dir: str = LOG_DIR) -> dict:
    """Opportunity-cost audit of the IMP-022 VWAP gate for one session.

    Best-effort and strictly read-only: needs market data, so it never runs
    unless asked for (``--replay-skips``) and never crashes the monitor.
    """
    try:
        lines = _read_log_lines(log_dir) if os.path.isdir(log_dir) else _journal_lines(date_str)
        candidates = _first_blocked(lines, date_str)
        if not candidates:
            return {"available": True, "candidates": 0, "replayed": 0, "no_data": 0,
                    "wins": 0, "losses": 0, "by_outcome": {}, "sum_ret_pct": 0.0,
                    "avg_ret_pct": None, "gate_paid": None, "results": []}
        from bot import data as bot_data  # local import: keeps the DB-only path light
        frames = bot_data.get_bars_for_symbols(
            [c["symbol"] for c in candidates], n_bars=390, timeframe="1Min")
        bars = {s: _bars_to_rows(df, date_str) for s, df in frames.items()
                if df is not None and not df.empty}
        stop_pct, tp_pct = _replay_geometry()
        return _replay_blocked(candidates, bars, stop_pct, tp_pct)
    except Exception as exc:  # noqa: BLE001 - audit must never break the monitor
        return {"available": False, "error": str(exc)}


def format_gate_cost(g: dict) -> list[str]:
    """Render the blocked-candidate counterfactual as report lines."""
    if not g.get("available"):
        return ["", f"IMP-022 opportunity cost: (unavailable: {g.get('error')})"]
    if not g.get("candidates"):
        return ["", "IMP-022 opportunity cost: no candidates were blocked this session."]
    lines = ["", f"IMP-022 opportunity cost — replay of the {g['candidates']} blocked "
                 f"candidate(s) under the real bracket "
                 f"({g.get('stop_pct', 0):.2f}% stop / +{g.get('tp_pct', 0):.2f}% target):"]
    if not g["replayed"]:
        lines.append("  (no bars available to replay)")
        return lines
    avg = g["avg_ret_pct"]
    lines.append(f"  if taken: {g['wins']}W/{g['losses']}L   avg {avg:+.2f}% per trade   "
                 f"sum {g['sum_ret_pct']:+.2f}%")
    lines.append("  outcomes: " + ", ".join(f"{k} {v}" for k, v in g["by_outcome"].items()))
    lines.append(f"  verdict: {'✅ gate PAID' if g['gate_paid'] else '⚠️ gate COST'} "
                 f"— blocked set would have {'lost' if g['gate_paid'] else 'made'} money "
                 f"({avg:+.2f}%/trade; floor-stop replay, so this is a lower bound)")
    worst = sorted((r for r in g["results"] if r["ret_pct"] is not None),
                   key=lambda r: r["ret_pct"])
    if worst:
        best = worst[-1]
        lines.append(f"  best blocked: {best['symbol']} {best['ret_pct']:+.2f}% ({best['outcome']})"
                     f"   worst blocked: {worst[0]['symbol']} {worst[0]['ret_pct']:+.2f}% "
                     f"({worst[0]['outcome']})")
    lines.append("  Read: one session is noise — the gate is tape-dependent by design. "
                 "Judge it on the running series, not tonight.")
    return lines


_ROWS_SQL = """
    WITH s AS (
      SELECT trade_id, breakout_score,
             ROW_NUMBER() OVER (PARTITION BY trade_id ORDER BY ts) rn
      FROM dbo.signals WHERE trade_id IS NOT NULL)
    SELECT t.symbol, t.status, t.realized_pl, t.exit_reason, t.entry_time, s.breakout_score
    FROM dbo.trades t
    LEFT JOIN s ON s.trade_id = t.trade_id AND s.rn = 1
    WHERE {where}
    ORDER BY t.entry_time
"""


def _fetch_rows(where: str, params: tuple) -> list[dict]:
    """Load gate-relevant trade rows matching ``where`` (parameterised)."""
    cn = db.connect()
    cur = cn.cursor()
    cur.execute(_ROWS_SQL.format(where=where), *params)
    rows = [{"symbol": r.symbol, "status": r.status,
             "pl": float(r.realized_pl) if r.realized_pl is not None else None,
             "exit_reason": r.exit_reason,
             "entry_date": r.entry_time.date().isoformat() if r.entry_time is not None else None,
             "bo": float(r.breakout_score) if r.breakout_score is not None else None}
            for r in cur.fetchall()]
    cn.close()
    return rows


def _aggregate(rows: list[dict]) -> dict:
    """Pure win/lose/exit/PF/IMP-021-hold summary of ``rows`` (empty-safe)."""
    closed = [r for r in rows if r["pl"] is not None]
    wins = sum(1 for r in closed if r["pl"] > 0)
    losses = len(closed) - wins
    gross_win = sum(r["pl"] for r in closed if r["pl"] > 0)
    gross_loss = -sum(r["pl"] for r in closed if r["pl"] < 0)
    strong_bo = [r for r in rows if r["bo"] is not None and r["bo"] >= config.BREAKOUT_FADE_CEILING]
    by_reason: dict[str, dict] = {}
    for r in closed:
        b = by_reason.setdefault(r["exit_reason"] or "OPEN", {"n": 0, "pl": 0.0})
        b["n"] += 1
        b["pl"] = round(b["pl"] + r["pl"], 2)
    return {
        "taken": len(rows),
        "closed": len(closed),
        "open": len(rows) - len(closed),
        "wins": wins,
        "losses": losses,
        "win_pct": round(100.0 * wins / len(closed), 1) if closed else 0.0,
        "net_pl": round(sum(r["pl"] for r in closed), 2),
        # PF is None ("n/a") when there are no losing trades (or no closed trades) —
        # honest and JSON-safe (no Infinity); mirrors scripts/report.py's "n/a".
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "by_reason": by_reason,
        "imp021_held": len(strong_bo) == 0,
        "strong_breakout_leaks": [r["symbol"] for r in strong_bo],
        "symbols": [r["symbol"] for r in rows],
    }


def _db_session(date_str: str) -> dict:
    """Trades that got through the gates on ``date_str`` + the IMP-021 hold check."""
    return _aggregate(_fetch_rows("CAST(t.entry_time AS DATE) = ?", (date_str,)))


def _db_window(since_str: str, until_str: str) -> dict:
    """Cumulative gate scorecard over the inclusive [since, until] session range.

    Same shape as :func:`_db_session` plus a per-session ``sessions`` net-P&L
    breakdown and ``n_sessions`` count — the post-IMP-021/022 era view the daily
    monitor can't give, so the keep/tune call reads one running scorecard instead
    of hand-summing daily runs.
    """
    rows = _fetch_rows("CAST(t.entry_time AS DATE) BETWEEN ? AND ?", (since_str, until_str))
    agg = _aggregate(rows)
    by_day: dict[str, float] = {}
    for r in rows:
        if r["pl"] is None or r["entry_date"] is None:
            continue
        by_day[r["entry_date"]] = round(by_day.get(r["entry_date"], 0.0) + r["pl"], 2)
    agg["sessions"] = sorted(by_day.items())
    agg["n_sessions"] = len(by_day)
    return agg


def _count_log_window(lines, since_str: str, until_str: str) -> dict:
    """Pure: per-session VWAP-skip counts over the inclusive [since, until] range.

    ISO dates compare lexicographically, so the prefix of each line is enough.
    """
    by_date: dict[str, int] = {}
    syms: dict[str, set] = {}
    for ln in lines:
        if "above session VWAP" not in ln or len(ln) < 10:
            continue
        day = ln[:10]
        if not (since_str <= day <= until_str):
            continue
        by_date[day] = by_date.get(day, 0) + 1
        m = _SKIP_RE.search(ln)
        if m:
            syms.setdefault(day, set()).add(m.group(1))
    return {"available": True,
            "vwap_skips": sum(by_date.values()),
            "sessions": [(d, n, len(syms.get(d, ()))) for d, n in sorted(by_date.items())]}


def _log_window(since_str: str, until_str: str, log_dir: str = LOG_DIR) -> dict:
    """Per-session VWAP-skip counts from the bot's own log (best-effort)."""
    try:
        if not os.path.isdir(log_dir):
            return {"available": False, "error": f"no log dir {log_dir}"}
        w = _count_log_window(_read_log_lines(log_dir), since_str, until_str)
        w["source"] = "bot.log"
        return w
    except Exception as exc:  # noqa: BLE001 - monitor must not crash on log access
        return {"available": False, "error": str(exc)}


def format_report(date_str: str, j: dict, d: dict, g: dict | None = None) -> str:
    lines = [
        f"🚦 USTradeWisBot — gate performance {date_str}",
        "",
        "IMP-022 VWAP gate:",
    ]
    if j.get("available"):
        by_sym = j.get("by_symbol") or {}
        lines.append(f"  🚫 skipped {j['vwap_skips']} stretched-above-VWAP entry attempts "
                     f"across {j.get('skipped_symbols', len(by_sym))} symbol(s)")
        if by_sym:
            lines.append("     " + ", ".join(f"{s}×{n}" for s, n in by_sym.items()))
        lines.append(f"  entries logged: {j['log_entries']}   rejects: {j['rejects']}"
                     f"   (source: {j.get('source', '?')})")
    else:
        lines.append(f"  (log unavailable: {j.get('error')})")
    lines += [
        "",
        "IMP-021 breakout veto:",
        f"  {'✅ held' if d['imp021_held'] else '⚠️ LEAK'} — "
        f"{'0 strong-breakout trades got through' if d['imp021_held'] else 'leaked: ' + ', '.join(d['strong_breakout_leaks'])}",
        "",
        f"Trades through the gates: {d['taken']}  (closed {d['closed']}, open {d['open']})",
        f"  ✅ {d['wins']} wins / ❌ {d['losses']} losses   win rate {d['win_pct']}%   "
        f"net ${d['net_pl']:,.2f}",
    ]
    if d["by_reason"]:
        lines.append("  by exit: " + ", ".join(
            f"{k} {v['n']} (${v['pl']:,.2f})" for k, v in sorted(d["by_reason"].items())))
    if d["symbols"]:
        lines.append("  symbols: " + ", ".join(d["symbols"]))
    if g is not None:
        lines += format_gate_cost(g)
    lines += [
        "",
        "Read: fewer, higher-quality trades = gates working. Historical baseline "
        "≈ 3–6 trades/day at ~38% win. One session is noise — trend matters.",
    ]
    return "\n".join(lines)


def format_window_report(since_str: str, until_str: str, d: dict, j: dict | None = None) -> str:
    pf = d.get("profit_factor")
    pf_s = "n/a" if pf is None else f"{pf:.2f}"
    lines = [
        f"🚦 USTradeWisBot — cumulative gate performance {since_str} → {until_str}",
        f"  (post-IMP-021/022 era · {d['n_sessions']} session(s))",
        "",
        "IMP-021 breakout veto: "
        + ("✅ held — 0 strong-breakout trades got through" if d["imp021_held"]
           else "⚠️ LEAK: " + ", ".join(d["strong_breakout_leaks"])),
        "",
        f"Trades through the gates: {d['taken']}  (closed {d['closed']}, open {d['open']})",
        f"  ✅ {d['wins']} wins / ❌ {d['losses']} losses   win rate {d['win_pct']}%   "
        f"net ${d['net_pl']:,.2f}   PF {pf_s}",
    ]
    if d["by_reason"]:
        lines.append("  by exit: " + ", ".join(
            f"{k} {v['n']} (${v['pl']:,.2f})" for k, v in sorted(d["by_reason"].items())))
    if d.get("sessions"):
        lines.append("  by session: " + ", ".join(
            f"{day} ${net:,.2f}" for day, net in d["sessions"]))
    if j and j.get("available"):
        lines += ["", f"IMP-022 VWAP gate: 🚫 {j['vwap_skips']} skipped entry attempts "
                      f"(source: {j.get('source', '?')})"]
        if j.get("sessions"):
            lines.append("  by session: " + ", ".join(
                f"{day} {n} ({k} sym)" for day, n, k in j["sessions"]))
    lines += [
        "",
        "Read: cumulative post-gate scorecard — judge the two gates on the trend "
        "across sessions, not any single day. Still a thin sample; keep accruing.",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    date_str = _arg(argv, "--date", datetime.now(config.MARKET_TZ).strftime("%Y-%m-%d"))
    since_str = _arg(argv, "--since", "")
    out = _arg(argv, "--out", "")

    if since_str:
        # Cumulative post-gate scorecard: [--since] .. [--date|today].
        d = _db_window(since_str, date_str)
        j = _log_window(since_str, date_str)
        report = format_window_report(since_str, date_str, d, j)
        print(report)
        payload = {"since": since_str, "until": date_str, "db": d, "log": j,
                   "generated_at": datetime.now(timezone.utc).isoformat(),
                   "report_text": report}
    else:
        j = _log_counts(date_str)
        d = _db_session(date_str)
        # Opt-in: the counterfactual needs market data, so the default path stays
        # DB+log only and never depends on the data API being reachable.
        g = _gate_cost(date_str) if "--replay-skips" in argv else None
        report = format_report(date_str, j, d, g)
        print(report)
        payload = {"date": date_str, "log": j, "db": d, "gate_cost": g,
                   "generated_at": datetime.now(timezone.utc).isoformat(),
                   "report_text": report}

    if out:
        with open(out, "w") as fh:
            json.dump(payload, fh, indent=2, default=str)
        print(f"\nWrote {out}")
    if "--telegram" in argv:
        print(f"\nTelegram sent: {notify.send(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
