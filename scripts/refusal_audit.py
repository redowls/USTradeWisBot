"""Was any REFUSED candidate winnable? The entry layer's blame ceiling (IMP-057).

Usage:
  python -m scripts.refusal_audit --date 2026-09-16
  python -m scripts.refusal_audit --date 2026-09-16 --detail
  python -m scripts.refusal_audit --date 2026-09-16 --feed iex   # SIP is the default

WHY THIS EXISTS
---------------
IMP-054 answered "could a doctrine WIN have been reached at all?" for the trades
the bot **filled**. The refused population is roughly an order of magnitude
larger — 2026-09-15 produced 34 refusals and zero fills — and until IMP-056 it
was not recorded anywhere durable, so no instrument in this repo could see it.
IMP-056 shipped ``dbo.entry_refusals`` and pre-registered this as the next step.
This is that step: the same ceiling arithmetic, pointed at the candidates the
bot said NO to.

It answers two questions that have never been answerable together:

1. **Did each filter pay?** Per refusal ``reason``, the win-feasibility ceiling
   and the forward return to the 15:55 flatten. A filter that refuses candidates
   which then go UP is costing money; one that refuses candidates which fall is
   earning its keep. Five prior VWAP audits could only ask this of the quality
   filter, and only through a log.
2. **Is the entry SIGNAL the problem, or the filters on top of it?** If the
   refused candidates are as unwinnable as the filled ones, the filters are not
   what is standing between this bot and a positive expectancy — the signal is.

WHAT IT REPAIRS
---------------
``scripts/gate_monitor._replay_geometry`` prices the blocked set at the flat
``MIN_STOP_PCT`` floor and says why in its own docstring: *"ATR is not
recoverable from the log."* Every VWAP counterfactual this repo has run
therefore used 1.5% instead of the live ``max(ATR x ATR_STOP_MULT,
MIN_STOP_PCT%)``. ``entry_refusals`` stores ``price`` AND ``atr``, the two
inputs ``bot.sizing.plan_position`` uses, so the real geometry is reconstructable
here — and ``geometry_binding()`` reports which term bound, turning that caveat
from an unquantified worry into a per-session measurement.

THE REASON SPLIT IS THE LEDGER'S, NOT A PARSED PREFIX
-----------------------------------------------------
IMP-042 had to unpick eligibility refusals from quality refusals out of a log
(2026-08-26: 9 of 31 "refusals" were a symbol already in the book). IMP-056 made
that distinction a column. This script groups on it directly, so an
``underlying_held`` row can never again be counted as a gate veto.

⚠️ **DIAGNOSTIC ONLY — IT CAN NEVER BECOME AN ENTRY GATE.** Like IMP-054's
ceiling, every number here is computed from bars printed AFTER the moment it
scores, and is unknowable at decision time. Sixteen entry discriminators have
been refuted; do not let a post-hoc ceiling become the seventeenth.

The WIN bar, the ceiling function and the bar window are all imported from the
modules that already own them (``bot.doctrine``, ``scripts.feasibility``) and
never redefined: IMP-049 and IMP-053 were both caused by two instruments
carrying two vocabularies for one verdict.

Not imported by the live trading path or by ``scripts/report.py``, so its
network dependency cannot break the always-on incubation report and the running
bot is unaffected by anything in it.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import date, datetime

from bot import config, logbook
from scripts.entry_discriminator import _f, _minute_bars
from scripts.feasibility import WIN_CEILING_R, is_reachable, win_ceiling_r, window_bars

#: ``entry_refusals.reason`` values that mean "this candidate was never eligible",
#: as opposed to "it was eligible and a quality filter vetoed it". IMPORTED from
#: ``bot.logbook``, never re-listed here: that module owns the vocabulary the
#: engine writes, and a local copy is how the report and the ledger would drift
#: apart the first time a reason is added (IMP-049's lesson, on the entry side).
ELIGIBILITY_REASONS = frozenset(logbook.REFUSAL_ELIGIBILITY)

#: A refusal only clears the doctrine's SCRATCH floor if it could reach past
#: ``config.BREAKEVEN_TRIGGER_R``; below that the ratchet would never have armed
#: and the candidate had no exit decision to make at all.
SCRATCH_CEILING_R = float(config.BREAKEVEN_TRIGGER_R)


def refusal_geometry(price: float, atr: float) -> tuple[float, float] | None:
    """The (stop_price, stop_distance) ``bot.sizing.plan_position`` would have set.

    Reproduces that function's two lines verbatim — ``max(atr *
    ATR_STOP_MULT, price * MIN_STOP_PCT / 100)`` — rather than approximating
    with the floor alone, which is the whole point of storing ``atr`` on the
    ledger. Returns None on inputs that could not have produced a bracket, so an
    unusable row is skipped rather than silently scored at a made-up 1R.

    Deliberately NOT rounded to the tick: ``_round_tick`` would change the 1R
    denominator by up to half a cent and every number downstream is an R-multiple
    with three decimals. The live bracket rounds; this instrument does not need
    to, and pretending otherwise would imply a precision the ledger's own
    four-decimal ``atr`` does not carry.
    """
    if price is None or atr is None or price <= 0 or atr <= 0:
        return None
    distance = max(atr * float(config.ATR_STOP_MULT),
                   price * float(config.MIN_STOP_PCT) / 100.0)
    if distance <= 0:
        return None
    return price - distance, distance


def geometry_binding(rows: list[dict]) -> dict:
    """Which term set the stop on each refusal: the ATR or the MIN_STOP_PCT floor.

    This is the measurement that retires ``gate_monitor._replay_geometry``'s
    caveat. When the floor binds on every row, that function's floor-width stop
    was not an approximation at all on that session and its result stands
    unqualified; when the ATR binds anywhere, the affected rows are exactly the
    ones its verdict was softest on.
    """
    atr_bound = floor_bound = 0
    widths: list[float] = []
    for r in rows:
        price, atr = _f(r.get("price"), 0.0), _f(r.get("atr"), 0.0)
        if price <= 0 or atr <= 0:
            continue
        atr_distance = atr * float(config.ATR_STOP_MULT)
        floor_distance = price * float(config.MIN_STOP_PCT) / 100.0
        widths.append(100.0 * atr_distance / price)
        if atr_distance > floor_distance:
            atr_bound += 1
        else:
            floor_bound += 1
    scored = atr_bound + floor_bound
    return {
        "scored": scored,
        "atr_bound": atr_bound,
        "floor_bound": floor_bound,
        "floor_share": round(100.0 * floor_bound / scored, 1) if scored else None,
        "median_atr_width_pct": round(statistics.median(widths), 3) if widths else None,
        "floor_width_pct": float(config.MIN_STOP_PCT),
    }


def build_records(rows: list[dict], feed: str) -> tuple[list[dict], list[str]]:
    """Attach the ceiling + forward return to each refusal. Needs network.

    Fetches per SESSION rather than per symbol: refusals cluster into one day by
    construction (``logbook.get_entry_refusals`` takes a single date) and the
    same symbol is typically refused dozens of times within it.
    """
    usable = [r for r in rows if r.get("ts") is not None]
    by_day: dict[str, set] = {}
    for r in usable:
        by_day.setdefault(r["ts"].strftime("%Y-%m-%d"), set()).add(r["symbol"])

    flat_h, flat_m = (int(x) for x in config.FLATTEN_ET.split(":"))
    records: list[dict] = []
    skipped = 0
    for day in sorted(by_day):
        bars = _minute_bars(sorted(by_day[day]), day, feed)
        for r in usable:
            if r["ts"].strftime("%Y-%m-%d") != day:
                continue
            price, atr = _f(r.get("price"), 0.0), _f(r.get("atr"), 0.0)
            geo = refusal_geometry(price, atr)
            if geo is None:
                skipped += 1
                continue
            stop, distance = geo
            # ts is naive ET, as logbook writes it.
            refused_et = r["ts"].replace(tzinfo=config.MARKET_TZ)
            flatten_et = refused_et.replace(hour=flat_h, minute=flat_m,
                                            second=0, microsecond=0)
            forward = window_bars(bars.get(r["symbol"], []), refused_et, flatten_et)
            ceiling = win_ceiling_r(price, stop, [float(b.high) for b in forward])
            if ceiling is None:
                skipped += 1
                continue
            close = float(forward[-1].close)
            records.append({
                "refusal_id": r.get("refusal_id"),
                "symbol": r["symbol"],
                "ts": r["ts"],
                "reason": r.get("reason"),
                "eligibility": r.get("reason") in ELIGIBILITY_REASONS,
                "confidence": _f(r.get("confidence"), 0.0),
                "price": price,
                "atr": atr,
                "stop": stop,
                "ceiling": ceiling,
                # What the refused candidate would have been worth held to the
                # flatten, in the same R units as the ceiling, so a refusal can
                # be compared against the book's own trades directly.
                "flatten_r": (close - price) / distance,
                "flatten_pct": 100.0 * (close / price - 1.0),
            })
    notes = [f"feed={feed}, 1-minute bars, ceiling from the refusal bar through "
             f"{config.FLATTEN_ET} ET",
             f"geometry = max({config.ATR_STOP_MULT}xATR, {config.MIN_STOP_PCT}% of price) "
             f"— the live bot.sizing.plan_position rule, from the ledger's own price+atr",
             f"{len(by_day)} session(s) fetched"]
    if skipped:
        notes.append(f"{skipped} refusal(s) skipped — no bars or unusable price/atr")
    if feed != "sip":
        notes.append("IEX-only highs understate the ceiling — the unwinnable share reads HIGH vs SIP")
    return records, notes


def _cohort(records: list[dict]) -> dict:
    """Feasibility + forward-return stats over one slice of refusals."""
    n = len(records)
    if not n:
        return {"refusals": 0}
    ceilings = [r["ceiling"] for r in records]
    feasible = [r for r in records if is_reachable(r["ceiling"])]
    scratchable = [r for r in records if r["ceiling"] > SCRATCH_CEILING_R]
    return {
        "refusals": n,
        "win_feasible": len(feasible),
        "win_feasible_share": round(100.0 * len(feasible) / n, 1),
        "scratch_feasible": len(scratchable),
        "best_ceiling": round(max(ceilings), 3),
        "median_ceiling": round(statistics.median(ceilings), 3),
        "mean_flatten_r": round(statistics.fmean(r["flatten_r"] for r in records), 3),
        "mean_flatten_pct": round(statistics.fmean(r["flatten_pct"] for r in records), 3),
        # The verdict on the filter: refusals that went UP are what it cost.
        "rose_to_flatten": sum(1 for r in records if r["flatten_pct"] > 0),
    }


def summarize(records: list[dict]) -> dict:
    """Overall, eligibility-vs-quality, per-reason and per-symbol cohorts.

    ``paid`` is the plain-language verdict a reader wants and it is deliberately
    conservative: a filter only "PAID" when it refused nothing that could have
    been a WIN **and** the refused set fell on average. Refusing an unwinnable
    candidate that nonetheless drifted up is scored ``neutral``, not a win for
    the filter, because the bot's own flatten would have banked that drift.
    """
    if not records:
        return {"refusals": 0}
    out = {
        "overall": _cohort(records),
        "eligibility": _cohort([r for r in records if r["eligibility"]]),
        "quality": _cohort([r for r in records if not r["eligibility"]]),
        "by_reason": {},
        "by_symbol": {},
        "geometry": geometry_binding(records),
    }
    for reason in sorted({r["reason"] for r in records}):
        sub = [r for r in records if r["reason"] == reason]
        cohort = _cohort(sub)
        cohort["eligibility"] = reason in ELIGIBILITY_REASONS
        cohort["paid"] = (
            "PAID" if cohort["win_feasible"] == 0 and cohort["mean_flatten_pct"] < 0
            else "COST" if cohort["win_feasible"] > 0
            else "neutral"
        )
        out["by_reason"][reason] = cohort
    for symbol in sorted({r["symbol"] for r in records}):
        out["by_symbol"][symbol] = _cohort([r for r in records if r["symbol"] == symbol])
    return out


def _fmt_cohort(label: str, c: dict) -> str:
    if not c.get("refusals"):
        return f"  {label:<26} (none)"
    return (f"  {label:<26} n={c['refusals']:>3}  win-feasible={c['win_feasible']:>2}"
            f" ({c['win_feasible_share']:>5.1f}%)  scratch-feasible={c['scratch_feasible']:>2}"
            f"  best={c['best_ceiling']:+.3f}R  med={c['median_ceiling']:+.3f}R"
            f"  ->flatten {c['mean_flatten_pct']:+.3f}% ({c['mean_flatten_r']:+.3f}R)"
            f"  rose={c['rose_to_flatten']}")


def format_report(day: date, summary: dict, notes: list[str]) -> list[str]:
    lines = [f"REFUSAL AUDIT — {day} (IMP-057)", "=" * 78]
    if not summary.get("refusals") and not summary.get("overall"):
        lines.append("No refusals recorded for this date.")
        lines.append("(dbo.entry_refusals starts 2026-09-16 — earlier sessions are not recoverable.)")
        return lines
    for note in notes:
        lines.append(f"  · {note}")
    g = summary["geometry"]
    lines += [
        "",
        f"STOP GEOMETRY — which term bound (repairs gate_monitor._replay_geometry's caveat)",
        f"  floor bound {g['floor_bound']}/{g['scored']} ({g['floor_share']}%)"
        f"   ATR bound {g['atr_bound']}/{g['scored']}"
        f"   median 3xATR width {g['median_atr_width_pct']}% vs {g['floor_width_pct']}% floor",
        "",
        f"FEASIBILITY (a WIN needs ceiling >= {WIN_CEILING_R}R; SCRATCH needs > {SCRATCH_CEILING_R}R)",
        _fmt_cohort("ALL REFUSALS", summary["overall"]),
        _fmt_cohort("eligibility (never eligible)", summary["eligibility"]),
        _fmt_cohort("quality (filter vetoed)", summary["quality"]),
        "",
        "BY REASON",
    ]
    for reason, c in summary["by_reason"].items():
        tag = "elig" if c["eligibility"] else "qual"
        lines.append(_fmt_cohort(f"{reason} [{tag}] {c['paid']}", c))
    lines += ["", "BY SYMBOL"]
    for symbol, c in summary["by_symbol"].items():
        lines.append(_fmt_cohort(symbol, c))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--date", required=True, help="session to audit, YYYY-MM-DD")
    parser.add_argument("--feed", default="sip", choices=("sip", "iex"))
    parser.add_argument("--detail", action="store_true",
                        help="one line per refusal, oldest first")
    args = parser.parse_args(argv)

    day = datetime.strptime(args.date, "%Y-%m-%d").date()
    rows = logbook.get_entry_refusals(day)
    if not rows:
        print("\n".join(format_report(day, {}, [])))
        return 0

    records, notes = build_records(rows, args.feed)
    summary = summarize(records)
    print("\n".join(format_report(day, summary, notes)))

    if args.detail:
        print("\nDETAIL (oldest first)")
        for r in sorted(records, key=lambda x: x["ts"]):
            print(f"  {r['ts'].strftime('%H:%M:%S')} {r['symbol']:<5} "
                  f"{r['reason']:<22} conf={r['confidence']:>5.2f} "
                  f"price={r['price']:>9.2f} stop={r['stop']:>9.2f} "
                  f"ceiling={r['ceiling']:+.3f}R ->flatten {r['flatten_pct']:+.3f}% "
                  f"({r['flatten_r']:+.3f}R)"
                  f"{'  WIN-FEASIBLE' if is_reachable(r['ceiling']) else ''}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
