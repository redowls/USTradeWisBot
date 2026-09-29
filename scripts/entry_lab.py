"""CLI: walk-forward backtest gate for candidate ENTRY rules (option-B rebuild).

  python -m scripts.entry_lab --start 2026-03-02 --end 2026-09-17
  python -m scripts.entry_lab --symbols AAPL,MSFT --slippage 0.03 --out /tmp/lab.json
  python -m scripts.entry_lab --incumbent            # also run the (slow) live-entry baseline
  python -m scripts.entry_lab --cache /tmp/bars.pkl  # reuse fetched bars between runs

Fetches SIP (consolidated) 5-min RTH bars for the active watchlist plus SPY,
splits the sessions chronologically (first 65% in-sample, rest held-out),
selects each rule's parameters on the in-sample window ONLY, then scores the
chosen set once on the held-out window and prints the gate verdict. Nothing in
here touches the live path, the database, or the service.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time as _time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from alpaca.data.enums import DataFeed
from alpaca.data.requests import StockBarsRequest

from bot import config, data, db, entry_lab

DEFAULT_SLIPPAGE_PCT = 0.03      # per market fill; megacap 5-min close-to-fill, conservative
DEFAULT_EQUITY = 7_500.0         # current paper equity; R-metrics are size-independent


def _arg(argv: list[str], flag: str, default: str) -> str:
    return argv[argv.index(flag) + 1] if flag in argv else default


def fetch_bars(symbols: list[str], start: date, end: date, feed: str = "sip") -> dict[str, pd.DataFrame]:
    """RTH 5-min bars, ET-indexed, oldest→newest, one frame per symbol."""
    tf = data.parse_timeframe(config.BAR_TIMEFRAME)
    req = StockBarsRequest(
        symbol_or_symbols=symbols, timeframe=tf,
        start=datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
        end=datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
        feed=DataFeed(feed),
    )
    raw = data.data_client().get_stock_bars(req).df
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        if raw is None or raw.empty or sym not in raw.index.get_level_values(0):
            out[sym] = pd.DataFrame(columns=data.OHLCV_COLUMNS)
            continue
        sdf = raw.xs(sym, level=0)
        sdf = data._to_et(sdf[[c for c in data.OHLCV_COLUMNS if c in sdf.columns]]).sort_index()
        out[sym] = data._filter_rth(sdf)
    return out


#: Marker key written beside the bars so a cache states which feed and window it
#: holds. Prefixed with a character no ticker uses, so it can never collide with
#: a symbol in the same dict (and an old, unmarked cache is simply treated as a
#: miss rather than misread).
CACHE_META_KEY = "__meta__"


def cache_matches(cached: dict, symbols: list[str], start: date, end: date, feed: str) -> bool:
    """Is ``cached`` usable for this request?

    **Why this guard exists (IMP-065).** The original check was
    ``set(symbols) <= set(cached)`` — the symbol set and nothing else. A cache
    built on SIP bars was therefore served, silently, to a run asking for IEX,
    and a cache built over a 3-week window was served to a run asking for 12
    months. Both produce a lab verdict about data the caller did not request, and
    the feed case is not hypothetical: the 2026-09-28 run found that the ``tod``
    volume gate clears the walk-forward gate on SIP and FAILS it on IEX, so which
    feed a cache holds decides the verdict.

    Unmarked (pre-IMP-065) caches return False: refetching is cheap, and a
    verdict from unknown bars is not.
    """
    meta = cached.get(CACHE_META_KEY)
    if not isinstance(meta, dict):
        return False
    if str(meta.get("feed")) != str(feed):
        return False
    if str(meta.get("start")) != str(start) or str(meta.get("end")) != str(end):
        return False
    return set(symbols) <= (set(cached) - {CACHE_META_KEY})


def load_or_fetch(symbols: list[str], start: date, end: date, feed: str, cache: str) -> dict[str, pd.DataFrame]:
    if cache and os.path.exists(cache):
        with open(cache, "rb") as fh:
            cached = pickle.load(fh)
        if cache_matches(cached, symbols, start, end, feed):
            return {s: cached[s] for s in symbols}
    bars = fetch_bars(symbols, start, end, feed)
    if cache:
        with open(cache, "wb") as fh:
            pickle.dump({**bars, CACHE_META_KEY: {
                "feed": str(feed), "start": str(start), "end": str(end),
            }}, fh)
    return bars


def resolve_feed(argv: list[str]) -> tuple[str, str | None]:
    """The feed to measure on, plus a warning when it is not the bot's own feed.

    **Defaults to ``config.DATA_FEED`` — the feed the LIVE bot trades on (IMP-065).**
    It used to default to ``"sip"``, which meant IMP-059's walk-forward gate and
    IMP-063's 64-cell grid both judged entry configurations on consolidated bars
    while the running bot saw IEX. Those are not the same measurement: on SIP the
    time-of-day volume gate cleared the gate at +0.100R/PF 1.42, and on IEX over
    the same 251 sessions it FAILED at +0.019R/PF 1.04. A gate that authorises
    live entry changes has to be computed on the bars the entry will actually see.
    """
    feed = _arg(argv, "--feed", str(config.DATA_FEED)).lower()
    live = str(config.DATA_FEED).lower()
    if feed != live:
        return feed, (f"feed={feed} is NOT the live bot's feed ({live}) — this run's "
                      f"numbers do not describe what the bot would have seen; "
                      f"do not ship an entry change on them")
    return feed, None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    end = date.fromisoformat(_arg(argv, "--end", str(date.today() - timedelta(days=1))))
    start = date.fromisoformat(_arg(argv, "--start", str(end - timedelta(days=200))))
    slippage = float(_arg(argv, "--slippage", str(DEFAULT_SLIPPAGE_PCT)))
    equity = float(_arg(argv, "--equity", str(DEFAULT_EQUITY)))
    feed, feed_warning = resolve_feed(argv)
    cache = _arg(argv, "--cache", "")
    out = _arg(argv, "--out", "")
    syms_arg = _arg(argv, "--symbols", "")
    if feed_warning:
        print(f"⚠️  {feed_warning}")
    rules_arg = _arg(argv, "--rules", ",".join(entry_lab.RULES))
    run_incumbent = "--incumbent" in argv
    # Exit-geometry sensitivity (lab only — the live config is untouched). Lets the
    # same rules be judged under the pre-IMP-040 ratchet (--be 0.5 --trail 1.0 --trail-dist 1.0)
    # or with the ratchet off (--no-trail) so an entry is not condemned by one exit setting.
    if "--be" in argv:
        config.BREAKEVEN_TRIGGER_R = float(_arg(argv, "--be", str(config.BREAKEVEN_TRIGGER_R)))
    if "--trail" in argv:
        config.TRAIL_TRIGGER_R = float(_arg(argv, "--trail", str(config.TRAIL_TRIGGER_R)))
    if "--trail-dist" in argv:
        config.TRAIL_DISTANCE_R = float(_arg(argv, "--trail-dist", str(config.TRAIL_DISTANCE_R)))
    if "--no-trail" in argv:
        config.TRAILING_STOP_ENABLED = False
    if "--rr" in argv:
        config.RR_RATIO = float(_arg(argv, "--rr", str(config.RR_RATIO)))
    only_incumbent = "--only-incumbent" in argv

    symbols = [s.strip().upper() for s in syms_arg.split(",") if s.strip()] or \
        [w["symbol"] for w in db.get_active_watchlist()]
    universe = sorted(set(symbols) | {"SPY"})

    t0 = _time.time()
    print(f"Fetching {config.BAR_TIMEFRAME} {feed.upper()} bars {start}..{end} for {len(universe)} symbols…", flush=True)
    bars = load_or_fetch(universe, start, end, feed, cache)
    sessions = sorted({ts.date() for ts in bars["SPY"].index if start <= ts.date() <= end})
    is_days, oos_days = entry_lab.split_sessions(sessions)
    print(f"Exit geometry: BE {config.BREAKEVEN_TRIGGER_R}R, trail {config.TRAIL_TRIGGER_R}R/{config.TRAIL_DISTANCE_R}R "
          f"(trailing={config.TRAILING_STOP_ENABLED}), RR {config.RR_RATIO}, stop max({config.ATR_STOP_MULT}xATR, {config.MIN_STOP_PCT}%)")
    print(f"Sessions: {len(sessions)}  in-sample {is_days[0]}..{is_days[-1]} ({len(is_days)})  "
          f"held-out {oos_days[0]}..{oos_days[-1]} ({len(oos_days)})   [{_time.time() - t0:.0f}s]", flush=True)

    feats = {s: entry_lab.precompute_features(bars[s]) for s in symbols if not bars[s].empty}
    mkt = entry_lab.market_ok(entry_lab.precompute_features(bars["SPY"]))

    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "symbols": symbols,
        "window": f"{sessions[0]}..{sessions[-1]}", "sessions": len(sessions),
        "in_sample": [str(is_days[0]), str(is_days[-1]), len(is_days)],
        "held_out": [str(oos_days[0]), str(oos_days[-1]), len(oos_days)],
        "slippage_pct": slippage, "equity": equity, "feed": feed, "rules": {},
        "exit_geometry": {"breakeven_r": config.BREAKEVEN_TRIGGER_R, "trail_trigger_r": config.TRAIL_TRIGGER_R,
                          "trail_distance_r": config.TRAIL_DISTANCE_R, "trailing": config.TRAILING_STOP_ENABLED,
                          "rr_ratio": config.RR_RATIO, "atr_stop_mult": config.ATR_STOP_MULT,
                          "min_stop_pct": config.MIN_STOP_PCT},
    }

    incumbent_oos = None
    if run_incumbent or only_incumbent:
        print("\nIncumbent (live MA entry + VWAP gate) — this is the slow one…", flush=True)
        t1 = _time.time()
        inc_is = entry_lab.doctrine_metrics(entry_lab.incumbent_trades({s: bars[s] for s in symbols}, is_days, equity, slippage))
        inc_oos_trades = entry_lab.incumbent_trades({s: bars[s] for s in symbols}, oos_days, equity, slippage)
        incumbent_oos = entry_lab.doctrine_metrics(inc_oos_trades)
        result["rules"]["incumbent"] = {"is": inc_is, "oos": incumbent_oos,
                                        "oos_trades": [t.to_dict() for t in inc_oos_trades]}
        print(entry_lab.metrics_header())
        print(entry_lab.format_metrics_row("incumbent / in-sample", inc_is))
        print(entry_lab.format_metrics_row("incumbent / held-out", incumbent_oos))
        print(f"[{_time.time() - t1:.0f}s]", flush=True)

    if not only_incumbent:
        print("\n" + entry_lab.metrics_header())
        for name in [r.strip() for r in rules_arg.split(",") if r.strip()]:
            fn, grid = entry_lab.RULES[name]
            t1 = _time.time()
            best, is_m, rows = entry_lab.select_in_sample(name, fn, grid, feats, is_days, equity, slippage, mkt)
            entry: dict = {"grid_size": len(rows), "grid": rows}
            if best is None:
                print(f"{name:<26} no parameter set reached {entry_lab.MIN_TRADES_IS} in-sample trades with PF > 1")
                entry.update({"selected": None, "gate": [False, ["no qualifying in-sample parameter set"]]})
            else:
                oos_trades = entry_lab.run_rule(name, fn, best, feats, oos_days, equity, slippage, mkt)
                oos_m = entry_lab.doctrine_metrics(oos_trades)
                ok, why = entry_lab.gate(oos_m, is_m, incumbent_oos)
                print(entry_lab.format_metrics_row(f"{name} / in-sample", is_m))
                print(entry_lab.format_metrics_row(f"{name} / held-out", oos_m))
                print(f"{'':<26}params {best}")
                print(f"{'':<26}GATE: {'PASS' if ok else 'FAIL — ' + '; '.join(why)}")
                entry.update({"selected": best, "is": is_m, "oos": oos_m, "gate": [ok, why],
                              "oos_trades": [t.to_dict() for t in oos_trades]})
            print(f"{'':<26}[{_time.time() - t1:.0f}s, {len(rows)} parameter sets]", flush=True)
            result["rules"][name] = entry

    if out:
        with open(out, "w") as fh:
            json.dump(result, fh, indent=1, default=str)
        print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
