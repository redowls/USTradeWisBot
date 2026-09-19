"""Test-suite guards.

The bot talks to a REAL SQL Server database (`bot.db`), and `bot.config` points
at it unconditionally — there is no test database. Any test that drives a code
path which writes therefore mutates the live trade history.

IMP-043 hit this for real: adding one `logbook.record_stop_raise(...)` call to
`Engine.manage_stops` silently turned three pre-existing test files
(`test_trailing_stop.py`, `test_naked_protection.py`, `test_naked_stop_race.py`)
into writers, because they drive `manage_stops` with fixtures carrying REAL
trade ids (1, 149, 244, 273, 274, 275). Running the suite incremented
`stop_raises` on live rows #149, #244 and #274 and invented arming events for
two trades from July and August whose logs had rotated away months ago —
corrupting the exact table the change existed to make trustworthy.

Reads are left alone: several tests legitimately read live rows, and a read
cannot damage anything. Only the write paths are blocked, and a test that
genuinely wants to exercise a write still can — `monkeypatch.setattr` inside a
test body runs after this autouse fixture, so it wins.
"""

from __future__ import annotations

import pytest

from bot import db

_WRITE_PATHS = ("execute", "executemany", "insert_returning_id")


class LiveDatabaseWriteBlocked(BaseException):
    """Raised when a test reaches a live write path.

    Deliberately a BaseException, NOT an Exception. Production code around these
    writes is written to swallow failures on purpose — ``record_stop_raise``
    catches ``Exception`` so a database hiccup can never break the ratchet loop,
    and ``Engine.manage_stops`` wraps each symbol the same way. Both are correct
    for trading and both would silently absorb this guard, turning a test that
    tried to write into a test that quietly passed. Inheriting from
    BaseException makes the attempt impossible to miss.
    """


@pytest.fixture(autouse=True)
def _no_live_db_writes(monkeypatch):
    """Fail loudly instead of silently mutating the live trade history."""
    def _blocked(name):
        def _fail(sql, *args, **kwargs):
            statement = " ".join(str(sql).split())[:120]
            raise LiveDatabaseWriteBlocked(
                f"bot.db.{name}() was called during a test and would have "
                f"written to the LIVE database: {statement!r}\n"
                "Patch the writer in your test (e.g. "
                "monkeypatch.setattr(logbook, 'record_stop_raise', ...) or "
                "monkeypatch.setattr(logbook.db, 'execute', ...)). See "
                "tests/conftest.py for why this guard exists (IMP-043)."
            )
        return _fail

    for name in _WRITE_PATHS:
        monkeypatch.setattr(db, name, _blocked(name))


class LiveBrokerOrderBlocked(BaseException):
    """Raised when a test reaches a live order-placement path (IMP-060).

    The IMP-043 guard above blocks live *database* writes. Nothing blocked live
    *broker* writes, and on 2026-09-18 that asymmetry cost $290.16 of real paper
    equity: a test run drove ``Engine.consider_entries`` with ``dry_run=False``
    and every collaborator stubbed EXCEPT the broker, so the IMP-056 META
    fixture (price 670.80, ATR 6.40) went through the real
    ``sizing.plan_position`` -> 1 share, stop 651.60, take-profit 699.60 -> and
    out through ``execution.submit_bracket_order`` to Alpaca. Fourteen 1-share
    META bracket orders were submitted pre-market at 11:22 UTC, filled at the
    13:30 open around $686, and were swept up by the 15:55 flatten at $665.50.
    The conftest DB guard is what hid it: the trades could never be recorded, so
    ``trades`` showed zero rows for the day while the broker showed a 14-share
    round trip.

    BaseException for the same reason as ``LiveDatabaseWriteBlocked``:
    ``submit_bracket_order`` is written to never raise (it catches ``Exception``
    and returns an error dict) so a plain exception would be swallowed and the
    test would pass while the order sat live at the broker.
    """


# Mutating broker surface only. Reads (account_summary, get_positions, get_clock,
# open_position_symbols, get_order, entry_fill_price, ...) are deliberately left
# alone: several tests legitimately read the live account and a read cannot move
# money.
_EXECUTION_ORDER_PATHS = ("submit_bracket_order", "cancel_order", "replace_stop_order")
_BROKER_ORDER_PATHS = ("cancel_all_orders", "close_all_positions", "close_position")
# Backstop: catches any path that skips the module functions above, including
# `broker.trading_client().submit_order(...)` called straight from a test.
_TRADING_CLIENT_ORDER_METHODS = (
    "submit_order", "replace_order_by_id", "cancel_order_by_id", "cancel_orders",
    "close_position", "close_all_positions", "exercise_options_position",
)


def _capture_real_execution() -> dict:
    """Bind the genuine execution functions once, at import, before any patching."""
    from bot import execution

    return {name: getattr(execution, name) for name in _EXECUTION_ORDER_PATHS}


_REAL_EXECUTION = _capture_real_execution()


@pytest.fixture(autouse=True)
def _no_live_broker_orders(monkeypatch):
    """Fail loudly instead of silently placing real orders on the paper account."""
    def _blocked(where, name):
        def _fail(*args, **kwargs):
            detail = ", ".join(
                [repr(a) for a in args[:2]] + [f"{k}={v!r}" for k, v in list(kwargs.items())[:2]]
            )[:160]
            raise LiveBrokerOrderBlocked(
                f"{where}.{name}() was called during a test and would have placed "
                f"or modified a REAL order on the live paper account: ({detail})\n"
                "Stub the broker in your test (e.g. monkeypatch.setattr(execution, "
                "'submit_bracket_order', ...) or build the Engine with dry_run=True). "
                "See tests/conftest.py for why this guard exists (IMP-060)."
            )
        return _fail

    from alpaca.trading.client import TradingClient

    from bot import broker, execution

    for name in _EXECUTION_ORDER_PATHS:
        monkeypatch.setattr(execution, name, _blocked("bot.execution", name))
    for name in _BROKER_ORDER_PATHS:
        monkeypatch.setattr(broker, name, _blocked("bot.broker", name))
    for name in _TRADING_CLIENT_ORDER_METHODS:
        monkeypatch.setattr(TradingClient, name, _blocked("TradingClient", name), raising=False)


@pytest.fixture
def real_order_functions(monkeypatch):
    """Opt back in to the genuine bot.execution order functions (IMP-060).

    For the handful of tests whose subject IS one of those functions' internals.
    They must stub ``broker.trading_client`` themselves; the TradingClient
    class-level backstop stays armed either way, so an unstubbed client still
    cannot reach Alpaca. Requesting this fixture is the visible, greppable
    record that a test drives a real order path on purpose.
    """
    from bot import execution

    for name in _EXECUTION_ORDER_PATHS:
        monkeypatch.setattr(execution, name, _REAL_EXECUTION[name])
    return execution


@pytest.fixture(autouse=True)
def _legacy_tests_run_in_ma_mode(monkeypatch):
    """Every test written before IMP-059 pins MA-mode behaviour (the IMP-021
    vetoes, the IMP-022 VWAP-distance gate, MA refusal vocabulary). They keep
    doing that under the MA entry; tests of the ORB entry opt in explicitly
    (see tests/test_imp059_orb_entry.py::orb_mode), and because that fixture
    runs after this autouse one, its setattr wins.
    """
    from bot import config
    monkeypatch.setattr(config, "ENTRY_MODE", "ma")
