"""IMP-057 — scripts/refusal_audit: score the refused-candidate ledger.

Every fixture below is a REAL row from the 2026-09-16 session, the first session
``dbo.entry_refusals`` ever held data for (52 rows: underlying_held 34, cooldown
9, above_vwap 9). Prices, ATRs and timestamps are copied from the ledger, and
the expected ceilings/forward returns from that session's SIP 1-minute bars, so
the failure that motivated the instrument is what the tests assert on.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from bot import config, doctrine
from scripts import refusal_audit as RA


# --- Real ledger rows (2026-09-16) ------------------------------------------
# refusal_id / symbol / ts / reason / confidence / price / session_vwap / atr,
# exactly as logbook.get_entry_refusals returned them.
META_HELD = {
    "refusal_id": 3, "symbol": "META", "ts": datetime(2026, 9, 16, 9, 46, 51),
    "reason": "underlying_held", "detail": "underlying_held_META",
    "confidence": 60.00, "price": 677.14, "session_vwap": 679.6658, "atr": 2.6244,
}
META_COOLDOWN = {
    "refusal_id": 6, "symbol": "META", "ts": datetime(2026, 9, 16, 9, 57, 31),
    "reason": "cooldown", "detail": "cooldown_29m",
    "confidence": 60.26, "price": 680.21, "session_vwap": 679.4148, "atr": 2.8103,
}
GOOG_HELD = {
    "refusal_id": 7, "symbol": "GOOG", "ts": datetime(2026, 9, 16, 9, 58, 35),
    "reason": "underlying_held", "detail": "underlying_held_GOOG",
    "confidence": 63.18, "price": 342.72, "session_vwap": 342.2883, "atr": 0.7862,
}
TSLA_VWAP = {
    "refusal_id": 24, "symbol": "TSLA", "ts": datetime(2026, 9, 16, 10, 20, 58),
    "reason": "above_vwap", "detail": "above_vwap_+0.48%",
    "confidence": 60.19, "price": 362.21, "session_vwap": 360.4907, "atr": 1.4086,
}
INTC_VWAP = {
    "refusal_id": 51, "symbol": "INTC", "ts": datetime(2026, 9, 16, 11, 49, 28),
    "reason": "above_vwap", "detail": "above_vwap_+0.45%",
    "confidence": 60.06, "price": 102.44, "session_vwap": 101.9830, "atr": 0.4346,
}

ALL_ROWS = [META_HELD, META_COOLDOWN, GOOG_HELD, TSLA_VWAP, INTC_VWAP]


@pytest.fixture(autouse=True)
def _imp040_geometry_for_these_scenarios(monkeypatch):
    """The recorded-trade scenarios in this file were derived under IMP-040's
    0.25R ratchet (prices such as +0.25R = 100.375 are literal in the asserts).
    IMP-059 restored IMP-013's 0.5 / 1.0 / 1.0 for the ORB entry; the shipped
    constants are pinned in tests/test_exit_sim.py. These tests pin the geometry
    they describe so they keep testing the mechanics they were written for.
    """
    monkeypatch.setattr(config, "BREAKEVEN_TRIGGER_R", 0.25)
    monkeypatch.setattr(config, "TRAIL_TRIGGER_R", 0.25)
    monkeypatch.setattr(config, "TRAIL_DISTANCE_R", 0.25)
    monkeypatch.setattr(RA, "SCRATCH_CEILING_R", 0.25)
def _record(row, ceiling, flatten_pct, flatten_r=None):
    """A build_records()-shaped record, so summarize() can be tested offline."""
    geo = RA.refusal_geometry(float(row["price"]), float(row["atr"]))
    assert geo is not None
    stop, distance = geo
    return {
        "refusal_id": row["refusal_id"], "symbol": row["symbol"], "ts": row["ts"],
        "reason": row["reason"], "eligibility": row["reason"] in RA.ELIGIBILITY_REASONS,
        "confidence": float(row["confidence"]), "price": float(row["price"]),
        "atr": float(row["atr"]), "stop": stop, "ceiling": ceiling,
        "flatten_r": flatten_r if flatten_r is not None
        else float(row["price"]) * flatten_pct / 100.0 / distance,
        "flatten_pct": flatten_pct,
    }


# --- refusal_geometry: the live sizing rule, not the floor approximation -----

def test_refusal_geometry_reproduces_plan_position():
    """The stop distance is bot.sizing's own max(ATR x mult, floor%) rule."""
    from bot import sizing
    plan = sizing.plan_position("META", 62.0, 677.14, 2.6244,
                                equity=7527.50, buying_power=7527.50)
    assert plan.tradable
    stop, distance = RA.refusal_geometry(677.14, 2.6244)
    # plan_position rounds to the tick; this instrument deliberately does not.
    assert distance == pytest.approx(plan.stop_distance, abs=0.005)
    assert stop == pytest.approx(float(plan.stop_price), abs=0.005)


