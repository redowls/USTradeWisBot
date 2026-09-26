"""Unit tests for bot.entry_sweep — the one-dimension entry sweep (IMP-063).

Pure and network-free. They pin: the base cell is read from the LIVE config (so a
sweep can never baseline against a gate the bot does not run), the candidate ship
test is the IMP-059 gate WITH the incumbent as the baseline to beat, the marginal
cohort diffs both directions (added AND concurrency-dropped), monotonicity, and
that a sweep with an untrustworthy incumbent reports INSUFFICIENT rather than a
clean bill of health for the live value.

The regression scenario is 2026-09-25's: a zero-trade session whose refusal
ledger blamed ``orb_after_cutoff`` for 67.2% of six sessions' candidates, where
extending ``ORB_CUTOFF_ET`` looked obvious and was refuted — held-out expectancy
fell monotonically 11:30 → 15:00 (+0.103R → -0.044R) and the trades the
relaxation bought were net losers.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from bot import config, entry_lab, entry_sweep


class _T:
    """Minimal stand-in for entry_lab.LabTrade — only what the sweep reads."""

    def __init__(self, symbol: str, minute: int, pl: float = 0.0):
        self.symbol = symbol
        self.entry_time = datetime(2026, 9, 25, 10, minute)
        self.exit_time = datetime(2026, 9, 25, 15, 55)
        self.pl = pl
        self.profit_r = pl / 10.0
        self.exit_reason = "EOD_FLATTEN"
        self.day = "2026-09-25"


def _cell(value, is_exp, oos_exp, *, is_n=100, oos_n=50, is_pf=1.1, oos_pf=1.5,
          trades=None) -> entry_sweep.SweepCell:
    """A cell with hand-set metrics; only the fields the verdict reads matter."""
    def m(n, exp, pf):
        return {"n": n, "exp_r": exp, "pf": pf, "net": round(exp * n * 10, 2),
                "t_stat": 1.0}
    return entry_sweep.SweepCell(
        dim="cutoff", value=value, params={"cutoff": value},
        is_metrics=m(is_n, is_exp, is_pf), oos_metrics=m(oos_n, oos_exp, oos_pf),
        oos_trades=trades or [])


# --- the base cell is the running bot ---------------------------------------

def test_live_orb_params_reads_the_shipped_gate_from_config():
    p = entry_sweep.live_orb_params()
    assert p["k"] == int(config.ORB_RANGE_BARS)
    assert p["cutoff"] == str(config.ORB_CUTOFF_ET)
    assert p["min_relvol"] == pytest.approx(float(config.ORB_MIN_REL_VOL))
    assert p["buffer_pct"] == pytest.approx(float(config.ORB_BUFFER_PCT))
    assert p["above_vwap"] is bool(config.ORB_REQUIRE_ABOVE_VWAP)
    # the live knob is a SYMBOL; the lab overlay is a bool
    assert p["mkt"] is bool(config.ORB_MARKET_FILTER_SYMBOL.strip())
    # every key must be one rule_orb understands, or the sweep silently no-ops
    assert set(p) == {"k", "cutoff", "min_relvol", "buffer_pct", "above_vwap", "mkt"}


def test_live_orb_params_disables_the_overlay_when_no_filter_symbol(monkeypatch):
    monkeypatch.setattr(config, "ORB_MARKET_FILTER_SYMBOL", "")
    assert entry_sweep.live_orb_params()["mkt"] is False


def test_sweep_dimension_pins_every_other_parameter(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(entry_lab, "run_rule",
                        lambda *a, **k: seen.append(dict(a[2])) or [])
    base = {"k": 6, "cutoff": "11:30", "min_relvol": 1.3, "buffer_pct": 0.0,
            "above_vwap": True, "mkt": True}
    cells = entry_sweep.sweep_dimension(
        "orb", entry_lab.rule_orb, base, "cutoff", ["11:30", "14:00"],
        {}, [], [], 7278.05, 0.03, None)
    assert [str(c.value) for c in cells] == ["11:30", "14:00"]
    # two windows per value
    assert [p["cutoff"] for p in seen] == ["11:30", "11:30", "14:00", "14:00"]
    for p in seen:                                  # nothing else moved
        assert {k: v for k, v in p.items() if k != "cutoff"} == \
               {k: v for k, v in base.items() if k != "cutoff"}
    assert base["cutoff"] == "11:30"                # caller's dict not mutated


# --- the verdict -------------------------------------------------------------

def test_confirmed_incumbent_when_no_candidate_beats_the_live_value():
    """2026-09-25's real shape: the live cell is best and the gradient falls."""
    cells = [_cell("11:30", 0.014, 0.103), _cell("12:00", 0.003, 0.071),
             _cell("13:00", -0.005, 0.017), _cell("14:00", -0.013, -0.024),
             _cell("15:00", -0.015, -0.044)]
    v = entry_sweep.sweep_verdict(cells, "11:30")
    assert v["verdict"] == entry_sweep.CONFIRMED_INCUMBENT
    assert v["best"] is None
    assert v["incumbent"] == "11:30"
    assert v["monotone"] == "decreasing"
    live_row = next(r for r in v["cells"] if r["incumbent"])
    assert live_row["delta_exp_r"] == 0.0
    # every rejection is legible, and beating the incumbent is one of the reasons
    late = next(r for r in v["cells"] if r["value"] == "13:00")
    assert not late["clears"] and late["delta_exp_r"] < 0
    assert any("incumbent" in w for w in late["why"])


