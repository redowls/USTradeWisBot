"""Era-controlled testing of ENTRY-side discriminators (IMP-036).

Eleven entry/exit discriminators have been tested and refuted (see todo.md
"Refuted / closed candidates"), and every one of them was settled by a
throwaway script whose numbers can never be re-run as the book grows. This
module is the reusable core those scripts should have shared, and it exists
because of a specific trap that was hit — and only just avoided — on
2026-08-18.

Bucketing the whole 250-trade book by *prior-day daily ATR(14) / 1R* (how wide
the instrument's normal day is compared with the stop the engine gives it)
produces a headline that reads like a shippable filter:

    ATR/1R >= 2.5 : n=115  net -$1841.08  win 28.7%  STOP-rate 68%
    ATR/1R <  2.5 : n=135  net  -$455.20  win 45.2%  STOP-rate 21%

80% of the lifetime loss on one side of one number, with a mechanism that is
easy to believe (the stop sits inside the instrument's daily noise, so noise
alone takes it out). Two checks say do not ship it, and neither existed
anywhere in this repo:

  * ERA CONTROL. 92% of that -$1841.08 comes from the single week
    2026-06-08..06-14 — the pre-gate overtrading era already addressed by the
    daily-loss halt, the widened stops, the breakout veto and the VWAP gate.
    Excluding that week the split is -$147.20 over n=64 (avg -$2.30) against
    -$339.65 over n=125 (avg -$2.72): no discrimination at all. Post-gate
    there is not one trade above ATR/1R 4.0.
  * COLLATERAL. The cohort the filter would refuse contains TSLA — +$577.07
    over 11 trades at a 72.7% win rate, the best symbol the bot has traded.

`bot/analytics.py` buckets by a discriminator, but always over one
undifferentiated population, which is exactly how a one-week artefact reads as
an 80%-of-the-loss finding. Everything here is PURE: no DB, no network, no
config reads. `scripts/entry_discriminator.py` supplies the samples.

Nothing in this module is imported by the live trading path.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

# The pre-gate overtrading era. 2026-06-08..06-14 is the bot's first week: 61 of
# the first 250 trades, and the week the -3% daily-loss halt, the 3xATR/1.5%
# stop widening, the breakout-fade veto (IMP-021) and the VWAP gate (IMP-022)
# were all later written to prevent. A discriminator whose edge lives here is
# re-discovering a problem that has already been fixed four separate ways.
PRE_GATE_ERA_END = "2026-06-14"

# IMP-021 + IMP-022 shipped after this close; the same boundary exit_geometry.py
# uses. The strictest cohort — small, but it is the only bot that still exists.
POST_GATE_START = "2026-07-25"

# A discriminator needs this many trades ABOVE its threshold in the
# era-controlled cohort before the split can be judged at all. Below it, the
# raw effect is by definition concentrated in the excluded era.
MIN_ERA_CONTROLLED_N = 20

# Net-positive symbols inside the refused cohort, as a fraction of that
# cohort's absolute net. Above this the filter is buying its aggregate by
# throwing away symbols that work (the TSLA case above: 44%).
MAX_COLLATERAL_FRACTION = 0.25

SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
ERA_ARTEFACT = "ERA_ARTEFACT"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class Sample:
    """One closed trade reduced to what a discriminator test needs.

    `day` is the ISO date (YYYY-MM-DD) the trade closed on, so cohorts can be
    cut by era with plain string comparison. `value` is the discriminator
    statistic measured AT ENTRY — a statistic that is not knowable at entry
    time cannot become a live gate, however well it separates (the 2026-08-13
    session-range refutation turned on exactly that point).
    """

    symbol: str
    day: str
    pl: float
    value: float


def bucket_stats(pls: list[float]) -> dict:
    """Win-rate / net / expectancy / profit-factor over one slice of P&Ls."""
    n = len(pls)
    if n == 0:
        return {"trades": 0, "net": 0.0, "avg": 0.0,
                "win_rate": 0.0, "profit_factor": None}
    wins = [p for p in pls if p > 0]
    gross_loss = -sum(p for p in pls if p <= 0)
    return {
        "trades": n,
        "net": round(sum(pls), 2),
        "avg": round(mean(pls), 2),
        "win_rate": round(100 * len(wins) / n, 1),
        "profit_factor": round(sum(wins) / gross_loss, 2) if gross_loss else None,
    }


def cohorts(
    samples: list[Sample],
    pre_gate_era_end: str = PRE_GATE_ERA_END,
    post_gate_start: str = POST_GATE_START,
) -> dict[str, list[Sample]]:
    """The three populations every discriminator must be judged on at once.

    "all-time" is the raw book (what the old ad-hoc scripts reported and what
    produces the trap); "era-controlled" drops the pre-gate week; "post-gate"
    keeps only the bot that currently exists. Order is meaningful — it runs
    from most data / least relevance to least data / most relevance.
    """
    return {
        "all-time": list(samples),
        "era-controlled": [s for s in samples if s.day > pre_gate_era_end],
        "post-gate": [s for s in samples if s.day >= post_gate_start],
    }


def split_at(samples: list[Sample], threshold: float) -> dict:
    """Split on `value >= threshold` and score both sides.

    `edge` is below-avg minus above-avg: the per-trade improvement a filter
    that REFUSED the above side would have produced, holding everything else
    equal. Positive edge is the only direction that could justify a filter.
    """
    above = [s for s in samples if s.value >= threshold]
    below = [s for s in samples if s.value < threshold]
    a, b = bucket_stats([s.pl for s in above]), bucket_stats([s.pl for s in below])
    edge = None
    if above and below:
        edge = round(b["avg"] - a["avg"], 2)
    return {"threshold": threshold, "above": a, "below": b, "edge": edge}


def era_concentration(
    samples: list[Sample],
    threshold: float,
    pre_gate_era_end: str = PRE_GATE_ERA_END,
) -> float | None:
    """Fraction of the refused cohort's net P&L contributed by the pre-gate era.

    The single number that kills the ATR/1R filter: 0.92. Returns None when the
    refused cohort is empty or nets exactly zero.
    """
    above = [s for s in samples if s.value >= threshold]
    total = sum(s.pl for s in above)
    if not above or total == 0:
        return None
    era = sum(s.pl for s in above if s.day <= pre_gate_era_end)
    return round(era / total, 4)


def collateral_symbols(samples: list[Sample], threshold: float) -> list[dict]:
    """Net-POSITIVE symbols inside the cohort a filter would refuse.

    Aggregate P&L hides these: a filter can look like it removes a big loss
    while quietly removing the only symbols that work. Sorted best first.
    """
    above = [s for s in samples if s.value >= threshold]
    by_symbol: dict[str, list[float]] = {}
    for s in above:
        by_symbol.setdefault(s.symbol, []).append(s.pl)
    rows = [
        {"symbol": sym, "trades": len(pls), "net": round(sum(pls), 2)}
        for sym, pls in by_symbol.items()
        if sum(pls) > 0
    ]
    return sorted(rows, key=lambda r: r["net"], reverse=True)


def collateral_fraction(samples: list[Sample], threshold: float) -> float | None:
    """Collateral net as a fraction of the refused cohort's absolute net."""
    above = [s for s in samples if s.value >= threshold]
    total = abs(sum(s.pl for s in above))
    if not above or total == 0:
        return None
    return round(sum(r["net"] for r in collateral_symbols(samples, threshold)) / total, 4)