def test_refusal_geometry_uses_atr_when_atr_is_the_wider_term():
    """A high-ATR name must NOT be priced at the 1.5% floor."""
    price, atr = 100.0, 1.0          # 3xATR = 3.00% > the 1.5% floor
    stop, distance = RA.refusal_geometry(price, atr)
    assert distance == pytest.approx(3.0)
    assert stop == pytest.approx(97.0)


def test_refusal_geometry_uses_floor_when_atr_is_narrow():
    """GOOG on 2026-09-16: 3xATR = 0.688% of price, so the floor must bind."""
    stop, distance = RA.refusal_geometry(342.72, 0.7862)
    assert distance == pytest.approx(342.72 * config.MIN_STOP_PCT / 100.0)
    assert distance > 0.7862 * config.ATR_STOP_MULT


@pytest.mark.parametrize("price,atr", [(0, 1.0), (-1, 1.0), (100.0, 0), (100.0, -1), (None, 1.0), (100.0, None)])
def test_refusal_geometry_rejects_unusable_inputs(price, atr):
    """An unusable row is skipped, never scored at a made-up 1R."""
    assert RA.refusal_geometry(price, atr) is None


# --- geometry_binding: the measurement that retires _replay_geometry's caveat -

def test_geometry_binding_says_floor_on_every_real_row():
    """All five real 09-16 rows had 3xATR narrower than the 1.5% floor.

    This is the whole finding: gate_monitor._replay_geometry priced the blocked
    set at the floor "because ATR is not recoverable from the log", and on this
    session that was not an approximation — it was exact.
    """
    binding = RA.geometry_binding(ALL_ROWS)
    assert binding["scored"] == 5
    assert binding["floor_bound"] == 5
    assert binding["atr_bound"] == 0
    assert binding["floor_share"] == 100.0
    assert binding["median_atr_width_pct"] < config.MIN_STOP_PCT


def test_geometry_binding_counts_an_atr_bound_row():
    wide = {"symbol": "X", "price": 100.0, "atr": 1.0}     # 3.00% > 1.5%
    binding = RA.geometry_binding(ALL_ROWS + [wide])
    assert binding["scored"] == 6
    assert binding["atr_bound"] == 1
    assert binding["floor_bound"] == 5


def test_geometry_binding_skips_unusable_rows_without_crashing():
    binding = RA.geometry_binding([{"symbol": "X", "price": 0, "atr": 0}])
    assert binding["scored"] == 0
    assert binding["floor_share"] is None


# --- the doctrine vocabulary is imported, never redefined -------------------

def test_win_bar_comes_from_the_doctrine():
    """IMP-049/IMP-053 were both two instruments carrying two vocabularies."""
    assert RA.WIN_CEILING_R == doctrine.WIN_MIN_R
    assert RA.SCRATCH_CEILING_R == float(config.BREAKEVEN_TRIGGER_R)


def test_eligibility_reasons_are_the_ledger_writers_own_set():
    """The split is IMP-056's column, so it must track bot.logbook's own sets.

    Asserted by identity of contents rather than by re-listing the reasons: if a
    future IMP adds a refusal reason, this audit must classify it the way the
    writer does or fail loudly, never silently drop it into 'quality'.
    """
    from bot import logbook
    assert RA.ELIGIBILITY_REASONS == frozenset(logbook.REFUSAL_ELIGIBILITY)
    assert RA.ELIGIBILITY_REASONS.isdisjoint(logbook.REFUSAL_QUALITY)
    assert RA.ELIGIBILITY_REASONS | frozenset(logbook.REFUSAL_QUALITY) \
        == frozenset(logbook.REFUSAL_REASONS)


# --- summarize: the 2026-09-16 verdict --------------------------------------

def _real_session_records():
    """The five fixtures with their measured 09-16 SIP ceilings/returns."""
    return [
        _record(META_HELD, ceiling=0.756, flatten_pct=-0.668),
        _record(META_COOLDOWN, ceiling=0.452, flatten_pct=-1.116),
        _record(GOOG_HELD, ceiling=0.150, flatten_pct=-0.913),
        _record(TSLA_VWAP, ceiling=0.519, flatten_pct=-1.193),
        _record(INTC_VWAP, ceiling=0.189, flatten_pct=-1.586),
    ]


