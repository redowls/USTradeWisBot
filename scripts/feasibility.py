"""Was a doctrine WIN reachable AT ALL? The exit layer's blame ceiling (IMP-054).

Usage:
  python -m scripts.feasibility                      # post-gate book
  python -m scripts.feasibility --since 2026-08-01
  python -m scripts.feasibility --detail             # one line per trade
  python -m scripts.feasibility --feed iex           # SIP is the default

WHY THIS EXISTS
---------------
Twelve consecutive daily reviews have argued the same question from both
sides — is the book losing because the entries are bad, or because the exit
geometry hands back what the entries earn? — and both sides keep citing the
same instrument: **session range / 1R**, the full day's high-minus-low measured
against the stop distance. That instrument answers a different question than
the one it is quoted for, and on 2026-09-11 it answered it backwards.

NVDA #344 (2026-09-11) is the archetype. Session range / 1R = **1.12**, so the
incumbent metric calls the trade *feasible* — a +1R WIN fitted inside the day's
range. But NVDA's session high (222.00) printed at **10:04** and the fill came
at **10:07**. From the fill forward the price never rose more than **+0.242R**.
A doctrine WIN was not merely unlikely, it was **arithmetically unavailable to
every possible exit policy**, and no trail width, no take-profit site and no
time-stop could have produced one. The incumbent metric scored a trade feasible
whose outcome was fixed three minutes before it was opened.

WHAT THIS MEASURES
------------------
For each closed trade, the **WIN ceiling**: the highest profit_R that ANY exit
policy could have banked, measured from the actual fill forward to the 15:55 ET
flatten.

    win_ceiling_R = (max high from the fill to the flatten - fill) / 1R

It is an **upper bound**, deliberately. It ignores the stop entirely, so it
credits a trade that stopped out at 10:30 with a rally that happened at 15:00
and that no policy holding a stop could have reached. That bias runs one way
only: the true share of unwinnable trades is **at least** what this reports.
When the ceiling is below `doctrine.WIN_MIN_R`, the trade could not have been a
WIN under any exit rule, full stop — and the exit layer cannot be blamed for it.

The bar containing the fill is INCLUDED, which can credit the trade with highs
printed in the seconds before the fill. Same direction: it inflates the ceiling
and so *understates* the impossible share. Both approximations are chosen so the
headline number is the conservative one.

⚠️ **THIS IS A DIAGNOSTIC AND IT CAN NEVER BECOME AN ENTRY GATE.** The ceiling
is computed from bars printed AFTER the fill; it is pure lookahead and is
unknowable at entry time. It exists to partition blame between the entry layer
and the exit layer on the book that already traded. The ex-ante cousin — the
`stop_distance% / ADR20%` entry-feasibility gate pre-registered on 2026-09-04 —
is a different instrument with a different burden of proof, and it belongs to
`scripts/entry_discriminator.py` and the weekly review. Sixteen entry
discriminators have been refuted; do not let this become the seventeenth by
mistaking a post-hoc ceiling for a prediction.

The WIN bar is imported from `bot.doctrine`, never redefined here: IMP-049 and
IMP-053 were both caused by two instruments carrying two vocabularies for one
verdict, and this file refuses to add a third.

Like scripts/entry_discriminator.py and scripts/exit_geometry.py this is NOT
imported by the live trading path or by scripts/report.py, so its network
dependency can never break the always-on incubation report and the running bot
is unaffected by anything in it.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from bot import analytics, config, discriminator as D, doctrine
from scripts.entry_discriminator import _f, _minute_bars

#: A WIN needs profit_R >= this. Imported, never redefined — see the docstring.
WIN_CEILING_R = doctrine.WIN_MIN_R

#: Ceiling bands. The 0-0.25R edge is `config.BREAKEVEN_TRIGGER_R`: below it the
#: ratchet never armed, so the trade had no exit decision to make at all.
CEILING_BANDS: tuple[tuple[float, float, str], ...] = (
    (float("-inf"), 0.0, "never green"),
    (0.0, 0.25, "0-0.25R (ratchet never armed)"),
    (0.25, 0.50, "0.25-0.5R"),
    (0.50, 1.00, "0.5-1.0R"),
    (1.00, 1.50, "1.0-1.5R"),
    (1.50, float("inf"), ">1.5R"),
)


def win_ceiling_r(entry_price: float, stop_price: float,
                  highs: list[float]) -> float | None:
    """Best profit_R any exit policy could have banked from the fill forward.

    `highs` are the bar highs from the fill through the flatten. Returns None
    when 1R is not positive or no bars cover the holding window — an unknown
    ceiling must never be silently counted as a reachable one.
    """
    risk = entry_price - stop_price
    if risk <= 0 or not highs:
        return None
    return (max(highs) - entry_price) / risk


def session_range_r(entry_price: float, stop_price: float,
                    highs: list[float], lows: list[float]) -> float | None:
    """The INCUMBENT metric: the whole session's range measured in R.

    Kept here so the two instruments are computed side by side from one set of
    bars and their disagreement is a first-class output rather than a claim.
    """
    risk = entry_price - stop_price
    if risk <= 0 or not highs or not lows:
        return None
    return (max(highs) - min(lows)) / risk


def is_reachable(ceiling: float | None) -> bool:
    """Could this trade have been a doctrine WIN under some exit policy?"""
    return ceiling is not None and ceiling >= WIN_CEILING_R


def window_bars(bars, start_et: datetime, end_et: datetime) -> list:
    """Bars whose minute overlaps [start_et, end_et], oldest first.

    The bar CONTAINING `start_et` is included — see the module docstring on why
    the approximation is deliberately biased toward a higher ceiling. Bars carry
    tz-aware timestamps; they are compared in ET.
    """
    out = []
    for b in bars:
        ts = b.timestamp.astimezone(config.MARKET_TZ)
        if ts.replace(second=0, microsecond=0) >= start_et.replace(second=0, microsecond=0) \
                and ts <= end_et:
            out.append(b)
    return out


def summarize(records: list[dict]) -> dict:
    """Partition the book by whether a WIN was reachable at all.

    Each record needs `ceiling`, `range_r`, `doctrine` and `pl`. Returns the
    cohort split, the per-band table, the conversion rate inside the reachable
    cohort, and the disagreement against the incumbent session-range metric.
    """
    usable = [r for r in records if r.get("ceiling") is not None]
    n = len(usable)
    if not n:
        return {"trades": 0}
    impossible = [r for r in usable if not is_reachable(r["ceiling"])]
    reachable = [r for r in usable if is_reachable(r["ceiling"])]
    wins = [r for r in reachable if r["doctrine"] == doctrine.WIN]
    # Trades the incumbent metric calls feasible and that never had a chance.
    disagree = [r for r in usable
                if r.get("range_r") is not None and r["range_r"] >= WIN_CEILING_R
                and not is_reachable(r["ceiling"])]
    incumbent_ok = [r for r in usable
                    if r.get("range_r") is not None and r["range_r"] >= WIN_CEILING_R]
    bands = {}
    for lo, hi, label in CEILING_BANDS:
        sub = [r for r in usable if lo <= r["ceiling"] < hi]
        bands[label] = {
            "trades": len(sub),
            "share": round(len(sub) / n * 100, 1),
            "net": round(sum(r["pl"] for r in sub), 2),
            "wins": sum(1 for r in sub if r["doctrine"] == doctrine.WIN),
        }
    return {
        "trades": n,
        "impossible": len(impossible),
        "impossible_share": round(len(impossible) / n * 100, 1),
        "impossible_net": round(sum(r["pl"] for r in impossible), 2),
        "reachable": len(reachable),
        "reachable_share": round(len(reachable) / n * 100, 1),
        "reachable_net": round(sum(r["pl"] for r in reachable), 2),
        # The number that adjudicates the exit layer: when the move WAS there,
        # how often did the bot actually bank a WIN?
        "conversion": (round(len(wins) / len(reachable) * 100, 1) if reachable else None),
        "median_ceiling": round(sorted(r["ceiling"] for r in usable)[n // 2], 3),
        "incumbent_feasible": len(incumbent_ok),
        "disagree": len(disagree),
        "disagree_share": round(len(disagree) / n * 100, 1),
        "disagree_of_incumbent": (round(len(disagree) / len(incumbent_ok) * 100, 1)
                                  if incumbent_ok else None),
        "disagree_net": round(sum(r["pl"] for r in disagree), 2),
        "disagree_wins": sum(1 for r in disagree if r["doctrine"] == doctrine.WIN),
        "bands": bands,
    }


def build_records(rows: list[dict], feed: str) -> tuple[list[dict], list[str]]:
    """Attach the ceiling + incumbent range to each closed trade. Needs network."""
    usable = [r for r in rows if r.get("entry_time") is not None]
    by_day: dict[str, set] = {}
    for r in usable:
        by_day.setdefault(r["entry_time"].strftime("%Y-%m-%d"), set()).add(r["symbol"])

    flat_h, flat_m = (int(x) for x in config.FLATTEN_ET.split(":"))
    records, skipped = [], 0
    for day in sorted(by_day):
        bars = _minute_bars(sorted(by_day[day]), day, feed)
        for r in usable:
            if r["entry_time"].strftime("%Y-%m-%d") != day:
                continue
            # entry_time is naive ET, as the bot writes it.
            entry_et = r["entry_time"].replace(tzinfo=config.MARKET_TZ)
            flatten_et = entry_et.replace(hour=flat_h, minute=flat_m,
                                          second=0, microsecond=0)
            day_bars = bars.get(r["symbol"], [])
            held = window_bars(day_bars, entry_et, flatten_et)
            entry, stop = _f(r["entry_price"]), _f(r["stop_price"])
            ceiling = win_ceiling_r(entry, stop, [float(b.high) for b in held])
            if ceiling is None:
                skipped += 1
                continue
            records.append({
                "trade_id": r.get("trade_id"),
                "symbol": r["symbol"],
                "day": day,
                "ceiling": ceiling,
                "range_r": session_range_r(entry, stop,
                                           [float(b.high) for b in day_bars],
                                           [float(b.low) for b in day_bars]),
                "doctrine": doctrine.classify(r),
                "profit_r": doctrine.profit_r(r),
                "pl": _f(r["realized_pl"]),
                "exit_reason": r.get("exit_reason"),
            })
    notes = [f"feed={feed}, 1-minute bars, ceiling from the fill bar through {config.FLATTEN_ET} ET",
             f"{len(by_day)} session(s) fetched"]
    if skipped:
        notes.append(f"{skipped} trade(s) skipped — no bars or 1R <= 0")
    if feed != "sip":
        notes.append("IEX-only highs understate the ceiling — the impossible share reads HIGH vs SIP")
    return records, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--since", default=D.POST_GATE_START,
                        help=f"first exit date to include (default {D.POST_GATE_START})")
    parser.add_argument("--feed", choices=["sip", "iex"], default="sip",
                        help="bar feed (default sip)")
    parser.add_argument("--detail", action="store_true",
                        help="print one line per trade")
    args = parser.parse_args(argv)

    rows = [r for r in analytics.load_closed_trades()
            if r.get("exit_time") is not None
            and r["exit_time"].strftime("%Y-%m-%d") >= args.since]
    if not rows:
        print(f"no closed trades since {args.since}")
        return 0

    records, notes = build_records(rows, args.feed)
    s = summarize(records)
    if not s.get("trades"):
        print("no trades with usable bars")
        return 0

    print("=" * 78)
    print(f"WIN FEASIBILITY — could a doctrine WIN ({WIN_CEILING_R:+.1f}R) have happened at all?")
    print(f"  trades={s['trades']}  since {args.since}")
    for note in notes:
        print(f"  note: {note}")
    print("=" * 78)
    print(f"\n  IMPOSSIBLE under ANY exit policy : {s['impossible']:4d}  "
          f"({s['impossible_share']:5.1f}%)   net ${s['impossible_net']:+9.2f}")
    print(f"  reachable (ceiling >= {WIN_CEILING_R:.1f}R)      : {s['reachable']:4d}  "
          f"({s['reachable_share']:5.1f}%)   net ${s['reachable_net']:+9.2f}")
    print(f"  median ceiling {s['median_ceiling']:+.3f}R")
    if s["conversion"] is not None:
        print(f"\n  >> CONVERSION when the move WAS there: {s['conversion']:.1f}% "
              f"of the reachable cohort became doctrine WINs.")
        print("     The exit layer can only be blamed for the reachable cohort.")

    print("\n  ceiling band                     n   share        net   WINs")
    for _lo, _hi, label in CEILING_BANDS:
        b = s["bands"][label]
        print(f"    {label:28s} {b['trades']:4d}  {b['share']:5.1f}%  "
              f"${b['net']:+9.2f}  {b['wins']:4d}")

    print(f"\n  vs the INCUMBENT session-range/1R metric:")
    print(f"    it calls {s['incumbent_feasible']} trades feasible; "
          f"{s['disagree']} of them ({s['disagree_of_incumbent']}%) could NEVER have won.")
    print(f"    that cohort is {s['disagree_share']}% of the book, "
          f"net ${s['disagree_net']:+.2f}, WINs {s['disagree_wins']}.")

    if args.detail:
        print("\n  trade detail (worst ceiling first)")
        for r in sorted(records, key=lambda r: r["ceiling"]):
            rng = "  n/a" if r["range_r"] is None else f"{r['range_r']:5.2f}"
            print(f"    #{r['trade_id']:<4} {r['day']} {r['symbol']:<5} "
                  f"ceiling {r['ceiling']:+7.3f}R  range/1R {rng}  "
                  f"{r['doctrine']:<7} {r['exit_reason']:<12} ${r['pl']:+8.2f}")
    print()
    return 0


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
