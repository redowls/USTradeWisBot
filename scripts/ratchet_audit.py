"""Decompose the STOP bucket and price what the ratchet actually DID (IMP-041).

Usage:
  python -m scripts.ratchet_audit                      # post-gate book, IMP-040 split
  python -m scripts.ratchet_audit --since 2026-08-01
  python -m scripts.ratchet_audit --split 2026-08-25   # era boundary to compare
  python -m scripts.ratchet_audit --detail             # one line per trade

WHY THIS EXISTS
---------------
Every daily and weekly review reads the exit mix, and the exit mix is
conflated. ``trades.exit_reason`` has exactly one string for a stop-out —
``'STOP'`` — and it covers two outcomes that are opposites:

  * a **plan stop**: the original 1R stop was hit, the trade lost a full R;
  * a **ratchet stop**: the break-even/trail stop the bot had already moved UP
    was hit, so the trade ended at or above break-even.

The post-gate book on 2026-08-25 reads ``STOP n=30, net -$471.16``, and that
single number has been quoted into strategy decisions for weeks. It merges MU
#273 (a full -1R, -$34.78) with TSM #287 (a break-even scratch, -$0.54) and
META #288 (a trail stop that BANKED +$1.21). ``trades.stop_price`` cannot
settle it either: it stays pinned to the ORIGINAL plan stop by design, because
that is the anchor that defines 1R (IMP-013). Nothing in the schema records
where the stop actually WAS when it fired.

This matters right now because **IMP-040's verdict depends on it.** IMP-040
(2026-08-24) slid the whole ratchet 0.5R -> 0.25R and pre-registered its pass
test as a shift in the exit MIX — "more STOP exits, fewer EOD_FLATTENs, more
STOP RAISED lines per trade, higher win rate with smaller average wins" — to be
judged over ~2 weeks. That test cannot be run against a bucket that cannot tell
a scratch from a disaster. Worse, the only place the arming events are recorded
is ``STOP RAISED`` lines in /var/log/ustradewisbot/bot.log, which rotates daily
and keeps 14 days, so the evidence expires at roughly the moment the verdict is
due.

So this script reconstructs, per trade, what the schema failed to record, and
prices the ratchet against the one counterfactual that answers the question:
**what would this trade have made with no ratchet at all?**

WHAT IT MEASURES
----------------
For every closed trade it replays the LIVE ``exits.compute_trailed_stop`` (the
real function, imported — not a copy, so this can never drift from the shipped
geometry) bar by bar across the 1-min window from entry to the 15:55 flatten,
and reports:

  * ``mfe_r`` / ``mae_r`` — excursions in R, the distribution the ratchet's
    trigger has to sit inside to do anything at all;
  * ``armed`` — whether the ratchet ever lifted the stop above the plan stop;
  * ``exit_class`` — PLAN_STOP / RATCHET_STOP / TAKE_PROFIT / EOD_FLATTEN;
  * ``noratchet_pl`` — the same trade held with ONLY its original plan stop,
    exiting at the plan stop if a bar's low reached it and at the 15:55 close
    otherwise;
  * ``ratchet_delta`` = ``realized_pl - noratchet_pl``, i.e. the dollars the
    ratchet earned (positive) or cost (negative) on that trade.

``ratchet_delta`` is priced for RATCHET_STOP exits and for those ONLY, because
those are the only trades whose outcome the ratchet actually decided. A trade
taken out by its plan stop, filled at its take-profit limit, or carried to the
15:55 flatten ends at the same price whether or not the stop was ratcheting
behind it, so its delta is zero by construction. Pricing the whole book instead
manufactures noise: an EOD_FLATTEN's counterfactual prices off the last 1-min
bar CLOSE while the real flatten fills at market a few seconds later, which
alone scattered +/-$1 of fake delta across 47 trades on the first cut of this
script and moved the headline by $19.

Summed over the book, ``ratchet_delta`` is the ratchet's realised P&L. It is
the number IMP-040 is owed and the number no existing tool produced: on
2026-08-25, IMP-040's first live session, it was **-$17.72 across two trades**
(META -$15.99, TSM -$1.73) against a day that netted -$13.75 — i.e. the day was
+$3.97 with the ratchet switched off. That is one session and four trades and
settles nothing on its own, which is exactly why the instrument has to keep
running until the sample is real.

FIDELITY — READ BEFORE ACTING ON THE OUTPUT
-------------------------------------------
This is a RECONSTRUCTION, not a recording, and it is optimistic in known ways:

  * **Classification is broker ground truth; arming is a model.** ``exit_class``
    is decided by the recorded fill price against the plan stop, which comes
    from Alpaca. ``armed`` comes from the replay. When the two disagree the
    disagreement is counted and printed as ``fidelity`` rather than hidden —
    a rising count means the replay is drifting from the live bot.
  * **The replay is ANACHRONISTIC before 2026-08-25.** ``compute_trailed_stop``
    reads the CURRENT module-level constants, so replaying a 2026-08-01 trade
    asks "what would today's 0.25R ratchet have done", not "what did the 0.5R
    ratchet do at the time". Everything replay-derived (``armed``, ``raises``)
    is therefore reported under one heading that says so, and is deliberately
    kept OUT of the era split — every number in that split is fill-derived or
    geometry-independent, so the two eras are compared on what really happened.
    IMP-040's criterion (b), "more STOP RAISED lines per trade", has no
    historical counterpart here and must be read forward off the live log.
  * **SIP bars here, IEX ticks live.** The live bot polls a last trade every
    POLL_INTERVAL_SEC and reads peaks off IEX; this reads consolidated SIP
    1-min bars. SIP prints highs IEX never saw, so the replay can arm trades
    the live bot did not.
  * **Bar resolution hides intrabar sequencing.** A bar whose low reaches the
    stop is treated as a stop-out at exactly the stop price. Real stop-market
    fills slip: TSM #287's break-even stop sat at 416.02 and filled 415.908.
    The counterfactual therefore flatters the no-ratchet leg slightly.
  * **The counterfactual is "ratchet off", NOT "the previous geometry".** It
    does not answer "what would 0.5R have done" — ``scripts/exit_geometry.py``
    is the tool for that, and it remains the one to use for sweeps.

Read the caveats in bot/exit_sim.py too; they apply here unchanged.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from bot import config, db, exits
from bot.data import get_bars_for_symbols

POST_GATE_START = "2026-07-25"   # IMP-021 + IMP-022 shipped after this close
IMP040_START = "2026-08-25"      # first session on the 0.25R ratchet
BARS_PER_SYMBOL = 10000          # ~390 RTH 1-min bars/day -> ~25 sessions

# A stop-out fills at or just below the stop that fired. A fill this far ABOVE
# the plan stop cannot have come from the plan stop, so the stop had moved.
# 0.1% of entry is the same scale as STOP_RATCHET_MIN_PCT (0.1), i.e. the
# smallest step the ratchet is allowed to take in the first place.
RATCHET_FILL_TOLERANCE_PCT = 0.1

PLAN_STOP = "PLAN_STOP"
RATCHET_STOP = "RATCHET_STOP"


def load_trades(since: str) -> list[dict]:
    return db.query(
        "SELECT trade_id, symbol, qty, entry_price, entry_time, stop_price, "
        "take_profit_price, exit_price, exit_time, realized_pl, exit_reason "
        "FROM trades WHERE status = 'CLOSED' AND exit_time IS NOT NULL "
        "AND entry_time >= ? ORDER BY entry_time",
        since,
    )


def bars_by_trade(trades: list[dict], n_bars: int = BARS_PER_SYMBOL) -> dict:
    """trade_id -> the 1-min window from entry through the 15:55 flatten.

    The window runs past the trade's ACTUAL exit out to the flatten, because
    the no-ratchet counterfactual has to be able to hold longer than the live
    trade did — truncating at the recorded exit is the bug IMP-030 found in
    ``exit_geometry.bars_by_trade``, where a candidate that would have held on
    had no bars to hold through and reported the live result straight back as
    its own counterfactual.
    """
    symbols = sorted({t["symbol"] for t in trades})
    all_bars = get_bars_for_symbols(symbols, n_bars=n_bars, timeframe="1Min")
    out: dict = {}
    for t in trades:
        df = all_bars.get(t["symbol"])
        if df is None or df.empty:
            continue
        entry = t["entry_time"]
        window = df[df.index.strftime("%Y-%m-%d") == entry.strftime("%Y-%m-%d")]
        window = window[
            (window.index.strftime("%H:%M") >= entry.strftime("%H:%M"))
            & (window.index.strftime("%H:%M") <= config.FLATTEN_ET)
        ]
        if not window.empty:
            out[t["trade_id"]] = window
    return out


def replay_stop_path(entry_price: float, plan_stop: float, bars,
                     until=None) -> dict:
    """Walk the live ratchet over ``bars`` and report what it would have done.

    Feeds ``compute_trailed_stop`` the bar CLOSE as the live price and the
    running session high as ``high_price``, mirroring how the engine calls it
    (a polled last trade plus ``peak_high_since``). ``until`` stops the walk at
    the trade's real exit time so the arming statistic describes the trade that
    actually happened, not the rest of the session it never saw.
    """
    risk = entry_price - plan_stop
    path = {"armed": False, "armed_at": None, "armed_stop": None,
            "final_stop": plan_stop, "mfe_r": None, "mae_r": None, "raises": 0}
    if risk <= 0 or bars is None or len(bars) == 0:
        return path

    current_stop = plan_stop
    running_high = None
    high_so_far = float("-inf")
    low_so_far = float("inf")
    for ts, bar in bars.iterrows():
        if until is not None and ts.strftime("%H:%M") > until.strftime("%H:%M"):
            break
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        high_so_far = max(high_so_far, high)
        low_so_far = min(low_so_far, low)
        running_high = high if running_high is None else max(running_high, high)
        moved = exits.compute_trailed_stop(
            entry_price, plan_stop, current_stop, live_price=close,
            high_price=running_high,
        )
        if moved is not None and moved > current_stop:
            current_stop = moved
            path["raises"] += 1
            if not path["armed"]:
                path["armed"] = True
                path["armed_at"] = ts
                path["armed_stop"] = moved

    path["final_stop"] = current_stop
    if high_so_far > float("-inf"):
        path["mfe_r"] = (high_so_far - entry_price) / risk
        path["mae_r"] = (low_so_far - entry_price) / risk
    return path


def noratchet_outcome(entry_price: float, plan_stop: float, qty: float,
                      bars) -> tuple[float, str] | None:
    """P&L and exit reason for the same trade with the ratchet switched OFF.

    Only the original plan stop protects it: the first bar whose LOW reaches
    that stop exits there, otherwise it rides to the 15:55 close. The
    take-profit leg is deliberately NOT modelled — it is untouched by every
    ratchet change, so including it would add noise to a difference that is
    supposed to isolate the ratchet alone.
    """
    if bars is None or len(bars) == 0 or entry_price <= plan_stop:
        return None
    for _, bar in bars.iterrows():
        if float(bar["low"]) <= plan_stop:
            return round((plan_stop - entry_price) * qty, 4), PLAN_STOP
    close = float(bars["close"].iloc[-1])
    return round((close - entry_price) * qty, 4), "EOD_FLATTEN"


def classify_exit(trade: dict) -> str:
    """PLAN_STOP / RATCHET_STOP / the recorded reason, from the broker's fill.

    Deliberately decided by the FILL, not by the replay: the fill price is
    Alpaca's, and a stop-out cannot fill materially above the stop that fired
    it. The replay's own opinion is kept separate and reported as fidelity.
    """
    reason = trade["exit_reason"]
    if reason != "STOP":
        return reason
    entry = float(trade["entry_price"])
    plan_stop = float(trade["stop_price"])
    exit_price = float(trade["exit_price"])
    tolerance = entry * RATCHET_FILL_TOLERANCE_PCT / 100.0
    return RATCHET_STOP if exit_price > plan_stop + tolerance else PLAN_STOP


def audit(trades: list[dict], bars: dict) -> list[dict]:
    rows: list[dict] = []
    for t in trades:
        window = bars.get(t["trade_id"])
        if window is None:
            continue
        entry = float(t["entry_price"])
        plan_stop = float(t["stop_price"])
        qty = float(t["qty"])
        pl = float(t["realized_pl"])
        path = replay_stop_path(entry, plan_stop, window, until=t["exit_time"])
        exit_class = classify_exit(t)
        # Only a RATCHET_STOP was decided BY the ratchet; every other exit ends
        # at the same price with the ratchet off, so its delta is zero and
        # pricing it would only add flatten-fill noise (see the module docstring).
        counterfactual = (noratchet_outcome(entry, plan_stop, qty, window)
                          if exit_class == RATCHET_STOP else None)
        row = {
            "trade_id": t["trade_id"], "symbol": t["symbol"],
            "entry_time": t["entry_time"], "qty": qty,
            "realized_pl": pl, "exit_class": exit_class,
            "mfe_r": path["mfe_r"], "mae_r": path["mae_r"],
            "armed": path["armed"], "raises": path["raises"],
            "noratchet_pl": None, "ratchet_delta": None,
            # The replay says the stop moved but the fill says it did not (or
            # the reverse). Counted, never silently corrected.
            "fidelity_gap": path["armed"] != (exit_class == RATCHET_STOP)
            if exit_class in (PLAN_STOP, RATCHET_STOP) else False,
        }
        if counterfactual is not None:
            row["noratchet_pl"] = counterfactual[0]
            row["ratchet_delta"] = round(pl - counterfactual[0], 4)
        rows.append(row)
    return rows


def exit_mix(rows: list[dict]) -> dict:
    mix: dict = defaultdict(lambda: {"n": 0, "pl": 0.0})
    for r in rows:
        mix[r["exit_class"]]["n"] += 1
        mix[r["exit_class"]]["pl"] += r["realized_pl"]
    return dict(mix)


def ratchet_ledger(rows: list[dict]) -> dict:
    priced = [r for r in rows if r["ratchet_delta"] is not None]
    helped = [r for r in priced if r["ratchet_delta"] > 0]
    hurt = [r for r in priced if r["ratchet_delta"] < 0]
    return {
        "priced": len(priced),
        "armed": sum(1 for r in rows if r["armed"]),
        "raises": sum(r["raises"] for r in rows),
        "saved": round(sum(r["ratchet_delta"] for r in helped), 2),
        "cost": round(sum(r["ratchet_delta"] for r in hurt), 2),
        "net": round(sum(r["ratchet_delta"] for r in priced), 2),
        "n_helped": len(helped), "n_hurt": len(hurt),
    }


def era_stats(rows: list[dict]) -> dict:
    """Era comparison built ONLY from fill-derived / geometry-independent facts.

    No replay output appears here on purpose. ``armed`` and ``raises`` are
    produced by running today's constants over yesterday's trades, so putting
    them in an era split would compare the current geometry against itself and
    read as a change that never happened.
    """
    n = len(rows)
    if n == 0:
        return {}
    wins = [r for r in rows if r["realized_pl"] > 0]
    flattens = sum(1 for r in rows if r["exit_class"] == "EOD_FLATTEN")
    ratchets = [r for r in rows if r["exit_class"] == RATCHET_STOP]
    plans = [r for r in rows if r["exit_class"] == PLAN_STOP]
    mfes = [r["mfe_r"] for r in rows if r["mfe_r"] is not None]
    priced = [r for r in ratchets if r["ratchet_delta"] is not None]
    return {
        "n": n,
        "net": round(sum(r["realized_pl"] for r in rows), 2),
        "win_pct": 100.0 * len(wins) / n,
        "avg_win": round(sum(r["realized_pl"] for r in wins) / len(wins), 2) if wins else 0.0,
        "flatten_pct": 100.0 * flattens / n,
        "ratchet_stop_pct": 100.0 * len(ratchets) / n,
        "plan_stop_pct": 100.0 * len(plans) / n,
        "median_mfe_r": sorted(mfes)[len(mfes) // 2] if mfes else float("nan"),
        "ratchet_net": round(sum(r["ratchet_delta"] for r in priced), 2),
    }


def _print_report(rows: list[dict], since: str, split: str, detail: bool) -> None:
    print(f"\nRATCHET AUDIT — {len(rows)} closed trades with bars, since {since}")
    print(f"  live geometry: breakeven {config.BREAKEVEN_TRIGGER_R}R / "
          f"trail {config.TRAIL_TRIGGER_R}R trigger / {config.TRAIL_DISTANCE_R}R distance")

    print("\nEXIT MIX (the STOP bucket, decomposed)")
    mix = exit_mix(rows)
    for name in (PLAN_STOP, RATCHET_STOP, "TAKE_PROFIT", "EOD_FLATTEN"):
        if name not in mix:
            continue
        m = mix[name]
        print(f"  {name:14s} n={m['n']:3d} ({100.0 * m['n'] / len(rows):5.1f}%)  "
              f"net ${m['pl']:9.2f}  avg ${m['pl'] / m['n']:8.2f}")
    for name, m in mix.items():
        if name not in (PLAN_STOP, RATCHET_STOP, "TAKE_PROFIT", "EOD_FLATTEN"):
            print(f"  {name:14s} n={m['n']:3d} net ${m['pl']:9.2f}")

    ledger = ratchet_ledger(rows)
    print("\nRATCHET LEDGER — RATCHET_STOP exits vs the same trade, ratchet OFF")
    print(f"  helped  n={ledger['n_helped']:3d}  ${ledger['saved']:+9.2f}")
    print(f"  hurt    n={ledger['n_hurt']:3d}  ${ledger['cost']:+9.2f}")
    print(f"  NET     n={ledger['priced']:3d}  ${ledger['net']:+9.2f}   "
          f"<- what the ratchet has actually earned")

    print("\nREPLAY under the CURRENT geometry (anachronistic before "
          f"{IMP040_START} — see docstring)")
    print(f"  would arm on {ledger['armed']}/{len(rows)} trades, "
          f"{ledger['raises']} stop raises")
    gaps = sum(1 for r in rows if r["fidelity_gap"])
    print(f"  fidelity: {gaps}/{len(rows)} trades where the replay's arming "
          f"disagrees with the fill-based class")

    pre = [r for r in rows if r["entry_time"].strftime("%Y-%m-%d") < split]
    post = [r for r in rows if r["entry_time"].strftime("%Y-%m-%d") >= split]
    if pre and post:
        a, b = era_stats(pre), era_stats(post)
        print(f"\nERA SPLIT at {split}   (before -> on/after)")
        rowfmt = "  {:22s} {:>12} -> {:>12}"
        print(rowfmt.format("trades", a["n"], b["n"]))
        print(rowfmt.format("net P&L", f"${a['net']:.2f}", f"${b['net']:.2f}"))
        print(rowfmt.format("EOD_FLATTEN share", f"{a['flatten_pct']:.1f}%",
                            f"{b['flatten_pct']:.1f}%"))
        print(rowfmt.format("RATCHET_STOP share", f"{a['ratchet_stop_pct']:.1f}%",
                            f"{b['ratchet_stop_pct']:.1f}%"))
        print(rowfmt.format("PLAN_STOP share", f"{a['plan_stop_pct']:.1f}%",
                            f"{b['plan_stop_pct']:.1f}%"))
        print(rowfmt.format("win rate", f"{a['win_pct']:.1f}%", f"{b['win_pct']:.1f}%"))
        print(rowfmt.format("avg win", f"${a['avg_win']:.2f}", f"${b['avg_win']:.2f}"))
        print(rowfmt.format("median MFE (R)", f"{a['median_mfe_r']:.3f}",
                            f"{b['median_mfe_r']:.3f}"))
        print(rowfmt.format("ratchet net P&L", f"${a['ratchet_net']:.2f}",
                            f"${b['ratchet_net']:.2f}"))

    if detail:
        print("\nPER TRADE")
        print("   id  sym    entry            class          P&L    no-ratchet"
              "     delta   MFE_R   MAE_R  arm")
        for r in rows:
            delta = f"{r['ratchet_delta']:+9.2f}" if r["ratchet_delta"] is not None else "        -"
            nr = f"{r['noratchet_pl']:+10.2f}" if r["noratchet_pl"] is not None else "         -"
            mfe = f"{r['mfe_r']:+7.3f}" if r["mfe_r"] is not None else "      -"
            mae = f"{r['mae_r']:+7.3f}" if r["mae_r"] is not None else "      -"
            print(f"  {r['trade_id']:4d}  {r['symbol']:5s} "
                  f"{r['entry_time'].strftime('%Y-%m-%d %H:%M')} "
                  f"{r['exit_class']:13s} {r['realized_pl']:+8.2f} {nr} {delta} "
                  f"{mfe} {mae}  {'Y' if r['armed'] else '.'}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--since", default=POST_GATE_START,
                        help=f"earliest entry_time (default {POST_GATE_START})")
    parser.add_argument("--split", default=IMP040_START,
                        help=f"era boundary to compare (default {IMP040_START})")
    parser.add_argument("--detail", action="store_true", help="one line per trade")
    args = parser.parse_args(argv)

    trades = load_trades(args.since)
    if not trades:
        print(f"no closed trades since {args.since}")
        return 0
    bars = bars_by_trade(trades)
    rows = audit(trades, bars)
    if not rows:
        print(f"{len(trades)} trades loaded but none had usable bars")
        return 1
    missing = len(trades) - len(rows)
    if missing:
        print(f"note: {missing} of {len(trades)} trades had no bar window and "
              f"are excluded")
    _print_report(rows, args.since, args.split, args.detail)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
