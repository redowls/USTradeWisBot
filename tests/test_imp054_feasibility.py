"""WIN-feasibility ceiling (IMP-054) — could a doctrine WIN have happened at all?

The anchor is **NVDA #344 (2026-09-11)**, the trade that motivated the module.
Its session range was 1.12x its 1R, so the incumbent `session range / 1R` metric
called it feasible — but the session high printed at 10:04 and the fill came at
10:07, so from the fill forward the price never rose above +0.242R. Every number
in the NVDA fixtures below is copied from the real SIP 1-minute bars and the
live `trades` row. If a future change ever lets that trade score as reachable,
the instrument has drifted back into the error it exists to correct.

Pure: no DB, no network. Bars are stubs carrying only `timestamp/high/low`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from bot import config, doctrine
from scripts.feasibility import (
    CEILING_BANDS,
    WIN_CEILING_R,
    is_reachable,
    session_range_r,
    summarize,
    win_ceiling_r,
    window_bars,
)


@dataclass
class Bar:
    timestamp: datetime
    high: float
    low: float


def bar(hhmm: str, high: float, low: float) -> Bar:
    h, m = (int(x) for x in hhmm.split(":"))
    return Bar(datetime(2026, 9, 11, h, m, tzinfo=config.MARKET_TZ), high, low)


# --- NVDA #344, 2026-09-11: the archetype ---------------------------------
# fill 221.1009 at 10:07:40, plan stop 217.67 -> 1R = 3.4309.
# Session high 222.00 at 10:04 (THREE MINUTES BEFORE the fill), RTH low 218.15
# at 15:59 — after the 15:55 flatten, so it counts toward the incumbent metric's
# session range but is unreachable by any trade the bot could still be holding.
NVDA_FILL = 221.1009
NVDA_STOP = 217.67
NVDA_ENTRY_ET = datetime(2026, 9, 11, 10, 7, 40, tzinfo=config.MARKET_TZ)
NVDA_FLATTEN_ET = datetime(2026, 9, 11, 15, 55, tzinfo=config.MARKET_TZ)
NVDA_DAY = [
    bar("09:35", 221.40, 220.90),
    bar("10:04", 222.00, 221.30),   # the session high — before the fill
    bar("10:07", 221.45, 221.05),   # the bar containing the fill
    bar("10:27", 221.93, 221.20),   # the post-fill peak: +0.242R
    bar("15:30", 218.90, 218.23),
    bar("15:59", 218.40, 218.15),   # RTH low, printed AFTER the flatten
]


def test_nvda_344_win_was_impossible_from_the_fill():
    """The post-fill ceiling is +0.242R — no exit policy could have made a WIN."""
    held = window_bars(NVDA_DAY, NVDA_ENTRY_ET, NVDA_FLATTEN_ET)
    ceiling = win_ceiling_r(NVDA_FILL, NVDA_STOP, [b.high for b in held])
    assert ceiling == pytest.approx(0.242, abs=0.001)
    assert not is_reachable(ceiling)


def test_nvda_344_incumbent_metric_calls_it_feasible_and_is_wrong():
    """session range / 1R = 1.12 >= 1R, so the incumbent metric disagrees."""
    rng = session_range_r(NVDA_FILL, NVDA_STOP,
                          [b.high for b in NVDA_DAY], [b.low for b in NVDA_DAY])
    assert rng == pytest.approx(1.122, abs=0.001)
    assert rng >= WIN_CEILING_R            # incumbent: "feasible"
    held = window_bars(NVDA_DAY, NVDA_ENTRY_ET, NVDA_FLATTEN_ET)
    assert not is_reachable(win_ceiling_r(NVDA_FILL, NVDA_STOP,
                                          [b.high for b in held]))


def test_window_excludes_the_pre_fill_session_high():
    """The 10:04 high must not leak into the ceiling; the 10:07 fill bar must."""
    held = window_bars(NVDA_DAY, NVDA_ENTRY_ET, NVDA_FLATTEN_ET)
    times = [b.timestamp.strftime("%H:%M") for b in held]
    assert "10:04" not in times
    assert times[0] == "10:07"             # fill bar included, by design
    assert "15:30" in times


def test_window_stops_at_the_flatten():
    """Bars after 15:55 ET are unreachable — the bot cannot hold overnight."""
    day = NVDA_DAY + [bar("15:58", 260.0, 259.0)]
    held = window_bars(day, NVDA_ENTRY_ET, NVDA_FLATTEN_ET)
    assert all(b.timestamp.hour * 60 + b.timestamp.minute <= 15 * 60 + 55 for b in held)
    assert win_ceiling_r(NVDA_FILL, NVDA_STOP,
                         [b.high for b in held]) == pytest.approx(0.242, abs=0.001)


# --- QQQ #346, 2026-09-11: bought the high to the cent --------------------
def test_qqq_346_ceiling_is_zero_never_green():
    """Filled 717.32 two minutes after a 717.63 high; never traded up again."""
    day = [bar("11:32", 717.63, 717.10), bar("11:34", 717.32, 717.05),
           bar("13:00", 716.80, 715.90), bar("15:50", 714.90, 714.71)]
    entry = datetime(2026, 9, 11, 11, 34, 15, tzinfo=config.MARKET_TZ)
    held = window_bars(day, entry, NVDA_FLATTEN_ET)
    ceiling = win_ceiling_r(717.32, 706.54, [b.high for b in held])
    assert ceiling == pytest.approx(0.0, abs=0.001)
    assert not is_reachable(ceiling)


# --- guards ---------------------------------------------------------------
def test_ceiling_is_none_when_risk_is_not_positive():
    """An unknown ceiling must never be silently counted as reachable."""
    assert win_ceiling_r(100.0, 100.0, [105.0]) is None
    assert win_ceiling_r(100.0, 110.0, [105.0]) is None
    assert not is_reachable(None)


def test_ceiling_is_none_without_bars():
    assert win_ceiling_r(100.0, 98.0, []) is None
    assert session_range_r(100.0, 98.0, [], []) is None


def test_win_bar_is_the_doctrine_bar():
    """IMP-049/IMP-053: one verdict, one vocabulary. Never redefine the bar."""
    assert WIN_CEILING_R == doctrine.WIN_MIN_R


def test_reachable_is_inclusive_at_exactly_one_r():
    assert is_reachable(win_ceiling_r(100.0, 98.0, [102.0]))      # exactly +1R
    assert not is_reachable(win_ceiling_r(100.0, 98.0, [101.98]))


# --- summarize ------------------------------------------------------------
def rec(ceiling, range_r, verdict, pl):
    return {"ceiling": ceiling, "range_r": range_r, "doctrine": verdict, "pl": pl}


def test_summarize_partitions_and_scores_conversion():
    records = [
        rec(0.24, 1.12, doctrine.FAIL, -27.69),     # NVDA #344 — incumbent disagrees
        rec(0.00, 0.37, doctrine.SCRATCH, -6.33),   # QQQ #346
        rec(1.60, 2.10, doctrine.WIN, 40.00),       # reachable, converted
        rec(1.20, 1.80, doctrine.SCRATCH, 5.00),    # reachable, not converted
    ]
    s = summarize(records)
    assert s["trades"] == 4
    assert s["impossible"] == 2 and s["impossible_share"] == 50.0
    assert s["reachable"] == 2 and s["reachable_net"] == 45.0
    assert s["conversion"] == 50.0
    # The incumbent calls 3 feasible (1.12, 2.10, 1.80); one of them never could win.
    assert s["incumbent_feasible"] == 3
    assert s["disagree"] == 1
    assert s["disagree_of_incumbent"] == pytest.approx(33.3)
    assert s["disagree_net"] == -27.69
    assert s["disagree_wins"] == 0


def test_summarize_bands_cover_every_trade_exactly_once():
    records = [rec(c, None, doctrine.FAIL, 0.0)
               for c in (-0.5, 0.1, 0.3, 0.7, 1.2, 2.0)]
    s = summarize(records)
    assert sum(b["trades"] for b in s["bands"].values()) == len(records)
    assert [s["bands"][label]["trades"] for _lo, _hi, label in CEILING_BANDS] == [1] * 6


def test_summarize_ignores_trades_without_a_ceiling():
    s = summarize([rec(None, 1.5, doctrine.FAIL, -10.0),
                   rec(0.5, 0.9, doctrine.SCRATCH, -1.0)])
    assert s["trades"] == 1 and s["impossible"] == 1


def test_summarize_handles_an_empty_book():
    assert summarize([]) == {"trades": 0}
