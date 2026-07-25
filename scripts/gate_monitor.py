"""Gate-performance monitor: how the IMP-021 (breakout veto) and IMP-022 (VWAP)
entry gates performed on a given trading session.

  python -m scripts.gate_monitor                 # today (ET), print only
  python -m scripts.gate_monitor --date 2026-07-27
  python -m scripts.gate_monitor --telegram --out /path/result.json

Combines two sources:
  * journald (the live service log) — counts the IMP-022 VWAP skips actually
    fired ("above session VWAP") plus entries/rejects for context.
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

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from bot import config, db, notify

SERVICE = "ustradewisbot.service"


def _arg(argv, flag, default):
    return argv[argv.index(flag) + 1] if flag in argv else default


def _journal_counts(date_str: str) -> dict:
    """Count IMP-022 VWAP skips / entries / rejects in the service log for the day."""
    try:
        out = subprocess.run(
            ["journalctl", "-u", SERVICE, "--no-pager", "-o", "cat",
             "--since", f"{date_str} 00:00:00", "--until", f"{date_str} 23:59:59"],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except Exception as exc:  # noqa: BLE001 - monitor must not crash on log access
        return {"available": False, "error": str(exc)}
    vwap = sum(1 for ln in out.splitlines() if "above session VWAP" in ln)
    entries = sum(1 for ln in out.splitlines() if " ENTRY " in ln and "order=" in ln)
    rejects = sum(1 for ln in out.splitlines() if "ENTRY REJECTED" in ln)
    return {"available": True, "vwap_skips": vwap, "log_entries": entries, "rejects": rejects}


def _db_session(date_str: str) -> dict:
    """Trades that got through the gates on ``date_str`` + the IMP-021 hold check."""
    cn = db.connect()
    cur = cn.cursor()
    cur.execute(
        """
        WITH s AS (
          SELECT trade_id, breakout_score,
                 ROW_NUMBER() OVER (PARTITION BY trade_id ORDER BY ts) rn
          FROM dbo.signals WHERE trade_id IS NOT NULL)
        SELECT t.symbol, t.status, t.realized_pl, t.exit_reason, s.breakout_score
        FROM dbo.trades t
        LEFT JOIN s ON s.trade_id = t.trade_id AND s.rn = 1
        WHERE CAST(t.entry_time AS DATE) = ?
        ORDER BY t.entry_time
        """,
        date_str,
    )
    rows = [{"symbol": r.symbol, "status": r.status,
             "pl": float(r.realized_pl) if r.realized_pl is not None else None,
             "exit_reason": r.exit_reason,
             "bo": float(r.breakout_score) if r.breakout_score is not None else None}
            for r in cur.fetchall()]
    cn.close()

    closed = [r for r in rows if r["pl"] is not None]
    wins = sum(1 for r in closed if r["pl"] > 0)
    losses = len(closed) - wins
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
        "by_reason": by_reason,
        "imp021_held": len(strong_bo) == 0,
        "strong_breakout_leaks": [r["symbol"] for r in strong_bo],
        "symbols": [r["symbol"] for r in rows],
    }


def format_report(date_str: str, j: dict, d: dict) -> str:
    lines = [
        f"🚦 USTradeWisBot — gate performance {date_str}",
        "",
        "IMP-022 VWAP gate:",
    ]
    if j.get("available"):
        lines.append(f"  🚫 skipped {j['vwap_skips']} stretched-above-VWAP entries "
                     f"(logged 'above session VWAP')")
        lines.append(f"  entries logged: {j['log_entries']}   rejects: {j['rejects']}")
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
    lines += [
        "",
        "Read: fewer, higher-quality trades = gates working. Historical baseline "
        "≈ 3–6 trades/day at ~38% win. One session is noise — trend matters.",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    date_str = _arg(argv, "--date", datetime.now(config.MARKET_TZ).strftime("%Y-%m-%d"))
    out = _arg(argv, "--out", "")

    j = _journal_counts(date_str)
    d = _db_session(date_str)
    report = format_report(date_str, j, d)
    print(report)

    if out:
        with open(out, "w") as fh:
            json.dump({"date": date_str, "journal": j, "db": d,
                       "generated_at": datetime.now(timezone.utc).isoformat(),
                       "report_text": report}, fh, indent=2, default=str)
        print(f"\nWrote {out}")
    if "--telegram" in argv:
        print(f"\nTelegram sent: {notify.send(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
