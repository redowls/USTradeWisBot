"""One-dimension entry sweep — "does moving ONLY this parameter help?"

**The methodological hole this closes (IMP-063, 2026-09-26).** ``bot.entry_lab``
is the walk-forward gate every entry-signal change must clear (IMP-059), and it
works by searching a full parameter grid: ``select_in_sample`` scores the whole
cartesian product of ``RULES[rule]`` and returns the single best cell. That
answers "what is the best ORB?" — but it cannot answer the only question a
one-IMP-per-run discipline is allowed to act on, which is **"the gate that is
live today, with exactly one parameter moved: better or worse?"** The grid's
winner differs from the shipped configuration in several dimensions at once, so
adopting it is never one traceable change, and when the winner *is* the shipped
value the run reports a bare ``GATE: PASS`` that says nothing about the parameter
actually under suspicion.

The 2026-09-25 session is the motivating case. It took **zero trades**, the sixth
live ORB session had produced four fills in total, and the refusal ledger said
``orb_after_cutoff`` was 67.2% of all 116 candidates over those six sessions —
25.0% of them blocked by the cutoff and nothing else. The obvious read is that
``ORB_CUTOFF_ET`` 11:30 is starving the book. A full-grid run answers it only
incidentally; this module answers it directly, and the answer was that every
later cutoff is worse **monotonically** on held-out data (see the IMP-063 entry
in ``memory/improvement-log.md``).

Three things it reports that the grid search structurally cannot:

* **The incumbent as the baseline.** ``live_orb_params`` reads the ORB gate out
  of ``bot.config``, so the sweep's base cell IS the running bot and cannot
  silently drift from it. Every candidate is scored against that cell, and the
  ship test is ``entry_lab.gate(candidate_oos, candidate_is, incumbent_oos)`` —
  the same gate, with the live configuration supplied as the incumbent it must
  beat.
* **Monotonicity.** One bad cell is noise; five cells degrading in order is a
  gradient. ``monotone_direction`` reports which, over the values as ordered by
  the caller — the single cheapest defence against reading a curve-fit dip as a
  finding.
* **The marginal cohort.** A relaxation does not just add trades, it also
  *displaces* them: ``entry_lab.run_rule`` applies ``MAX_CONCURRENT_POSITIONS``
  across symbols, so an earlier admitted trade can crowd out one the incumbent
  took. ``marginal_cohort`` diffs the two trade lists both ways and scores the
  ADDED and DROPPED sets separately. That is the number that actually decides a
  relaxation — "the extra trades it buys are worth −X" — and an aggregate
  expectancy comparison hides it.

Pure: no DB, no network, no config writes. Features and the market overlay are
passed in, exactly as ``entry_lab.run_rule`` takes them. **Nothing in the live
path imports this module** — it is lab tooling, like ``bot.entry_lab`` itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import config, entry_lab

#: Verdicts. ``CONFIRMED_INCUMBENT`` is the one the grid search cannot say: not
#: "we found nothing" but "the shipped value was re-tested head-to-head against
#: named alternatives on held-out data and it won".
CANDIDATE_CLEARS = "candidate-clears"
CONFIRMED_INCUMBENT = "confirmed-incumbent"
INSUFFICIENT = "insufficient-evidence"


@dataclass
class SweepCell:
    """One value of the swept dimension, scored on both windows."""

    dim: str
    value: object
    params: dict
    is_metrics: dict
    oos_metrics: dict
    #: Held-out trades, kept so ``marginal_cohort`` can diff cells. Not summary
    #: data — the diff is the point, and it is not recoverable from metrics.
    oos_trades: list = field(default_factory=list)

    @property
    def is_incumbent_of(self) -> object:
        return self.value


def live_orb_params() -> dict:
    """The ORB gate as the running bot is configured, in ``rule_orb``'s vocabulary.

    Read from ``bot.config`` rather than hard-coded so a sweep can never quietly
    baseline against a configuration the bot no longer runs. ``mkt`` is a bool in
    the lab (the overlay is SPY-above-its-own-VWAP either way) while the live knob
    is the filter SYMBOL, so an empty symbol disables it in both.
    """
    return {
        "k": int(config.ORB_RANGE_BARS),
        "cutoff": str(config.ORB_CUTOFF_ET),
        "min_relvol": float(config.ORB_MIN_REL_VOL),
        "buffer_pct": float(config.ORB_BUFFER_PCT),
        "above_vwap": bool(config.ORB_REQUIRE_ABOVE_VWAP),
        "mkt": bool((config.ORB_MARKET_FILTER_SYMBOL or "").strip()),
    }


def sweep_dimension(
    rule: str,
    trigger_fn,
    base: dict,
    dim: str,
    values: list,
    feats: dict[str, pd.DataFrame],
    is_days: list[date],
    oos_days: list[date],
    equity: float,
    slippage_pct: float = 0.0,
    mkt: pd.Series | None = None,
) -> list[SweepCell]:
    """Score ``base`` with ``dim`` set to each of ``values``, on both windows.

    Cells come back in the order ``values`` was given — ``monotone_direction``
    reads that order, so pass the values along the axis you mean (for a cutoff:
    earliest to latest).
    """
    cells: list[SweepCell] = []
    for value in values:
        params = dict(base)
        params[dim] = value
        is_t = entry_lab.run_rule(rule, trigger_fn, params, feats, is_days, equity, slippage_pct, mkt)
        oos_t = entry_lab.run_rule(rule, trigger_fn, params, feats, oos_days, equity, slippage_pct, mkt)
        cells.append(SweepCell(
            dim=dim, value=value, params=params,
            is_metrics=entry_lab.doctrine_metrics(is_t),
            oos_metrics=entry_lab.doctrine_metrics(oos_t),
            oos_trades=oos_t,
        ))
    return cells


def incumbent_cell(cells: list[SweepCell], value) -> SweepCell | None:
    """The cell holding the live value, or None when it was not swept.

    Compared as strings so ``"11:30"`` from config matches a swept ``"11:30"``
    and ``1.3`` matches ``1.3`` without depending on the caller's literal types.
    """
    for c in cells:
        if str(c.value) == str(value):
            return c
    return None


def _key(trade) -> tuple:
    """Identity of a lab trade: the symbol and the bar it was entered on."""
    return (trade.symbol, trade.entry_time)


def marginal_cohort(cell: SweepCell, incumbent: SweepCell) -> dict:
    """What ``cell`` trades that ``incumbent`` does not, and what it loses.

    Two cohorts, because concurrency makes a relaxation non-monotone in the trade
    set: **added** trades exist only under ``cell``, **dropped** trades existed
    under ``incumbent`` and were crowded out by an earlier admission. Each is
    scored with the same doctrine metrics as a whole window, so "the extra trades
    are worth −$441 at −0.19R each" is stated rather than inferred from two
    aggregate expectancies.

    ``net_delta`` is the held-out P&L difference the two cohorts explain; it ties
    to ``cell.oos_metrics['net'] - incumbent.oos_metrics['net']`` exactly, since
    every trade not in a cohort is common to both cells.
    """
    mine = {_key(t): t for t in cell.oos_trades}
    theirs = {_key(t): t for t in incumbent.oos_trades}
    added = [mine[k] for k in mine.keys() - theirs.keys()]
    dropped = [theirs[k] for k in theirs.keys() - mine.keys()]
    return {
        "added": added,
        "dropped": dropped,
        "added_metrics": entry_lab.doctrine_metrics(added),
        "dropped_metrics": entry_lab.doctrine_metrics(dropped),
        "net_delta": round(
            entry_lab.doctrine_metrics(added)["net"]
            - entry_lab.doctrine_metrics(dropped)["net"], 2),
    }


def monotone_direction(cells: list[SweepCell], key: str = "exp_r",
                       window: str = "oos") -> str:
    """'decreasing' / 'increasing' / 'none' for ``key`` across the cells in order.

    Non-strict on either side, so a flat pair does not break a run; a sweep that
    both rises and falls returns 'none'. Fewer than two cells is 'none' — there
    is no direction in a single point. A clean direction over several cells is
    what separates a gradient from a cherry-picked cell, and it is deliberately
    reported rather than folded into the verdict: it is evidence for the reader,
    not a ship criterion.
    """
    vals = [(c.oos_metrics if window == "oos" else c.is_metrics)[key] for c in cells]
    if len(vals) < 2:
        return "none"
    pairs = list(zip(vals, vals[1:]))
    if all(b <= a for a, b in pairs):
        return "decreasing"
    if all(b >= a for a, b in pairs):
        return "increasing"
    return "none"


def sweep_verdict(cells: list[SweepCell], incumbent_value) -> dict:
    """Ship / no-ship for a one-dimension sweep, with every cell's reasons kept.

    A candidate must clear ``entry_lab.gate`` **with the incumbent supplied as the
    baseline it has to beat** — so passing requires held-out n >= MIN_TRADES_OOS,
    positive held-out AND in-sample expectancy, held-out PF >= GATE_MIN_PF, and
    strictly better held-out expectancy than the live configuration. When more
    than one clears, the highest held-out expectancy wins.

    ``INSUFFICIENT`` when the incumbent itself is absent from the sweep or has
    fewer than ``MIN_TRADES_OOS`` held-out trades: with no trustworthy baseline a
    "candidate beats incumbent" comparison is meaningless, and reporting that as
    ``CONFIRMED_INCUMBENT`` would be the same failure IMP-062 fixed on the
    escalation side — an unknown dressed up as a clean bill of health.
    """
    inc = incumbent_cell(cells, incumbent_value)
    if inc is None:
        return {"verdict": INSUFFICIENT, "incumbent": None, "best": None,
                "reason": f"live value {incumbent_value!r} was not one of the swept values",
                "cells": [], "monotone": monotone_direction(cells)}
    if inc.oos_metrics["n"] < entry_lab.MIN_TRADES_OOS:
        return {"verdict": INSUFFICIENT, "incumbent": str(inc.value), "best": None,
                "reason": (f"incumbent held-out n={inc.oos_metrics['n']} < "
                           f"{entry_lab.MIN_TRADES_OOS} — no trustworthy baseline"),
                "cells": [], "monotone": monotone_direction(cells)}

    rows: list[dict] = []
    clears: list[tuple[SweepCell, float]] = []
    for c in cells:
        if c is inc:
            rows.append({"value": str(c.value), "incumbent": True, "clears": False,
                         "why": ["incumbent"], "oos_exp_r": c.oos_metrics["exp_r"],
                         "delta_exp_r": 0.0})
            continue
        ok, why = entry_lab.gate(c.oos_metrics, c.is_metrics, inc.oos_metrics)
        rows.append({"value": str(c.value), "incumbent": False, "clears": ok, "why": why,
                     "oos_exp_r": c.oos_metrics["exp_r"],
                     "delta_exp_r": round(c.oos_metrics["exp_r"] - inc.oos_metrics["exp_r"], 4)})
        if ok:
            clears.append((c, c.oos_metrics["exp_r"]))

    best = max(clears, key=lambda kv: kv[1])[0] if clears else None
    return {
        "verdict": CANDIDATE_CLEARS if best is not None else CONFIRMED_INCUMBENT,
        "incumbent": str(inc.value),
        "best": None if best is None else str(best.value),
        "reason": ("no swept value beat the live configuration through the gate"
                   if best is None else
                   f"{best.dim}={best.value} clears the gate against the incumbent"),
        "cells": rows,
        "monotone": monotone_direction(cells),
    }
