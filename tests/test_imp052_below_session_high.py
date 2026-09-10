"""IMP-052 — the `below-session-high` entry discriminator.

The statistic asks the one question two consecutive losing sessions pointed at:
when the MA crossover fired, had the day's high **already printed**? On
2026-09-08 XOM topped at 163.01 at 09:38 and the bot bought at 10:12 and 15:05;
on 2026-09-09 TSLA topped at 375.44 at 09:33 and the bot bought at 09:42 and
10:36. Both sessions' entire loss came from entries taken below a high that was
already in. That is a describable, ex-ante, mechanically plausible entry defect
— which is exactly the kind of story that has been wrong fourteen times before,
so it goes through `bot.discriminator`'s era control rather than a spreadsheet.

The fixtures below are the two REAL 2026-09-09 trades (#336, #337) and the real
TSLA 1-minute opening prints they were taken against. They pin two things:

  * the statistic's ex-ante contract — the entry minute's own bar is excluded,
    because it contains prints from AFTER the fill. This is the defect that made
    realised session range inadmissible on 2026-08-13, and it is the one way a
    statistic like this can look good and be unusable.
  * the motivating fact itself, so the refutation cannot silently rot: both of
    2026-09-09's trades sit in the cohort a 0.50% filter would have refused, and
    that filter is NOT SUPPORTED at any threshold.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scripts.entry_discriminator import (
    DEFAULT_BSH_THRESHOLDS,
    below_session_high_pct,
    session_high_before,
)

ET = ZoneInfo("America/New_York")


class Bar:
    """Minimal stand-in for an Alpaca minute bar: a timestamp and a high."""

    def __init__(self, hhmm: str, high: float, day: str = "2026-09-09"):
        hour, minute = (int(p) for p in hhmm.split(":"))
        self.timestamp = datetime(*(int(p) for p in day.split("-")),
                                  hour, minute, tzinfo=ET)
        self.high = high


# TSLA's real 2026-09-09 opening minutes (SIP). The 09:33 bar is the day high,
# and it is the number both of the day's entries were taken below.
TSLA_OPEN = [
    Bar("09:30", 371.50), Bar("09:31", 374.57), Bar("09:32", 375.00),
    Bar("09:33", 375.44), Bar("09:34", 374.98), Bar("09:35", 374.15),
    Bar("09:36", 372.17), Bar("09:37", 372.30), Bar("09:38", 372.44),
    Bar("09:39", 372.55), Bar("09:40", 372.60), Bar("09:41", 372.98),
    Bar("09:42", 373.00),
]


def _at(hhmm: str, second: int = 0, day: str = "2026-09-09") -> datetime:
    hour, minute = (int(p) for p in hhmm.split(":"))
    return datetime(*(int(p) for p in day.split("-")), hour, minute, second, tzinfo=ET)


# --------------------------------------------------------------------------
# The ex-ante contract
# --------------------------------------------------------------------------

def test_the_entry_minutes_own_bar_is_excluded():
    """The bar containing the fill also contains prints made after it.

    Constructed so the guard is the ONLY thing that can produce the right
    answer: the 10:00 bar's high (400.0) is the highest in the series, so a
    function that included it would return 400.0 rather than 375.44.
    """
    bars = TSLA_OPEN + [Bar("10:00", 400.0)]
    assert session_high_before(bars, _at("10:00", 30)) == 375.44


def test_a_bar_that_closed_before_the_entry_minute_is_included():
    """The complement of the guard — one minute earlier and it counts."""
    bars = TSLA_OPEN + [Bar("10:00", 400.0)]
    assert session_high_before(bars, _at("10:01")) == 400.0


def test_pre_market_prints_never_leak_in():
    """The bot trades the regular session and its VWAP is a session VWAP."""
    bars = [Bar("08:15", 999.0), Bar("09:29", 998.0)] + TSLA_OPEN
    assert session_high_before(bars, _at("09:42", 38)) == 375.44


def test_a_fill_on_the_opening_minute_is_unscoreable_not_zero():
    """No prior high is absence of evidence, not evidence of a fresh high.

    Returning 0.0 here would tag the trade into the 'entered at the session
    high' cohort, which is precisely the claim the data cannot support.
    """
    assert session_high_before(TSLA_OPEN, _at("09:30", 5)) is None


def test_bars_from_another_session_are_ignored():
    bars = [Bar("15:00", 500.0, day="2026-09-08")] + TSLA_OPEN
    assert session_high_before(bars, _at("09:42", 38)) == 375.44


# --------------------------------------------------------------------------
# The statistic
# --------------------------------------------------------------------------

def test_a_fresh_high_floors_at_zero():
    """An entry AT or ABOVE the prior high is the same event: nothing topped it."""
    assert below_session_high_pct(375.44, 375.44) == 0.0
    assert below_session_high_pct(380.00, 375.44) == 0.0


def test_trade_336_the_real_2026_09_09_first_tsla_entry():
    """#336: filled 372.25 at 09:42:38, nine minutes after the 09:33 high."""
    high = session_high_before(TSLA_OPEN, _at("09:42", 38))
    assert high == 375.44
    assert below_session_high_pct(372.25, high) == pytest.approx(0.8570, abs=1e-4)


def test_trade_337_the_real_2026_09_09_second_tsla_entry():
    """#337: filled 372.91 at 10:36:11, an hour after the same high."""
    high = session_high_before(TSLA_OPEN, _at("10:36", 11))
    assert high == 375.44
    assert below_session_high_pct(372.91, high) == pytest.approx(0.6784, abs=1e-4)


def test_both_2026_09_09_trades_land_in_the_cohort_a_filter_would_refuse():
    """The motivating fact, pinned so the refutation keeps its subject.

    Both entries clear 0.50% — the threshold whose post-gate split reads
    +$7.99/trade and whose era-controlled split reads -0.34. The finding this
    file records is that the story is true about these two trades and still
    does not generalise.
    """
    high = session_high_before(TSLA_OPEN, _at("09:42", 38))
    for fill in (372.25, 372.91):
        assert below_session_high_pct(fill, high) > 0.50


def test_the_swept_thresholds_are_the_ones_the_refutation_was_recorded_at():
    """todo.md quotes numbers per threshold; a silent re-sweep would orphan them."""
    assert DEFAULT_BSH_THRESHOLDS == [0.25, 0.40, 0.50, 0.60, 0.75, 1.00]
