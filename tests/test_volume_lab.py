"""Unit tests for bot.volume_lab — the ORB volume-confirmation lab (IMP-065).

Pure and network-free. They pin the properties the finding rests on:

* the ``live`` cell reproduces ``entry_lab.rule_orb`` at live parameters EXACTLY,
  so the sweep's incumbent is the running bot and not an approximation of it;
* ``rule_orb_volume`` changes **only** the volume leg (fresh-break geometry,
  buffer, above-VWAP and the time cutoff all still come from ``rule_orb``);
* the ``tod`` baseline is CAUSAL — a session is never compared against itself, so
  no backtest built on it can leak the future;
* every baseline fails **CLOSED** on missing history, because a gate that opens
  when it cannot measure is how a lab result becomes a live surprise;
* ``clearance_profile`` reproduces the U-shape that motivated the whole run.

The regression scenario is 2026-09-28's: ten distinct in-window ORB candidates,
zero fills, and not one candidate clearing ``rel_vol >= 1.3`` — the nine measured
in-window values are pinned below and a time-of-day baseline is shown to admit
the genuine surges among them while the live definition admits none.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot import config, entry_lab, entry_sweep, volume_lab

ET = "America/New_York"

#: The nine in-window ORB candidates the live bot refused on 2026-09-28, with the
#: ``rel_vol`` each actually printed (SIP 5-min bars). Every one is below the 1.3
#: floor: this is the session that motivated IMP-065.
LIVE_0928_CANDIDATES = [
    ("MSFT", "11:10", 0.567), ("CRWD", "11:15", 0.626), ("AMZN", "10:20", 0.654),
    ("CRM", "10:05", 0.676), ("MSFT", "10:10", 0.719), ("AMZN", "11:05", 0.915),
    ("CRWD", "11:05", 0.942), ("WMT", "11:10", 1.125), ("PANW", "11:05", 1.252),
]


def _session(day: str, volumes: list[float], closes: list[float] | None = None,
             highs: list[float] | None = None) -> pd.DataFrame:
    """One RTH session of 5-min bars starting 09:30 ET, len == len(volumes)."""
    n = len(volumes)
    idx = pd.date_range(f"{day} 09:30", periods=n, freq="5min", tz=ET)
    closes = closes if closes is not None else [100.0] * n
    highs = highs if highs is not None else [c + 0.1 for c in closes]
    return pd.DataFrame(
        {"open": closes, "high": highs, "low": [c - 0.1 for c in closes],
         "close": closes, "volume": volumes}, index=idx)


def _feats(frames: list[pd.DataFrame]) -> pd.DataFrame:
    return entry_lab.precompute_features(pd.concat(frames).sort_index())


# --- The tod baseline: causal, per-bar_idx, fail-closed ----------------------

def test_tod_baseline_is_causal_first_session_has_none():
    """No prior session -> NaN baseline -> the gate cannot open on day one."""
    f = _feats([_session("2026-09-01", [1000.0] * 10)])
    base = volume_lab.tod_volume_baseline(f, lookback=20, min_sessions=1)
    assert base.isna().all()


def test_tod_baseline_never_sees_its_own_session():
    """A session whose volume explodes must not raise its OWN baseline.

    This is the test that makes the backtest trustworthy: if the baseline were
    computed over a window including today, a high-volume day would normalise
    itself away and every measured expectancy would be fiction.
    """
    prior = _session("2026-09-01", [100.0] * 8)
    today = _session("2026-09-02", [10_000.0] * 8)
    f = _feats([prior, today])
    base = volume_lab.tod_volume_baseline(f, lookback=20, min_sessions=1)
    todays = base[base.index.normalize() == pd.Timestamp("2026-09-02", tz=ET)]
    assert (todays == 100.0).all()


def test_tod_baseline_is_per_bar_index_not_per_day():
    """The whole point: bar 0 is compared to bar 0, not to the session average."""
    prior = _session("2026-09-01", [900.0, 300.0, 100.0, 100.0])
    today = _session("2026-09-02", [900.0, 300.0, 100.0, 100.0])
    f = volume_lab.add_volume_features(_feats([prior, today]),
                                       k=2, lookback=20, min_sessions=1)
    today_rows = f[f.index.normalize() == pd.Timestamp("2026-09-02", tz=ET)]
    # Identical session -> every ratio is exactly 1.0 at every bar_idx, even
    # though raw volume spans 900 -> 100 across the session.
    assert np.allclose(today_rows["tod_rel_vol"].to_numpy(), 1.0)


def test_tod_baseline_uses_median_so_one_spike_does_not_set_the_bar():
    prior = [_session(f"2026-09-0{d}", [100.0]) for d in (1, 2, 3)]
    spike = _session("2026-09-04", [100_000.0])
    today = _session("2026-09-07", [200.0])
    f = volume_lab.add_volume_features(_feats([*prior, spike, today]),
                                       k=0, lookback=20, min_sessions=1)
    row = f[f.index.normalize() == pd.Timestamp("2026-09-07", tz=ET)]
    # median(100, 100, 100, 100000) == 100 -> ratio 2.0, not ~0.008
    assert row["tod_rel_vol"].iloc[0] == pytest.approx(2.0)


def test_tod_baseline_respects_min_sessions():
    days = [_session(f"2026-09-0{d}", [100.0] * 3) for d in (1, 2, 3, 4)]
    f = _feats(days)
    base = volume_lab.tod_volume_baseline(f, lookback=20, min_sessions=3)
    per_day = base.groupby(base.index.normalize()).apply(lambda s: s.notna().all())
    # Sessions 1-3 have <3 priors; only the 4th qualifies.
    assert list(per_day) == [False, False, False, True]


@pytest.mark.parametrize("lookback", [0, -5])
def test_tod_baseline_bad_lookback_degrades_instead_of_raising(lookback):
    """A nonsense constant must degrade to a short window, not crash the lab and
    not produce a baseline that admits everything."""
    days = [_session(f"2026-09-0{d}", [100.0] * 3) for d in (1, 2, 3)]
    f = volume_lab.add_volume_features(_feats(days), k=0, lookback=lookback,
                                       min_sessions=1)
    assert not volume_lab.volume_ok(f, ("tod", 1.3)).any()
    # Degraded to a 1-session baseline: session 1 has no prior, 2 and 3 do.
    base = volume_lab.tod_volume_baseline(f, lookback=lookback, min_sessions=1)
    assert base.isna().sum() == 3                      # session 1's three bars
    assert (base.dropna() == 100.0).all()


def test_tod_baseline_min_sessions_cannot_exceed_the_window():
    """min_sessions > lookback would raise inside pandas; it is clamped instead."""
    days = [_session(f"2026-09-0{d}", [100.0] * 2) for d in (1, 2, 3)]
    f = _feats(days)
    base = volume_lab.tod_volume_baseline(f, lookback=2, min_sessions=99)
    assert base.notna().any()


# --- The session baseline: excludes the opening range, blind at bar k --------

def test_session_baseline_excludes_the_opening_range():
    f = _feats([_session("2026-09-01", [1000.0, 1000.0, 100.0, 200.0, 300.0])])
    base = volume_lab.session_volume_baseline(f, k=2)
    # bar 2 is the first post-range bar -> no prior -> NaN (fails closed)
    assert pd.isna(base.iloc[2])
    # bar 3's baseline is bar 2 alone (100), NOT the 1000-volume opening bars
    assert base.iloc[3] == pytest.approx(100.0)
    # bar 4's baseline is mean(100, 200)
    assert base.iloc[4] == pytest.approx(150.0)


def test_session_baseline_does_not_bleed_across_sessions():
    f = _feats([_session("2026-09-01", [9_000.0] * 5),
                _session("2026-09-02", [10.0, 10.0, 100.0, 200.0])])
    base = volume_lab.session_volume_baseline(f, k=2)
    day2 = base[base.index.normalize() == pd.Timestamp("2026-09-02", tz=ET)]
    assert pd.isna(day2.iloc[2])
    assert day2.iloc[3] == pytest.approx(100.0)   # yesterday's 9,000s are absent


# --- volume_ok: fail closed, explicit definitions ---------------------------

def test_volume_ok_fails_closed_on_missing_baseline():
    f = volume_lab.add_volume_features(
        _feats([_session("2026-09-01", [100.0] * 4)]), k=2, min_sessions=1)
    assert f["tod_rel_vol"].isna().all()          # no prior session at all
    assert not volume_lab.volume_ok(f, ("tod", 1.3)).any()


def test_volume_ok_zero_threshold_disables_the_leg():
    f = volume_lab.add_volume_features(
        _feats([_session("2026-09-01", [100.0] * 4)]), k=2, min_sessions=1)
    assert volume_lab.volume_ok(f, ("tod", 0.0)).all()


def test_volume_ok_rejects_an_unknown_definition():
    f = volume_lab.add_volume_features(
        _feats([_session("2026-09-01", [100.0] * 4)]), k=2, min_sessions=1)
    with pytest.raises(ValueError, match="unknown volume definition"):
        volume_lab.volume_ok(f, ("tod_rel_vol", 1.3))   # column name, not a def


def test_volume_ok_requires_features_to_have_been_added():
    f = _feats([_session("2026-09-01", [100.0] * 4)])
    with pytest.raises(KeyError, match="add_volume_features"):
        volume_lab.volume_ok(f, ("tod", 1.3))


def test_add_volume_features_does_not_mutate_the_caller_frame():
    f = _feats([_session("2026-09-01", [100.0] * 4)])
    before = list(f.columns)
    volume_lab.add_volume_features(f, k=2, min_sessions=1)
    assert list(f.columns) == before


# --- The one-dimension property: live cell == rule_orb exactly --------------

def _breakout_history() -> pd.DataFrame:
    """20 flat sessions, then a session that breaks its opening range on bar 6."""
    frames = []
    for d in range(1, 21):
        frames.append(_session(f"2026-08-{d:02d}", [1_000.0] * 12,
                               closes=[100.0] * 12, highs=[100.2] * 12))
    closes = [100.0] * 6 + [101.0] + [101.0] * 5
    highs = [100.2] * 6 + [101.2] + [101.2] * 5
    frames.append(_session("2026-09-01", [1_000.0] * 6 + [4_000.0] + [1_000.0] * 5,
                           closes=closes, highs=highs))
    return volume_lab.add_volume_features(_feats(frames), k=6, min_sessions=1)


def test_live_cell_reproduces_rule_orb_exactly():
    """The incumbent must BE the live rule, not a near-copy of it.

    If this ever diverges, every "candidate beats incumbent" verdict the sweep
    prints is comparing against a gate the bot does not run.
    """
    f = _breakout_history()
    base = entry_sweep.live_orb_params()
    expected = entry_lab.rule_orb(f, base)
    got = volume_lab.rule_orb_volume(f, {**base, "volume_spec": ("live", base["min_relvol"])})
    pd.testing.assert_series_equal(got, expected, check_names=False)


def test_volume_spec_defaults_to_the_live_gate():
    f = _breakout_history()
    base = entry_sweep.live_orb_params()
    pd.testing.assert_series_equal(
        volume_lab.rule_orb_volume(f, base),
        entry_lab.rule_orb(f, base), check_names=False)


def test_rule_changes_only_the_volume_leg():
    """With volume confirmation switched off, the rule is rule_orb's geometry."""
    f = _breakout_history()
    base = entry_sweep.live_orb_params()
    pd.testing.assert_series_equal(
        volume_lab.rule_orb_volume(f, {**base, "volume_spec": ("tod", 0.0)}),
        entry_lab.rule_orb(f, {**base, "min_relvol": 0.0}), check_names=False)


