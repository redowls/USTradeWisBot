"""IMP-048 — the entry-discriminator must judge candidates on the doctrine.

`bot/discriminator.py` is the gate that decides which entry filters ship. Until
IMP-048 it scored every candidate on DOLLAR P&L alone and printed a `win_rate`
computed from `realized_pl > 0` — the exact metric the standing stop-exit
doctrine (user directive 2026-09-01) exists to distrust, and the one IMP-046
measured as inflating this book's record by ~7x.

The concrete failure this pins, from the real 2026-09-03 run of the 1R/ATR
feasibility candidate over all 297 closed trades:

    refused (1R/ATR <= 0.5)   n=168   win_rate(pl>0) 33.9%   TRUE win 16.1%
    kept    (1R/ATR >  0.5)   n=129   win_rate(pl>0) 50.4%   TRUE win  6.2%

The module's own column says the KEPT side is better by 16.5pp. The doctrine
says it is worse by 9.9pp, and that refusing the low side would discard 27 of
the book's 35 doctrine WINs (77%). A filter chosen on the printed number would
have been chosen on the discredited one.

Every test here is PURE — hand-built `Sample`s, no DB, no network — which is
also the invariant that stops `bot.discriminator` from importing `bot.doctrine`
(that would pull `bot.analytics` and therefore `bot.db` behind every test).
"""

from __future__ import annotations

import pytest

from bot import discriminator as D
from bot import doctrine


def _s(symbol, day, pl, value, profit_r=None, label=None):
    return D.Sample(symbol=symbol, day=day, pl=pl, value=value,
                    profit_r=profit_r, doctrine=label)


# --------------------------------------------------------------------------
# The literal that must not drift
# --------------------------------------------------------------------------

def test_win_label_matches_the_doctrine_module():
    """`WIN_LABEL` is a deliberate duplicate; this is the pin that keeps it honest."""
    assert D.WIN_LABEL == doctrine.WIN


# --------------------------------------------------------------------------
# Backward compatibility — pre-IMP-048 callers must be untouched
# --------------------------------------------------------------------------

def test_samples_without_doctrine_data_still_construct():
    s = D.Sample(symbol="AAPL", day="2026-09-03", pl=10.0, value=1.0)
    assert s.profit_r is None and s.doctrine is None


def test_doctrine_stats_returns_none_when_no_sample_is_labelled():
    """Absent data must mean absent columns, never a silent zero win rate."""
    assert D.doctrine_stats([_s("A", "2026-09-03", 5.0, 1.0)]) is None


def test_win_collateral_is_none_without_labels_and_without_wins():
    plain = [_s("A", "2026-09-03", 5.0, 1.0), _s("B", "2026-09-03", -5.0, 3.0)]
    assert D.win_collateral_fraction(plain, 2.0) is None
    # Labelled, but the cohort contains no WIN at all: nothing to protect.
    labelled = [_s("A", "2026-09-03", 5.0, 1.0, 0.2, "SCRATCH"),
                _s("B", "2026-09-03", -5.0, 3.0, -1.0, "FAIL")]
    assert D.win_collateral_fraction(labelled, 2.0) is None


def test_split_at_reports_no_r_edge_when_doctrine_data_is_absent():
    split = D.split_at([_s("A", "2026-09-03", 5.0, 1.0),
                        _s("B", "2026-09-03", -5.0, 3.0)], 2.0)
    assert split["r_edge"] is None
    assert split["above_doctrine"] is None and split["below_doctrine"] is None
    # edge = below-avg minus above-avg = 5.0 - (-5.0). Unchanged by IMP-048.
    assert split["edge"] == 10.0


def test_verdict_without_doctrine_data_can_still_be_supported():
    """The new gates must not be able to block a candidate that carries no labels."""
    samples = (
        [_s(f"GOOD{i}", "2026-08-01", 12.0, 1.0) for i in range(30)]
        + [_s(f"BAD{i}", "2026-08-01", -12.0, 3.0) for i in range(25)]
    )
    v = D.verdict(samples, 2.0)
    assert v["verdict"] == D.SUPPORTED
    assert v["win_collateral_fraction"] is None
    assert v["era_r_edge"] is None


# --------------------------------------------------------------------------
# doctrine_stats
# --------------------------------------------------------------------------

def test_doctrine_stats_counts_wins_not_green_pnl():
    """Three green trades, one doctrine WIN. TRUE win rate is 33.3%, not 100%."""
    rows = [
        _s("WMT", "2026-09-03", 56.74, 1.0, 1.602, "WIN"),
        _s("XOM", "2026-09-03", 3.30, 1.0, 0.092, "FAIL"),      # break-even stop
        _s("NVDA", "2026-09-03", 19.03, 1.0, 0.520, "SCRATCH"),  # trailed, unpaid
    ]
    stats = D.doctrine_stats(rows)
    assert stats["trades"] == 3
    assert stats["wins"] == 1
    assert stats["true_win_rate"] == 33.3
    assert stats["avg_r"] == pytest.approx(0.738, abs=5e-4)
    # The old column would have read 100% on the same three rows.
    assert D.bucket_stats([r.pl for r in rows])["win_rate"] == 100.0


