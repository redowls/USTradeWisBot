"""Alpaca trading-client wrapper.

Phase 1 only needs account access (equity / buying power). Order submission
arrives in Phase 6. Paper vs live is controlled by ALPACA_PAPER in .env
(summary.md §2 — going live is one flag, not a rewrite).
"""

from __future__ import annotations

from functools import lru_cache

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

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


def close_position(symbol: str):
    """Liquidate a single position at market (DELETE /v2/positions/{symbol}).

    Used by the EOD flatten so each position is closed explicitly and can be
    individually verified flat afterwards, rather than relying on the bulk
    close_all_positions (which races held_for_orders and silently leaves some
    positions open — the 06-16 C/AMZN/BAC two-night naked hold, IMP-002)."""
    return trading_client().close_position(symbol)


def latest_filled_exit_price(symbol: str) -> float | None:
    """`filled_avg_price` of the most recently filled SELL for `symbol`, or None.

    The EOD flatten uses this to record each liquidation at its REAL fill price
    instead of a pre-liquidation market-value approximation that fell through to
    the entry price. On 2026-06-22 SPY/QQQ/TSM were each booked at exit==entry
    ($0.00 P&L) while the actual flatten sells filled at 744.12 / 737.18 /
    466.222 — a ~$60 P&L misstatement in one day. The most recent filled sell
    after liquidation is the flatten order (canceled bracket legs carry no
    filled_avg_price and are skipped). IMP-003."""
    req = GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        side=OrderSide.SELL,
        symbols=[symbol.upper()],
        limit=50,
        direction="desc",
    )
    for order in trading_client().get_orders(filter=req):
        price = getattr(order, "filled_avg_price", None)
        if price is None:
            continue
        try:
            return float(price)
        except (TypeError, ValueError):
            continue
    return None


def entry_fill_price(order_id: str | None) -> float | None:
    """`filled_avg_price` of the bracket entry (parent) order, or None.

    The EOD flatten computes P&L from the trade's stored entry_price, which is
    the *signal/intended* price at submission — not the actual market fill. On a
    fast open the bracket buy can slip materially: 2026-06-24 CRM was recorded
    154.48 but filled 155.17, BAC recorded 57.93 but filled 58.2154, so the DB
    booked the day at -$61.34 while the broker truth was -$87.08 (~42% of the
    loss hidden). detect_exits already prices STOP/TP exits off the parent's
    filled_avg_price; this gives eod_flatten the same real entry basis. IMP-005.
    """
    if not order_id:
        return None
    try:
        order = trading_client().get_order_by_id(order_id)
    except Exception:  # noqa: BLE001 - a lookup failure must not block the flatten
        return None
    price = getattr(order, "filled_avg_price", None)
    try:
        return float(price) if price is not None else None
    except (TypeError, ValueError):
        return None
