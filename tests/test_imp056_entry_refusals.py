"""IMP-056 tests — the refused-candidate ledger, fixtured on 2026-09-15.

That session is the reason this exists. The bot generated **34 entry candidates
and filled none of them**: META x25, BAC x5, CRM x2, GOOG x1, INTC x1, every one
refused by the IMP-022 VWAP gate. `daily_summary` recorded 0 buys / 0 sells /
$0.00, `signals` recorded NOTHING (it only ever gets a row once a trade_id
exists), and so the entire day's decision record lived exclusively as
``ENTRY SKIPPED`` lines in /var/log/ustradewisbot/bot.log — which rotates daily
and keeps 14 (/etc/logrotate.d/ustradewisbot).

This is IMP-043's defect on the entry side. IMP-043 moved the ratchet's evidence
out of that same rotating log and into ``trades.stop_raises`` /
``trades.final_stop_price`` precisely because "IMP-040's evidence expires at
about the moment its verdict is due". The refused-candidate stream is the larger
population by an order of magnitude — 34 candidates on a day with 0 fills — it
is the only sample big enough to judge the entry signal that 16 refuted
discriminators have failed to fix, and ~39 days of it (2026-07-25 post-gate
start to 14 days ago) is already gone.

The numbers below are the real 09-15 log lines, not invented ones.
"""

from datetime import timedelta

import pytest

from bot import broker, config, confidence, data, engine, exits, logbook, signals

# 2026-09-15 14:21:35 EDT | ENTRY SKIPPED META: entry 670.80 is +0.33% above
# session VWAP 668.62 (>0.25% — stretched fill, fades)
META_PRICE = 670.80
META_VWAP = 668.62
META_ATR = 6.40          # ~0.95% of price; below the 1.5% MIN_STOP_PCT floor
META_CONF = 61.30

# 2026-09-15 15:00:48 EDT | ENTRY SKIPPED BAC: entry 59.77 is +0.71% above
# session VWAP 59.35 — the day's most stretched refusal.
BAC_PRICE = 59.77
BAC_VWAP = 59.35


def _ev(symbol: str, price: float, vwap: float, atr: float = META_ATR) -> dict:
    return {"symbol": symbol, "signal_type": "MA", "close": price,
            "atr": atr, "session_vwap": vwap}


def _run(monkeypatch, evs, *, dry_run: bool, held=frozenset(), activity=None):
    """Drive consider_entries and capture what reached the refusal ledger."""
    now = exits.now_et().replace(hour=14, minute=21, second=35, microsecond=0)
    monkeypatch.setattr(exits, "entries_allowed", lambda _now: True)
    monkeypatch.setattr(broker, "account_summary",
                        lambda: {"equity": 7_527.50, "buying_power": 7_527.50})
    monkeypatch.setattr(broker, "open_position_symbols", lambda: set(held))
    monkeypatch.setattr(logbook, "open_trade_symbols", lambda: set())
    monkeypatch.setattr(logbook, "get_today_realized_pl", lambda _d: 0.0)
    monkeypatch.setattr(logbook, "get_symbol_activity_today",
                        lambda _d: dict(activity or {}))
    monkeypatch.setattr(signals, "evaluate_watchlist", lambda: list(evs))
    monkeypatch.setattr(confidence, "score", lambda _ev: META_CONF)
    monkeypatch.setattr(data, "latest_trade_price", lambda _s: None)

    writes: list[list[dict]] = []
    monkeypatch.setattr(logbook, "record_entry_refusals",
                        lambda rows: writes.append(list(rows)) or len(rows))

    eng = engine.Engine(dry_run=dry_run)
    monkeypatch.setattr(eng, "_log", lambda _m: None)
    return eng.consider_entries(now=now), writes


# --- the 2026-09-15 session, recorded ---------------------------------------

def test_the_0915_meta_refusal_becomes_a_durable_row(monkeypatch):
    """The day's first refusal, with everything needed to replay it later."""
    actions, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                           dry_run=False)

    assert actions[0]["action"] == "skip"
    assert writes, "a refused candidate left no ledger row — the 09-15 defect"
    (row,) = writes[0]
    assert row["symbol"] == "META"
    assert row["reason"] == "above_vwap"
    assert row["detail"] == "above_vwap_+0.33%"      # the real log line's number
    assert row["price"] == pytest.approx(META_PRICE)
    assert row["session_vwap"] == pytest.approx(META_VWAP)
    assert row["confidence"] == pytest.approx(META_CONF)
    assert row["signal_type"] == "MA"
    assert row["ts"] is not None and row["ts"].tzinfo is None   # naive ET