def test_cutoff_and_vwap_legs_still_bind_under_a_new_volume_definition():
    """A generous volume definition must not smuggle in a later entry time."""
    f = _breakout_history()
    base = entry_sweep.live_orb_params()
    trig = volume_lab.rule_orb_volume(f, {**base, "cutoff": "09:30",
                                          "volume_spec": ("tod", 0.0)})
    assert not trig.any()


# --- The 2026-09-28 regression scenario -------------------------------------

def test_live_gate_refused_every_in_window_candidate_on_2026_09_28():
    """The measured rel_vol of all nine in-window candidates is below the floor."""
    floor = float(config.ORB_MIN_REL_VOL)
    assert floor == 1.3
    assert all(rv < floor for _, _, rv in LIVE_0928_CANDIDATES)
    assert max(rv for _, _, rv in LIVE_0928_CANDIDATES) == 1.252   # PANW, nearest miss


def test_tod_definition_admits_a_genuine_surge_the_live_definition_refuses():
    """The defect, reproduced end to end on synthetic bars shaped like a real day.

    A U-shaped session (opening bars 5x midday volume) with a bar-7 break on
    DOUBLE its normal bar-7 volume: the live definition refuses it because the
    100-minute average is still anchored on the open, the time-of-day definition
    admits it because it compares bar 7 to bar 7.
    """
    u = [5_000.0, 3_000.0, 2_000.0, 1_500.0, 1_200.0, 1_000.0, 800.0, 700.0,
         650.0, 600.0, 600.0, 600.0]
    frames = [_session(f"2026-08-{d:02d}", u, closes=[100.0] * 12,
                       highs=[100.2] * 12) for d in range(1, 21)]
    surge = list(u)
    surge[7] = u[7] * 2.0                     # bar 7 on 2x its usual volume
    closes = [100.0] * 7 + [101.0] * 5
    highs = [100.2] * 7 + [101.2] * 5
    frames.append(_session("2026-09-01", surge, closes=closes, highs=highs))
    f = volume_lab.add_volume_features(_feats(frames), k=6, min_sessions=5)
    bar7 = f[(f.index.normalize() == pd.Timestamp("2026-09-01", tz=ET))
             & (f["bar_idx"] == 7)]
    assert len(bar7) == 1
    assert bar7["rel_vol"].iloc[0] < 1.3           # live: refused
    assert bar7["tod_rel_vol"].iloc[0] == pytest.approx(2.0)   # tod: 2x normal
    base = entry_sweep.live_orb_params()
    assert not volume_lab.rule_orb_volume(f, {**base, "volume_spec": ("live", 1.3)}).any()
    assert volume_lab.rule_orb_volume(f, {**base, "volume_spec": ("tod", 1.5)}).loc[bar7.index].all()


