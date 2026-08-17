"""IMP-033 regression tests — the EOD flatten must get flat on the FIRST pass.

IMP-002 made `flatten_all` cancel working orders before closing each position,
which was necessary but not sufficient: `cancel_orders()` returns BEFORE the
cancels settle, so the closes still raced them.

The 2026-08-13 broker record is the fixture below. Alpaca's own timestamps:

    19:55:23.596Z  bracket STOP legs canceled   (GOOG, NVDA, QQQ)
    19:55:23.6-24  close_position() x3          -> rejected, ZERO orders created
    19:55:26.706Z  bracket LIMIT legs canceled  (3.1s after the stop legs)
    19:56:25.4-25.8 close_position() x3 (pass 2) -> accepted
    19:56:26.885Z  QQQ fill        19:56:29.174Z  GOOG fill (3.8s after submit)

So pass 1 submitted nothing at all and burned a whole 60s poll, and the engine's
own position re-check then fired a second spurious "incomplete" because it ran
while the pass-2 market sells were still in flight. Same first-pass failure on
10 of the last 10 sessions (2026-07-31 .. 2026-08-13), needing a SECOND retry on
6 of them — leaving the bot long at 15:57 with five minutes to the close.

These tests pin: shares released before liquidating, flat before returning,
both waits bounded, and every wait failing OPEN so a broker problem can only
shorten the flatten, never stall it.
"""

import pytest

from bot import broker, config, exits


class FakeBroker:
    """Alpaca's async cancel/fill behaviour, timed off the 08-13 record.

    `release_after` / `fill_after` count position probes (one per poll), so at
    the live FLATTEN_SETTLE_POLL_SEC of 0.5s the defaults reproduce the real
    3.1s leg-cancel and 3.8s fill latencies.
    """

    def __init__(self, positions, release_after=7, fill_after=8, cancel_raises=False):
        self.qty = dict(positions)
        # release_after=0 means "no leg ever held these shares"; otherwise the
        # bracket legs hold them until `release_after` probes past the cancel.
        self.available = dict(positions) if release_after == 0 else {s: 0 for s in positions}
        self.release_after = release_after
        self.fill_after = fill_after
        self.cancel_raises = cancel_raises
        self.cancelled_at = None
        self.probes = 0
        self.closed: list[str] = []
        self.rejected: list[str] = []
        self.pending_fill: dict[str, int] = {}

    # --- broker surface ---
    def cancel_all_orders(self):
        if self.cancel_raises:
            raise ConnectionError("paper-api.alpaca.markets: connection refused")
        self.cancelled_at = self.probes

    def get_positions(self):
        self.probes += 1
        if self.cancelled_at is not None and self.probes - self.cancelled_at >= self.release_after:
            self.available = dict(self.qty)              # legs finally released
        for sym, at in list(self.pending_fill.items()):
            if self.probes - at >= self.fill_after:
                self.qty.pop(sym, None)
                self.available.pop(sym, None)
                self.pending_fill.pop(sym)
        return [_Pos(sym, q, self.available.get(sym, 0)) for sym, q in self.qty.items()]

    def close_position(self, symbol):
        if self.available.get(symbol, 0) < self.qty.get(symbol, 0):
            self.rejected.append(symbol)
            raise RuntimeError('{"code":42210000,"message":"held_for_orders"}')
        self.closed.append(symbol)
        self.pending_fill[symbol] = self.probes


class _Pos:
    def __init__(self, symbol, qty, qty_available):
        self.symbol = symbol
        self.qty = str(qty)
        self.qty_available = str(qty_available)
        self.avg_entry_price = "1.0"
        self.market_value = "1.0"
        self.unrealized_pl = "0.0"


# The three positions the bot actually held into 15:55 ET on 2026-08-13.
AUG13 = {"GOOG": 7, "NVDA": 11, "QQQ": 3}


@pytest.fixture
def wired(monkeypatch):
    """Install a FakeBroker plus a sleep that only counts, never waits."""
    slept: list[float] = []

    def _install(fake):
        monkeypatch.setattr(broker, "cancel_all_orders", fake.cancel_all_orders)
        monkeypatch.setattr(broker, "get_positions", fake.get_positions)
        monkeypatch.setattr(broker, "close_position", fake.close_position)
        return fake, slept, slept.append
    return _install


