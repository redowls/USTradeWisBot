"""CLI: does the ORB volume confirmation have to land on the break bar itself?

  python -m scripts.confirm_lab --values 0,1,2,3,4,6 \
      --start 2025-09-30 --end 2026-09-29 --cache /tmp/uswisbot_iex_12m.pkl

Sweeps ``confirm_bars`` — how many bars after a fresh opening-range break the
live volume floor is still allowed to be met — with **every other ORB parameter,
including ``ORB_MIN_REL_VOL`` itself, pinned to the running bot**. ``0`` is the
incumbent: the live gate demands volume on the break bar and permanently discards
the break otherwise.

Judged by the IMP-059 walk-forward gate through ``entry_sweep.sweep_verdict``,
with the live cell supplied as the baseline a candidate must beat. In-sample
selection is reported **separately and first**, because ``sweep_verdict`` ranks
clearing cells by held-out expectancy and the standing rule is that the
parameter is chosen in-sample and judged once on held-out data — so a value only
ships when it is BOTH the in-sample pick and a gate-clearer.

Defaults to ``config.DATA_FEED`` (IMP-065): the feed the bot actually trades.
Reads market data only; touches no database table, no config file, no live path.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone

from bot import config, confirm_lab, db, entry_lab, entry_sweep
from scripts.entry_lab import (
    DEFAULT_EQUITY, DEFAULT_SLIPPAGE_PCT, _arg, load_or_fetch, resolve_feed,
)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    end = date.fromisoformat(_arg(argv, "--end", str(date.today() - timedelta(days=1))))
    start = date.fromisoformat(_arg(argv, "--start", str(end - timedelta(days=365))))
    slippage = float(_arg(argv, "--slippage", str(DEFAULT_SLIPPAGE_PCT)))
    equity = float(_arg(argv, "--equity", str(DEFAULT_EQUITY)))
    feed, feed_warning = resolve_feed(argv)
    cache = _arg(argv, "--cache", "")
    out = _arg(argv, "--out", "")
    syms_arg = _arg(argv, "--symbols", "")
    values = [int(v.strip()) for v in _arg(argv, "--values", "0,1,2,3,4,6").split(",") if v.strip()]
    if confirm_lab.LIVE_CONFIRM_BARS not in values:
        print(f"--values must include the live value {confirm_lab.LIVE_CONFIRM_BARS} "
              f"or there is no baseline to judge against")
        return 2
    if feed_warning:
        print(f"⚠️  {feed_warning}")

    base = confirm_lab.live_confirm_params()
    symbols = [s.strip().upper() for s in syms_arg.split(",") if s.strip()] or \
        [w["symbol"] for w in db.get_active_watchlist()]
    universe = sorted(set(symbols) | {"SPY"})

    print(f"Fetching {config.BAR_TIMEFRAME} {feed.upper()} bars {start}..{end} "
          f"for {len(universe)} symbols…", flush=True)
    bars = load_or_fetch(universe, start, end, feed, cache)
    sessions = sorted({ts.date() for ts in bars["SPY"].index if start <= ts.date() <= end})
    is_days, oos_days = entry_lab.split_sessions(sessions)
    feats = {s: entry_lab.precompute_features(bars[s]) for s in symbols if not bars[s].empty}
    mkt = entry_lab.market_ok(entry_lab.precompute_features(bars["SPY"]))

    print(f"Live ORB gate (base cell): {base}")
    print(f"Sweeping {confirm_lab.DIM} over {values} — every other parameter pinned to live,")
    print(f"  INCLUDING the volume floor: min_relvol stays {base['min_relvol']} in every cell.")
    print(f"Exit geometry: BE {config.BREAKEVEN_TRIGGER_R}R, trail "
          f"{config.TRAIL_TRIGGER_R}R/{config.TRAIL_DISTANCE_R}R "
          f"(trailing={config.TRAILING_STOP_ENABLED}), RR {config.RR_RATIO}, "
          f"stop max({config.ATR_STOP_MULT}xATR, {config.MIN_STOP_PCT}%)")
    print(f"Sessions: {len(sessions)}  in-sample {is_days[0]}..{is_days[-1]} ({len(is_days)})  "
          f"held-out {oos_days[0]}..{oos_days[-1]} ({len(oos_days)})", flush=True)

    # How big is the population the dimension can even reach?
    prof = {"admitted": 0, "refused": 0, "rescued": {n: 0 for n in values if n > 0}}
    for f in feats.values():
        p = confirm_lab.confirmation_profile(f, base, max_bars=max(values), mkt=mkt)
        prof["admitted"] += p["admitted"]
        prof["refused"] += p["refused"]
        for n in prof["rescued"]:
            prof["rescued"][n] += p["rescued"][n]
    print(f"\nReachable population ({feed.upper()}, {len(sessions)} sessions, before concurrency):")
    print(f"  fresh breaks the LIVE gate admits             : {prof['admitted']}")
    print(f"  fresh breaks refused on volume alone          : {prof['refused']}")
    for n in sorted(prof["rescued"]):
        print(f"  confirmed within {n} bar(s) → extra triggers  : {prof['rescued'][n]}"
              f"  (+{100 * prof['rescued'][n] / max(prof['admitted'], 1):.0f}% throughput)")

    cells = entry_sweep.sweep_dimension(
        "orb", confirm_lab.rule_orb_confirm, base, confirm_lab.DIM, values, feats,
        is_days, oos_days, equity, slippage, mkt)
    verdict = entry_sweep.sweep_verdict(cells, base[confirm_lab.DIM])
    inc = entry_sweep.incumbent_cell(cells, base[confirm_lab.DIM])

    print("\n" + entry_lab.metrics_header())
    for c in cells:
        tag = " *LIVE*" if c is inc else ""
        print(entry_lab.format_metrics_row(f"{confirm_lab.DIM}={c.value} / in-sample{tag}", c.is_metrics))
        print(entry_lab.format_metrics_row(f"{confirm_lab.DIM}={c.value} / held-out{tag}", c.oos_metrics))

    # In-sample selection, reported BEFORE the held-out verdict is read, because
    # that is the order the standing rule requires the choice to be made in.
    ranked = sorted(cells, key=lambda c: c.is_metrics["exp_r"], reverse=True)
    is_pick = ranked[0]
    print(f"\nIN-SAMPLE selection (the choice the rule allows): {confirm_lab.DIM}="
          f"{is_pick.value} at {is_pick.is_metrics['exp_r']:+.4f}R "
          f"(PF {is_pick.is_metrics['pf']}, n={is_pick.is_metrics['n']})")
    print("  in-sample ranking: " + " · ".join(
        f"{c.value}={c.is_metrics['exp_r']:+.4f}R" for c in ranked))

    marginals: dict = {}
    if inc is not None:
        print(f"\n--- held-out marginal cohorts vs LIVE {confirm_lab.DIM}={inc.value} ---")
        print(f"{'value':<12}{'added n':>9}{'added $':>10}{'added expR':>12}"
              f"{'dropped n':>11}{'dropped $':>11}{'net Δ$':>10}")
        for c in cells:
            if c is inc:
                continue
            m = entry_sweep.marginal_cohort(c, inc)
            marginals[str(c.value)] = {
                "added": m["added_metrics"], "dropped": m["dropped_metrics"],
                "net_delta": m["net_delta"]}
            print(f"{str(c.value):<12}{m['added_metrics']['n']:>9}"
                  f"{m['added_metrics']['net']:>10.2f}{m['added_metrics']['exp_r']:>12.4f}"
                  f"{m['dropped_metrics']['n']:>11}{m['dropped_metrics']['net']:>11.2f}"
                  f"{m['net_delta']:>10.2f}")

    print(f"\nheld-out expectancy gradient over {confirm_lab.DIM}: {verdict['monotone'].upper()}")
    for row in verdict["cells"]:
        mark = "LIVE " if row["incumbent"] else ("PASS " if row["clears"] else "fail ")
        why = "" if row["incumbent"] or row["clears"] else "  — " + "; ".join(row["why"])
        print(f"  {mark}{confirm_lab.DIM}={row['value']:<6} held-out {row['oos_exp_r']:+.4f}R "
              f"(Δ {row['delta_exp_r']:+.4f}R){why}")

    ships = (verdict["verdict"] == entry_sweep.CANDIDATE_CLEARS
             and str(is_pick.value) == str(verdict["best"]))
    print(f"\nVERDICT: {verdict['verdict'].upper()} — {verdict['reason']}")
    if verdict["verdict"] == entry_sweep.CANDIDATE_CLEARS and not ships:
        print(f"  ⚠️  NOT SHIPPABLE: the gate's best held-out cell ({verdict['best']}) is not the "
              f"in-sample pick ({is_pick.value}). Choosing it would be held-out selection.")
    print(f"SHIPPABLE: {'YES' if ships else 'NO'}")

    if out:
        with open(out, "w") as fh:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dim": confirm_lab.DIM, "values": values, "base": base,
                "window": f"{sessions[0]}..{sessions[-1]}", "sessions": len(sessions),
                "in_sample": [str(is_days[0]), str(is_days[-1]), len(is_days)],
                "held_out": [str(oos_days[0]), str(oos_days[-1]), len(oos_days)],
                "slippage_pct": slippage, "equity": equity, "feed": feed,
                "symbols": symbols, "reachable": prof,
                "in_sample_pick": str(is_pick.value),
                "cells": [{"value": str(c.value), "params": c.params,
                           "is": c.is_metrics, "oos": c.oos_metrics} for c in cells],
                "marginal_cohorts": marginals, "verdict": verdict, "shippable": ships,
            }, fh, indent=1, default=str)
        print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
