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
