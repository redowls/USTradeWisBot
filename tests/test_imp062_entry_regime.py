"""IMP-062 — the escalation clause must describe ONE entry strategy.

Motivating session: **2026-09-21**, the first ORB session with fills (IMP-059
switched the entry on 09-18). The escalation window that night was
``2026-09-16 / 09-17 / 09-21`` = **six MA-ribbon trades plus three ORB**, and it
reported ``escalated=True, fail_scratch_share=88.9%`` as though that judged the
live bot. Two thirds of the evidence came from an entry that no longer exists.

IMP-060 and IMP-061 both had to correct this by hand, in prose, in the
improvement log ("every one of those sessions is MA-entry history"; "the clause
now has to re-prove itself against the ORB book"). This file pins the fix so the
correction lives in code instead.

Two properties matter and are tested separately:

1. A regime-filtered verdict picks that strategy's OWN last N sessions.
2. ``escalated=False`` is never ambiguous — a brand-new strategy reports
   ``insufficient-sessions`` (unknown), not a clean pass.

★ The anti-gaming property is tested too: making the mixing VISIBLE must not
make the blended escalation stop firing. A measurement fix that quietly
unlatched the gate barring parameter tweaks would be a loosened safety rule
wearing a measurement fix's clothes.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from bot import doctrine


def _row(symbol, signal_type, entry, stop, exit_price, reason, pl,
         exit_time, entry_time=None):
    return {
        "symbol": symbol,
        "signal_type": signal_type,
        "entry_price": entry,
        "stop_price": stop,
        "exit_price": exit_price,
        "exit_reason": reason,
        "realized_pl": pl,
        "entry_time": entry_time or exit_time,
        "exit_time": exit_time,
    }


# --- the real 2026-09-21 book (ORB), broker- and DB-verified ----------------
# META  fill 715.74, plan stop 701.75, TP fill 735.295 -> profit_R +1.398 WIN
# MSFT  fill 496.99, plan stop 489.04, flatten  500.84 -> profit_R +0.484 SCRATCH
# INTC  fill 120.392, plan stop 117.11, stop    121.20 -> profit_R +0.246 FAIL/break-even
META_0921 = _row("META", "ORB", 715.74, 701.75, 735.295, "TAKE_PROFIT", 39.11,
                 datetime(2026, 9, 21, 13, 16, 42),
                 datetime(2026, 9, 21, 10, 5, 42))
MSFT_0921 = _row("MSFT", "ORB", 496.99, 489.04, 500.84, "EOD_FLATTEN", 15.40,
                 datetime(2026, 9, 21, 15, 55, 43),
                 datetime(2026, 9, 21, 10, 5, 54))
INTC_0921 = _row("INTC", "ORB", 120.392, 117.11, 121.20, "STOP", 8.08,
                 datetime(2026, 9, 21, 13, 25, 25),
                 datetime(2026, 9, 21, 10, 21, 0))
ORB_0921 = [META_0921, MSFT_0921, INTC_0921]

# --- the MA-ribbon sessions that shared the window -------------------------
MA_0916 = [
    _row("AMD", "MA", 100.0, 97.0, 97.0, "STOP", -30.0,
         datetime(2026, 9, 16, 11, 0, 0)),
    _row("NKE", "BOTH", 80.0, 77.0, 80.1, "STOP", 1.0,
         datetime(2026, 9, 16, 12, 0, 0)),
]
MA_0917 = [
    _row("KO", "MA", 60.0, 58.0, 60.2, "STOP", 2.0,
         datetime(2026, 9, 17, 11, 0, 0)),
    _row("PEP", "MA", 150.0, 146.0, 150.5, "EOD_FLATTEN", 5.0,
         datetime(2026, 9, 17, 14, 0, 0)),
]
MIXED_BOOK = MA_0916 + MA_0917 + ORB_0921


# --- regime attribution ----------------------------------------------------

def test_orb_and_ma_ribbon_are_separate_regimes():
    assert doctrine.entry_regime(META_0921) == "orb"
    assert doctrine.entry_regime(MA_0916[0]) == "ma-ribbon"


@pytest.mark.parametrize("signal_type", ["MA", "BOTH", "BREAKOUT"])
def test_every_pre_orb_signal_type_maps_to_the_retired_regime(signal_type):
    """All three came out of the same ribbon + level-break scorer."""
    row = dict(META_0921, signal_type=signal_type)
    assert doctrine.entry_regime(row) == "ma-ribbon"


@pytest.mark.parametrize("signal_type", [None, "", "SOMETHING_NEW"])
def test_unknown_signal_type_is_unattributed_not_defaulted(signal_type):
    """Attributing a trade to the WRONG strategy is worse than not attributing."""
    assert doctrine.entry_regime(dict(META_0921, signal_type=signal_type)) is None


def test_by_regime_drops_unattributable_rows_rather_than_pooling_them():
    book = ORB_0921 + [dict(MA_0916[0], signal_type=None)]
    split = doctrine.by_regime(book)
    assert set(split) == {"orb"}
    assert len(split["orb"]) == 3


def test_signal_type_matching_is_case_insensitive():
    assert doctrine.entry_regime(dict(META_0921, signal_type="orb")) == "orb"


# --- the 2026-09-21 defect, pinned -----------------------------------------

def test_unfiltered_window_on_2026_09_21_blends_two_strategies():
    """The defect: 6 MA-ribbon + 3 ORB, reported as one verdict."""
    v = doctrine.escalation_verdict(MIXED_BOOK)
    assert v["sessions"] == ["2026-09-16", "2026-09-17", "2026-09-21"]
    assert v["regimes_in_window"] == {"ma-ribbon": 4, "orb": 3}
    assert v["mixed"] is True


def test_mixed_window_still_escalates():
    """★ Anti-gaming: surfacing the blend must not unlatch the gate.

    The clause bars parameter tweaks. If making mixing visible also made the
    escalation stop firing, this 'measurement fix' would be a loosened safety
    rule — the one thing the doctrine forbids outright.
    """
    v = doctrine.escalation_verdict(MIXED_BOOK)
    assert v["escalated"] is True
    assert v["reason"] == doctrine.ESCALATED


def test_filtering_to_orb_picks_orbs_own_sessions_not_the_calendars():
    v = doctrine.escalation_verdict(MIXED_BOOK, regime="orb")
    assert v["sessions"] == ["2026-09-21"]
    assert v["regimes_in_window"] == {"orb": 3}
    assert v["mixed"] is False
    assert v["summary"]["trades"] == 3


def test_orb_on_one_session_reports_unknown_not_a_clean_pass():
    """★ 'Don't report fine when you don't know' (IMP-061's principle).

    ORB's first session was 3/3 headline wins. Reporting escalated=False there
    would read as a clean bill of health for a strategy with n=3.
    """
    v = doctrine.escalation_verdict(MIXED_BOOK, regime="orb")
    assert v["escalated"] is False
    assert v["reason"] == doctrine.INSUFFICIENT_SESSIONS


def test_below_threshold_is_distinguishable_from_insufficient_evidence():
    """Both return escalated=False; only `reason` tells them apart."""
    good = [
        _row("A", "ORB", 100.0, 90.0, 120.0, "TAKE_PROFIT", 20.0,
             datetime(2026, 9, 21, 12, 0, 0)),
        _row("B", "ORB", 100.0, 90.0, 120.0, "TAKE_PROFIT", 20.0,
             datetime(2026, 9, 22, 12, 0, 0)),
        _row("C", "ORB", 100.0, 90.0, 120.0, "TAKE_PROFIT", 20.0,
             datetime(2026, 9, 23, 12, 0, 0)),
    ]
    v = doctrine.escalation_verdict(good, regime="orb")
    assert v["escalated"] is False
    assert v["reason"] == doctrine.BELOW_THRESHOLD
    assert v["summary"]["true_win_rate"] == 100.0


def test_empty_book_reports_no_trades():
    v = doctrine.escalation_verdict([])
    assert v["escalated"] is False
    assert v["reason"] == doctrine.NO_TRADES


def test_filtering_to_a_regime_with_no_trades_is_not_an_escalation():
    v = doctrine.escalation_verdict(ORB_0921, regime="ma-ribbon")
    assert v["escalated"] is False
    assert v["reason"] == doctrine.NO_TRADES
    assert v["summary"]["trades"] == 0


# --- the per-regime split ---------------------------------------------------

def test_escalation_by_regime_judges_each_strategy_on_its_own_book():
    per = doctrine.escalation_by_regime(MIXED_BOOK)
    assert set(per) == {"ma-ribbon", "orb"}
    # The retired book carries the escalation; ORB is simply not yet known.
    assert per["ma-ribbon"]["summary"]["trades"] == 4
    assert per["ma-ribbon"]["fail_scratch_share"] == 100.0
    assert per["orb"]["reason"] == doctrine.INSUFFICIENT_SESSIONS
    assert per["orb"]["summary"]["trades"] == 3


def test_per_regime_verdicts_are_never_mixed_by_construction():
    for v in doctrine.escalation_by_regime(MIXED_BOOK).values():
        assert v["mixed"] is False


def test_orb_true_win_rate_on_its_debut_is_one_of_three():
    """The day's headline was 3W/0L; the doctrine says one WIN."""
    s = doctrine.escalation_by_regime(MIXED_BOOK)["orb"]["summary"]
    assert (s["win"], s["scratch"], s["fail"]) == (1, 1, 1)
    assert s["true_win_rate"] == pytest.approx(33.3, abs=0.1)
    assert s["headline_win_rate"] == 100.0
    assert s["fail_kinds"]["break-even"] == 1


# --- backward compatibility -------------------------------------------------

def test_default_call_is_unchanged_for_a_single_regime_book():
    """No regime arg on a pure book must behave exactly as before IMP-062."""
    plain = doctrine.escalation_verdict(ORB_0921)
    filtered = doctrine.escalation_verdict(ORB_0921, regime="orb")
    for key in ("escalated", "sessions", "fail_scratch_share", "summary"):
        assert plain[key] == filtered[key]


def test_capital_protection_invariants_untouched():
    """IMP-062 is pure measurement — bot/doctrine.py is not in the order path."""
    from bot import config, secrets
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert secrets.ALPACA_PAPER is True