def test_no_refusal_was_win_feasible_on_the_real_session():
    """The headline: not one refused candidate could have produced a WIN."""
    s = RA.summarize(_real_session_records())
    assert s["overall"]["refusals"] == 5
    assert s["overall"]["win_feasible"] == 0
    assert s["overall"]["win_feasible_share"] == 0.0
    assert s["overall"]["best_ceiling"] < doctrine.WIN_MIN_R
    assert s["overall"]["mean_flatten_pct"] < 0
    # Every one fell to the flatten — the sharpest form of "the filter paid".
    assert s["overall"]["rose_to_flatten"] == 0


def test_eligibility_and_quality_are_reported_apart():
    """IMP-042's conflation must be impossible: held/cooldown != a gate veto."""
    s = RA.summarize(_real_session_records())
    assert s["eligibility"]["refusals"] == 3      # META held, META cooldown, GOOG held
    assert s["quality"]["refusals"] == 2          # TSLA, INTC above_vwap
    assert set(s["by_reason"]) == {"underlying_held", "cooldown", "above_vwap"}
    assert s["by_reason"]["underlying_held"]["eligibility"] is True
    assert s["by_reason"]["cooldown"]["eligibility"] is True
    assert s["by_reason"]["above_vwap"]["eligibility"] is False


def test_every_filter_scores_paid_on_the_real_session():
    s = RA.summarize(_real_session_records())
    assert [c["paid"] for c in s["by_reason"].values()] == ["PAID", "PAID", "PAID"]


def test_a_win_feasible_refusal_scores_the_filter_as_cost():
    """The verdict must be able to convict a filter, or it is not a test."""
    records = _real_session_records()
    records.append(_record(TSLA_VWAP, ceiling=1.4, flatten_pct=+2.0))
    s = RA.summarize(records)
    assert s["by_reason"]["above_vwap"]["win_feasible"] == 1
    assert s["by_reason"]["above_vwap"]["paid"] == "COST"
    assert s["overall"]["rose_to_flatten"] == 1


def test_an_unwinnable_refusal_that_drifted_up_is_neutral_not_paid():
    """Refusing a candidate the flatten would have banked is not a win."""
    s = RA.summarize([_record(GOOG_HELD, ceiling=0.15, flatten_pct=+0.30)])
    assert s["by_reason"]["underlying_held"]["paid"] == "neutral"


def test_scratch_feasibility_uses_the_breakeven_trigger():
    """GOOG's +0.150R ceiling never reaches the 0.25R the ratchet arms at."""
    s = RA.summarize([_record(GOOG_HELD, ceiling=0.150, flatten_pct=-0.913),
                      _record(META_COOLDOWN, ceiling=0.452, flatten_pct=-1.116)])
    assert s["overall"]["scratch_feasible"] == 1


def test_summarize_is_empty_on_no_records():
    assert RA.summarize([]) == {"refusals": 0}


def test_per_symbol_cohorts_are_present():
    s = RA.summarize(_real_session_records())
    assert set(s["by_symbol"]) == {"META", "GOOG", "TSLA", "INTC"}
    assert s["by_symbol"]["META"]["refusals"] == 2


# --- report rendering -------------------------------------------------------

def test_format_report_shows_the_geometry_line_and_both_cohorts():
    s = RA.summarize(_real_session_records())
    text = "\n".join(RA.format_report(datetime(2026, 9, 16).date(), s, ["note"]))
    assert "REFUSAL AUDIT — 2026-09-16" in text
    assert "floor bound 5/5 (100.0%)" in text
    assert "eligibility (never eligible)" in text
    assert "quality (filter vetoed)" in text
    assert "PAID" in text


def test_format_report_is_explicit_when_a_date_has_no_ledger_rows():
    """An empty day must not read as 'the bot proposed nothing'."""
    text = "\n".join(RA.format_report(datetime(2026, 9, 15).date(), {}, []))
    assert "No refusals recorded" in text
    assert "2026-09-16" in text      # names when the ledger starts


# --- the instrument must not touch the live path ----------------------------

def test_module_does_not_import_the_engine_or_execution():
    """A diagnostic that can reach the order path is a diagnostic that can trade."""
    import inspect
    src = inspect.getsource(RA)
    assert "from bot import config, logbook" in src
    for banned in ("execution", "broker", "engine"):
        assert f"from bot import {banned}" not in src
        assert f"import bot.{banned}" not in src
