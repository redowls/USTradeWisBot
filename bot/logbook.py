"""Database logging & daily summary (todo.md Phase 8).

Persists the trade lifecycle to SQL Server (summary.md §6), turning the dicts
produced by signals/sizing/execution/exits into rows:

  on entry  -> trades (status OPEN) + signals (confidence + component scores +
               signal_type + broken level)  [the "why" of every trade]
  on exit   -> update the trades row (exit price/time, P&L, status CLOSED, reason)
  after close -> one daily_summary row (buys/sells, wins/losses, gross P&L, etc.)

All writes go through bot.db, which uses parameterized queries only.
"""

from __future__ import annotations

from datetime import date, datetime

from . import config, confidence as _confidence, db


def _et_naive(dt: datetime | None) -> datetime:
    """Normalize to naive US-Eastern wall-clock for DATETIME2 storage."""
    if dt is None:
        dt = datetime.now(config.MARKET_TZ)
    if dt.tzinfo is not None:
        dt = dt.astimezone(config.MARKET_TZ).replace(tzinfo=None)
    return dt


# --- Signal logging ---------------------------------------------------------

def log_signal(
    evaluation: dict,
    confidence: float | None = None,
    trade_id: int | None = None,
    ts: datetime | None = None,
) -> int | None:
    """Insert a signals row (the explainability record). Returns signal_id."""
    if confidence is None:
        confidence = _confidence.score(evaluation)
    return db.insert_returning_id(
        """
        INSERT INTO signals
            (trade_id, symbol, ts, signal_type, confidence,
             breakout_score, ma_score, value_score, momentum_score,
             regime_ok, broke_level)
        OUTPUT INSERTED.signal_id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            trade_id,
            evaluation.get("symbol"),
            _et_naive(ts),
            evaluation.get("signal_type"),
            confidence,
            evaluation.get("breakout_score"),
            evaluation.get("ma_score"),
            evaluation.get("value_score"),
            evaluation.get("momentum_score"),
            1 if evaluation.get("regime_ok") else 0,
            evaluation.get("broke_level"),
        ],
    )


# --- Trade entry / exit -----------------------------------------------------

def record_entry(
    evaluation: dict,
    plan,
    order_result: dict,
    confidence: float | None = None,
    entry_time: datetime | None = None,
) -> int:
    """Insert the OPEN trade row + its signals row. Returns trade_id."""
    if confidence is None:
        confidence = _confidence.score(evaluation)
    entry_time = _et_naive(entry_time)

    trade_id = db.insert_returning_id(
        """
        INSERT INTO trades
            (symbol, side, qty, entry_price, entry_time,
             stop_price, take_profit_price, status, alpaca_order_id)
        OUTPUT INSERTED.trade_id
        VALUES (?, 'BUY', ?, ?, ?, ?, ?, 'OPEN', ?)
        """,
        [
            plan.symbol, plan.shares, plan.entry_price, entry_time,
            plan.stop_price, plan.take_profit_price, order_result.get("order_id"),
        ],
    )
    log_signal(evaluation, confidence=confidence, trade_id=trade_id, ts=entry_time)
    return trade_id


def update_trade_exit(
    trade_id: int,
    exit_price: float,
    exit_time: datetime | None,
    realized_pl: float,
    realized_pl_pct: float,
    exit_reason: str,
    status: str = "CLOSED",
) -> int:
    """Update a trade row on exit. Returns rows affected."""
    return db.execute(
        """
        UPDATE trades
        SET exit_price = ?, exit_time = ?, realized_pl = ?, realized_pl_pct = ?,
            status = ?, exit_reason = ?
        WHERE trade_id = ?
        """,
        [exit_price, _et_naive(exit_time), realized_pl, realized_pl_pct,
         status, exit_reason, trade_id],
    )


def record_exit(exit_record: dict) -> int | None:
    """Close the OPEN trade matching the exit's entry order id. Returns trade_id."""
    row = db.query_one(
        "SELECT trade_id FROM trades WHERE alpaca_order_id = ? AND status = 'OPEN'",
        [exit_record.get("entry_order_id")],
    )
    if not row:
        return None
    trade_id = row["trade_id"]
    update_trade_exit(
        trade_id,
        exit_price=exit_record["exit_price"],
        exit_time=exit_record.get("exit_time"),
        realized_pl=exit_record["realized_pl"],
        realized_pl_pct=exit_record["realized_pl_pct"],
        exit_reason=exit_record["exit_reason"],
    )
    return trade_id


# --- Daily summary ----------------------------------------------------------

def write_daily_summary(
    trade_date: date,
    equity_open: float | None = None,
    equity_close: float | None = None,
) -> dict:
    """Aggregate the day's trades and upsert the daily_summary row. Returns it."""
    agg = db.query_one(
        """
        SELECT
            (SELECT COUNT(*) FROM trades WHERE CAST(entry_time AS DATE) = ?) AS num_buys,
            (SELECT COUNT(*) FROM trades WHERE CAST(exit_time AS DATE) = ?) AS num_sells,
            (SELECT COUNT(*) FROM trades WHERE CAST(exit_time AS DATE) = ? AND realized_pl > 0) AS wins,
            (SELECT COUNT(*) FROM trades WHERE CAST(exit_time AS DATE) = ? AND realized_pl < 0) AS losses,
            (SELECT COALESCE(SUM(realized_pl), 0) FROM trades WHERE CAST(exit_time AS DATE) = ?) AS gross_pl
        """,
        [trade_date, trade_date, trade_date, trade_date, trade_date],
    )
    sym_row = db.query_one(
        """
        SELECT STRING_AGG(symbol, ',') AS symbols FROM
            (SELECT DISTINCT symbol FROM trades WHERE CAST(entry_time AS DATE) = ?) s
        """,
        [trade_date],
    )
    gross_pl = float(agg["gross_pl"])
    realized_pl_pct = (gross_pl / equity_open * 100.0) if equity_open else None

    db.execute(
        """
        MERGE daily_summary AS tgt
        USING (SELECT ? AS trade_date) AS src ON tgt.trade_date = src.trade_date
        WHEN MATCHED THEN UPDATE SET
            num_buys = ?, num_sells = ?, wins = ?, losses = ?, gross_pl = ?,
            realized_pl_pct = ?, equity_open = ?, equity_close = ?, symbols_traded = ?
        WHEN NOT MATCHED THEN INSERT
            (trade_date, num_buys, num_sells, wins, losses, gross_pl,
             realized_pl_pct, equity_open, equity_close, symbols_traded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            trade_date,
            agg["num_buys"], agg["num_sells"], agg["wins"], agg["losses"], gross_pl,
            realized_pl_pct, equity_open, equity_close, sym_row["symbols"],
            trade_date,
            agg["num_buys"], agg["num_sells"], agg["wins"], agg["losses"], gross_pl,
            realized_pl_pct, equity_open, equity_close, sym_row["symbols"],
        ],
    )
    return get_daily_summary(trade_date)


# --- Read helpers (verification / ops) --------------------------------------

def get_trade(trade_id: int) -> dict | None:
    return db.query_one("SELECT * FROM trades WHERE trade_id = ?", [trade_id])


def get_open_trades() -> list[dict]:
    return db.query("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY entry_time")


def open_trade_symbols() -> set[str]:
    """Symbols with an OPEN trade in the logbook (submitted but maybe unfilled).

    Feeds the entry guard so a just-submitted bracket that has not yet shown up
    as a filled Alpaca position can't be entered a second time on the next tick
    (the 2026-06-15 ENPH double-entry, IMP-001).
    """
    return {r["symbol"].upper() for r in get_open_trades()}


def get_daily_summary(trade_date: date) -> dict | None:
    return db.query_one("SELECT * FROM daily_summary WHERE trade_date = ?", [trade_date])


# --- Risk-gate inputs (circuit breaker / re-entry throttle) -----------------

def get_today_realized_pl(trade_date: date) -> float:
    """Sum of realized P&L for trades that CLOSED on trade_date (0.0 if none)."""
    row = db.query_one(
        "SELECT COALESCE(SUM(realized_pl), 0) AS pl "
        "FROM trades WHERE CAST(exit_time AS DATE) = ?",
        [trade_date],
    )
    return float(row["pl"]) if row and row["pl"] is not None else 0.0


def get_symbol_activity_today(trade_date: date) -> dict[str, dict]:
    """Per-symbol activity for the re-entry throttle.

    Returns {symbol: {"entries": int, "last_exit": datetime|None}} for every
    symbol entered on trade_date. ``last_exit`` is the most recent exit_time
    (naive ET, as stored) or None while a trade is still open.
    """
    rows = db.query(
        """
        SELECT symbol, COUNT(*) AS entries, MAX(exit_time) AS last_exit
        FROM trades WHERE CAST(entry_time AS DATE) = ?
        GROUP BY symbol
        """,
        [trade_date],
    )
    return {
        r["symbol"]: {"entries": int(r["entries"]), "last_exit": r["last_exit"]}
        for r in rows
    }