def verdict(
    samples: list[Sample],
    threshold: float,
    min_era_controlled_n: int = MIN_ERA_CONTROLLED_N,
    max_collateral_fraction: float = MAX_COLLATERAL_FRACTION,
    pre_gate_era_end: str = PRE_GATE_ERA_END,
    post_gate_start: str = POST_GATE_START,
) -> dict:
    """Judge one threshold of one discriminator. SUPPORTED is deliberately hard.

    SUPPORTED requires the edge to be positive in ALL THREE cohorts, enough
    modern trades above the line to be judgeable, and no large collateral of
    working symbols. Anything that passes only on the raw book is
    ERA_ARTEFACT, which is a distinct outcome from REFUTED and the one this
    module was built to be able to say out loud.
    """
    groups = cohorts(samples, pre_gate_era_end, post_gate_start)
    splits = {name: split_at(rows, threshold) for name, rows in groups.items()}
    era_frac = era_concentration(samples, threshold, pre_gate_era_end)
    collateral = collateral_symbols(samples, threshold)
    coll_frac = collateral_fraction(samples, threshold)

    all_edge = splits["all-time"]["edge"]
    era_split = splits["era-controlled"]
    era_edge = era_split["edge"]
    era_n = era_split["above"]["trades"]

    reasons: list[str] = []

    if all_edge is None:
        reasons.append("threshold does not split the book — every trade falls on one side")
        result = INSUFFICIENT_DATA
    elif era_n < min_era_controlled_n:
        reasons.append(
            f"only {era_n} trade(s) above the line survive era control "
            f"(need {min_era_controlled_n})"
        )
        if era_frac is not None and era_frac > 0.5:
            reasons.append(
                f"{era_frac:.0%} of the refused cohort's P&L is the pre-gate era "
                f"(<= {pre_gate_era_end})"
            )
        result = ERA_ARTEFACT if all_edge > 0 else INSUFFICIENT_DATA
    elif all_edge > 0 and (era_edge is None or era_edge <= 0):
        reasons.append(
            f"raw edge +${all_edge:.2f}/trade disappears under era control "
            f"(era-controlled edge {era_edge})"
        )
        if era_frac is not None:
            reasons.append(
                f"{era_frac:.0%} of the refused cohort's P&L is the pre-gate era"
            )
        result = ERA_ARTEFACT
    elif all_edge <= 0 and (era_edge is None or era_edge <= 0):
        reasons.append("no positive edge in any cohort — the split does not discriminate")
        result = REFUTED
    else:
        negative = [n for n, s in splits.items()
                    if s["edge"] is None or s["edge"] <= 0]
        if negative:
            reasons.append(f"edge is not positive in every cohort (fails: {', '.join(negative)})")
            result = REFUTED
        elif coll_frac is not None and coll_frac > max_collateral_fraction:
            names = ", ".join(f"{r['symbol']} +${r['net']:.2f}" for r in collateral[:3])
            reasons.append(
                f"refuses {coll_frac:.0%} worth of net-positive symbols ({names}) — "
                f"cap is {max_collateral_fraction:.0%}"
            )
            result = REFUTED
        else:
            reasons.append("positive edge in all three cohorts, era-controlled and "
                           "not carried by collateral damage to working symbols")
            result = SUPPORTED

    return {
        "verdict": result,
        "threshold": threshold,
        "reasons": reasons,
        "splits": splits,
        "era_concentration": era_frac,
        "collateral": collateral,
        "collateral_fraction": coll_frac,
    }


def threshold_sweep(samples: list[Sample], thresholds: list[float], **kwargs) -> list[dict]:
    """`verdict` over a range of thresholds, so non-monotonicity is visible.

    A discriminator whose verdict flips back and forth across adjacent
    thresholds is fitting noise even where an individual row looks strong —
    the same reading that stopped IMP-032's break-even sweep.
    """
    return [verdict(samples, t, **kwargs) for t in thresholds]


def any_supported(sweep: list[dict]) -> bool:
    """True when at least one threshold in a sweep is SUPPORTED."""
    return any(row["verdict"] == SUPPORTED for row in sweep)
