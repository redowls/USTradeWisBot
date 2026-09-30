"""Unit tests for bot.confirm_lab — delayed ORB volume confirmation (IMP-066).

Pure and network-free. They pin the properties the finding rests on:

* ``confirm_bars=0`` reproduces ``entry_lab.rule_orb`` **exactly**, so the sweep's
  incumbent is the running bot and not an approximation of it;
* the rule changes **only** when the volume leg may be satisfied — the floor
  itself, the fresh-break geometry, the buffer, the above-VWAP leg and the time
  cutoff all still come from the live code;
* **one break is still one entry**: an armed window fires at most once, so a
  breakout cannot be bought repeatedly while volume oscillates over the floor;
* the armed window is **causal** and **session-local** — it counts forward from a
  break that has already closed, and never survives into the next day;
* a break that **falls back through its level** is dead, not pending: the rule
  refuses to buy a failed breakout on a later volume spike;
* every live trigger is **kept** (the candidate trigger set is a superset), so
  the dimension can only add trades, never silently drop the incumbent's.

The regression scenario is 2026-09-29's MSFT, the session that motivated the run:
it broke its opening range at 10:30 on ``rel_vol`` 0.894 and was refused, then
printed 2.148 and 1.729 on the next two bars while holding above both the level
and VWAP, inside the 11:30 window. The live gate can never take that trade; the
tests below pin that ``confirm_bars>=1`` can.
"""

from __future__ import annotations

import ast
import pathlib

import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from bot import config, confirm_lab, entry_lab, entry_sweep

ET = "America/New_York"

#: MSFT's measured 2026-09-29 in-window bars on the bot's own IEX feed, from the
#: 09:30 bar onward: (close, rel_vol). The opening range (first 6 bars) tops at
#: 509.12; the 10:30 bar is the FRESH break at rel_vol 0.894 — refused — and the
#: 10:35 bar prints 2.148. Both are above VWAP and inside the 11:30 cutoff.
MSFT_0929 = [
    (507.20, 2.400), (506.10, 1.100), (507.90, 0.900), (508.40, 0.800),
    (508.10, 0.700), (509.12, 0.650),          # bars 0-5 = 09:30..09:55, the range
    (508.00, 0.600), (508.50, 0.550),          # 10:00, 10:05 — below the level
    (508.20, 0.500), (508.90, 0.480),          # 10:10, 10:15
    (508.60, 0.470), (508.70, 0.460),          # 10:20, 10:25
    (511.15, 0.894),                            # bar 12 = 10:30 FRESH BREAK, vol short
    (512.98, 2.148),                            # 10:35 volume arrives, +1 bar
    (512.26, 1.729),                            # 10:40 still confirming
    (510.83, 0.760), (511.12, 0.250), (510.69, 0.803),
]

#: Position of the 10:30 fresh break inside ``MSFT_0929`` — asserted, not assumed,
#: because an off-by-one in the fixture would silently move the scenario.
MSFT_BREAK_IDX = 12


def _session(day: str, closes: list[float], rel_vols: list[float] | None = None,
             volumes: list[float] | None = None) -> pd.DataFrame:
    """One RTH session of 5-min bars starting 09:30 ET."""
    n = len(closes)
    idx = pd.date_range(f"{day} 09:30", periods=n, freq="5min", tz=ET)
    vols = volumes if volumes is not None else [1000.0] * n
    return pd.DataFrame(
        {"open": closes, "high": [c + 0.05 for c in closes],
         "low": [c - 0.05 for c in closes], "close": closes, "volume": vols},
        index=idx)


def _feats(frames: list[pd.DataFrame]) -> pd.DataFrame:
    return entry_lab.precompute_features(pd.concat(frames).sort_index())


def _with_relvol(f: pd.DataFrame, rel_vols: list[float]) -> pd.DataFrame:
    """Override the computed rel_vol so a scenario can pin measured values.

    ``relative_volume`` needs 20 prior bars, so a two-session fixture cannot
    reproduce a specific live reading; the values are the measurement under test.
    """
    out = f.copy()
    out["rel_vol"] = rel_vols
    return out