# --- clearance_profile: the U-shape instrument ------------------------------

def test_clearance_profile_shows_the_u_shape_for_the_live_definition():
    u = [5_000.0, 3_000.0, 2_000.0, 1_500.0, 1_200.0, 1_000.0, 800.0, 700.0]
    frames = [_session(f"2026-08-{d:02d}", u) for d in range(1, 21)]
    f = volume_lab.add_volume_features(_feats(frames), k=6, min_sessions=5)
    prof = volume_lab.clearance_profile(f, ("live", 1.3), max_bar_idx=7)
    # The opening bar clears easily; the bars an ORB break is legal on NEVER do.
    # 85% not 100% at bar 0 because ``relative_volume``'s own 20-BAR window needs
    # 2.5 sessions of history, so the first three sessions have no ratio at all
    # and are counted as not clearing — fail-closed, visible in the instrument.
    assert prof.loc[0, "pct_clearing"] == 85.0
    assert prof.loc[6, "pct_clearing"] == 0.0
    assert prof.loc[7, "pct_clearing"] == 0.0
    # The live definition's ratio DECAYS through the session even though this
    # synthetic day repeats identically: that decay is the defect.
    assert prof.loc[0, "median_ratio"] > prof.loc[6, "median_ratio"]


def test_clearance_profile_counts_missing_baselines_as_not_clearing():
    """Fail-closed must show up in the instrument too, not as a silent gap."""
    f = volume_lab.add_volume_features(
        _feats([_session("2026-09-01", [100.0] * 3)]), k=2, min_sessions=5)
    prof = volume_lab.clearance_profile(f, ("tod", 1.3), max_bar_idx=2)
    assert (prof["pct_clearing"] == 0.0).all()
    assert prof["n"].sum() == 3           # the bars are counted, not dropped


