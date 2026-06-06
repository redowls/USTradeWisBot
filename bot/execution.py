"""Order execution — bracket orders on paper (todo.md Phase 6).

Every entry is a single BRACKET order: a market buy with an attached take-profit
(limit) and stop-loss (stop) leg, submitted atomically (summary.md §5.10). When
one exit fills the other cancels (OCO), so the position always has a server-side
stop even if the bot crashes.

Handles order rejections, insufficient buying power, and Alpaca's 200 req/min
rate limit (retry with exponential backoff on transient errors only). Returns the
broker order id for logging in Phase 8.
"""

from __future__ import annotations

import time
import uuid

from alpaca.common.exceptions import APIError
from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
from alpaca.trading.requests import (
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

from . import broker
from .sizing import PositionPlan

_MAX_RETRIES = 3
_BACKOFF_BASE_SEC = 1.0


def _api_status(exc: APIError) -> int | None:
    return getattr(exc, "status_code", None)


def _is_retryable(exc: Exception) -> bool:
    """Only retry transient failures: rate limits, 5xx, and network blips."""
    if isinstance(exc, APIError):
        code = _api_status(exc)
        return code == 429 or (isinstance(code, int) and code >= 500)
    return isinstance(exc, (ConnectionError, TimeoutError))


def _with_retry(fn, *args, **kwargs):
    """Call fn with exponential backoff on transient errors."""
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - re-raised below if not retryable
            last = exc
            if not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(_BACKOFF_BASE_SEC * (2 ** attempt))
    assert last is not None
    raise last


def new_client_order_id(symbol: str) -> str:
    """Unique id so a retried submit can't silently duplicate the order."""
    return f"utwb-{symbol.upper()}-{uuid.uuid4().hex[:12]}"


def build_bracket_request(
    plan: PositionPlan,
    *,
    time_in_force: TimeInForce = TimeInForce.DAY,
    client_order_id: str | None = None,
) -> MarketOrderRequest:
    """Construct (but don't submit) the bracket MarketOrderRequest for a plan.

    Pure/testable: no network. TIF defaults to DAY (intraday; positions are
    flattened at 15:55 anyway).
    """
    return MarketOrderRequest(
        symbol=plan.symbol,
        qty=plan.shares,
        side=OrderSide.BUY,
        time_in_force=time_in_force,
        order_class=OrderClass.BRACKET,
        take_profit=TakeProfitRequest(limit_price=plan.take_profit_price),
        stop_loss=StopLossRequest(stop_price=plan.stop_price),
        client_order_id=client_order_id or new_client_order_id(plan.symbol),
    )


def submit_bracket_order(
    plan: PositionPlan, *, time_in_force: TimeInForce = TimeInForce.DAY
) -> dict:
    """Submit a bracket order for a tradable plan. Never raises — returns a result dict.

    Result keys: ok, status, symbol, qty, order_id, client_order_id,
    take_profit, stop, error.
    """
    base = {
        "ok": False, "status": None, "symbol": plan.symbol, "qty": plan.shares,
        "order_id": None, "client_order_id": None,
        "take_profit": plan.take_profit_price, "stop": plan.stop_price, "error": None,
    }

    if not plan.tradable:
        return {**base, "status": "skipped", "error": f"plan not tradable: {plan.skip_reason}"}

    coid = new_client_order_id(plan.symbol)
    request = build_bracket_request(plan, time_in_force=time_in_force, client_order_id=coid)
    base["client_order_id"] = coid

    try:
        order = _with_retry(broker.trading_client().submit_order, request)
    except APIError as exc:
        return {**base, "status": "rejected", "error": f"APIError {_api_status(exc)}: {exc}"}
    except Exception as exc:  # noqa: BLE001 - surface any other failure to the caller
        return {**base, "status": "error", "error": f"{type(exc).__name__}: {exc}"}

    return {
        **base,
        "ok": True,
        "status": str(order.status),
        "order_id": str(order.id),
    }


def get_order(order_id: str):
    """Fetch an order (including its bracket child legs) by id."""
    return broker.trading_client().get_order_by_id(order_id)


def cancel_order(order_id: str) -> None:
    """Cancel an order by id (used to clean up test orders)."""
    broker.trading_client().cancel_order_by_id(order_id)
