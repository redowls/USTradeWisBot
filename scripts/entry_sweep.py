"""CLI: sweep ONE entry parameter around the live gate and judge it head-to-head.

  python -m scripts.entry_sweep --dim cutoff --values 11:30,12:00,13:00,14:00,15:00 \
      --start 2025-09-26 --end 2026-09-25 --cache /tmp/uswisbot_bars.pkl

  python -m scripts.entry_sweep --dim min_relvol --values 1.0,1.3,1.6,2.0
  python -m scripts.entry_sweep --dim k --values 3,6,9 --out /tmp/sweep_k.json

Complements ``scripts.entry_lab``, which searches the whole grid and answers
"what is the best ORB?". This answers the question a one-change-per-run
discipline can act on: **the gate that is live right now, with exactly one
parameter moved — better or worse?** The base cell is read out of ``bot.config``
by ``entry_sweep.live_orb_params``, so it always is the running bot, and each
candidate must clear the IMP-059 walk-forward gate *with the incumbent supplied
as the baseline it has to beat*.

Prints, per swept value: in-sample and held-out doctrine metrics, the held-out
expectancy delta vs the live value, the ADDED / DROPPED marginal cohorts against
the live cell, whether the held-out gradient is monotone, and the verdict. Reads
market data only; touches no database table, no config file and no live path.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone

from bot import config, db, entry_lab, entry_sweep
from scripts.entry_lab import DEFAULT_EQUITY, DEFAULT_SLIPPAGE_PCT, _arg, load_or_fetch

#: Values are read off the command line as strings; these dimensions are numeric
#: in ``rule_orb``'s vocabulary and must be cast or the rule silently compares a
#: string to a float. ``cutoff`` stays a string ("11:30"), ``above_vwap``/``mkt``
#: are parsed as booleans.
CASTS = {"k": int, "min_relvol": float, "buffer_pct": float}
BOOLS = ("above_vwap", "mkt")


def parse_values(dim: str, raw: str) -> list:
    vals = [v.strip() for v in raw.split(",") if v.strip()]
    if dim in BOOLS:
        return [v.lower() in ("1", "true", "yes", "on") for v in vals]
    cast = CASTS.get(dim)
    return [cast(v) for v in vals] if cast else vals


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    dim = _arg(argv, "--dim", "cutoff")
    end = date.fromisoformat(_arg(argv, "--end", str(date.today() - timedelta(days=1))))
    start = date.fromisoformat(_arg(argv, "--start", str(end - timedelta(days=365))))
    slippage = float(_arg(argv, "--slippage", str(DEFAULT_SLIPPAGE_PCT)))
    equity = float(_arg(argv, "--equity", str(DEFAULT_EQUITY)))
    feed = _arg(argv, "--feed", "sip")
    cache = _arg(argv, "--cache", "")
    out = _arg(argv, "--out", "")
    syms_arg = _arg(argv, "--symbols", "")

    base = entry_sweep.live_orb_params()
    if dim not in base:
        print(f"--dim {dim!r} is not an ORB parameter; expected one of {sorted(base)}")
        return 2
    values = parse_values(dim, _arg(argv, "--values", str(base[dim])))
    if not values:
        print("--values is empty")
        return 2

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
    print(f"Sweeping {dim} over {values}   — every other parameter pinned to live")
    print(f"Exit geometry: BE {config.BREAKEVEN_TRIGGER_R}R, trail "
          f"{config.TRAIL_TRIGGER_R}R/{config.TRAIL_DISTANCE_R}R "
          f"(trailing={config.TRAILING_STOP_ENABLED}), RR {config.RR_RATIO}, "
          f"stop max({config.ATR_STOP_MULT}xATR, {config.MIN_STOP_PCT}%)")
    print(f"Sessions: {len(sessions)}  in-sample {is_days[0]}..{is_days[-1]} ({len(is_days)})  "
          f"held-out {oos_days[0]}..{oos_days[-1]} ({len(oos_days)})", flush=True)

    cells = entry_sweep.sweep_dimension(
        "orb", entry_lab.rule_orb, base, dim, values, feats,
        is_days, oos_days, equity, slippage, mkt)
    verdict = entry_sweep.sweep_verdict(cells, base[dim])
    inc = entry_sweep.incumbent_cell(cells, base[dim])

    print("\n" + entry_lab.metrics_header())
    for c in cells:
        tag = " *LIVE*" if c is inc else ""
        print(entry_lab.format_metrics_row(f"{dim}={c.value} / in-sample{tag}", c.is_metrics))
        print(entry_lab.format_metrics_row(f"{dim}={c.value} / held-out{tag}", c.oos_metrics))

    marginals: dict = {}
    if inc is not None:
        print(f"\n--- held-out marginal cohorts vs LIVE {dim}={inc.value} ---")
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

    print(f"\nheld-out expectancy gradient over {dim}: {verdict['monotone'].upper()}")
    for row in verdict["cells"]:
        mark = "LIVE " if row["incumbent"] else ("PASS " if row["clears"] else "fail ")
        why = "" if row["incumbent"] or row["clears"] else "  — " + "; ".join(row["why"])
        print(f"  {mark}{dim}={row['value']:<8} held-out {row['oos_exp_r']:+.4f}R "
              f"(Δ {row['delta_exp_r']:+.4f}R){why}")
    print(f"\nVERDICT: {verdict['verdict'].upper()} — {verdict['reason']}")

    if out:
        with open(out, "w") as fh:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dim": dim, "values": [str(v) for v in values], "base": base,
                "window": f"{sessions[0]}..{sessions[-1]}", "sessions": len(sessions),
                "in_sample": [str(is_days[0]), str(is_days[-1]), len(is_days)],
                "held_out": [str(oos_days[0]), str(oos_days[-1]), len(oos_days)],
                "slippage_pct": slippage, "equity": equity, "feed": feed,
                "symbols": symbols,
                "cells": [{"value": str(c.value), "params": c.params,
                           "is": c.is_metrics, "oos": c.oos_metrics} for c in cells],
                "marginal_cohorts": marginals, "verdict": verdict,
            }, fh, indent=1, default=str)
        print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
