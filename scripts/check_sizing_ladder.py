"""Confidence -> risk-tier reachability check (IMP-027).

summary.md §5.9 documents "more confidence = more money": CONFIDENCE_RISK_TABLE
scales per-trade risk from 0.5% to 2.0% of equity as confidence rises. That
mechanism is no longer live, and nothing in the reporting says so.

IMP-021 (2026-07-25) vetoes every signal whose breakout_score >=
BREAKOUT_FADE_CEILING, and breakout_score is empirically bimodal -- across 219
recorded trades it is either 0.0 or >= 0.5, never in between. So every entry the
bot now takes scores breakout_score = 0.0 exactly, which caps confidence at
100 * (WEIGHT_MA + WEIGHT_VALUE + WEIGHT_MOMENTUM) = 65 and makes the 70/80/90
tiers UNREACHABLE. The ladder is inert: every live trade sizes at the bottom
0.5% tier.

This is a SAFE degeneracy -- risk is pinned at the floor, never the ceiling --
so this script deliberately changes NO behaviour. It exists for two reasons:

  1. Make the inertness visible on every run. Reviews have repeatedly reasoned
     about "confidence 60-62" as if it were a live discriminator; it is a
     5-point dead band, and its one varying input (momentum) has Pearson
     r = 0.0001 with realized P&L over n=145 (2026-08-06 daily review).
  2. Monitor the inverse risk. If breakout_score ever lands strictly between 0
     and the veto ceiling, the ladder silently un-freezes and sizes UP -- on the
     single component IMP-021 proved toxic. A bo=0.49 signal reaches confidence
     82.15 and the 1.5% tier: 3x the risk of every trade the bot takes today.

It also guards the trap in IMP-021's own registered follow-up ("down-weight
WEIGHT_BREAKOUT now that its leg is gated out"): renormalizing the remaining
weights to sum to 1.0 lifts today's real signals from ~61 to ~92 confidence and
straight to the 2.0% MAX_RISK_PCT cap -- a 4x risk widening dressed up as a
tidy-up. Never ship that form.

Run:  python -m scripts.check_sizing_ladder
"""

from __future__ import annotations

import sys

from bot import config, confidence, db, sizing

# Component scores are bounded 0..1 and the regime multiplier maxes at
# REGIME_MULT_OK, so a perfect non-breakout signal is the ceiling.
_PERFECT = 1.0


def confidence_ceiling(max_breakout_score: float = 0.0) -> float:
    """Highest confidence attainable when breakout_score cannot exceed a bound.

    Every other component is given its perfect value, so this is a true
    supremum for the live population, not an average.
    """
    return confidence.score(
        {
            "breakout_score": max_breakout_score,
            "ma_score": _PERFECT,
            "value_score": _PERFECT,
            "momentum_score": _PERFECT,
            "regime_multiplier": config.REGIME_MULT_OK,
        }
    )


def tier_reachability(ceiling: float) -> list[tuple[float, float, bool]]:
    """(min_confidence, risk_pct, reachable) for every CONFIDENCE_RISK_TABLE tier."""
    return [
        (min_conf, pct, min_conf <= ceiling)
        for min_conf, pct in config.CONFIDENCE_RISK_TABLE
    ]


def breakout_tier_lift(evaluation: dict) -> float:
    """Extra risk % this signal gets purely from its breakout component.

    Zero for every trade the bot currently takes (breakout_score is 0.0), and
    positive exactly when the toxic leg is buying bigger size.
    """
    with_bo = sizing.risk_fraction_for_confidence(confidence.score(evaluation))
    without_bo = sizing.risk_fraction_for_confidence(
        confidence.score({**evaluation, "breakout_score": 0.0})
    )
    return with_bo - without_bo