def test_a_candidate_clears_only_by_beating_the_incumbent_through_the_gate():
    cells = [_cell("11:30", 0.014, 0.05), _cell("14:00", 0.020, 0.150)]
    v = entry_sweep.sweep_verdict(cells, "11:30")
    assert v["verdict"] == entry_sweep.CANDIDATE_CLEARS
    assert v["best"] == "14:00"


@pytest.mark.parametrize("kw, why_fragment", [
    ({"is_exp": -0.01, "oos_exp": 0.20}, "in-sample expectancy"),
    ({"is_exp": 0.02, "oos_exp": 0.20, "oos_pf": 1.0}, "PF"),
    ({"is_exp": 0.02, "oos_exp": 0.20, "oos_n": 10}, "held-out n"),
    ({"is_exp": 0.02, "oos_exp": 0.04}, "incumbent"),
])
def test_every_gate_leg_still_applies_to_a_sweep_candidate(kw, why_fragment):
    """A better-looking held-out number is not enough on its own."""
    cells = [_cell("11:30", 0.014, 0.05), _cell("14:00", **kw)]
    v = entry_sweep.sweep_verdict(cells, "11:30")
    assert v["verdict"] == entry_sweep.CONFIRMED_INCUMBENT
    row = next(r for r in v["cells"] if r["value"] == "14:00")
    assert any(why_fragment in w for w in row["why"]), row["why"]


def test_untrustworthy_or_missing_incumbent_is_insufficient_not_confirmed():
    thin = [_cell("11:30", 0.014, 0.103, oos_n=entry_lab.MIN_TRADES_OOS - 1),
            _cell("14:00", 0.020, 0.200)]
    v = entry_sweep.sweep_verdict(thin, "11:30")
    assert v["verdict"] == entry_sweep.INSUFFICIENT
    assert "no trustworthy baseline" in v["reason"]

    absent = entry_sweep.sweep_verdict([_cell("14:00", 0.02, 0.2)], "11:30")
    assert absent["verdict"] == entry_sweep.INSUFFICIENT
    assert "not one of the swept values" in absent["reason"]


def test_incumbent_cell_matches_across_literal_types():
    cells = [_cell(1.3, 0.01, 0.1), _cell(2.0, 0.01, 0.1)]
    assert entry_sweep.incumbent_cell(cells, "1.3").value == 1.3
    assert entry_sweep.incumbent_cell(cells, 2.0).value == 2.0
    assert entry_sweep.incumbent_cell(cells, 9.9) is None


# --- the marginal cohort -----------------------------------------------------