def test_clearance_profile_empty_frame_is_empty_not_an_error():
    empty = pd.DataFrame(columns=["bar_idx", "rel_vol"])
    assert volume_lab.clearance_profile(empty, ("live", 1.3)).empty


# --- candidate_admission: diagnostic, and it must tie to the rule -----------

def test_candidate_admission_ties_to_the_rule_and_is_monotone_in_threshold():
    f = _breakout_history()
    base = entry_sweep.live_orb_params()
    specs = [("tod", 0.0), ("tod", 1.5), ("tod", 99.0)]
    tab = volume_lab.candidate_admission({"X": f}, base, specs)
    row = {r["spec"]: r for _, r in tab.iterrows()}
    assert row["('tod', 0.0)"]["admitted"] == row["('tod', 0.0)"]["candidates"]
    assert row["('tod', 99.0)"]["admitted"] == 0
    assert (row["('tod', 0.0)"]["admitted"] >= row["('tod', 1.5)"]["admitted"]
            >= row["('tod', 99.0)"]["admitted"])


def test_live_volume_spec_reads_config_not_a_literal():
    assert volume_lab.live_volume_spec() == ("live", float(config.ORB_MIN_REL_VOL))


# --- Invariant: nothing in the live trading path imports this lab -----------

def test_live_path_does_not_import_volume_lab():
    """``bot.volume_lab`` is lab tooling. If a live module ever imports it, the
    IMP-065 claim "zero effect on trade selection" stops being true by
    construction and has to be re-argued from behaviour."""
    import ast
    import pathlib
    for name in ("engine", "signals", "sizing", "exits", "execution", "strategy"):
        path = pathlib.Path(__file__).resolve().parents[1] / "bot" / f"{name}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all("volume_lab" not in a.name for a in node.names), name
            elif isinstance(node, ast.ImportFrom):
                assert "volume_lab" not in (node.module or ""), name
                assert all(a.name != "volume_lab" for a in node.names), name