def _offline() -> bool:
    print("[1] Offline: ladder reachability from config")
    ok = True

    live_ceiling = confidence_ceiling(0.0)
    veto_ceiling = confidence_ceiling(config.BREAKOUT_FADE_CEILING)
    print(f"    MIN_CONFIDENCE            : {config.MIN_CONFIDENCE}")
    print(f"    ceiling, breakout_score=0 : {live_ceiling:.2f}   <- the live population")
    print(
        f"    ceiling, breakout at veto : {veto_ceiling:.2f}   "
        f"(bo={config.BREAKOUT_FADE_CEILING}, vetoed by IMP-021)"
    )

    reachable = tier_reachability(live_ceiling)
    print("    tier          risk%   reachable")
    for min_conf, pct, ok_reach in reachable:
        print(f"      conf>={min_conf:<5.0f}   {pct:.1f}%   {'yes' if ok_reach else 'NO'}")

    live_tiers = [pct for _, pct, r in reachable if r]
    if len(live_tiers) != 1:
        print(f"    ✅ ladder is live -- {len(live_tiers)} tiers reachable")
    else:
        print(
            f"    ⚠️  ladder INERT -- only the {live_tiers[0]:.1f}% tier is reachable; "
            "summary.md §5.9 scaling does not apply to any live trade"
        )

    # The floor must still admit trades at all: a ceiling under MIN_CONFIDENCE
    # would mean the bot can never trade, which is a real defect.
    if live_ceiling < config.MIN_CONFIDENCE:
        print(
            f"    ❌ ceiling {live_ceiling:.2f} < MIN_CONFIDENCE "
            f"{config.MIN_CONFIDENCE} -- no signal can ever qualify"
        )
        ok = False

    # The inverse risk: a sub-veto breakout must not buy a higher tier silently.
    lift = breakout_tier_lift(
        {
            "breakout_score": config.BREAKOUT_FADE_CEILING - 0.01,
            "ma_score": _PERFECT,
            "value_score": _PERFECT,
            "momentum_score": _PERFECT,
            "regime_multiplier": config.REGIME_MULT_OK,
        }
    )
    if lift > 0:
        print(
            f"    ⚠️  latent: a just-under-veto breakout (bo="
            f"{config.BREAKOUT_FADE_CEILING - 0.01:.2f}) would size "
            f"+{lift:.1f}% of equity ABOVE its non-breakout tier."
        )
        print(
            "        Not live (breakout_score is bimodal: 0.0 or >=0.5 across all "
            "recorded trades), but unguarded if the scorer ever changes."
        )
    return ok


def summarize(rows: list[tuple]) -> dict:
    """Confidence range, risk-tier histogram and bo>0 count for a set of signals.

    rows are (breakout_score, ma, value, momentum, confidence).
    """
    confs = [float(r[4]) for r in rows]
    tiers: dict[float, int] = {}
    for row in rows:
        pct = sizing.risk_fraction_for_confidence(float(row[4]))
        tiers[pct] = tiers.get(pct, 0) + 1
    return {
        "n": len(rows),
        "conf_min": min(confs),
        "conf_max": max(confs),
        "tiers": tiers,
        "breakout_entries": sum(1 for r in rows if float(r[0]) > 0.0),
    }


def _print_era(label: str, rows: list[tuple]) -> None:
    s = summarize(rows)
    tiers = "  ".join(f"{pct:.1f}%x{n}" for pct, n in sorted(s["tiers"].items()))
    print(
        f"    {label:<24} n={s['n']:<4} conf {s['conf_min']:.2f}..{s['conf_max']:.2f}"
        f"   tiers: {tiers}"
    )


def _recorded() -> bool:
    """Empirical check against real recorded signals. Never fails on no data."""
    print("\n[2] Recorded: what the ladder actually did")
    try:
        with db.get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.breakout_score, s.ma_score, s.value_score,
                       s.momentum_score, s.confidence, t.entry_time
                FROM trades t JOIN signals s ON s.trade_id = t.trade_id
                WHERE t.status = 'CLOSED'
                ORDER BY t.entry_time
                """
            )
            rows = cur.fetchall()
    except Exception as exc:  # DB is optional for this diagnostic
        print(f"    (skipped -- database unavailable: {exc})")
        return True

    if not rows:
        print("    (no recorded trades yet)")
        return True

    post = [r for r in rows if r[5].date() >= config.BREAKOUT_VETO_LIVE_FROM]
    _print_era("all-time", rows)
    if post:
        _print_era(f"post-IMP-021 ({config.BREAKOUT_VETO_LIVE_FROM})", post)

    ceiling = confidence_ceiling(0.0)
    zero_bo = [float(r[4]) for r in rows if float(r[0]) == 0.0]
    if zero_bo and max(zero_bo) > ceiling + 1e-6:
        print(
            f"    ❌ a breakout_score=0 trade scored {max(zero_bo):.2f} > ceiling "
            f"{ceiling:.2f} -- the scorer and the ladder disagree"
        )
        return False

    # Only the post-veto era can tell us whether the ladder is un-freezing.
    leaked = summarize(post)["breakout_entries"] if post else 0
    if leaked:
        print(
            f"    ❌ {leaked} post-veto entries carry breakout_score > 0 -- the "
            "ladder can un-freeze and size up on the vetoed leg"
        )
        return False
    print(
        f"    post-veto entries with breakout_score > 0: 0 "
        "-- IMP-021 veto holding, ladder pinned at the floor tier"
    )
    return True


def main() -> int:
    print("=" * 72)
    print("USTradeWisBot — confidence -> risk-tier ladder reachability (IMP-027)")
    print("=" * 72)
    ok = _offline()
    ok = _recorded() and ok
    print("\n" + "=" * 72)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