# --- 1. the regression: 2026-08-13's first pass must now liquidate ------------

def test_imp033_first_pass_liquidates_the_aug13_book(wired):
    fake, slept, sleep = wired(FakeBroker(AUG13))
    snap = exits.flatten_all("EOD_FLATTEN", sleep=sleep)

    assert sorted(fake.closed) == ["GOOG", "NVDA", "QQQ"], (
        "all three positions must be liquidated on the FIRST pass — the live run "
        "submitted zero orders at 19:55:23.6Z and had to wait a full 60s poll")
    assert fake.rejected == [], "no close may be rejected once the legs have settled"
    assert not any(s.get("flatten_error") for s in snap)
    assert broker.get_positions() == [], (
        "flatten_all must not return until the book is verifiably flat, or the "
        "caller's IMP-002 re-check fires a spurious 'incomplete' (19:56:26 ET)")


def test_imp033_without_the_wait_the_first_pass_submits_nothing(wired, monkeypatch):
    """Control: the pre-IMP-033 behaviour, i.e. exactly what happened live."""
    monkeypatch.setattr(config, "FLATTEN_SETTLE_TIMEOUT_SEC", 0.0)
    fake, _slept, sleep = wired(FakeBroker(AUG13))
    snap = exits.flatten_all("EOD_FLATTEN", sleep=sleep)

    assert fake.closed == [], "no wait -> the closes race the async cancel and all fail"
    assert sorted(fake.rejected) == ["GOOG", "NVDA", "QQQ"]
    # ...and the failures are now visible instead of silently swallowed.
    assert all("held_for_orders" in s["flatten_error"] for s in snap)


# --- 1b. IMP-034: the fill phase needs its own budget ------------------------
#
# IMP-033's first live session (2026-08-14) fixed the submission but exposed the
# next link. Alpaca's own timestamps:
#
#     19:55:11.478Z  bracket STOP legs canceled    (AAPL, META, SPY)
#     19:55:16.43Z   bracket LIMIT legs canceled   (5.0s after the stop legs)
#     19:55:16.7-17  close_position() x3 (pass 1)  -> ACCEPTED, orders created
#     19:55:20.5-20.7  submitted (3.8s of queueing, vs <=0.12s on every other
#                      session in the 07-24..08-14 sample)
#     19:55:29.2-31.7  filled  (12.4-15.0s after creation)
#
# The shared 8s budget expired at ~19:55:25, so flatten_all returned with the
# sells still working and engine.eod_flatten logged "EOD flatten incomplete —
# 3 position(s) still open" at 15:55:26 over a book that was flat 5s later. The
# exits were then only recorded on the next poll (DB exit_time 15:56:28 vs the
# true 15:55:29 fill).

AUG14 = {"AAPL": 8, "META": 4, "SPY": 3}
# probes at the 0.5s poll: 10 -> the real 5.0s leg cancel, 30 -> the real 15.0s fill.
AUG14_TIMING = {"release_after": 10, "fill_after": 30}


def test_imp034_slow_fills_still_confirm_flat_on_the_first_pass(wired):
    fake, slept, sleep = wired(FakeBroker(AUG14, **AUG14_TIMING))
    snap = exits.flatten_all("EOD_FLATTEN", sleep=sleep)

    assert sorted(fake.closed) == ["AAPL", "META", "SPY"]
    assert not any(s.get("flatten_error") for s in snap)
    assert broker.get_positions() == [], (
        "a 15s fill must still be waited out — otherwise the caller raises a "
        "false 'EOD flatten incomplete', the same alarm a genuine stranded "
        "position uses, and defers the exit records a whole 60s poll")
    assert sum(slept) < 60, "the whole flatten must still fit inside one poll"


def test_imp034_the_old_shared_budget_reproduces_the_false_incomplete(wired, monkeypatch):
    """Control: 8s for the fill phase is exactly what happened live on 08-14."""
    monkeypatch.setattr(config, "FLATTEN_FILL_TIMEOUT_SEC",
                        config.FLATTEN_SETTLE_TIMEOUT_SEC)
    fake, _slept, sleep = wired(FakeBroker(AUG14, **AUG14_TIMING))
    snap = exits.flatten_all("EOD_FLATTEN", sleep=sleep)

    assert sorted(fake.closed) == ["AAPL", "META", "SPY"], "pass 1 still submits (IMP-033)"
    assert not any(s.get("flatten_error") for s in snap), "nothing was rejected"
    assert len(broker.get_positions()) == 3, (
        "under the old 8s budget the wait expires with the sells in flight — "
        "the caller then reports 3 positions 'still open after liquidation'")


