"""Exit-geometry scorecard + what-if grid over the POST-GATE book (IMP-028).

Usage:
  python -m scripts.exit_geometry                 # baseline + default what-if grid
  python -m scripts.exit_geometry --since 2026-07-25
  python -m scripts.exit_geometry --trail 1.0 0.5 # add custom trail distances (R)

Only post-IMP-021/022 trades are loaded by default: the pre-2026-07-25 book is
populated by breakout entries the bot can no longer take, so fitting exit
geometry to it would be fitting to a dead strategy (2026-08-01 weekly review).

Read the caveats in bot/exit_sim.py before acting on the output. The baseline
row's |error| is the simulation noise budget — a what-if delta has to clear it
to be signal rather than bar-resolution artefact.
"""

from __future__ import annotations

import argparse
import sys

from bot import db
from bot.data import get_bars_for_symbols
from bot.exit_sim import ExitGeometry, giveback_rows, replay_geometry

POST_GATE_START = "2026-07-25"   # IMP-021 + IMP-022 shipped after this close
BARS_PER_SYMBOL = 6000           # ~390 RTH 1-min bars/day -> ~15 sessions


def load_trades(since: str) -> list[dict]:
    return db.query(
        "SELECT trade_id, symbol, qty, entry_price, entry_time, stop_price, "
        "take_profit_price, exit_price, exit_time, realized_pl, exit_reason "
        "FROM trades WHERE status = 'CLOSED' AND entry_time >= ? "
        "ORDER BY entry_time",
        since,
    )


def bars_by_trade(trades: list[dict]) -> dict:
    """trade_id -> the 1-min bar window from entry to exit, same session."""
    symbols = sorted({t["symbol"] for t in trades})
    all_bars = get_bars_for_symbols(symbols, n_bars=BARS_PER_SYMBOL,
                                    timeframe="1Min")
    out: dict = {}
    for t in trades:
        df = all_bars.get(t["symbol"])
        if df is None or df.empty:
            continue
        day = t["entry_time"].strftime("%Y-%m-%d")
        window = df[df.index.strftime("%Y-%m-%d") == day]
        window = window[
            (window.index.strftime("%H:%M") >= t["entry_time"].strftime("%H:%M"))
            & (window.index.strftime("%H:%M") <= t["exit_time"].strftime("%H:%M"))
        ]
        if not window.empty:
            out[t["trade_id"]] = window
    return out


def _mislabelled(result: dict) -> int:
    """Replayed exits whose REASON disagrees with what really happened.

    The sharpest fidelity signal: a model with no ratchet cannot report a STOP
    for a trade taken out by the moved stop, because the original stop was never
    touched. (A residual few are IEX bar sparsity — see bot/exit_sim.py.)
    """
    return sum(1 for r in result["rows"] if r["sim_reason"] != r["actual_reason"])


def _print_run(result: dict, budget: float | None) -> None:
    delta = result["delta"]
    verdict = ""
    if budget is not None:
        verdict = "  ✅ clears noise" if abs(delta) > budget else "  ⚠️ within noise"
    captured = result["captured_pct"]
    print(f"  {result['geometry']:44s} sim ${result['sim_pl']:8.2f}  "
          f"delta ${delta:+8.2f}  wins {result['sim_wins']:2d}/{result['trades']:2d}  "
          f"captured {captured if captured is not None else float('nan'):5.1f}%"
          f"{verdict}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default=POST_GATE_START,
                        help=f"earliest entry date (default {POST_GATE_START})")
    parser.add_argument("--trail", nargs="*", type=float, default=[],
                        help="extra TRAIL_DISTANCE_R values to test")
    args = parser.parse_args(argv)

    trades = load_trades(args.since)
    if not trades:
        print(f"No closed trades since {args.since}.")
        return 0
    windows = bars_by_trade(trades)

    live = ExitGeometry.from_config()
    baseline = replay_geometry(trades, windows, live)
    budget = baseline["abs_error"]

    print("=" * 78)
    print(f"USTradeWisBot — exit geometry, post-gate book since {args.since}")
    print("=" * 78)
    print(f"Trades replayed : {baseline['trades']} (actual net "
          f"${baseline['actual_pl']:.2f})")
    print(f"Peak open profit: ${baseline['peak_mfe_usd']:.2f} across all trades")
    print(f"Noise budget    : ${budget:.2f} (sum |sim - actual| under live geometry)")
    print(f"Ratchet armed   : break-even {baseline['armed_breakeven']}, "
          f"trail-above-entry {baseline['armed_trail']}")

    print("\nFidelity baseline (the geometry the bot is running):")
    _print_run(baseline, None)
    print(f"    exits mislabelled vs recorded: {_mislabelled(baseline)}"
          f"/{baseline['trades']}")

    static = ExitGeometry(live.breakeven_trigger_r, live.trail_trigger_r,
                          live.trail_distance_r, live.ratchet_min_pct,
                          trailing_enabled=False)
    static_run = replay_geometry(trades, windows, static)
    print("\nStatic bracket — what bot/replay.py models (no ratchet):")
    _print_run(static_run, None)
    print(f"    exits mislabelled vs recorded: {_mislabelled(static_run)}"
          f"/{static_run['trades']}  (all real STOPs reported as EOD_FLATTEN)")
    print("    its small $ error is an artefact: the EOD fallback IS the recorded"
          "\n    exit price, so ratchet-caused exits fall through to the answer.")

    print("\nGive-back cohort (peaked >= +0.5R, banked <= $1):")
    gb = giveback_rows(baseline["rows"])
    for r in sorted(gb, key=lambda x: -x["mfe_usd"]):
        print(f"  {r['day']} {r['symbol']:5s} #{r['trade_id']:<4d} "
              f"peak {r['mfe_r']:+.2f}R (${r['mfe_usd']:6.2f})  "
              f"banked ${r['actual_pl']:+6.2f}  {r['actual_reason']}")
    if gb:
        peak = sum(r["mfe_usd"] for r in gb)
        banked = sum(r["actual_pl"] for r in gb)
        print(f"  {'TOTAL':>10s} n={len(gb)}  peak ${peak:.2f}  banked ${banked:+.2f}"
              f"  capture {banked / peak * 100.0:.1f}%")
    else:
        print("  (none)")

    print("\nWhat-if grid (trail distance below the running high, in R):")
    for dist in list(args.trail) or [0.75, 0.5, 0.35, 0.25]:
        for trigger in (live.trail_trigger_r, 0.5):
            if trigger < dist:
                continue    # trail would sit below entry at the trigger: pointless
            cand = ExitGeometry(
                breakeven_trigger_r=live.breakeven_trigger_r,
                trail_trigger_r=trigger,
                trail_distance_r=dist,
                ratchet_min_pct=live.ratchet_min_pct,
            )
            _print_run(replay_geometry(trades, windows, cand), budget)

    print("\nRead: 'captured %' is realized P&L as a share of total peak open "
          "profit.\nA delta inside the noise budget is bar-resolution artefact, "
          "not evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