def _live_params(**over) -> dict:
    """Live ORB params without reading the DB. ``mkt`` off: the market overlay is
    applied by ``run_rule``, not by the rule, so it is not part of these tests."""
    return {"k": 6, "cutoff": "11:30", "min_relvol": 1.3, "buffer_pct": 0.0,
            "above_vwap": True, "mkt": False, "confirm_bars": 0, **over}


# --- Parity: confirm_bars=0 IS the running bot -------------------------------

def test_confirm_bars_zero_reproduces_rule_orb_exactly():
    """The incumbent cell must be the live rule's own output, bar for bar."""
    closes = [c for c, _ in MSFT_0929]
    f = _feats([_session("2026-09-28", closes), _session("2026-09-29", closes)])
    p = _live_params()
    assert_series_equal(confirm_lab.rule_orb_confirm(f, p),
                        entry_lab.rule_orb(f, p), check_names=False)


def test_confirm_bars_zero_parity_holds_for_negative_and_missing_values():
    """A bad or absent parameter must degrade to live behaviour, not detonate."""
    closes = [c for c, _ in MSFT_0929]
    f = _feats([_session("2026-09-28", closes), _session("2026-09-29", closes)])
    live = entry_lab.rule_orb(f, _live_params())
    for value in (0, -1, -99):
        assert_series_equal(confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=value)),
                            live, check_names=False)
    p = _live_params()
    del p["confirm_bars"]
    assert_series_equal(confirm_lab.rule_orb_confirm(f, p), live, check_names=False)


def test_break_geometry_is_the_live_rule_with_confirmation_legs_off():
    """``break_geometry`` must be rule_orb's own fresh-break test, nothing new."""
    closes = [c for c, _ in MSFT_0929]
    f = _feats([_session("2026-09-28", closes), _session("2026-09-29", closes)])
    p = _live_params()
    bare = entry_lab.rule_orb(f, {**p, "min_relvol": 0.0, "above_vwap": False,
                                  "cutoff": None})
    assert_series_equal(confirm_lab.break_geometry(f, p), bare, check_names=False)


# --- The 2026-09-29 MSFT regression scenario ---------------------------------

def test_msft_0929_live_gate_refuses_the_break_that_volume_confirmed_one_bar_late():
    """The motivating failure, pinned: live takes nothing, confirm_bars>=1 takes it."""
    closes = [c for c, _ in MSFT_0929]
    rel = [v for _, v in MSFT_0929]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    p = _live_params()

    fresh = confirm_lab.break_geometry(f, p)
    assert fresh.sum() == 1, "exactly one fresh break in the scenario"
    break_ts = f.index[fresh][0]
    assert list(f.index).index(break_ts) == MSFT_BREAK_IDX
    assert break_ts.strftime("%H:%M") == "10:30"
    assert f.loc[break_ts, "rel_vol"] == pytest.approx(0.894)
    assert f.loc[break_ts, "rel_vol"] < p["min_relvol"], "refused on volume"

    assert confirm_lab.rule_orb_confirm(f, p).sum() == 0, "live gate takes nothing"

    got = confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=1))
    assert got.sum() == 1
    assert f.index[got][0].strftime("%H:%M") == "10:35"
    assert f.loc[f.index[got][0], "rel_vol"] == pytest.approx(2.148)


def test_msft_0929_fires_on_the_first_confirming_bar_not_the_best_one():
    """With a wider window it must still take 10:35 (2.148), not wait for a peak.

    Picking the largest rel_vol in the window would be lookahead. The rule is
    causal: the first bar that clears the floor is the entry.
    """
    closes = [c for c, _ in MSFT_0929]
    rel = [v for _, v in MSFT_0929]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    for n in (1, 2, 3, 4, 6):
        got = confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=n))
        assert got.sum() == 1, n
        assert f.index[got][0].strftime("%H:%M") == "10:35", n


def test_msft_0929_volume_arriving_after_the_window_is_still_refused():
    """confirm_bars is a window, not an abolition of the floor."""
    closes = [c for c, _ in MSFT_0929]
    # Move the confirming volume to 10:50 = four bars after the 10:30 break.
    rel = [v for _, v in MSFT_0929]
    rel[13] = rel[14] = 0.5          # 10:35, 10:40 no longer confirm
    rel[16] = 2.148                  # 10:50 does — four bars after the break
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    assert confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=2)).sum() == 0
    assert confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=4)).sum() == 1


# --- One break is still one entry -------------------------------------------

