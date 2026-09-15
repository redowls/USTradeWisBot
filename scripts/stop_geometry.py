"""Is 1R the wrong SIZE? A stop-width what-if over the post-gate book (IMP-055).

Usage:
  python -m scripts.stop_geometry                    # post-gate book, default grid
  python -m scripts.stop_geometry --since 2026-08-01
  python -m scripts.stop_geometry --detail           # one line per trade, live vs best
  python -m scripts.stop_geometry --feed iex         # SIP is the default, see below

WHY THIS EXISTS
---------------
The week-ending-09-11 weekly named ONE live-path change and refused to let a
tenth measurement stand in for it: *"make 1R scale with the name's realized
daily range instead of a 1.5% constant, so the risk unit stops exceeding what
the instrument can travel"*. It also attached a condition — **re-derive the
case against IMP-054's WIN ceiling, not against `session range / 1R`**, because
IMP-054 falsified the latter and the `stop_distance% / ADR20%` gate
pre-registered on 09-04 inherits that error.

This module is that re-derivation, and it exists because the ceiling alone
**cannot** answer the question. `scripts.feasibility` reports the ceiling in R,
and R is the stop distance — so shrinking the stop raises every ceiling
mechanically and would "prove" any tightening whatsoever. META #347
(2026-09-14) is the worked example: ceiling **+0.670R** at the live 1.832% stop,
**+1.117R** at 60% of it. Nothing about the tape changed; only the denominator
did. Answering the weekly's question honestly therefore requires re-walking the
bars with the tighter stop actually in place, so the trades that the tighter
stop would have KILLED are charged against it at the same time as the trades it
would have rescued.

WHAT IT MEASURES
----------------
For each candidate 1R policy, every post-gate trade is re-planned and re-run:

  * ``stop' = entry - sd'``            where ``sd'`` is the policy's stop distance
  * ``tp'   = entry + RR_RATIO * sd'`` the live take-profit rule, re-anchored
  * ``qty'  = floor(dollar_risk / sd')`` **dollar risk per trade is held CONSTANT**
  * the live IMP-013/028/040 ratchet is then simulated bar by bar to 15:55.

Holding dollar risk constant is what makes the comparison honest AND what keeps
it inside the capital-protection invariants: a tighter stop buys more shares at
the same risk budget, exactly as ``sizing.plan_position`` already does. Nothing
here widens a stop, raises ``MAX_RISK_PCT``, or touches the ratchet.

Policies:
  ``scale=k``    sd' = k * the stop distance the bot actually used (uniform)
  ``adrcap=c``   sd' = min(live sd, c * ADR20$) — the weekly's designated shape:
                 cap 1R at a fraction of what the name really travels in a day.

THE BIAS, STATED UP FRONT
-------------------------
``bot/exit_sim.py`` records that simulated stops fire LESS often than real ones
when bars are sparse, so **a what-if that tightens stops is biased optimistic**.
That bias is the single largest threat to this measurement, so this module
defaults to the **SIP** feed (consolidated tape) rather than the IEX feed
``bot.data`` uses, which removes most of it. The residual is bounded by the
``scale=1.0`` row: its ``sum|error|`` against the real book is the noise budget,
and a candidate's edge must clear it by a wide margin before it is believed.

Judged on **expectancy and payoff first, stop rate second** (stop doctrine).
A tightening will MECHANICALLY raise the stop rate; that is not disqualifying,
and a lower stop rate would not by itself be a reason to accept anything.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

from bot import config, db, doctrine
from bot.data import data_client
from bot.exit_sim import ExitGeometry, simulate_exit
from scripts.entry_discriminator import _minute_bars

POST_GATE_START = "2026-07-25"   # IMP-021 + IMP-022 shipped after this close
ADR_LOOKBACK = 20                # sessions in the ADR20 average
ET = ZoneInfo("America/New_York")

#: The grid. ``scale`` probes "tighter everywhere"; ``adrcap`` probes the
#: weekly's designated shape — 1R capped at a fraction of the name's own ADR20.
#: Both are deliberately coarse: this is a direction test, not a curve fit, and
#: a fine grid over 100-odd trades would be over-fitting by construction.
SCALES = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5)
ADR_CAPS = (0.75, 0.6, 0.5, 0.4, 0.3)


class Policy:
    """One candidate 1R rule: name + a stop-distance function."""

    def __init__(self, label: str, fn):
        self.label = label
        self.fn = fn

    def stop_distance(self, entry: float, live_sd: float, adr: float | None) -> float | None:
        return self.fn(entry, live_sd, adr)


def build_policies() -> list[Policy]:
    out = [Policy(f"scale={k:.2f}", lambda e, sd, a, k=k: sd * k) for k in SCALES]
    for c in ADR_CAPS:
        def _cap(e, sd, a, c=c):
            if a is None or a <= 0:
                return None          # unknown ADR -> the policy has no opinion
            return min(sd, c * a)
        out.append(Policy(f"adrcap={c:.2f}", _cap))
    return out


# --- Data --------------------------------------------------------------------

def load_trades(since: str) -> list[dict]:
    return db.query(
        "SELECT trade_id, symbol, qty, entry_price, entry_time, stop_price, "
        "take_profit_price, exit_price, exit_time, realized_pl, exit_reason "
        "FROM trades WHERE status = 'CLOSED' AND entry_time >= ? "
        "ORDER BY entry_time",
        since,
    )


def adr20_by_symbol_day(trades: list[dict], feed: str) -> dict:
    """(symbol, 'YYYY-MM-DD') -> mean daily high-low over the 20 sessions BEFORE it.

    Strictly prior sessions: the entry day's own range is not knowable at the
    moment the stop is planned, and including it would leak the answer into the
    predictor. Returns $ per share, not a percentage.
    """
    symbols = sorted({t["symbol"] for t in trades})
    first = min(t["entry_time"] for t in trades).date()
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=datetime.combine(first - timedelta(days=ADR_LOOKBACK * 3), datetime.min.time(),
                               tzinfo=ET),
        # The free SIP entitlement refuses "recent" data ("subscription does not
        # permit querying recent SIP data"), so the window stops well short of now.
        # Harmless here: ADR20 is only ever read for sessions that already traded.
        end=datetime.now(ET) - timedelta(minutes=30),
        feed=DataFeed.SIP if feed == "sip" else DataFeed.IEX,
    )
    data = getattr(data_client().get_stock_bars(request), "data", None) or {}
    out: dict = {}
    for sym, bars in data.items():
        bars = sorted(bars, key=lambda b: b.timestamp)
        days = [b.timestamp.astimezone(ET).strftime("%Y-%m-%d") for b in bars]
        ranges = [float(b.high) - float(b.low) for b in bars]
        for i, day in enumerate(days):
            prior = ranges[max(0, i - ADR_LOOKBACK):i]
            if prior:
                out[(sym, day)] = sum(prior) / len(prior)
    return out


def windows_by_trade(trades: list[dict], feed: str) -> tuple[dict, dict, int]:
    """trade_id -> (bars entry..15:55, session-close fallback). Fetched per session.

    The window runs past the recorded exit out to the flatten (IMP-030), so a
    candidate that would have held LONGER has real bars to hold through instead
    of falling straight back to the live answer.
    """
    by_day: dict[str, set] = {}
    for t in trades:
        by_day.setdefault(t["entry_time"].strftime("%Y-%m-%d"), set()).add(t["symbol"])

    windows: dict = {}
    fallbacks: dict = {}
    for day, syms in sorted(by_day.items()):
        bars = _minute_bars(sorted(syms), day, feed)
        for t in trades:
            if t["entry_time"].strftime("%Y-%m-%d") != day:
                continue
            series = bars.get(t["symbol"], [])
            entry_hm = t["entry_time"].strftime("%H:%M")
            window = [b for b in series
                      if entry_hm <= b.timestamp.astimezone(ET).strftime("%H:%M")
                      <= config.FLATTEN_ET]
            if window:
                windows[t["trade_id"]] = window
                fallbacks[t["trade_id"]] = float(window[-1].close)
    return windows, fallbacks, len(by_day)


class _BarRow(dict):
    """Adapter so ``exit_sim.simulate_exit`` can walk raw Alpaca bars."""


def _as_frame(bars: list):
    """Minimal iterable of {'high','low'} rows — simulate_exit only needs those."""
    class _Seq:
        def __init__(self, rows): self._rows = rows
        def __len__(self): return len(self._rows)
        def iterrows(self):
            for i, r in enumerate(self._rows):
                yield i, r
    return _Seq([_BarRow(high=float(b.high), low=float(b.low)) for b in bars])


# --- Scoring -----------------------------------------------------------------

def run_policy(policy: Policy, trades: list[dict], windows: dict,
               fallbacks: dict, adr: dict, geometry: ExitGeometry) -> dict:
    rows: list[dict] = []
    skipped = 0
    for t in trades:
        bars = windows.get(t["trade_id"])
        if not bars:
            continue
        entry = float(t["entry_price"])
        live_sd = entry - float(t["stop_price"])
        if live_sd <= 0:
            continue
        day = t["entry_time"].strftime("%Y-%m-%d")
        sd = policy.stop_distance(entry, live_sd, adr.get((t["symbol"], day)))
        if sd is None or sd <= 0:
            skipped += 1
            continue
        dollar_risk = float(t["qty"]) * live_sd
        # The epsilon matters: at scale=1.00, dollar_risk/sd is the share count the
        # bot really traded, and binary float makes 3 * 12.10 / 12.10 == 2.999...,
        # which would silently under-size the FIDELITY BASELINE by one share on
        # every exact-division trade and bias the whole grid against the incumbent.
        qty = int(dollar_risk / sd + 1e-9)
        if qty < 1:
            skipped += 1
            continue
        stop = round(entry - sd, 2)
        tp = round(entry + sd * config.RR_RATIO, 2)
        sim = simulate_exit(_as_frame(bars), entry, stop, tp,
                            float(fallbacks[t["trade_id"]]), geometry)
        # IMP-054's ceiling, recomputed in THIS policy's R. Tightening the stop
        # shrinks the denominator, so the ceiling rises mechanically — that is
        # precisely the claim under test, and printing it beside the WIN count
        # the same replay actually produced is what tests it: a ceiling that
        # crosses +1R without a WIN following is reachability that did not convert.
        ceiling = max(float(b.high) for b in bars)
        row = {
            "trade_id": t["trade_id"], "symbol": t["symbol"], "day": day,
            "entry_price": entry, "stop_price": stop, "exit_price": sim.exit_price,
            "exit_reason": sim.exit_reason, "qty": qty,
            "realized_pl": round((sim.exit_price - entry) * qty, 2),
            "actual_pl": float(t["realized_pl"]),
            "stop_pct": 100.0 * sd / entry,
            "ceiling_r": round((ceiling - entry) / sd, 3),
        }
        row["profit_r"] = doctrine.profit_r(row)
        row["verdict"] = doctrine.classify(row)
        rows.append(row)

    net = sum(r["realized_pl"] for r in rows)
    wins = [r["realized_pl"] for r in rows if r["realized_pl"] > 0]
    losses = [-r["realized_pl"] for r in rows if r["realized_pl"] < 0]
    rs = [r["profit_r"] for r in rows if r["profit_r"] is not None]
    doc = doctrine.summarize(rows)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    return {
        "label": policy.label, "rows": rows, "n": len(rows), "skipped": skipped,
        "net": round(net, 2),
        "expectancy": round(net / len(rows), 2) if rows else 0.0,
        "avg_r": round(sum(rs) / len(rs), 3) if rs else 0.0,
        "payoff": round(avg_win / avg_loss, 2) if avg_loss else None,
        "profit_factor": round(sum(wins) / sum(losses), 2) if losses else None,
        "stop_rate": doc["stop_rate"], "win": doc["win"], "scratch": doc["scratch"],
        "fail": doc["fail"], "true_win_rate": doc["true_win_rate"],
        "reachable": sum(1 for r in rows if r["ceiling_r"] >= doctrine.WIN_MIN_R),
        "converted": sum(1 for r in rows
                         if r["ceiling_r"] >= doctrine.WIN_MIN_R
                         and r["verdict"] == doctrine.WIN),
        "tp_fills": sum(1 for r in rows if r["exit_reason"] == "TAKE_PROFIT"),
        "mean_stop_pct": round(sum(r["stop_pct"] for r in rows) / len(rows), 3) if rows else 0.0,
        "abs_error": round(sum(abs(r["realized_pl"] - r["actual_pl"]) for r in rows), 2),
    }


def _fmt(res: dict, budget: float | None) -> str:
    pf = "  n/a" if res["profit_factor"] is None else f"{res['profit_factor']:5.2f}"
    payoff = " n/a" if res["payoff"] is None else f"{res['payoff']:4.2f}"
    flag = ""
    if budget is not None and abs(res["net"] - res["baseline_net"]) < budget:
        flag = "  <-- inside noise budget, NOT believed"
    conv = (100.0 * res["converted"] / res["reachable"]) if res["reachable"] else 0.0
    return (f"  {res['label']:12} n={res['n']:3d} stop%={res['mean_stop_pct']:5.2f} "
            f"net={res['net']:9.2f} exp={res['expectancy']:7.2f} avgR={res['avg_r']:+6.3f} "
            f"payoff={payoff} PF={pf} stopRate={res['stop_rate']:5.1f}% "
            f"W/S/F={res['win']:2d}/{res['scratch']:2d}/{res['fail']:2d} "
            f"trueWR={res['true_win_rate']:5.1f}% TP={res['tp_fills']:2d} "
            f"reach={res['reachable']:3d} conv={res['converted']:2d} ({conv:4.1f}%){flag}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default=POST_GATE_START)
    parser.add_argument("--feed", default="sip", choices=("sip", "iex"))
    parser.add_argument("--detail", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    trades = load_trades(args.since)
    if not trades:
        print(f"no closed trades since {args.since}")
        return 0

    windows, fallbacks, sessions = windows_by_trade(trades, args.feed)
    adr = adr20_by_symbol_day(trades, args.feed)
    geometry = ExitGeometry.from_config()

    results = [run_policy(p, trades, windows, fallbacks, adr, geometry)
               for p in build_policies()]
    baseline = next(r for r in results if r["label"] == "scale=1.00")
    for r in results:
        r["baseline_net"] = baseline["net"]
    budget = baseline["abs_error"]

    actual_net = round(sum(float(t["realized_pl"]) for t in trades
                           if t["trade_id"] in windows), 2)

    print("=" * 108)
    print("STOP-WIDTH WHAT-IF — is 1R the wrong SIZE?  (IMP-055)")
    print(f"  trades={len(trades)}  replayed={baseline['n']}  sessions={sessions}  "
          f"since {args.since}  feed={args.feed}")
    print(f"  ratchet held at the live geometry: {geometry.label()}")
    print(f"  dollar risk per trade held CONSTANT; qty re-derived; TP re-anchored at "
          f"{config.RR_RATIO:g}R")
    print("=" * 108)
    print(f"\n  fidelity: actual ${actual_net:+,.2f} vs scale=1.00 sim "
          f"${baseline['net']:+,.2f}  sum|error| ${budget:,.2f}  <-- NOISE BUDGET")
    print("  a candidate's |net - baseline net| must clear that budget to mean anything.\n")

    for r in results:
        print(_fmt(r, budget))

    print("\n  read: expectancy and payoff FIRST, stop rate second (stop doctrine).")
    print("  a tightening raises the stop rate mechanically — that is not a defect,")
    print("  and a lower stop rate would not by itself justify anything.")
    print("  reach/conv is the hypothesis under test: 'reach' counts trades whose")
    print(f"  IMP-054 ceiling clears +{doctrine.WIN_MIN_R:g}R once the stop is tightened —")
    print("  'conv' counts how many of those the same replay actually turned into a")
    print("  doctrine WIN. A widening reach with a flat conv is arithmetic, not edge.")

    if args.detail:
        best = max((r for r in results if r["label"] != "scale=1.00"),
                   key=lambda r: r["expectancy"])
        by_id = {r["trade_id"]: r for r in best["rows"]}
        print(f"\n  per-trade, live vs {best['label']} (worst live first)")
        for r in sorted(baseline["rows"], key=lambda x: x["actual_pl"]):
            cand = by_id.get(r["trade_id"])
            if cand is None:
                continue
            print(f"    #{r['trade_id']:<4} {r['day']} {r['symbol']:<5} "
                  f"live ${r['actual_pl']:>8.2f} {r['verdict']:<7} -> "
                  f"cand ${cand['realized_pl']:>8.2f} {cand['verdict']:<7} "
                  f"{cand['exit_reason']:<12} stop%={cand['stop_pct']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
