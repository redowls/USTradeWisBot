"""SQL Server access via pyodbc (ODBC Driver 18).

Every query uses parameterized placeholders ('?') — never string-formatted SQL
(summary.md §6). Connection settings come from bot.secrets (loaded from .env).
"""

from __future__ import annotations

import contextlib
from typing import Any, Iterable, Sequence

import pyodbc

from . import secrets


def _connection_string() -> str:
    encrypt = "yes"
    trust = "yes" if secrets.DB_TRUST_CERT else "no"
    return (
        f"DRIVER={{{secrets.DB_DRIVER}}};"
        f"SERVER={secrets.DB_SERVER};"
        f"DATABASE={secrets.DB_NAME};"
        f"UID={secrets.DB_USER};"
        f"PWD={secrets.DB_PASSWORD};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust};"
    )


def connect() -> pyodbc.Connection:
    """Open a new connection. Caller owns it (use as a context manager)."""
    return pyodbc.connect(_connection_string())


@contextlib.contextmanager
def get_conn():
    """Context-managed connection that commits on success, rolls back on error."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(sql: str, params: Sequence[Any] | None = None) -> int:
    """Run a write statement (INSERT/UPDATE/DELETE/DDL). Returns rows affected."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        return cur.rowcount


def executemany(sql: str, rows: Iterable[Sequence[Any]]) -> int:
    """Run a write statement against many parameter sets in one batch."""
    rows = list(rows)
    if not rows:
        return 0
    with get_conn() as conn:
        cur = conn.cursor()
        cur.fast_executemany = True
        cur.executemany(sql, rows)
        return cur.rowcount


def insert_returning_id(sql: str, params: Sequence[Any] | None = None) -> int | None:
    """Run an INSERT whose statement uses OUTPUT INSERTED.<id>; return that id."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        row = cur.fetchone()
        return int(row[0]) if row else None


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Run a SELECT and return rows as a list of dicts."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def query_one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    """Run a SELECT and return the first row as a dict (or None)."""
    rows = query(sql, params)
    return rows[0] if rows else None


def ping() -> bool:
    """True if the database answers a trivial query."""
    return query_one("SELECT 1 AS ok") == {"ok": 1}


# --- Watchlist helpers (used from Phase 1 onward) ---

def get_active_watchlist() -> list[dict[str, Any]]:
    """Return active watchlist rows, ordered by symbol."""
    return query(
        "SELECT symbol, name, is_active, added_at, notes "
        "FROM watchlist WHERE is_active = 1 ORDER BY symbol"
    )


def upsert_watchlist_symbol(symbol: str, name: str | None = None) -> None:
    """Insert a symbol if absent; (re)activate it if present."""
    execute(
        """
        MERGE watchlist AS target
        USING (SELECT ? AS symbol, ? AS name) AS src
        ON target.symbol = src.symbol
        WHEN MATCHED THEN
            UPDATE SET is_active = 1, name = COALESCE(src.name, target.name)
        WHEN NOT MATCHED THEN
            INSERT (symbol, name, is_active, added_at)
            VALUES (src.symbol, src.name, 1, SYSUTCDATETIME());
        """,
        [symbol, name],
    )