def test_doctrine_stats_ignores_unlabelled_rows_in_a_mixed_slice():
    rows = [_s("WMT", "2026-09-03", 56.74, 1.0, 1.602, "WIN"),
            _s("XXX", "2026-09-03", 10.0, 1.0)]
    assert D.doctrine_stats(rows)["trades"] == 1


# --------------------------------------------------------------------------
# The WIN-collateral gate — the 2026-09-03 refutation
# --------------------------------------------------------------------------

def _feasibility_book():
    """A scale model of the real 1R/ATR split, in the LOW-side orientation.

    `value` is the NEGATED statistic, which is how a low-side filter is
    expressed (see Sample's docstring): refusing `value >= -0.5` refuses
    trades whose real 1R/ATR is <= 0.5. Proportions mirror the live book —
    the refused side holds most of the WINs.
    """
    refused = (
        [_s(f"TSLA{i}", "2026-08-03", 40.0, -0.3, 1.4, "WIN") for i in range(6)]
        + [_s(f"LOW{i}", "2026-08-03", -14.0, -0.3, -0.6, "FAIL") for i in range(24)]
    )
    kept = (
        [_s("INTC0", "2026-08-03", 60.0, -0.9, 1.3, "WIN")]
        + [_s(f"HIGH{i}", "2026-08-03", 2.0, -0.9, 0.1, "SCRATCH") for i in range(24)]
    )
    return refused + kept


def test_the_low_side_feasibility_filter_is_refuted_and_holds_most_of_the_wins():
    """The 2026-09-03 refutation, in miniature.

    On the real book the DOLLAR collateral guard is what fired first (45% of
    net-positive symbols — TSLA +$577.07, INTC +$143.40 — against a 25% cap),
    and this model reproduces that ordering: the candidate is REFUTED before
    the WIN gate is ever reached. That is the correct outcome and worth pinning,
    because it shows the two guards agreeing rather than the new one doing work
    the old one already did. The WIN collateral is still COMPUTED and reported
    on every verdict, which is what makes the agreement visible: 86% here, 77%
    on the live book (27 of 35 WINs).
    """
    samples = _feasibility_book()
    assert D.win_collateral_fraction(samples, -0.5) == pytest.approx(6 / 7, abs=1e-3)
    v = D.verdict(samples, -0.5)
    assert v["verdict"] == D.REFUTED
    assert any("net-positive symbols" in r for r in v["reasons"])
    assert v["win_collateral_fraction"] == pytest.approx(6 / 7, abs=1e-3)


def test_win_collateral_gate_fires_even_when_the_dollar_checks_all_pass():
    """The point of the gate: dollars say ship it, the WINs say do not.

    Refusing the above side removes a big net loss and no net-positive symbol,
    so `edge` is positive in all three cohorts and dollar collateral is 0% —
    the pre-IMP-048 module would have returned SUPPORTED.
    """
    above = ([_s(f"L{i}", "2026-08-03", -20.0, 3.0, -0.9, "FAIL") for i in range(22)]
             + [_s(f"W{i}", "2026-08-03", -1.0, 3.0, 1.2, "WIN") for i in range(3)])
    below = [_s(f"K{i}", "2026-08-03", 4.0, 1.0, 0.15, "SCRATCH") for i in range(30)]
    samples = above + below

    v = D.verdict(samples, 2.0)
    assert all(s["edge"] > 0 for s in v["splits"].values())
    assert v["collateral_fraction"] == 0.0          # no net-positive symbol refused
    assert v["win_collateral_fraction"] == 1.0      # but ALL the WINs are in there
    assert v["verdict"] == D.REFUTED
    assert any("doctrine WINs" in r for r in v["reasons"])


def test_win_collateral_under_the_cap_does_not_block():
    above = ([_s(f"L{i}", "2026-08-03", -20.0, 3.0, -0.9, "FAIL") for i in range(24)]
             + [_s("W0", "2026-08-03", -1.0, 3.0, 1.2, "WIN")])
    below = ([_s(f"K{i}", "2026-08-03", 4.0, 1.0, 0.15, "SCRATCH") for i in range(26)]
             + [_s(f"KW{i}", "2026-08-03", 50.0, 1.0, 1.3, "WIN") for i in range(4)])
    v = D.verdict(above + below, 2.0)
    assert v["win_collateral_fraction"] == 0.2
    assert v["verdict"] == D.SUPPORTED


# --------------------------------------------------------------------------
# The R-edge gate
# --------------------------------------------------------------------------

def test_r_edge_is_the_dollar_edge_recomputed_in_r():
    split = D.split_at(
        [_s("A", "2026-08-03", -10.0, 3.0, -0.500, "FAIL"),
         _s("B", "2026-08-03", 10.0, 1.0, 0.300, "SCRATCH")], 2.0)
    assert split["r_edge"] == pytest.approx(0.8)


