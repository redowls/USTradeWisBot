"""Replay closed trades against session bars; what-if exit rules (PHASE-001).

Usage:
  python -m scripts.replay                 # fidelity baseline + breakeven what-ifs
  python -m scripts.replay --be 0.75       # add a custom breakeven trigger (in R)

Read the caveats in bot/replay.py before acting on the output: the baseline
row's |error| is the simulation noise budget — a what-if delta has to clear it
comfortably before it justifies a strategy phase.
"""

from __future__ import annotations

import sys

from bot import replay


def _print_run(label: str, result: dict, baseline_abs_error: float | None = None) -> None:
    note = ""
    if baseline_abs_error is not None and result["delta"] != 0:
        note = "  <-- compare |delta| to noise budget"
    print(f"{label:24} sim P&L ${result['sim_pl']:>+10,.2f}   "
          f"delta vs actual ${result['delta']:>+9,.2f}   "
          f"sum|error| ${result['abs_error']:>9,.2f}{note}")


def main(argv: list[str]) -> int:
    extra_be = [float(a) for a in argv[argv.index("--be") + 1:] if _is_float(a)] \
        if "--be" in argv else []

    trades = replay.load_closed_trades()
    if not trades:
        print("No closed trades to replay.")
        return 0
    all_bars = replay.load_all_bars(trades)

    baseline = replay.replay_trades(trades, all_bars)
    print("=" * 72)
    print(f"USTradeWisBot — trade replay ({baseline['trades']} closed trades "
          f"with bars, actual P&L ${baseline['actual_pl']:+,.2f})")
    print("=" * 72)
    print(f"MFE: reached +0.5R: {baseline['reached_half_r']}   "
          f"reached +1R: {baseline['reached_one_r']}   "
          f"losers that saw +1R first: {baseline['losers_reached_one_r']}")
    print()
    _print_run("baseline (current)", baseline)
    print(f"{'':24} (noise budget: baseline sum|error| above — bar-level "
          f"replay vs intrabar fills)")
    print()
    for be in [0.5, 1.0, *extra_be]:
        result = replay.replay_trades(trades, all_bars, breakeven_at_r=be)
        _print_run(f"breakeven at +{be}R", result, baseline["abs_error"])
    print("=" * 72)
    return 0


def _is_float(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
