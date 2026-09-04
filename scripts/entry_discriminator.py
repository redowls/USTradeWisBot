"""Era-controlled entry-discriminator scorecard (IMP-036).

Usage:
  python -m scripts.entry_discriminator                       # atr-1r, default sweep
  python -m scripts.entry_discriminator --stat time-of-day
  python -m scripts.entry_discriminator --thresholds 2.0 2.5 3.0
  python -m scripts.entry_discriminator --stat atr-1r --feed iex

Eleven entry/exit discriminators have been tested and refuted (todo.md
"Refuted / closed candidates"), each by a throwaway script whose numbers cannot
be re-run as the book grows. This is the durable replacement. It reports every
candidate statistic against THREE cohorts at once — the raw book, the book
without the pre-gate week 2026-06-08..06-14, and the post-gate book — plus the
share of the refused cohort's P&L that comes from the pre-gate era and the
net-positive symbols the filter would discard. See bot/discriminator.py for why
those two columns exist and what they caught on 2026-08-18.

Built-in statistics:

  atr-1r        prior-day daily ATR(14) / 1R at entry. How wide the
                instrument's normal day is compared with the stop the engine
                gives it: high values mean the stop sits inside the daily noise.
                Needs daily bars (network).
  time-of-day   minutes after the 09:30 ET open. Pure, no network.

Both are EX-ANTE by construction. A statistic that is not knowable at entry
cannot become a live gate however well it separates — the 2026-08-13
session-range refutation turned on exactly that point, and realised range is
deliberately not offered here.

This is a STANDALONE analysis tool. Like scripts/regime_analysis.py and
scripts/exit_geometry.py it is NOT imported by the live trading path or by
scripts/report.py, so its network dependency can never break the always-on
incubation report and the running bot is unaffected by anything in it.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from alpaca.data.enums import DataFeed
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from bot import analytics, discriminator as D, doctrine
from bot.data import data_client
from bot.discriminator import Sample

ATR_PERIOD = 14
DEFAULT_ATR_THRESHOLDS = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
DEFAULT_TOD_THRESHOLDS = [15.0, 30.0, 45.0, 60.0, 90.0, 120.0]

# Daily-bar history to pull before the first trade, so an ATR(14) exists for it.
WARMUP_DAYS = 60


def _sample(row: dict, day: str, value: float) -> Sample:
    """One `Sample`, carrying the stop-exit doctrine's view of the trade (IMP-048).

    `bot.discriminator` is pure by contract and must not import `bot.doctrine`
    (which reaches the DB through `bot.analytics`), so the classification is
    done HERE and handed in. Every sample builder goes through this function so
    no statistic can quietly lose its doctrine columns and fall back to being
    judged on `realized_pl > 0` alone.
    """
    return Sample(symbol=row["symbol"], day=day, pl=_f(row["realized_pl"]),
                  value=value, profit_r=doctrine.profit_r(row),
                  doctrine=doctrine.classify(row))


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _daily_bars(symbols: list[str], start: date, end: date, feed: str) -> dict:
    """{symbol: [bar, ...]} of daily bars, oldest first.

    SIP is preferred (consolidated highs/lows are what a range statistic means)
    but the plan rejects SIP for very recent data, so `end` is clamped to
    yesterday and IEX is used as a fallback. IEX-only highs/lows understate the
    true range, which biases an ATR/1R statistic DOWN — noted rather than
    hidden, since it changes bucket boundaries.
    """
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        feed=DataFeed.SIP if feed == "sip" else DataFeed.IEX,
    )
    barset = data_client().get_stock_bars(request)
    out: dict[str, list] = {s: [] for s in symbols}
    data = getattr(barset, "data", None) or {}
    for symbol, bars in data.items():
        out[symbol] = sorted(bars, key=lambda b: b.timestamp)
    return out


def _prior_atr(bars: list, day: str, period: int = ATR_PERIOD) -> float | None:
    """Wilder-style simple ATR over the `period` days ENDING BEFORE `day`.

    Strictly prior days only — using `day`'s own bar would be lookahead and
    would make the statistic unusable as a live gate.
    """
    prior = [b for b in bars if b.timestamp.strftime("%Y-%m-%d") < day]
    if len(prior) < period + 1:
        return None
    window = prior[-period - 1:]
    trs = []
    for i in range(1, len(window)):
        high, low = float(window[i].high), float(window[i].low)
        prev_close = float(window[i - 1].close)
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return sum(trs) / len(trs)


def _atr_samples(rows: list[dict], feed: str) -> tuple[list[Sample], list[str]]:
    """Tag each closed trade with prior-day ATR(14) / 1R. Returns (samples, notes)."""
    usable = [
        r for r in rows
        if _f(r.get("entry_price")) - _f(r.get("stop_price")) > 0
        and r.get("exit_time") is not None
    ]
    if not usable:
        return [], ["no closed trade carries a usable entry/stop pair"]

    symbols = sorted({r["symbol"] for r in usable})
    first = min(r["exit_time"] for r in usable).date()
    last = max(r["exit_time"] for r in usable).date()
    end = min(last, date.today() - timedelta(days=1))
    bars = _daily_bars(symbols, first - timedelta(days=WARMUP_DAYS), end, feed)

    samples, skipped = [], 0
    for r in usable:
        day = r["exit_time"].strftime("%Y-%m-%d")
        one_r = _f(r["entry_price"]) - _f(r["stop_price"])
        atr = _prior_atr(bars.get(r["symbol"], []), day)
        if atr is None:
            skipped += 1
            continue
        samples.append(_sample(r, day, atr / one_r))
    notes = [f"feed={feed}, daily bars to {end}, ATR({ATR_PERIOD}) from prior days only"]
    if skipped:
        notes.append(f"{skipped} trade(s) skipped — no {ATR_PERIOD}-day history before entry")
    if feed != "sip":
        notes.append("IEX highs/lows understate true range — ATR/1R reads LOW vs SIP")
    return samples, notes


def _time_of_day_samples(rows: list[dict]) -> tuple[list[Sample], list[str]]:
    """Tag each closed trade with minutes after the 09:30 ET open."""
    samples = []
    for r in rows:
        et = r.get("entry_time")
        if et is None:
            continue
        minutes = (et.hour * 60 + et.minute) - (9 * 60 + 30)
        samples.append(_sample(r, (r.get("exit_time") or et).strftime("%Y-%m-%d"),
                               float(minutes)))
    return samples, ["entry_time is naive ET, as the bot writes it"]


def _fmt(stats: dict, doc: dict | None = None) -> str:
    pf = stats["profit_factor"]
    out = (f"n={stats['trades']:4d} net={stats['net']:9.2f} avg={stats['avg']:7.2f} "
           f"win={stats['win_rate']:5.1f}% PF={'  n/a' if pf is None else f'{pf:5.2f}'}")
    if doc:
        # Printed right beside the headline win rate on purpose: when the two
        # disagree the true one governs, and the reader has to see both to know
        # that they did. IMP-048.
        avg_r = "  n/a" if doc["avg_r"] is None else f"{doc['avg_r']:+.3f}"
        out += f"  | TRUE={doc['true_win_rate']:5.1f}% W={doc['wins']:3d} avgR={avg_r}"
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--stat", choices=["atr-1r", "time-of-day"], default="atr-1r",
                        help="which entry-time statistic to test")
    parser.add_argument("--thresholds", type=float, nargs="+",
                        help="thresholds to sweep (defaults per statistic)")
    parser.add_argument("--feed", choices=["sip", "iex"], default="sip",
                        help="daily-bar feed for atr-1r (default sip)")
    parser.add_argument("--since", help="only trades entered on/after YYYY-MM-DD")
    args = parser.parse_args(argv)

    since = date.fromisoformat(args.since) if args.since else None
    rows = analytics.load_closed_trades(since=since)
    if not rows:
        print("No closed trades. Nothing to test.")
        return 0

    if args.stat == "atr-1r":
        samples, notes = _atr_samples(rows, args.feed)
        thresholds = args.thresholds or DEFAULT_ATR_THRESHOLDS
        label = f"prior-day daily ATR({ATR_PERIOD}) / 1R at entry"
    else:
        samples, notes = _time_of_day_samples(rows)
        thresholds = args.thresholds or DEFAULT_TOD_THRESHOLDS
        label = "minutes after the 09:30 ET open"

    print("=" * 78)
    print(f"ENTRY-DISCRIMINATOR SCORECARD — {args.stat}")
    print(f"  statistic : {label}")
    print(f"  samples   : {len(samples)} of {len(rows)} closed trades")
    for note in notes:
        print(f"  note      : {note}")
    if not samples:
        print("\nNo usable samples — cannot judge.")
        return 0

    groups = D.cohorts(samples)
    print(f"  cohorts   : " + ", ".join(f"{n}={len(r)}" for n, r in groups.items()))
    print(f"  era cut   : pre-gate era ends {D.PRE_GATE_ERA_END}; "
          f"post-gate starts {D.POST_GATE_START}")
    print("=" * 78)

    sweep = D.threshold_sweep(samples, thresholds)
    for row in sweep:
        print(f"\n>>> refuse entries with {args.stat} >= {row['threshold']}  "
              f"[{row['verdict']}]")
        for name, split in row["splits"].items():
            print(f"      {name:15} ABOVE {_fmt(split['above'], split['above_doctrine'])}")
            print(f"      {'':15} BELOW {_fmt(split['below'], split['below_doctrine'])}")
            r_edge = split["r_edge"]
            print(f"      {'':15}   edge="
                  f"{split['edge'] if split['edge'] is not None else 'n/a'}"
                  f"  R-edge={'n/a' if r_edge is None else f'{r_edge:+.3f}'}")
        if row.get("win_collateral_fraction") is not None:
            print(f"      doctrine WINs inside the refused cohort: "
                  f"{row['win_collateral_fraction']:.0%}")
        if row["era_concentration"] is not None:
            print(f"      pre-gate era share of the refused cohort's P&L: "
                  f"{row['era_concentration']:.0%}")
        if row["collateral"]:
            top = ", ".join(f"{c['symbol']} +${c['net']:.2f} ({c['trades']})"
                            for c in row["collateral"][:5])
            print(f"      collateral ({row['collateral_fraction']:.0%} of |net|): {top}")
        for reason in row["reasons"]:
            print(f"      -> {reason}")

    print("\n" + "=" * 78)
    if D.any_supported(sweep):
        winners = [r["threshold"] for r in sweep if r["verdict"] == D.SUPPORTED]
        print(f"VERDICT: SUPPORTED at {winners} — era-controlled and free of collateral.")
        print("A supported threshold is a CANDIDATE, not a mandate: confirm it is")
        print("knowable at entry, then ship it behind tests as its own IMP.")
    else:
        counts: dict[str, int] = {}
        for r in sweep:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        print("VERDICT: NOT SUPPORTED at any threshold tested — "
              + ", ".join(f"{v}x{n}" for v, n in sorted(counts.items())))
        print("Do not ship an entry filter on this statistic. Record it in todo.md")
        print("under 'Refuted / closed candidates' with the numbers above.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