def test_atr_is_carried_because_the_log_cannot_carry_it(monkeypatch):
    """The one field that makes the gate counterfactual honest.

    ``scripts.gate_monitor._replay_geometry`` says it in its own docstring:
    "Uses the MIN_STOP_PCT floor rather than 3xATR because ATR is not
    recoverable from the log." Every VWAP counterfactual this repo has run —
    including 2026-09-15's — therefore priced the stop at the flat 1.5% floor
    rather than the 3xATR stop the bot would really have used. META's 09-15 ATR
    puts 3xATR at ~2.86% of price, nearly TWICE the floor, so the two geometries
    are not interchangeable and the approximation is not free.
    """
    _, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                     dry_run=False)
    (row,) = writes[0]
    assert row["atr"] == pytest.approx(META_ATR)
    real_stop_pct = config.ATR_STOP_MULT * META_ATR / META_PRICE * 100.0
    assert real_stop_pct > config.MIN_STOP_PCT, (
        "fixture must keep the real stop above the floor, or it proves nothing")


def test_every_refusal_of_a_multi_symbol_session_is_kept(monkeypatch):
    """09-15 refused 5 distinct symbols; a ledger that keeps one is no ledger."""
    _, writes = _run(monkeypatch,
                     [_ev("META", META_PRICE, META_VWAP),
                      _ev("BAC", BAC_PRICE, BAC_VWAP, atr=0.55)],
                     dry_run=False)
    (batch,) = writes
    assert {r["symbol"] for r in batch} == {"META", "BAC"}
    assert all(r["reason"] == "above_vwap" for r in batch)


def test_ledger_is_flushed_once_per_tick_not_once_per_refusal(monkeypatch):
    """A write per refusal would sit between a gate decision and an order."""
    _, writes = _run(monkeypatch,
                     [_ev("META", META_PRICE, META_VWAP),
                      _ev("BAC", BAC_PRICE, BAC_VWAP, atr=0.55),
                      _ev("CRM", 262.33, 256.89, atr=2.4)],
                     dry_run=False)
    assert len(writes) == 1
    assert len(writes[0]) == 3


# --- IMP-042's distinction, kept first-class --------------------------------

def test_eligibility_refusals_are_not_filed_as_quality_refusals(monkeypatch):
    """A held symbol is 'could not buy', not 'judged the price bad'.

    IMP-042 had to unpick exactly this conflation out of the log (2026-08-26:
    9 of 31 TSM 'refusals' were a symbol already in the book). Recording the
    reason as a column means the next audit never has to.
    """
    _, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                     dry_run=False, held={"META"})
    (row,) = writes[0]
    assert row["reason"] == "underlying_held"
    assert row["reason"] in logbook.REFUSAL_ELIGIBILITY
    assert row["reason"] not in logbook.REFUSAL_QUALITY


def test_cooldown_refusal_files_under_eligibility(monkeypatch):
    now_naive = exits.now_et().replace(
        hour=14, minute=21, second=35, microsecond=0,
    ).astimezone(config.MARKET_TZ).replace(tzinfo=None)
    activity = {"META": {"entries": 1, "last_exit": now_naive - timedelta(minutes=5)}}
    _, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                     dry_run=False, activity=activity)
    (row,) = writes[0]
    assert row["reason"] == "cooldown"
    assert row["detail"].startswith("cooldown_")
    assert row["reason"] in logbook.REFUSAL_ELIGIBILITY


def test_max_entries_refusal_files_under_eligibility(monkeypatch):
    activity = {"META": {"entries": config.MAX_ENTRIES_PER_SYMBOL_PER_DAY,
                         "last_exit": None}}
    _, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                     dry_run=False, activity=activity)
    (row,) = writes[0]
    assert row["reason"] == "max_entries_per_symbol"


def test_engine_never_invents_a_reason_outside_the_vocabulary(monkeypatch):
    """A typo'd category is a silently lost cohort, so pin the vocabulary."""
    cases = [
        ({}, frozenset()),
        ({}, {"META"}),
        ({"META": {"entries": config.MAX_ENTRIES_PER_SYMBOL_PER_DAY,
                   "last_exit": None}}, frozenset()),
    ]
    for activity, held in cases:
        _, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                         dry_run=False, held=held, activity=activity)
        for row in writes[0]:
            assert row["reason"] in logbook.REFUSAL_REASONS


def test_eligibility_and_quality_reasons_do_not_overlap():
    assert not set(logbook.REFUSAL_ELIGIBILITY) & set(logbook.REFUSAL_QUALITY)
    assert len(set(logbook.REFUSAL_REASONS)) == len(logbook.REFUSAL_REASONS)


# --- blast radius: nothing about trading may change -------------------------

def test_action_dicts_are_unchanged(monkeypatch):
    """The refusal ledger must be invisible to every existing consumer.

    tests/test_entry_gate_ordering.py, test_underlying_guard.py and
    test_entry_slippage_guard.py all assert against these dicts.
    """
    actions, _ = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                      dry_run=False)
    assert actions == [{"symbol": "META", "confidence": META_CONF,
                        "action": "skip", "detail": "above_vwap_+0.33%"}]


def test_dry_run_records_nothing(monkeypatch):
    """scripts/check_engine.py runs dry; it must stay a pure read."""
    actions, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                           dry_run=True)
    assert actions[0]["detail"] == "above_vwap_+0.33%"
    assert writes == []