def test_a_filter_that_buys_dollars_by_flattening_r_is_refuted():
    """Positive dollar edge, non-positive R edge — the doctrine's payoff-first rule.

    The refused cohort is a few large losing positions; the kept cohort is many
    small ones with the SAME per-trade R. Removing the big positions improves
    average dollars while improving nothing about the strategy.
    """
    above = [_s(f"BIG{i}", "2026-08-03", -60.0, 3.0, -0.4, "FAIL") for i in range(25)]
    below = [_s(f"SML{i}", "2026-08-03", -2.0, 1.0, -0.4, "FAIL") for i in range(30)]
    v = D.verdict(above + below, 2.0)
    assert v["splits"]["all-time"]["edge"] > 0
    assert v["era_r_edge"] == 0.0
    assert v["verdict"] == D.REFUTED
    assert any("per-trade R" in r for r in v["reasons"])


def test_neither_gate_can_rescue_a_candidate_the_dollar_checks_rejected():
    """The doctrine gates only ever tighten. A REFUTED stays REFUTED."""
    above = [_s(f"G{i}", "2026-08-03", 30.0, 3.0, 1.5, "WIN") for i in range(25)]
    below = [_s(f"B{i}", "2026-08-03", -30.0, 1.0, -1.0, "FAIL") for i in range(25)]
    v = D.verdict(above + below, 2.0)
    assert v["splits"]["all-time"]["edge"] < 0
    assert v["verdict"] == D.REFUTED


# --------------------------------------------------------------------------
# Anti-gaming: the gates must not be passable by widening the stop
# --------------------------------------------------------------------------

def test_widening_the_stop_cannot_pass_the_r_edge_gate():
    """R is anchored to the ORIGINAL 1R stop, so a wider stop re-denominates
    BOTH sides of the split at once and the edge is unchanged."""
    above = [_s(f"BIG{i}", "2026-08-03", -60.0, 3.0, -0.4, "FAIL") for i in range(25)]
    below = [_s(f"SML{i}", "2026-08-03", -2.0, 1.0, -0.4, "FAIL") for i in range(30)]
    base = D.verdict(above + below, 2.0)["era_r_edge"]

    halved = [_s(s.symbol, s.day, s.pl, s.value, s.profit_r / 2, s.doctrine)
              for s in above + below]
    assert D.verdict(halved, 2.0)["era_r_edge"] == pytest.approx(base / 2)
    assert D.verdict(halved, 2.0)["verdict"] == D.REFUTED


def test_win_collateral_cannot_be_diluted_by_relabelling_scratches_as_green():
    """A SCRATCH that books positive dollars is still not a WIN.

    The refused cohort's trades are all green in dollars, so the old
    `win_rate` column reads 100% for it — but only one is a doctrine WIN, and
    that one is the book's only WIN, so the gate fires.
    """
    above = ([_s("BAC", "2026-08-03", 27.72, 3.0, 0.733, "SCRATCH")]
             + [_s(f"S{i}", "2026-08-03", 5.0, 3.0, 0.3, "SCRATCH") for i in range(23)]
             + [_s("WMT", "2026-08-03", 56.74, 3.0, 1.602, "WIN")])
    below = [_s(f"K{i}", "2026-08-03", -1.0, 1.0, -0.05, "FAIL") for i in range(30)]
    split = D.split_at(above + below, 2.0)
    assert split["above"]["win_rate"] == 100.0        # the discredited column
    assert split["above_doctrine"]["true_win_rate"] == 4.0
    assert D.verdict(above + below, 2.0)["win_collateral_fraction"] == 1.0
    assert D.verdict(above + below, 2.0)["verdict"] == D.REFUTED


# --------------------------------------------------------------------------
# The real 2026-09-03 session, verbatim
# --------------------------------------------------------------------------

SESSION_2026_09_03 = [
    # symbol, pl, profit_r, doctrine label — exactly as the DB and bot.doctrine
    # scored them on the night of 2026-09-03 (trades #320-#325).
    ("WMT", 56.74, 1.602, "WIN"),
    ("XOM", 3.30, 0.092, "FAIL"),
    ("QQQ", 14.58, 0.450, "SCRATCH"),
    ("NVDA", 19.03, 0.520, "SCRATCH"),
    ("CRM", -0.36, -0.009, "FAIL"),
    ("GOOG", -9.23, -0.253, "FAIL"),
]


def test_the_real_2026_09_03_session_reads_1_win_not_4():
    """+$84.06 on 4 green trades, and exactly ONE of them paid the thesis."""
    rows = [_s(sym, "2026-09-03", pl, 1.0, r, lab)
            for sym, pl, r, lab in SESSION_2026_09_03]
    stats = D.doctrine_stats(rows)
    assert stats["trades"] == 6
    assert stats["wins"] == 1
    assert stats["true_win_rate"] == 16.7
    assert D.bucket_stats([r.pl for r in rows])["win_rate"] == 66.7
    assert sum(r.pl for r in rows) == pytest.approx(84.06)


def test_xom_banked_3_dollars_and_is_still_a_failure():
    """The doctrine's worked example, from this session: a break-even stop that
    booked +$3.30 is a FAIL, and no amount of green makes it a WIN."""
    xom = _s("XOM", "2026-09-03", 3.30, 1.0, 0.092, "FAIL")
    assert xom.pl > 0
    assert D.doctrine_stats([xom])["true_win_rate"] == 0.0