def test_imp034_fill_budget_covers_the_worst_session_on_record():
    """36 EOD liquidations, 07-24..08-14: median 2.8s, p90 8.7s, max 15.0s."""
    assert config.FLATTEN_FILL_TIMEOUT_SEC >= 15.0 * 1.5, (
        "must clear the worst measured fill with margin")
    assert (config.FLATTEN_SETTLE_TIMEOUT_SEC + config.FLATTEN_FILL_TIMEOUT_SEC) < 60.0, (
        "both phases must fit inside one 60s poll of the 15:55->16:00 runway")


# --- 2. bounded, and failing open --------------------------------------------

def test_imp033_waits_are_bounded_when_the_broker_never_settles(wired):
    """A broker that never releases must not stall the loop, and must still try."""
    fake, slept, sleep = wired(FakeBroker(AUG13, release_after=10**6, fill_after=10**6))
    snap = exits.flatten_all("EOD_FLATTEN", sleep=sleep)

    budget = config.FLATTEN_SETTLE_TIMEOUT_SEC + config.FLATTEN_FILL_TIMEOUT_SEC
    assert sum(slept) <= budget, f"total wait {sum(slept)}s must stay inside {budget}s"
    assert budget < 60, "both phases together must fit well inside one 60s poll"
    assert sorted(fake.rejected) == ["GOOG", "NVDA", "QQQ"], "must fail OPEN and still attempt"
    assert all(s.get("flatten_error") for s in snap)
    # IMP-034: nothing was accepted, so there is no fill to wait for — hand back
    # to IMP-002's retry immediately instead of burning the fill budget too.
    assert sum(slept) <= config.FLATTEN_SETTLE_TIMEOUT_SEC, (
        "a fully rejected pass must skip the fill wait entirely")


def test_imp033_cancel_failure_still_attempts_liquidation(wired):
    """IMP-002's invariant: a failed cancel must never skip the liquidation."""
    fake, _slept, sleep = wired(FakeBroker(AUG13, release_after=0, cancel_raises=True))
    exits.flatten_all("EOD_FLATTEN", sleep=sleep)
    assert sorted(fake.closed) == ["GOOG", "NVDA", "QQQ"]


def test_imp033_probe_errors_are_treated_as_not_settled(monkeypatch, wired):
    """A transient API error during a settle probe must not abort the flatten.

    (The pre-flatten snapshot read is deliberately NOT covered here: if that
    raises there is nothing to liquidate yet, and tick()'s handler retries.)
    """
    fake, _slept, sleep = wired(FakeBroker(AUG13, release_after=3))
    real_get = fake.get_positions
    calls = {"n": 0}

    def _flaky():
        calls["n"] += 1
        if calls["n"] in (2, 3):       # 1 is the snapshot; 2-3 are settle probes
            raise ConnectionError("Max retries exceeded with url: /v2/positions")
        return real_get()
    monkeypatch.setattr(broker, "get_positions", _flaky)
    exits.flatten_all("EOD_FLATTEN", sleep=sleep)      # must not raise
    assert sorted(fake.closed) == ["GOOG", "NVDA", "QQQ"]


def test_imp033_no_positions_is_a_fast_noop(wired):
    fake, slept, sleep = wired(FakeBroker({}))
    assert exits.flatten_all("EOD_FLATTEN", sleep=sleep) == []
    assert slept == [], "nothing held -> no cancel, no wait"
    assert fake.cancelled_at is None


# --- 3. shares_released semantics --------------------------------------------

def test_shares_released_blocks_while_a_leg_holds_the_shares():
    assert exits.shares_released([_Pos("GOOG", 7, 0)]) is False
    assert exits.shares_released([_Pos("GOOG", 7, 3)]) is False
    assert exits.shares_released([_Pos("GOOG", 7, 7)]) is True
    assert exits.shares_released([]) is True


def test_shares_released_ignores_a_missing_qty_available():
    """A broker that doesn't report the field must never stall the flatten."""
    class Bare:
        symbol, qty, qty_available = "GOOG", "7", None
    assert exits.shares_released([Bare()]) is True
