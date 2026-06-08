"""Alpaca trading-client wrapper.

Phase 1 only needs account access (equity / buying power). Order submission
arrives in Phase 6. Paper vs live is controlled by ALPACA_PAPER in .env
(summary.md §2 — going live is one flag, not a rewrite).
"""

from __future__ import annotations

from functools import lru_cache

from alpaca.trading.client import TradingClient

from . import secrets


@lru_cache(maxsize=1)
def trading_client() -> TradingClient:
    """A cached Alpaca TradingClient bound to the paper or live endpoint."""
    return TradingClient(
        api_key=secrets.ALPACA_API_KEY,
        secret_key=secrets.ALPACA_SECRET_KEY,
        paper=secrets.ALPACA_PAPER,
    )


def get_account():
    """Return the raw Alpaca account object."""
    return trading_client().get_account()


def account_summary() -> dict:
    """Key account figures as a plain dict (equity, buying power, etc.).

    Position sizing keys off buying_power, not the deprecated PDT fields
    (summary.md §10 — PDT fields are being removed ~July 2026).
    """
    acct = get_account()
    return {
        "account_number": acct.account_number,
        "status": str(acct.status),
        "currency": acct.currency,
        "equity": float(acct.equity),
        "cash": float(acct.cash),
        "buying_power": float(acct.buying_power),
        "paper": secrets.ALPACA_PAPER,
    }


def get_positions() -> list:
    """All currently open positions (raw Alpaca position objects)."""
    return trading_client().get_all_positions()


def open_position_symbols() -> set[str]:
    """Set of symbols currently held — feeds sizing's already-held / concurrency checks."""
    return {p.symbol.upper() for p in get_positions()}


def get_clock():
    """Alpaca market clock (is_open, next_open, next_close, timestamp)."""
    return trading_client().get_clock()


def is_market_open() -> bool:
    """True when US equities regular session is currently open."""
    return bool(get_clock().is_open)


def cancel_all_orders():
    """Cancel every open order. Returns Alpaca's per-order cancel statuses."""
    return trading_client().cancel_orders()


def close_all_positions(cancel_orders: bool = True):
    """Liquidate all open positions at market (and optionally cancel open orders first)."""
    return trading_client().close_all_positions(cancel_orders=cancel_orders)