def test_a_session_with_no_refusals_writes_nothing(monkeypatch):
    _, writes = _run(monkeypatch, [], dry_run=False)
    assert writes == []


# --- the writer itself ------------------------------------------------------

def test_writer_never_raises_when_the_database_is_down(monkeypatch):
    """A lost measurement is acceptable; a lost tick of trading is not."""
    def _boom(_sql, _rows):
        raise RuntimeError("SQL Server unreachable")
    monkeypatch.setattr(logbook.db, "executemany", _boom)
    assert logbook.record_entry_refusals(
        [{"symbol": "META", "ts": None, "reason": "above_vwap"}]) == 0


def test_writer_does_not_swallow_the_conftest_write_guard(monkeypatch):
    """IMP-043's lesson: a BaseException-swallowing writer hides a live write.

    tests/conftest.py raises ``LiveDatabaseWriteBlocked`` — a BaseException, NOT
    an Exception, chosen exactly so that production code written to swallow
    database failures cannot absorb it and turn a test that tried to write into
    one that quietly passed. This writer must catch Exception only. Restated
    with a local stand-in rather than the real guard class so the test is
    hermetic: pytest loads conftest as top-level ``conftest``, so importing
    ``tests.conftest`` would build a SECOND, non-identical class object.
    """
    class Guard(BaseException):
        pass

    def _blocked(_sql, _rows):
        raise Guard("live write blocked")

    monkeypatch.setattr(logbook.db, "executemany", _blocked)
    with pytest.raises(Guard):
        logbook.record_entry_refusals([{"symbol": "META", "reason": "above_vwap"}])


def test_an_overlong_detail_cannot_cost_the_whole_tick(monkeypatch):
    """One long string must not take 33 good rows down with it.

    The batch is a single executemany, so a value wider than the column would
    fail the entire statement, not just its own row.
    """
    captured = {}
    monkeypatch.setattr(logbook.db, "executemany",
                        lambda sql, rows: captured.setdefault("rows", list(rows))
                        or len(rows))
    logbook.record_entry_refusals([
        {"symbol": "META", "reason": "not_tradable", "detail": "x" * 200},
        {"symbol": "BAC", "reason": "above_vwap", "detail": "above_vwap_+0.71%"},
    ])
    assert len(captured["rows"]) == 2
    assert len(captured["rows"][0][3]) == logbook.REFUSAL_DETAIL_MAX
    assert captured["rows"][1][3] == "above_vwap_+0.71%"   # short ones untouched


def test_every_detail_the_engine_builds_fits_the_column(monkeypatch):
    """The guard above is insurance; today nothing should actually need it."""
    _, writes = _run(monkeypatch, [_ev("META", META_PRICE, META_VWAP)],
                     dry_run=False)
    for row in writes[0]:
        assert len(row["detail"]) <= logbook.REFUSAL_DETAIL_MAX


def test_success_count_ignores_the_drivers_rowcount(monkeypatch):
    """pyodbc returns -1 for a fast_executemany batch, whatever it inserted.

    Verified against the live table on 2026-09-16: a one-row batch stored every
    field correctly and still reported -1. Returning that would make the
    documented "0 on failure" contract indistinguishable from success.
    """
    monkeypatch.setattr(logbook.db, "executemany", lambda _sql, _rows: -1)
    rows = [{"symbol": "META", "reason": "above_vwap"},
            {"symbol": "BAC", "reason": "above_vwap"}]
    assert logbook.record_entry_refusals(rows) == 2


def test_empty_batch_does_not_touch_the_database(monkeypatch):
    calls = []
    monkeypatch.setattr(logbook.db, "executemany",
                        lambda *a, **k: calls.append(a))
    assert logbook.record_entry_refusals([]) == 0
    assert calls == []


def test_blank_detail_is_stored_as_null(monkeypatch):
    """`not_tradable` can carry an empty skip_reason; don't store ''."""
    captured = {}
    monkeypatch.setattr(logbook.db, "executemany",
                        lambda sql, rows: captured.setdefault("rows", list(rows))
                        or len(rows))
    logbook.record_entry_refusals(
        [{"symbol": "META", "reason": "not_tradable", "detail": ""}])
    assert captured["rows"][0][3] is None


def test_row_column_order_matches_the_insert(monkeypatch):
    """Nine placeholders, nine values, in the schema's order."""
    captured = {}
    monkeypatch.setattr(logbook.db, "executemany",
                        lambda sql, rows: captured.update(sql=sql, rows=list(rows))
                        or len(rows))
    logbook.record_entry_refusals([{
        "symbol": "META", "ts": None, "reason": "above_vwap",
        "detail": "above_vwap_+0.33%", "confidence": META_CONF,
        "signal_type": "MA", "price": META_PRICE, "session_vwap": META_VWAP,
        "atr": META_ATR,
    }])
    values = captured["rows"][0]
    assert len(values) == captured["sql"].count("?") == 9
    assert values[0] == "META"
    assert values[2] == "above_vwap"
    assert values[6] == META_PRICE
    assert values[7] == META_VWAP
    assert values[8] == META_ATR
