"""IMP-060 — tests must never be able to place a real order (the 2026-09-18 loss).

What happened, from the broker record and the bot's own log:

  11:22:01-03Z  seven `utwb-META-*` 1-share BRACKET buys submitted (pre-market)
  11:22:57-58Z  seven more, ~56s later — two runs of the same test selection
  13:30:12Z+    all fourteen fill at the open, $684.29-$688.45 (avg $686.226)
  19:55:13-23Z  every unused leg cancelled
  19:55:34Z     one market sell, qty 14 @ $665.50  ->  -$290.16 realised

The service's own main loop was asleep the whole time ("market closed —
sleeping ~6348s until next open" at 07:44:11 EDT; the 07:54 restart came after
the orders). The orders came from a pytest run: `_run(...)` in
tests/test_imp056_entry_refusals.py builds `engine.Engine(dry_run=False)` and
stubs signals/confidence/logbook/account — but not the order path. Any
candidate in that file that is NOT refused therefore goes through the real
`sizing.plan_position` and out to Alpaca.

The DB guard added in IMP-043 is what made it invisible rather than obvious:
the trade rows were blocked, so `trades` held zero rows for 2026-09-18 while
Alpaca held a 14-share round trip, and `daily_summary` recorded a $290.16
equity drop against "0 trades".

These tests pin the guard that closes it. They must never be rewritten to
assert that an order WAS placed.
"""

from __future__ import annotations

import pytest

from bot import broker, execution, sizing
from conftest import LiveBrokerOrderBlocked

# The IMP-056 fixture constants that were live on 2026-09-18, and the plan the
# real sizing path builds from them. These three numbers are what Alpaca filled.
META_PRICE = 670.80
META_ATR = 6.40
META_CONF = 61.30
FILLED_QTY = 1
FILLED_STOP = 651.60
FILLED_TAKE_PROFIT = 699.60


def _incident_plan():
    return sizing.plan_position(
        "META", META_CONF, META_PRICE, META_ATR, 7_527.50, 7_527.50
    )


def test_the_incident_plan_still_reproduces_exactly():
    """Anchor: the geometry that reached the broker is what sizing still builds.

    If this drifts, the rest of the file stops describing the real event and
    the numbers above must be re-derived from the order record, not adjusted.
    """
    plan = _incident_plan()
    assert plan.tradable is True and plan.skip_reason is None
    assert plan.shares == FILLED_QTY
    assert plan.stop_price == pytest.approx(FILLED_STOP)
    assert plan.take_profit_price == pytest.approx(FILLED_TAKE_PROFIT)


def test_submitting_the_incident_plan_is_blocked():
    """The exact call that placed fourteen META orders now fails loudly."""
    with pytest.raises(LiveBrokerOrderBlocked) as exc:
        execution.submit_bracket_order(_incident_plan())
    assert "submit_bracket_order" in str(exc.value)
    assert "REAL order" in str(exc.value)


def test_the_guard_survives_submit_bracket_orders_own_error_swallowing():
    """Why the guard is a BaseException.

    `submit_bracket_order` catches `Exception` and returns an error dict so a
    broker hiccup can never break the entry loop. A guard raising `Exception`
    would be swallowed by that handler: the test would see `ok=False`, pass,
    and the order would still be live. Inheriting BaseException is the only
    reason the assertion above can hold at all.
    """
    assert issubclass(LiveBrokerOrderBlocked, BaseException)
    assert not issubclass(LiveBrokerOrderBlocked, Exception)


@pytest.mark.parametrize("name", ["cancel_order", "replace_stop_order"])
def test_other_execution_mutators_are_blocked(name):
    with pytest.raises(LiveBrokerOrderBlocked):
        getattr(execution, name)("leg-1", 101.5) if name == "replace_stop_order" \
            else getattr(execution, name)("leg-1")


@pytest.mark.parametrize("name", ["cancel_all_orders", "close_all_positions", "close_position"])
def test_broker_mutators_are_blocked(name):
    with pytest.raises(LiveBrokerOrderBlocked):
        getattr(broker, name)("META") if name == "close_position" else getattr(broker, name)()


def test_the_class_level_backstop_catches_a_hand_rolled_client():
    """A test that bypasses bot.execution entirely still cannot reach Alpaca.

    `broker.trading_client()` hands back a real TradingClient; the module-level
    patches above do nothing for code that calls it directly. This is the layer
    that makes the guard a guarantee rather than a convention.
    """
    from alpaca.trading.client import TradingClient

    with pytest.raises(LiveBrokerOrderBlocked) as exc:
        TradingClient.submit_order(object(), None)
    assert "TradingClient.submit_order" in str(exc.value)


def test_reads_are_deliberately_left_alone():
    """Reads cannot move money and several tests legitimately use them.

    Asserted against the guard's own path lists so that widening the blocked
    surface to a read has to be a deliberate edit here, not an accident.
    """
    import conftest

    blocked = set(conftest._EXECUTION_ORDER_PATHS) | set(conftest._BROKER_ORDER_PATHS)
    reads = {
        "account_summary", "get_positions", "open_position_symbols", "get_clock",
        "is_market_open", "get_account", "latest_filled_exit_price",
        "entry_fill_price", "get_order",
    }
    assert blocked & reads == set()


def test_a_test_can_still_opt_in_to_the_real_function(monkeypatch, real_order_functions):
    """The escape hatch works, and is greppable (`real_order_functions`)."""
    class _Client:
        def replace_order_by_id(self, order_id, order_data=None):
            return type("O", (), {"id": "new-leg-9"})()

    monkeypatch.setattr(execution.broker, "trading_client", lambda: _Client())
    assert execution.replace_stop_order("leg-1", 101.5)["order_id"] == "new-leg-9"