def test_one_break_fires_at_most_once_even_when_volume_oscillates():
    """Volume crossing the floor repeatedly must not buy the same break twice."""
    closes = [100.0] * 5 + [100.5] + [102.0] * 8
    rel = [0.5] * 6 + [0.4, 2.0, 0.4, 2.0, 0.4, 2.0, 0.4, 2.0]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    for n in (1, 2, 3, 4, 6):
        got = confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=n))
        assert got.sum() == 1, f"confirm_bars={n} fired {int(got.sum())} times on one break"


def test_a_new_fresh_break_rearms_the_window():
    """Break, fail back below, break again: that is two setups, not one."""
    # OR high = 100.5 (bars 0-5). Break at bar 6, back below at 7-8, break at 9.
    closes = [100.0] * 5 + [100.5, 101.0, 100.0, 100.0, 101.0, 101.5, 101.5, 101.5]
    rel = [0.5] * 6 + [0.4, 0.4, 0.4, 0.4, 2.0, 0.4, 0.4]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    fresh = confirm_lab.break_geometry(f, _live_params())
    assert fresh.sum() == 2, "two distinct fresh breaks"
    got = confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=1))
    assert got.sum() == 1
    # It is the SECOND break that confirms (bar 10), not the first.
    assert list(f.index).index(f.index[got][0]) == 10


def test_bars_since_break_resets_every_session():
    """A break at the end of one day must not arm the next day's open."""
    # Day 1 breaks on its last bar; day 2 never breaks its own opening range.
    d1 = _session("2026-09-28", [100.0] * 5 + [100.5] + [100.2] * 3 + [101.0])
    d2 = _session("2026-09-29", [90.0] * 12)
    f = _feats([d1, d2])
    age = confirm_lab.bars_since_break(f, _live_params())
    day2 = age[[ts.date().isoformat() == "2026-09-29" for ts in age.index]]
    assert day2.isna().all(), "day 2 must start with no armed window"


def test_a_break_that_fails_back_below_its_level_is_dead_not_pending():
    """The thesis must survive the wait: no buying a failed breakout on a spike."""
    # OR high 100.5. Break at bar 6 on thin volume, then back BELOW the level
    # while a big volume bar prints. Nothing may fire.
    closes = [100.0] * 5 + [100.5, 101.0, 100.1, 100.2]
    rel = [0.5] * 6 + [0.4, 2.0, 2.0]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    for n in (1, 2, 3, 6):
        assert confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=n)).sum() == 0, n


# --- The live legs still bind ------------------------------------------------

def test_the_volume_floor_still_binds_inside_the_window():
    """confirm_bars widens WHEN the floor may be met, never lowers it."""
    closes = [100.0] * 5 + [100.5] + [102.0] * 6
    rel = [0.5] * 6 + [0.4] * 6              # never reaches 1.3
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    for n in (0, 1, 2, 3, 4, 6):
        assert confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=n)).sum() == 0, n


def test_the_cutoff_still_binds_on_the_confirming_bar():
    """A confirmation that lands after ORB_CUTOFF_ET is not an opening-range entry."""
    # 09:30 + 24 bars = 11:30 is bar 24. Break at bar 23 (11:25), confirm at 25.
    closes = [100.0] * 5 + [100.5] + [100.2] * 17 + [101.0, 101.0, 101.0, 101.0]
    rel = [0.5] * 23 + [0.4, 0.4, 2.0, 2.0]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    fresh = confirm_lab.break_geometry(f, _live_params())
    assert fresh.sum() == 1 and f.index[fresh][0].strftime("%H:%M") == "11:25"
    got = confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=3))
    assert got.sum() == 0, "the confirming bars are 11:35 and 11:40 — past the cutoff"


def test_the_above_vwap_leg_still_binds_on_the_confirming_bar():
    """Volume alone is not confirmation: the close must still hold above VWAP."""
    closes = [100.0] * 5 + [100.5] + [100.6, 100.70]
    rel = [0.5] * 6 + [0.4, 2.0]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    # Force VWAP above the confirming close so only the VWAP leg can refuse it.
    f = f.copy()
    f["vwap"] = [99.0] * 7 + [200.0]
    assert confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=1)).sum() == 0
    f["vwap"] = [99.0] * 8
    assert confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=1)).sum() == 1


