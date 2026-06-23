"""Incubation analytics (todo.md Phase 12).

Reads the logged trades/signals/daily_summary from SQL Server and computes the
metrics that decide whether the strategy is worth taking live (summary.md §10,
todo Phase 12): win rate, average P&L %, expectancy, profit factor, performance
by signal type, and the false-breakout rate.

`compute_metrics()` is a pure function (testable without a database); the load_*
helpers read from bot.db.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from statistics import mean

from . import config, db

# Minimum closed trades before results mean much (summary.md §10 / §12).
MIN_SAMPLE = 50
# A false-breakout rate at/above this is a red flag (todo Phase 12).
FALSE_BREAKOUT_LIMIT = 40.0


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Confidence bands for the by-confidence breakdown. The live scoring distribution
# tops out around the low-60s, so the bands deliberately span the actual range and
# expose that nothing scores >=64 — a "raise the floor to 65" change would disable
# the entire book (see daily-review 2026-06-23 / refuted improvement candidate).
CONFIDENCE_BANDS: tuple[tuple[float, float, str], ...] = (
    (0.0, 60.0, "<60"),
    (60.0, 62.0, "60-62"),
    (62.0, 64.0, "62-64"),
    (64.0, 66.0, "64-66"),
    (66.0, float("inf"), "66+"),
)


def _bucket(pls: list[float]) -> dict:
    """Win-rate / total / expectancy / profit-factor over one slice of P&Ls."""
    n = len(pls)
    if n == 0:
        return {"trades": 0, "win_rate": 0.0, "total_pl": 0.0,
                "expectancy": 0.0, "profit_factor": None}
    wins = [p for p in pls if p > 0]
    losses = [p for p in pls if p <= 0]
    gross_loss = sum(losses)  # <= 0
    return {
        "trades": n,
        "win_rate": round(100 * len(wins) / n, 1),
        "total_pl": round(sum(pls), 2),
        "expectancy": round(mean(pls), 2),
        "profit_factor": round(sum(wins) / abs(gross_loss), 2) if gross_loss else None,
    }


def load_closed_trades(since: date | None = None) -> list[dict]:
    """Closed trades joined to their signal (signal_type/confidence)."""
    sql = (
        "SELECT t.trade_id, t.symbol, t.realized_pl, t.realized_pl_pct, "
        "t.exit_reason, t.entry_time, t.exit_time, s.signal_type, s.confidence "
        "FROM trades t LEFT JOIN signals s ON s.trade_id = t.trade_id "
        "WHERE t.status = 'CLOSED' AND t.realized_pl IS NOT NULL"
    )
    params: list = []
    if since is not None:
        sql += " AND CAST(t.entry_time AS DATE) >= ?"
        params.append(since)
    sql += " ORDER BY t.entry_time"
    return db.query(sql, params)


def load_daily_summaries(since: date | None = None) -> list[dict]:
    sql = "SELECT * FROM daily_summary"
    params: list = []
    if since is not None:
        sql += " WHERE trade_date >= ?"
        params.append(since)
    sql += " ORDER BY trade_date"
    return db.query(sql, params)


def compute_metrics(rows: list[dict]) -> dict:
    """Pure metric computation over closed-trade rows."""
    closed = [r for r in rows if r.get("realized_pl") is not None]
    n = len(closed)
    if n == 0:
        return {"trades": 0}

    pls = [_f(r["realized_pl"]) for r in closed]
    pcts = [_f(r["realized_pl_pct"]) for r in closed if r.get("realized_pl_pct") is not None]
    wins = [p for p in pls if p > 0]
    losses = [p for p in pls if p <= 0]

    gross_win = sum(wins)
    gross_loss = sum(losses)  # <= 0
    by_type: dict[str, dict] = {}
    for st in sorted({(r.get("signal_type") or "UNKNOWN") for r in closed}):
        sub = [_f(r["realized_pl"]) for r in closed if (r.get("signal_type") or "UNKNOWN") == st]
        by_type[st] = _bucket(sub)

    # By confidence band — exposes the actual scoring distribution so a "raise the
    # MIN_CONFIDENCE floor" candidate is judged against where trades really land.
    by_band: dict[str, dict] = {}
    for lo, hi, label in CONFIDENCE_BANDS:
        sub = [_f(r["realized_pl"]) for r in closed
               if r.get("confidence") is not None and lo <= _f(r["confidence"]) < hi]
        by_band[label] = _bucket(sub)

    # False-breakout rate: of breakout-driven trades, the share that stopped out.
    bo = [r for r in closed if (r.get("signal_type") in ("BREAKOUT", "BOTH"))]
    fb_rate = (round(100 * sum(1 for r in bo if r.get("exit_reason") == "STOP") / len(bo), 1)
               if bo else None)

    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(100 * len(wins) / n, 1),
        "total_pl": round(sum(pls), 2),
        "expectancy": round(mean(pls), 2),            # expected $ per trade
        "avg_pl_pct": round(mean(pcts), 4) if pcts else 0.0,
        "avg_win": round(mean(wins), 2) if wins else 0.0,
        "avg_loss": round(mean(losses), 2) if losses else 0.0,
        "profit_factor": round(gross_win / abs(gross_loss), 2) if gross_loss else None,
        "by_signal_type": by_type,
        "by_confidence_band": by_band,
        "false_breakout_rate": fb_rate,
        "exit_reasons": dict(Counter(r.get("exit_reason") for r in closed)),
    }


def incubation_verdict(metrics: dict) -> str:
    """A blunt readiness check — never a recommendation to go live by itself."""
    n = metrics.get("trades", 0)
    if n < MIN_SAMPLE:
        return f"INSUFFICIENT DATA — {n}/{MIN_SAMPLE}+ closed trades needed"
    issues = []
    if metrics.get("expectancy", 0) <= 0:
        issues.append("expectancy not positive")
    fb = metrics.get("false_breakout_rate")
    if fb is not None and fb >= FALSE_BREAKOUT_LIMIT:
        issues.append(f"false-breakout rate {fb}% >= {FALSE_BREAKOUT_LIMIT}%")
    if not issues:
        return "PROMISING — review by-signal-type before any live decision"
    return "NEEDS WORK — " + "; ".join(issues)


def since_days(days: int) -> date:
    return (datetime.now(config.MARKET_TZ) - timedelta(days=days)).date()