def test_risk_invariants_unchanged_by_this_imp():
    """IMP-065 is lab-only; these are the limits it must not have touched."""
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert str(config.ENTRY_CUTOFF_ET) == "15:30"
    assert str(config.FLATTEN_ET) == "15:55"
    # The ORB gate is unchanged: this run measured it, it did not move it.
    assert float(config.ORB_MIN_REL_VOL) == 1.3
    assert str(config.ORB_CUTOFF_ET) == "11:30"
    assert int(config.ORB_RANGE_BARS) == 6


# --- Feed parity: the lab must measure the feed the bot trades (IMP-065) ----

def test_lab_feed_defaults_to_the_bots_own_feed():
    """The whole reason the tod result was believed and then refuted.

    Defaulting to ``sip`` meant IMP-059's gate and IMP-063's grid judged entry
    configurations on bars the live bot never sees. The same 251 sessions give
    opposite verdicts on the two feeds, so this default is load-bearing.
    """
    from scripts.entry_lab import resolve_feed
    feed, warning = resolve_feed([])
    assert feed == str(config.DATA_FEED).lower()
    assert warning is None


def test_lab_warns_when_asked_to_measure_a_feed_the_bot_does_not_trade():
    from scripts.entry_lab import resolve_feed
    other = "sip" if str(config.DATA_FEED).lower() != "sip" else "iex"
    feed, warning = resolve_feed(["--feed", other])
    assert feed == other
    assert warning and "NOT the live bot's feed" in warning


def test_bar_cache_refuses_a_different_feed():
    """A SIP cache served to an IEX run is how a verdict becomes about nothing."""
    from datetime import date as _date

    from scripts.entry_lab import CACHE_META_KEY, cache_matches
    cached = {"AAPL": object(), CACHE_META_KEY: {
        "feed": "sip", "start": "2025-09-29", "end": "2026-09-28"}}
    args = (["AAPL"], _date(2025, 9, 29), _date(2026, 9, 28))
    assert cache_matches(cached, *args, "sip")
    assert not cache_matches(cached, *args, "iex")


def test_bar_cache_refuses_a_different_window():
    from datetime import date as _date

    from scripts.entry_lab import CACHE_META_KEY, cache_matches
    cached = {"AAPL": object(), CACHE_META_KEY: {
        "feed": "iex", "start": "2025-09-29", "end": "2026-09-28"}}
    assert not cache_matches(cached, ["AAPL"], _date(2026, 9, 1), _date(2026, 9, 28), "iex")


def test_bar_cache_refuses_an_unmarked_legacy_cache():
    """Pre-IMP-065 caches hold unknown bars; refetching beats guessing."""
    from datetime import date as _date

    from scripts.entry_lab import cache_matches
    assert not cache_matches({"AAPL": object()}, ["AAPL"],
                             _date(2025, 9, 29), _date(2026, 9, 28), "iex")


def test_bar_cache_refuses_a_missing_symbol():
    from datetime import date as _date

    from scripts.entry_lab import CACHE_META_KEY, cache_matches
    cached = {"AAPL": object(), CACHE_META_KEY: {
        "feed": "iex", "start": "2025-09-29", "end": "2026-09-28"}}
    assert not cache_matches(cached, ["AAPL", "MSFT"],
                             _date(2025, 9, 29), _date(2026, 9, 28), "iex")


def test_cache_meta_key_cannot_be_mistaken_for_a_symbol():
    from scripts.entry_lab import CACHE_META_KEY
    assert not CACHE_META_KEY.isalpha()