def test_marginal_cohort_reports_added_and_concurrency_dropped_separately():
    """A relaxation both adds trades and crowds existing ones out."""
    common = _T("MSFT", 5, pl=10.0)
    inc = _cell("11:30", 0.01, 0.1, trades=[common, _T("AAPL", 10, pl=25.0)])
    late = _cell("14:00", 0.01, 0.1,
                 trades=[common, _T("BAC", 15, pl=-40.0), _T("WMT", 20, pl=-5.0)])
    m = entry_sweep.marginal_cohort(late, inc)
    assert sorted(t.symbol for t in m["added"]) == ["BAC", "WMT"]
    assert [t.symbol for t in m["dropped"]] == ["AAPL"]
    assert m["added_metrics"]["n"] == 2
    assert m["added_metrics"]["net"] == pytest.approx(-45.0)
    assert m["dropped_metrics"]["net"] == pytest.approx(25.0)
    # net_delta explains the whole P&L difference: the common trade cancels
    assert m["net_delta"] == pytest.approx(-70.0)
    assert m["net_delta"] == pytest.approx(
        sum(t.pl for t in late.oos_trades) - sum(t.pl for t in inc.oos_trades))


def test_marginal_cohort_is_empty_for_the_incumbent_against_itself():
    inc = _cell("11:30", 0.01, 0.1, trades=[_T("MSFT", 5, pl=10.0)])
    m = entry_sweep.marginal_cohort(inc, inc)
    assert m["added"] == [] and m["dropped"] == [] and m["net_delta"] == 0.0


def test_the_same_symbol_on_a_different_bar_is_a_different_trade():
    inc = _cell("11:30", 0.01, 0.1, trades=[_T("MSFT", 5, pl=10.0)])
    other = _cell("14:00", 0.01, 0.1, trades=[_T("MSFT", 40, pl=-8.0)])
    m = entry_sweep.marginal_cohort(other, inc)
    assert len(m["added"]) == 1 and len(m["dropped"]) == 1


# --- monotonicity ------------------------------------------------------------

@pytest.mark.parametrize("oos, expected", [
    ([0.10, 0.07, 0.02, -0.02, -0.04], "decreasing"),
    ([-0.04, -0.02, 0.02, 0.07, 0.10], "increasing"),
    ([0.10, 0.02, 0.07], "none"),
    ([0.05, 0.05, 0.05], "decreasing"),        # flat is non-strict on both sides
    ([0.05], "none"),                          # one point has no direction
    ([], "none"),
])
def test_monotone_direction(oos, expected):
    cells = [_cell(str(i), 0.0, v) for i, v in enumerate(oos)]
    assert entry_sweep.monotone_direction(cells) == expected


def test_monotone_can_read_the_in_sample_window_too():
    cells = [_cell("a", 0.02, 0.05), _cell("b", 0.01, 0.09)]
    assert entry_sweep.monotone_direction(cells, window="is") == "decreasing"
    assert entry_sweep.monotone_direction(cells, window="oos") == "increasing"


# --- invariants this change must not touch -----------------------------------

def test_entry_sweep_is_lab_only_and_moves_no_risk_limit():
    """Analysis tooling: the live path must not import it, and nothing shifts."""
    import pathlib
    import bot.engine, bot.signals, bot.sizing, bot.exits, bot.execution
    for mod in (bot.engine, bot.signals, bot.sizing, bot.exits, bot.execution):
        src = pathlib.Path(mod.__file__).read_text()
        assert "entry_sweep" not in src, f"{mod.__name__} imports the lab"
    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    from bot import secrets
    assert secrets.ALPACA_PAPER is True
    # the ORB gate the sweep confirmed on 2026-09-25 — unchanged by this run
    assert config.ORB_CUTOFF_ET == "11:30"
    assert config.ORB_RANGE_BARS == 6
    assert config.ORB_MIN_REL_VOL == 1.3
    assert config.RR_RATIO == 1.5
    assert (config.BREAKEVEN_TRIGGER_R, config.TRAIL_TRIGGER_R,
            config.TRAIL_DISTANCE_R) == (0.5, 1.0, 1.0)
