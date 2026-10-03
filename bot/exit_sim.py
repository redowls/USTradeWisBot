"""Exit-geometry replay — simulates the bot's ACTUAL two-stage stop ratchet (IMP-028).

Why this exists (and why ``bot/replay.py`` was not enough)
---------------------------------------------------------
``replay.simulate_bracket`` models a *static* bracket plus an optional
``breakeven_at_r`` what-if. Since IMP-013 (2026-07-08) the live bot has run a
**two-stage** ratchet instead (``exits.compute_trailed_stop``):

  * at ``BREAKEVEN_TRIGGER_R`` (0.5R) unrealized -> stop moves to the entry price;
  * at ``TRAIL_TRIGGER_R``   (1.0R) unrealized -> stop trails ``TRAIL_DISTANCE_R``
    (1.0R) below the live price;
  * a move is skipped unless it improves the stop by ``STOP_RATCHET_MIN_PCT``
    (0.10%) of entry, so the leg is not replaced for pennies every 60s tick.

The static model has **no representation of the ratchet at all**, with three
consequences on the 36-trade post-gate book (since 2026-07-25):

  1. It mislabels **11 of 36** exits, every one of them a real STOP reported as
     EOD_FLATTEN — because a trade taken out by the *moved* stop never touches its
     original 3xATR stop, so a static bracket sees no stop leg fire.
  2. Its P&L error nevertheless looks tiny ($2.70). That is an artefact, not
     accuracy: ``replay_trades`` passes the trade's **actual exit price** as the
     EOD fallback, so every ratchet-caused exit falls through to the recorded
     answer. The model looks most accurate on exactly the trades it does not model.
  3. **No trail counterfactual is computable.** "What would a 0.5R trail have
     done?" has no expressible form, which is why the 2026-08-01 weekly recorded
     that the exit change it named as the #1 lever "cannot be honestly validated".

This module closes (3), which is the one that blocks the equity curve.

Fidelity on the same 36 trades: sim -$147.28 vs actual -$148.39, sum|error|
**$4.73** (~$0.13/trade), mislabels down to 6.

Bar-data caveat that bounds all of the above (IEX sparsity)
-----------------------------------------------------------
Bars come from IEX, roughly 2-3% of consolidated volume, so a minute with no IEX
print has no bar and printed highs/lows are inside the true range. META #233 is
the worked example: 270 bars for a 279-minute window, and the lowest IEX low
after the stop armed was 590.555 while the fill that actually took it out printed
at 590.38 — IEX never saw the tick. That is the whole of the residual 6-trade
mislabel, and it means simulated stops fire **less** often than real ones. A
what-if that TIGHTENS stops is therefore biased optimistic and its edge must
clear the noise budget by a wide margin before it is believed.

The defect it was built to measure
----------------------------------
Because the trail is anchored ``TRAIL_DISTANCE_R`` below price and 1.0R is also
the trigger, the trail candidate at exactly +1.0R equals the entry price — the
same level the break-even stage already set — and the ratchet min-step then
blocks it until roughly +1.1R. **Between +0.5R and ~+1.08R the protective stop is
pinned at entry and captures nothing.** Post-gate (36 trades since 2026-07-25),
6 trades peaked >= +0.5R carrying $174.12 of combined peak open profit and
realized -$5.29 (capture -3.0%); the +0.5R..+1.0R band as a whole captured 16.3%
of its peak against 52.0% for trades that cleared +1.0R.

Bar-level caveats (same honesty as bot/replay.py)
-------------------------------------------------
  - Within one bar we cannot know whether the stop or the target was touched
    first, so the stop is always checked FIRST (conservative).
  - The ratchet is evaluated from the bar's HIGH at the END of the bar, after the
    stop/target checks. The live bot ratchets once per ~60s tick, so arming from
    the same bar that is then tested against the new stop would be optimistic.
  - Entries/exits happened at intrabar prices the bars cannot reproduce, so
    per-trade deltas of a few dollars are expected even for a perfect model. The
    aggregate ``abs_error`` is the noise budget: a what-if delta must clear it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import config


# --- Geometry ----------------------------------------------------------------

@dataclass(frozen=True)
class ExitGeometry:
    """One candidate stop/target ratchet configuration.

    ``from_config()`` returns the geometry the live bot is running right now, so
    the fidelity baseline and every what-if are described by the same object.
    """

    breakeven_trigger_r: float
    trail_trigger_r: float
    trail_distance_r: float
    ratchet_min_pct: float
    trailing_enabled: bool = True

    @classmethod
    def from_config(cls) -> "ExitGeometry":
        return cls(
            breakeven_trigger_r=config.BREAKEVEN_TRIGGER_R,
            trail_trigger_r=config.TRAIL_TRIGGER_R,
            trail_distance_r=config.TRAIL_DISTANCE_R,
            ratchet_min_pct=config.STOP_RATCHET_MIN_PCT,
            trailing_enabled=config.TRAILING_STOP_ENABLED,
        )

    def label(self) -> str:
        if not self.trailing_enabled:
            return "no-ratchet (static bracket)"
        return (f"be={self.breakeven_trigger_r:g}R trail@{self.trail_trigger_r:g}R"
                f"-{self.trail_distance_r:g}R min={self.ratchet_min_pct:g}%")


@dataclass
class ExitSimResult:
    exit_price: float
    exit_reason: str          # 'STOP' / 'TAKE_PROFIT' / 'EOD_FLATTEN'
    mfe: float                # max favorable excursion, $/share vs entry
    mae: float                # max adverse excursion, $/share vs entry (<= 0)
    final_stop: float         # where the protective stop ended up
    armed_breakeven: bool     # did the stop ever reach the entry price?
    armed_trail: bool         # did the stop ever move ABOVE the entry price?


# --- Pure ratchet ------------------------------------------------------------

def ratchet_stop(
    entry_price: float,
    initial_stop: float,
    current_stop: float,
    live_price: float | None,
    geometry: ExitGeometry,
    high_price: float | None = None,
) -> float | None:
    """New (higher) stop for a long, or None when it should not move.

    A parameterised mirror of ``exits.compute_trailed_stop`` — that function reads
    the module-level config constants, which makes it impossible to ask "what
    would a different trail have done?". Behaviour is otherwise identical, and
    ``tests/test_exit_sim.py`` asserts the two agree under the live config so they
    cannot silently drift apart.

    R is anchored to the ORIGINAL plan stop, never the already-moved stop.
    ``high_price`` mirrors IMP-031: the break-even stage tests the highest price
    PRINTED since entry, the trail stage keeps testing the live price. It exists
    here so the parity assertion above stays exact now that the live function
    takes it — ``simulate_exit`` already passes each bar's high as ``live_price``,
    which is why the simulator has always modelled a bot that sees every high.
    """
    if not geometry.trailing_enabled or live_price is None:
        return None
    risk = entry_price - initial_stop
    if risk <= 0 or entry_price <= 0:
        return None
    peak = live_price if high_price is None else max(live_price, high_price)
    candidate: float | None = None
    if (live_price - entry_price) / risk >= geometry.trail_trigger_r:
        candidate = live_price - geometry.trail_distance_r * risk
    if (peak - entry_price) / risk >= geometry.breakeven_trigger_r:
        candidate = entry_price if candidate is None else max(candidate, entry_price)
    if candidate is None:
        return None
    min_step = entry_price * geometry.ratchet_min_pct / 100.0
    if candidate <= current_stop + min_step:
        return None
    return round(candidate, 2)


# --- Simulation core (pure: bars in, result out) -----------------------------

def simulate_exit(
    bars: pd.DataFrame,
    entry_price: float,
    initial_stop: float,
    take_profit_price: float | None,
    fallback_exit_price: float,
    geometry: ExitGeometry,
) -> ExitSimResult:
    """Walk one trade's bars under ``geometry`` and report how it would have exited.

    ``bars`` must cover entry..exit with ``high``/``low`` columns in chronological
    order. ``fallback_exit_price`` is used when neither leg triggers (the 15:55
    EOD flatten).
    """
    stop = initial_stop
    mfe = 0.0
    mae = 0.0
    armed_be = False
    armed_trail = False

    for _, bar in bars.iterrows():
        high = float(bar["high"])
        low = float(bar["low"])
        mfe = max(mfe, high - entry_price)
        mae = min(mae, low - entry_price)

        if low <= stop:
            return ExitSimResult(stop, "STOP", mfe, mae, stop, armed_be, armed_trail)
        if take_profit_price is not None and high >= take_profit_price:
            return ExitSimResult(take_profit_price, "TAKE_PROFIT", mfe, mae,
                                 stop, armed_be, armed_trail)

        moved = ratchet_stop(entry_price, initial_stop, stop, high, geometry)
        if moved is not None:
            stop = moved
            armed_be = armed_be or stop >= entry_price
            armed_trail = armed_trail or stop > entry_price

    return ExitSimResult(fallback_exit_price, "EOD_FLATTEN", mfe, mae,
                         stop, armed_be, armed_trail)


# --- Aggregation -------------------------------------------------------------

def _round2(value: float) -> float:
    return round(value, 2)


def replay_geometry(
    trades: list[dict],
    bars_by_trade: dict,
    geometry: ExitGeometry,
    fallback_by_trade: dict | None = None,
) -> dict:
    """Replay every trade under ``geometry``; return the aggregate + per-trade rows.

    ``trades`` are DB rows (trade_id/qty/entry_price/stop_price/
    take_profit_price/exit_price/realized_pl/exit_reason); ``bars_by_trade`` maps
    trade_id -> the bar window to walk. Trades without bars are skipped.

    ``fallback_by_trade`` maps trade_id -> the price to use when neither leg
    triggers. Pass the **session-end close** together with an entry..15:55 window
    (IMP-030) so a candidate that would have held PAST the live exit is judged on
    real bars. Omit it and each trade falls back to its own recorded exit price,
    which is only correct when the window itself ends at that exit.

    ``abs_error`` (sum of |sim - actual|) is the simulation noise budget for the
    CURRENT geometry — a what-if's ``delta`` has to clear it to mean anything.
    ``captured_pct`` is realized P&L as a share of total peak open profit: the
    give-back metric this module was built to expose.
    """
    rows: list[dict] = []
    for t in trades:
        bars = bars_by_trade.get(t["trade_id"])
        if bars is None or len(bars) == 0:
            continue
        entry = float(t["entry_price"])
        plan_stop = float(t["stop_price"])
        risk = entry - plan_stop
        if risk <= 0:
            continue
        qty = float(t["qty"])
        tp = float(t["take_profit_price"]) if t.get("take_profit_price") else None
        fallback = float(t["exit_price"])
        if fallback_by_trade is not None and t["trade_id"] in fallback_by_trade:
            fallback = float(fallback_by_trade[t["trade_id"]])
        sim = simulate_exit(bars, entry, plan_stop, tp, fallback, geometry)
        rows.append({
            "trade_id": t["trade_id"],
            "symbol": t["symbol"],
            "day": t["entry_time"].strftime("%Y-%m-%d"),
            "actual_pl": float(t["realized_pl"]),
            "actual_reason": t["exit_reason"],
            "sim_pl": _round2((sim.exit_price - entry) * qty),
            "sim_reason": sim.exit_reason,
            "mfe_r": round(sim.mfe / risk, 2),
            "mae_r": round(sim.mae / risk, 2),
            "mfe_usd": _round2(sim.mfe * qty),
            "armed_breakeven": sim.armed_breakeven,
            "armed_trail": sim.armed_trail,
        })

    actual = sum(r["actual_pl"] for r in rows)
    sim_total = sum(r["sim_pl"] for r in rows)
    peak = sum(r["mfe_usd"] for r in rows)
    return {
        "geometry": geometry.label(),
        "rows": rows,
        "trades": len(rows),
        "actual_pl": _round2(actual),
        "sim_pl": _round2(sim_total),
        "delta": _round2(sim_total - actual),
        "abs_error": _round2(sum(abs(r["sim_pl"] - r["actual_pl"]) for r in rows)),
        "sim_wins": sum(1 for r in rows if r["sim_pl"] > 0),
        "peak_mfe_usd": _round2(peak),
        "captured_pct": round(sim_total / peak * 100.0, 1) if peak > 0 else None,
        "armed_breakeven": sum(1 for r in rows if r["armed_breakeven"]),
        "armed_trail": sum(1 for r in rows if r["armed_trail"]),
    }


def giveback_rows(rows: list[dict], min_peak_r: float = 0.5,
                  max_realized: float = 1.0) -> list[dict]:
    """Trades that reached ``min_peak_r`` and still banked <= ``max_realized``.

    The give-back population: the ratchet saved them from a loss but the geometry
    captured none of the profit they had shown. This is the cohort the +0.5R..+1.0R
    dead zone produces (see the module docstring).
    """
    return [r for r in rows
            if r["mfe_r"] >= min_peak_r and r["actual_pl"] <= max_realized]


# --- Entry quality, measured independently of the exit (IMP-069) -------------
#
# Every number this bot reports — net P&L, win rate, stop rate, profit factor,
# expectancy, and every doctrine WIN/SCRATCH/FAIL bucket — is a function of the
# signal AND the exit together. That is why the improvement log has oscillated
# between "fix the exit" (IMP-013/028/029/040) and "fix the entry"
# (IMP-017/021/022/059/065/066) for 68 runs without ever settling which one is
# actually broken: no statistic in the repo could separate them.
#
# MFE and MAE can. Measured from the fill over a window that runs to the 15:55
# flatten, they say which way the stock went AFTER the signal fired and how far,
# and they do not depend on where any stop was placed. Two tests follow from
# that, and neither has a tunable threshold:
#
#   1. DIRECTIONAL INFORMATION. ``edge_ratio = mean(MFE_R) / mean(|MAE_R|)``.
#      A signal that predicts direction travels further for you than against
#      you, so the only non-arbitrary floor is 1.0. Below it the entry is
#      anti-predictive and no exit geometry can rescue it.
#   2. TARGET REACHABILITY. The share of trades whose MFE ever prints
#      ``RR_RATIO`` R, against the ``1/(1+RR_RATIO)`` hit rate a 1R-stop /
#      RR_RATIO-target bracket needs to break even. If the target is never
#      touched the TAKE_PROFIT leg is decorative and all upside has to come from
#      the trail and the flatten capturing sub-target excursions.
#
# Then the leak is ATTRIBUTED by partitioning realized P&L three ways. The split
# is exhaustive and mutually exclusive, so the three sub-totals sum to the book:
#
#   banked            realized > 0 — the trade paid.
#   no-follow-through realized <= 0 and MFE never reached the break-even
#                     trigger. The trade never showed enough profit for ANY
#                     ratchet to act on, so no exit change could have helped it.
#                     This loss belongs to the ENTRY.
#   gave-back         realized <= 0 and MFE did reach the trigger. The thesis
#                     paid and the geometry handed it back. This loss belongs to
#                     the EXIT.
#
# Measured on the live ORB book (10 trades, 2026-09-21..2026-10-02): edge_ratio
# **1.012**, target reached **0/10** against the 40% a 1.5R bracket needs, and
# the attribution is no-follow-through **-$93.72** vs gave-back **-$0.36**. On
# the wider window bars still cover (21 trades back to 2026-09-10) it is worse:
# edge_ratio **0.669**, target 0/21, no-follow-through **-$212.70** vs gave-back
# **-$1.50**. The exit geometry owns under 1% of the leak in both windows, which
# is the measurement the 2026-10-02 daily review used to stop proposing exit
# tweaks against a no-demonstrated-edge entry.
#
# Caveat inherited from the module docstring: IEX bars under-report true highs
# and lows, so BOTH excursions are biased small. The ratio is a quotient of two
# quantities biased the same direction, which is why it is reported rather than
# the raw magnitudes alone.

EXCURSION_CLASSES = ("banked", "no-follow-through", "gave-back")


def classify_excursion(row: dict, breakeven_trigger_r: float) -> str:
    """Attribute one replayed trade to ``banked`` / ``no-follow-through`` / ``gave-back``.

    ``row`` is a ``replay_geometry`` per-trade row (needs ``actual_pl``, ``mfe_r``).
    The three classes partition the book exactly — see the block comment above.
    """
    if float(row["actual_pl"]) > 0:
        return "banked"
    if float(row["mfe_r"]) < breakeven_trigger_r:
        return "no-follow-through"
    return "gave-back"


def excursion_summary(rows: list[dict],
                      breakeven_trigger_r: float | None = None,
                      target_r: float | None = None) -> dict:
    """Exit-independent entry-quality scorecard over ``replay_geometry`` rows.

    Returns ``{}`` for an empty book. ``breakeven_trigger_r`` and ``target_r``
    default to the live config so the verdict describes the geometry actually
    running. Pure — no DB, no network, no mutation of ``rows``.
    """
    if not rows:
        return {}
    trigger = (config.BREAKEVEN_TRIGGER_R if breakeven_trigger_r is None
               else float(breakeven_trigger_r))
    target = config.RR_RATIO if target_r is None else float(target_r)

    n = len(rows)
    mfes = [float(r["mfe_r"]) for r in rows]
    maes = [abs(float(r["mae_r"])) for r in rows]
    mean_mfe = sum(mfes) / n
    mean_mae = sum(maes) / n
    # mean_mae is a mean of absolute values, so it is 0 only when NO trade ever
    # traded below its fill. Leave the ratio undefined there rather than inventing
    # an infinity the caller would have to special-case anyway.
    edge_ratio = round(mean_mfe / mean_mae, 3) if mean_mae > 0 else None

    reached = sum(1 for m in mfes if m >= target)
    needed = 100.0 / (1.0 + target) if target > 0 else None

    attribution: dict[str, dict] = {}
    for label in EXCURSION_CLASSES:
        sub = [r for r in rows if classify_excursion(r, trigger) == label]
        attribution[label] = {
            "trades": len(sub),
            "total_pl": _round2(sum(float(r["actual_pl"]) for r in sub)),
            "peak_mfe_usd": _round2(sum(float(r["mfe_usd"]) for r in sub)),
        }

    if edge_ratio is None:
        verdict = "UNDEFINED — no trade traded below its fill"
    elif edge_ratio <= 1.0:
        verdict = ("NO DIRECTIONAL EDGE — the average trade travels further "
                   "AGAINST the entry than for it")
    else:
        verdict = (f"excursions favour the entry {edge_ratio:g}:1 — judge it "
                   f"against the {needed:.0f}% target-reach the bracket needs"
                   if needed is not None else
                   f"excursions favour the entry {edge_ratio:g}:1")

    return {
        "trades": n,
        "breakeven_trigger_r": trigger,
        "target_r": target,
        "mean_mfe_r": round(mean_mfe, 3),
        "mean_mae_r": round(mean_mae, 3),
        "median_mfe_r": round(sorted(mfes)[n // 2], 3),
        "edge_ratio": edge_ratio,
        "target_reached": reached,
        "target_reach_pct": round(reached / n * 100.0, 1),
        "target_reach_needed_pct": round(needed, 1) if needed is not None else None,
        "attribution": attribution,
        "exit_owned_pl": attribution["gave-back"]["total_pl"],
        "entry_owned_pl": attribution["no-follow-through"]["total_pl"],
        "verdict": verdict,
    }