def test_every_live_trigger_is_kept_by_a_wider_window():
    """The candidate trigger set must be a SUPERSET: the dimension only adds."""
    closes = [100.0] * 5 + [100.5] + [102.0, 101.0, 100.0, 103.0, 103.5]
    rel = [0.5] * 6 + [2.0, 0.4, 0.4, 2.0, 0.4]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    live = confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=0))
    assert live.sum() >= 1, "the fixture must contain a live trigger to preserve"
    for n in (1, 2, 3, 4, 6):
        wider = confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=n))
        assert int((live & ~wider).sum()) == 0, f"confirm_bars={n} dropped a live trigger"


def test_no_break_no_trigger_whatever_the_volume():
    """A session that never crosses its opening range cannot arm anything."""
    f = _with_relvol(_feats([_session("2026-09-29", [100.0] * 12)]), [3.0] * 12)
    for n in (0, 1, 3, 6):
        assert confirm_lab.rule_orb_confirm(f, _live_params(confirm_bars=n)).sum() == 0, n


# --- Diagnostics -------------------------------------------------------------

def test_confirmation_profile_counts_the_population_the_rule_can_reach():
    """``rescued`` must count breaks the LIVE gate refused, not re-count its own."""
    closes = [c for c, _ in MSFT_0929]
    rel = [v for _, v in MSFT_0929]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), rel)
    prof = confirm_lab.confirmation_profile(f, _live_params(), max_bars=3)
    assert prof["admitted"] == 0, "the live gate admitted nothing in this session"
    assert prof["refused"] == 1, "one fresh break, refused on volume alone"
    assert prof["rescued"] == {1: 1, 2: 1, 3: 1}


def test_confirmation_profile_does_not_mutate_its_input():
    closes = [c for c, _ in MSFT_0929]
    f = _with_relvol(_feats([_session("2026-09-29", closes)]), [v for _, v in MSFT_0929])
    before = f.copy()
    confirm_lab.confirmation_profile(f, _live_params(), max_bars=2)
    pd.testing.assert_frame_equal(f, before)


def test_live_confirm_params_reads_the_running_config():
    """The base cell must come from bot.config, so it cannot drift from the bot."""
    p = confirm_lab.live_confirm_params()
    assert p["min_relvol"] == float(config.ORB_MIN_REL_VOL)
    assert p["cutoff"] == str(config.ORB_CUTOFF_ET)
    assert p["k"] == int(config.ORB_RANGE_BARS)
    assert p[confirm_lab.DIM] == confirm_lab.LIVE_CONFIRM_BARS == 0
    # It must be a valid base cell for the one-dimension sweep machinery.
    assert set(entry_sweep.live_orb_params()) <= set(p)


# --- Lab-only isolation and the risk invariants ------------------------------

def test_no_live_module_imports_confirm_lab():
    """Lab tooling stays out of the trading path — asserted by parsing the ASTs."""
    for name in ("engine", "signals", "sizing", "exits", "execution", "strategy"):
        path = pathlib.Path(__file__).resolve().parents[1] / "bot" / f"{name}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all("confirm_lab" not in a.name for a in node.names), name
            elif isinstance(node, ast.ImportFrom):
                assert "confirm_lab" not in (node.module or ""), name
                assert all(a.name != "confirm_lab" for a in node.names), name


def test_risk_invariants_unchanged_by_this_imp():
    """IMP-066 is lab-only; these are the limits it must not have touched."""
    inv = confirm_lab.risk_invariants()
    assert inv["MAX_RISK_PCT"] <= 2.0
    assert inv["DAILY_LOSS_HALT_PCT"] == 8.0
    assert inv["MAX_CONCURRENT_POSITIONS"] <= 3
    assert inv["ENTRY_CUTOFF_ET"] == "15:30"
    assert inv["FLATTEN_ET"] == "15:55"
    # The volume floor is the PREMISE of this run, not its target: the IEX sweep
    # of 2026-09-30 confirmed 1.3 as the held-out best of nine values.
    assert inv["ORB_MIN_REL_VOL"] == 1.3
    # IMP-013's break-even / 1R-trail protection is untouched.
    assert inv["BREAKEVEN_TRIGGER_R"] == 0.5
    assert inv["TRAIL_TRIGGER_R"] == 1.0
