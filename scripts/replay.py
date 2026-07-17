"""Replay closed trades against session bars; what-if exit rules (PHASE-001).

Usage:
  python -m scripts.replay                 # fidelity baseline + breakeven + VWAP what-ifs
  python -m scripts.replay --be 0.75       # add a custom breakeven trigger (in R)
  python -m scripts.replay --vwap-skip 1.0 # add a custom VWAP-skip threshold (in %)

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
    extra_skip = [float(a) for a in argv[argv.index("--vwap-skip") + 1:]
                  if _is_float(a)] if "--vwap-skip" in argv else []

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
    print()
    _print_vwap_bands(trades, all_bars)
    print()
    _print_vwap_skip(trades, all_bars, baseline["abs_error"], extra_skip)
    print("=" * 72)
    return 0


def _print_vwap_bands(trades: list[dict], all_bars: dict) -> None:
    """★ open-fade lever: does entry stretch above the session VWAP predict fades?"""
    rows = replay.vwap_distance_rows(trades, all_bars)
    bands = replay.bucket_vwap_distance(rows)
    print(f"By entry distance from session VWAP ({len(rows)} trades with bars):")
    print("  tests the open-fade hypothesis — fills stretched above the session")
    print("  volume-weighted price should fade back; near/below VWAP should hold")
    print(f"  {'band':>16}{'trades':>8}{'win%':>7}{'total$':>11}{'exp$':>9}")
    for b in bands:
        print(f"  {b['label']:>16}{b['n']:>8}{b['win_pct']:>7.1f}"
              f"{b['total']:>11.2f}{b['exp']:>9.2f}")


def _print_vwap_skip(
    trades: list[dict], all_bars: dict, noise_budget: float, extra: list[float]
) -> None:
    """★★ pre-ship validation for the PROPOSED VWAP entry-quality gate (todo.md).

    Simulates skipping entries filled more than PCT above their session VWAP.
    The delta is EXACT recorded P&L (an entry skip, no fill simulation); the
    noise budget is shown only as a materiality bar. NOT an engine change —
    this is the replay evidence the gate needs before human sign-off.
    """
    rows = replay.vwap_distance_rows(trades, all_bars)
    thresholds = [0.25, 0.5, *extra]
    print(f"VWAP-skip what-if — skip fills > PCT above session VWAP "
          f"({len(rows)} gate-evaluable trades):")
    print(f"  noise budget (baseline sum|error|) = ${noise_budget:,.2f}; "
          f"a |delta| clearing it comfortably = real signal")
    print(f"  {'skip >':>8}{'kept':>6}{'skipped':>8}{'kept$':>10}"
          f"{'skip$':>10}{'delta$':>10}{'kept w%':>9}{'skip w%':>9}")
    for thr in thresholds:
        r = replay.vwap_skip_whatif(rows, thr)
        clears = "  <-- clears budget" if abs(r["delta"]) > noise_budget else ""
        print(f"  {thr:>+7.2f}%{r['n_kept']:>6}{r['n_skipped']:>8}"
              f"{r['kept_pl']:>10.2f}{r['skipped_pl']:>10.2f}"
              f"{r['delta']:>+10.2f}{r['kept_win_pct']:>9.1f}"
              f"{r['skipped_win_pct']:>9.1f}{clears}")


def _is_float(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
