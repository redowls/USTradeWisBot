"""CLI: walk-forward gate for the ORB VOLUME-CONFIRMATION definition (IMP-065).

  python -m scripts.volume_lab --start 2025-09-29 --end 2026-09-28 --cache /tmp/bars.pkl
  python -m scripts.volume_lab --profile-only        # just the U-shape evidence table
  python -m scripts.volume_lab --out /tmp/vol.json

Sweeps ONE dimension — the volume leg of the live ORB entry — across three
definitions x several thresholds, with every other ORB parameter pinned to the
running configuration. The live ``('live', ORB_MIN_REL_VOL)`` cell is the
incumbent every candidate must beat on held-out data, via
``entry_sweep.sweep_verdict`` -> ``entry_lab.gate``.

Reads bars and ``bot.config``; touches no DB table, no live path and no file
other than the optional ``--out`` JSON. See ``bot/volume_lab.py`` for why.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta

import pandas as pd

from bot import config, db, entry_lab, entry_sweep, volume_lab
from scripts.entry_lab import (
    DEFAULT_EQUITY, DEFAULT_SLIPPAGE_PCT, load_or_fetch, resolve_feed,
)

#: Thresholds swept per definition. Chosen IN-SAMPLE by the gate, never here.
#: 1.3 appears in all three so the shipped number is always one of the cells and
#: a definition change is never confounded with a threshold change.
SPEC_GRID: list[tuple] = [
    ("live", 1.3),          # <- incumbent, the running bot
    ("tod", 1.0),
    ("tod", 1.3),
    ("tod", 1.6),
    ("tod", 2.0),
    ("session", 1.0),
    ("session", 1.3),
    ("session", 1.6),
    ("session", 2.0),
]


def _arg(argv: list[str], flag: str, default: str) -> str:
    return argv[argv.index(flag) + 1] if flag in argv else default


def _profile_table(feats: dict[str, pd.DataFrame], spec, max_bar_idx: int) -> pd.DataFrame:
    """Clearance profile pooled over every symbol (one row per ``bar_idx``)."""
    parts = [volume_lab.clearance_profile(f, spec, max_bar_idx) for f in feats.values()]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame(columns=["median_ratio", "pct_clearing", "n"])
    wide = pd.concat(parts)
    g = wide.groupby(level=0)
    return pd.DataFrame({
        # n-weighted, so a symbol with fewer bars does not count the same
        "median_ratio": g["median_ratio"].median().round(3),
        "pct_clearing": ((wide["pct_clearing"] * wide["n"]).groupby(level=0).sum()
                         / g["n"].sum()).round(2),
        "n": g["n"].sum(),
    })


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    end = date.fromisoformat(_arg(argv, "--end", str(date.today() - timedelta(days=1))))
    start = date.fromisoformat(_arg(argv, "--start", str(end - timedelta(days=365))))
    slippage = float(_arg(argv, "--slippage", str(DEFAULT_SLIPPAGE_PCT)))
    equity = float(_arg(argv, "--equity", str(DEFAULT_EQUITY)))
    feed, feed_warning = resolve_feed(argv)
    cache = _arg(argv, "--cache", "")
    out_path = _arg(argv, "--out", "")
    max_bar_idx = int(_arg(argv, "--max-bar-idx", "26"))
    profile_only = "--profile-only" in argv
    if feed_warning:
        print(f"⚠️  {feed_warning}")

    filt = (config.ORB_MARKET_FILTER_SYMBOL or "SPY").strip()
    symbols = sorted({r["symbol"] for r in db.get_active_watchlist()} | {filt})
    print(f"symbols ({len(symbols)}): {','.join(symbols)}")
    print(f"window {start} .. {end}  feed={feed}  slippage={slippage}%  equity=${equity:,.0f}")

    bars = load_or_fetch(symbols, start, end, feed, cache)
    feats_raw = {s: entry_lab.precompute_features(df) for s, df in bars.items()
                 if df is not None and not df.empty}
    feats = volume_lab.add_volume_features_all(feats_raw, k=int(config.ORB_RANGE_BARS))
    mkt = volume_lab.entry_lab.market_ok(feats[filt]) if filt in feats else None
    trade_feats = {s: f for s, f in feats.items() if s != filt}

    base = entry_sweep.live_orb_params()
    incumbent = volume_lab.live_volume_spec()
    print(f"base ORB params (live): {base}")
    print(f"incumbent volume spec:  {incumbent}")

    # --- Evidence: the U-shape, per definition ------------------------------
    print(f"\n=== clearance profile by bar_idx (0=09:30, {int(config.ORB_RANGE_BARS)}"
          f"=first legal ORB bar, 24=11:30 cutoff) ===")
    profiles: dict[str, dict] = {}
    for spec in (("live", 1.3), ("tod", 1.3), ("session", 1.3)):
        tab = _profile_table(trade_feats, spec, max_bar_idx)
        profiles[str(spec)] = json.loads(tab.to_json(orient="index"))
        print(f"\n-- {spec} --")
        print(tab.to_string())
    if profile_only:
        return 0

    # --- Throughput diagnostic (never a ship reason) ------------------------
    adm = volume_lab.candidate_admission(trade_feats, base, SPEC_GRID, mkt)
    print("\n=== candidate admission (diagnostic only) ===")
    print(adm.to_string(index=False))

    # --- The gate -----------------------------------------------------------
    sessions = sorted({ts.date() for f in trade_feats.values() for ts in f.index})
    is_days, oos_days = entry_lab.split_sessions(sessions)
    print(f"\nsessions={len(sessions)}  in-sample={len(is_days)} "
          f"({is_days[0]}..{is_days[-1]})  held-out={len(oos_days)} "
          f"({oos_days[0]}..{oos_days[-1]})")

    cells = entry_sweep.sweep_dimension(
        "orb_volume", volume_lab.rule_orb_volume, base, "volume_spec", SPEC_GRID,
        trade_feats, is_days, oos_days, equity, slippage, mkt,
    )
    print("\n=== in-sample ===")
    print(entry_lab.metrics_header())
    for c in cells:
        print(entry_lab.format_metrics_row(str(c.value), c.is_metrics))
    print("\n=== held-out ===")
    print(entry_lab.metrics_header())
    for c in cells:
        print(entry_lab.format_metrics_row(str(c.value), c.oos_metrics))

    verdict = entry_sweep.sweep_verdict(cells, incumbent)
    print(f"\nVERDICT: {verdict['verdict']}")
    if verdict.get("reason"):
        print(f"  reason: {verdict['reason']}")
    for row in verdict.get("cells", []):
        tag = " (incumbent)" if row["incumbent"] else ""
        mark = "CLEARS" if row["clears"] else "refused"
        print(f"  {row['value']:<20}{tag:<13} {mark}  expR {row['oos_exp_r']:+.4f} "
              f"(delta {row['delta_exp_r']:+.4f})"
              + ("" if row["clears"] or row["incumbent"] else f"  <- {'; '.join(row['why'])}"))

    # Monotonicity WITHIN each definition only — a run across definitions has no axis.
    mono: dict[str, str] = {}
    for name in ("tod", "session"):
        subset = [c for c in cells if c.value[0] == name]
        mono[name] = entry_sweep.monotone_direction(subset)
        print(f"  monotone({name} thresholds, held-out expR): {mono[name]}")

    # --- Marginal cohort vs the incumbent -----------------------------------
    inc_cell = entry_sweep.incumbent_cell(cells, incumbent)
    cohorts: dict[str, dict] = {}
    if inc_cell is not None:
        print("\n=== marginal cohort vs the live gate (held-out) ===")
        for c in cells:
            if c is inc_cell:
                continue
            mc = entry_sweep.marginal_cohort(c, inc_cell)
            a, d = mc["added_metrics"], mc["dropped_metrics"]
            cohorts[str(c.value)] = {
                "added": {"n": a["n"], "net": a["net"], "exp_r": a["exp_r"]},
                "dropped": {"n": d["n"], "net": d["net"], "exp_r": d["exp_r"]},
                "net_delta": mc["net_delta"],
            }
            print(f"  {str(c.value):<20} added {a['n']:>4} @ {a['exp_r']:+.3f}R "
                  f"= ${a['net']:+9.2f} | dropped {d['n']:>4} @ {d['exp_r']:+.3f}R "
                  f"= ${d['net']:+9.2f} | net delta ${mc['net_delta']:+.2f}")

    if out_path:
        with open(out_path, "w") as fh:
            json.dump({
                "window": {"start": str(start), "end": str(end)},
                "base_params": {k: str(v) for k, v in base.items()},
                "incumbent": str(incumbent),
                "sessions": len(sessions), "is": len(is_days), "oos": len(oos_days),
                "profiles": profiles,
                "admission": json.loads(adm.to_json(orient="records")),
                "cells": [{"spec": str(c.value), "is": c.is_metrics, "oos": c.oos_metrics}
                          for c in cells],
                "verdict": {k: v for k, v in verdict.items() if k != "cells"},
                "verdict_cells": verdict.get("cells", []),
                "monotone": mono,
                "cohorts": cohorts,
            }, fh, indent=2, default=str)
        print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
