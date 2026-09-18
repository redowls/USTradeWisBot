"""Entry-hypothesis lab — the backtest gate for the option-B entry rebuild (2026-09-18).

Why this exists. The incumbent entry — a 5-min EMA-stack ("MA") crossover, which
is all that has fired since IMP-021's fade veto silenced the breakout leg on
2026-07-25 — was measured win-infeasible FROM THE FILL on 83.5% of the post-gate
book (IMP-054), IMP-055 refuted the one stop-geometry change that remained, and
the weekly verdict has read "no demonstrated edge" for six consecutive weeks.
The user chose to rebuild the ENTRY and keep the exit, risk and reliability
layers, with the rule that nothing reaches the live path until a backtest shows
positive expectancy OUT OF SAMPLE.

This module is that gate. It evaluates candidate entry rules over historical
5-min bars with the LIVE exit and sizing stack held fixed, scores every trade
with the stop-exit doctrine (WIN / SCRATCH / FAIL, expectancy in R, payoff), and
applies a walk-forward split: parameters are chosen on the in-sample sessions
only, then judged once on the held-out sessions. NOTHING here is imported by the
live path.

Held fixed (the layers IMP-054 exonerated):
  * ``sizing.plan_position``   — stop = max(ATR_STOP_MULT×ATR, MIN_STOP_PCT), TP = RR_RATIO×1R,
                                  risk fraction from CONFIDENCE_RISK_TABLE (flat 0.5%).
  * ``backtest.simulate_exit`` — stop-before-target inside a bar, the IMP-013/040
                                  break-even→trail ratchet on the bar high, 15:55 flatten.
  * MAX_ENTRIES_PER_SYMBOL_PER_DAY, REENTRY_COOLDOWN_MIN, MAX_CONCURRENT_POSITIONS.
  * Entry window: never the 09:30 bar, nothing at/after ENTRY_CUTOFF_ET (15:30).
  * IMP-050 fill anchoring: the stop sits ``stop_distance`` below the REAL fill.

Deliberately conservative: slippage is charged on every market fill (entry,
stop, flatten — not the take-profit limit), and a candidate must beat the gate
on the held-out window, not the window its parameters were read off.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from . import backtest, config, indicators, sizing

# Confidence handed to sizing.plan_position for lab trades. The live risk ladder
# is flat (every row of CONFIDENCE_RISK_TABLE is 0.5%), so this only has to clear
# MIN_CONFIDENCE; the new rules carry no confidence blend of their own.
LAB_CONFIDENCE = 70.0
ENTRY_CUTOFF = time(15, 30)          # exits.past_entry_cutoff — no new entries at/after
RTH_CLOSE = time(16, 0)
MIN_TRADES_IS = 30                   # a parameter set needs this many in-sample trades to be chosen
MIN_TRADES_OOS = 30                  # and this many held-out trades to be judged at all
GATE_MIN_PF = 1.2                    # held-out profit factor floor
IS_FRACTION = 0.65                   # first 65% of sessions = in-sample, rest = held-out


@dataclass
class LabTrade:
    rule: str
    symbol: str
    day: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float                # REAL (slipped) fill
    stop_price: float                 # fill-anchored original 1R stop (IMP-050)
    take_profit_price: float
    exit_price: float
    shares: int
    exit_reason: str
    pl: float
    profit_r: float                   # (exit - fill) / 1R  — the doctrine's unit

    @property
    def win(self) -> bool:
        return self.pl > 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["entry_time"] = self.entry_time.isoformat()
        d["exit_time"] = self.exit_time.isoformat()
        return d


# --- Features ---------------------------------------------------------------

def precompute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Full-series feature frame for one symbol's RTH 5-min bars (ET index).

    Everything a rule may test, computed once, vectorised:
      ema_8/20/55, atr (Wilder 14), vwap (session-reset), rel_vol (live def.),
      day, bar_idx (0 = the 09:30 bar), sess_high_prev (running session high
      BEFORE this bar), sess_open, pdh/pdl (prior session high/low),
      or{3,6}_high/low (opening range of the first 3 / 6 bars = 15 / 30 min).
    """
    out = df.copy()
    out["ema_8"] = indicators.ema(df["close"], 8)
    out["ema_20"] = indicators.ema(df["close"], 20)
    out["ema_55"] = indicators.ema(df["close"], 55)
    out["atr"] = indicators.atr(df)
    out["vwap"] = indicators.session_vwap(df)
    out["rel_vol"] = indicators.relative_volume(df["volume"])
    day = df.index.normalize()
    out["day"] = day
    g = out.groupby(day, sort=False)
    out["bar_idx"] = g.cumcount()
    out["sess_high_prev"] = g["high"].transform(lambda s: s.cummax().shift(1))
    out["sess_open"] = g["open"].transform("first")
    for k in (3, 6):
        out[f"or{k}_high"] = g["high"].transform(lambda s, k=k: s.iloc[:k].max())
        out[f"or{k}_low"] = g["low"].transform(lambda s, k=k: s.iloc[:k].min())
    daily_high = g["high"].max().sort_index()
    daily_low = g["low"].min().sort_index()
    pdh = daily_high.shift(1).to_dict()
    pdl = daily_low.shift(1).to_dict()
    out["pdh"] = [pdh.get(d, np.nan) for d in day]
    out["pdl"] = [pdl.get(d, np.nan) for d in day]
    return out


def _time_le(f: pd.DataFrame, hhmm: str) -> pd.Series:
    hh, mm = (int(x) for x in hhmm.split(":"))
    cutoff = time(hh, mm)
    return pd.Series([t <= cutoff for t in f.index.time], index=f.index)


def _common(f: pd.DataFrame, p: dict, cond: pd.Series) -> pd.Series:
    """Gates every rule shares: relative-volume floor, above-VWAP, time cutoff."""
    if p.get("min_relvol"):
        cond = cond & (f["rel_vol"] >= p["min_relvol"])
    if p.get("above_vwap", True):
        cond = cond & (f["close"] > f["vwap"])
    if p.get("cutoff"):
        cond = cond & _time_le(f, p["cutoff"])
    return cond.fillna(False).astype(bool)


# --- Candidate entry rules (vectorised triggers) ----------------------------
# Each returns a boolean Series aligned to ``f``: True on a bar whose CLOSE is a
# candidate entry. The walker applies the window, caps, cooldown and exits.

def rule_orb(f: pd.DataFrame, p: dict) -> pd.Series:
    """Opening-range breakout: first close above the first-``k``-bars high.

    ``fresh`` = the prior bar's close was still at/below the range high, so a
    session triggers once per break, never on every bar that sits above it.
    """
    k = int(p.get("k", 6))
    oh = f[f"or{k}_high"]
    buf = 1.0 + float(p.get("buffer_pct", 0.0)) / 100.0
    fresh = (f["close"] > oh * buf) & (f["close"].shift(1) <= oh)
    cond = fresh & (f["bar_idx"] >= k)
    return _common(f, p, cond)


def rule_pdh(f: pd.DataFrame, p: dict) -> pd.Series:
    """Prior-day-high breakout: first close above yesterday's high (no gap chase).

    A session that OPENS above the level never triggers (bar 0's close is
    already above it, so no later bar can cross), which is the point — buying a
    gap is not buying a breakout.
    """
    pdh = f["pdh"]
    buf = 1.0 + float(p.get("buffer_pct", 0.0)) / 100.0
    fresh = (f["close"] > pdh * buf) & (f["close"].shift(1) <= pdh)
    cond = fresh & (f["bar_idx"] >= 1) & pdh.notna()
    return _common(f, p, cond)


def rule_session_high(f: pd.DataFrame, p: dict) -> pd.Series:
    """Consolidation-then-new-session-high: close above the running session high
    after that high has stood unchanged for ``consol_bars`` bars (a base), not
    before ``min_bar_idx`` (skip the open's noise).
    """
    n = int(p.get("consol_bars", 6))
    shp = f["sess_high_prev"]
    new_high = f["close"] > shp
    based = shp == shp.shift(n)
    first_ok = max(int(p.get("min_bar_idx", 6)), n + 1)
    cond = new_high & based & (f["bar_idx"] >= first_ok)
    return _common(f, p, cond)


def rule_vwap_reclaim(f: pd.DataFrame, p: dict) -> pd.Series:
    """Pullback-to-VWAP in an up-session, then momentum resumes.

    Context: VWAP rising over the last 6 bars and EMA20 > EMA55. Setup: within
    the prior ``lookback`` bars a low touched VWAP (within ``touch_pct`` above it
    or below). Trigger: this bar closes above VWAP AND crosses back above EMA8
    (prior close at/below EMA8) — one event per pullback, not every bar after.
    """
    touch = 1.0 + float(p.get("touch_pct", 0.1)) / 100.0
    lb = int(p.get("lookback", 6))
    touched = (f["low"] <= f["vwap"] * touch).astype(float)
    touched_recent = touched.shift(1).rolling(lb, min_periods=1).max() >= 1.0
    cross_up = (f["close"] > f["ema_8"]) & (f["close"].shift(1) <= f["ema_8"].shift(1))
    context = (f["vwap"] > f["vwap"].shift(6)) & (f["ema_20"] > f["ema_55"])
    cond = touched_recent & cross_up & context & (f["bar_idx"] >= lb)
    p = {**p, "above_vwap": True}
    return _common(f, p, cond)


RULES: dict[str, tuple] = {
    # name: (trigger_fn, parameter grid searched IN-SAMPLE only)
    "orb": (rule_orb, {
        "k": [3, 6], "cutoff": ["11:30", "13:00"], "min_relvol": [0.0, 1.3],
        "buffer_pct": [0.0, 0.1], "above_vwap": [True], "mkt": [False, True],
    }),
    "pdh": (rule_pdh, {
        "cutoff": ["12:00", "15:00"], "min_relvol": [0.0, 1.3], "buffer_pct": [0.0, 0.1],
        "above_vwap": [True], "mkt": [False, True],
    }),
    "session_high": (rule_session_high, {
        "consol_bars": [6, 12], "min_bar_idx": [6, 12], "cutoff": ["13:00", "15:00"],
        "min_relvol": [0.0, 1.3], "above_vwap": [True], "mkt": [False, True],
    }),
    "vwap_reclaim": (rule_vwap_reclaim, {
        "touch_pct": [0.1, 0.25], "lookback": [6, 12], "cutoff": ["14:00"],
        "min_relvol": [0.0], "mkt": [False, True],
    }),
}


def market_ok(spy_features: pd.DataFrame) -> pd.Series:
    """Index-regime overlay: SPY closing above its own session VWAP."""
    return (spy_features["close"] > spy_features["vwap"]).fillna(False)


# --- Walker: triggers -> trades with the LIVE exit / sizing stack -----------

def walk_symbol(
    rule: str,
    symbol: str,
    f: pd.DataFrame,
    trigger: pd.Series,
    sessions: set[date],
    equity: float,
    slippage_pct: float = 0.0,
) -> list[LabTrade]:
    """Every trade ``rule`` would have taken on ``symbol`` over ``sessions``."""
    trades: list[LabTrade] = []
    trig = trigger.to_numpy(dtype=bool)
    closes = f["close"].to_numpy(dtype=float)
    atrs = f["atr"].to_numpy(dtype=float)
    bar_idx = f["bar_idx"].to_numpy()
    index = f.index
    slip = slippage_pct / 100.0
    for day_ts, pos in f.groupby("day", sort=True).indices.items():
        if pd.Timestamp(day_ts).date() not in sessions:
            continue
        pos = np.sort(pos)
        day_bars = f.iloc[pos][["low", "high", "close"]]
        day_times = day_bars.index
        eod_close = float(closes[pos[-1]])
        entries = 0
        cooldown_until: datetime | None = None
        i = 0
        while i < len(pos):
            if entries >= config.MAX_ENTRIES_PER_SYMBOL_PER_DAY:
                break
            row = pos[i]
            ts = index[row]
            if ts.time() >= ENTRY_CUTOFF:
                break
            if bar_idx[row] < 1 or not trig[row] or (cooldown_until is not None and ts < cooldown_until):
                i += 1
                continue
            close, atr = closes[row], atrs[row]
            if not (math.isfinite(close) and math.isfinite(atr)) or atr <= 0 or close <= 0:
                i += 1
                continue
            plan = sizing.plan_position(
                symbol, LAB_CONFIDENCE, close, atr, equity, equity * 2.0,
                held_symbols=set(), open_positions_count=0,
            )
            if not plan.tradable:
                i += 1
                continue
            fill = round(close * (1.0 + slip), 4)
            dist = plan.stop_distance
            stop = round(fill - dist, 4)               # IMP-050 fill-anchored 1R
            tp = plan.take_profit_price                 # limit leg stays on the plan
            after = day_bars[(day_times > ts) & (day_times.time < RTH_CLOSE)]
            exit_price, reason, exit_ts = backtest.simulate_exit(after, fill, stop, tp, eod_close)
            if reason != "TAKE_PROFIT":
                exit_price = exit_price * (1.0 - slip)  # market fills pay the slip too
            exit_price = round(exit_price, 4)
            exit_ts = exit_ts or ts
            pl = round((exit_price - fill) * plan.shares, 2)
            trades.append(LabTrade(
                rule=rule, symbol=symbol, day=str(ts.date()), entry_time=ts, exit_time=exit_ts,
                entry_price=fill, stop_price=stop, take_profit_price=round(tp, 4),
                exit_price=exit_price, shares=plan.shares, exit_reason=reason, pl=pl,
                profit_r=round((exit_price - fill) / dist, 4),
            ))
            entries += 1
            cooldown_until = exit_ts + timedelta(minutes=config.REENTRY_COOLDOWN_MIN)
            j = i + 1
            while j < len(pos) and index[pos[j]] <= exit_ts:
                j += 1
            i = j
    return trades


def run_rule(
    rule: str,
    trigger_fn,
    params: dict,
    feats: dict[str, pd.DataFrame],
    sessions: list[date] | set[date],
    equity: float,
    slippage_pct: float = 0.0,
    mkt: pd.Series | None = None,
) -> list[LabTrade]:
    """All symbols, one parameter set, MAX_CONCURRENT applied across symbols."""
    sessions = set(sessions)
    raw: list[LabTrade] = []
    for sym, f in feats.items():
        trig = trigger_fn(f, params)
        if params.get("mkt") and mkt is not None:
            trig = trig & mkt.reindex(f.index).fillna(False).astype(bool)
        raw.extend(walk_symbol(rule, sym, f, trig, sessions, equity, slippage_pct))
    return backtest.apply_concurrency(raw, config.MAX_CONCURRENT_POSITIONS)


# --- Doctrine scoring --------------------------------------------------------

def doctrine_bucket(exit_reason: str, profit_r: float) -> str:
    """The stop-exit doctrine (user directive 2026-09-01), in R.

    WIN     = TAKE_PROFIT fill, or any exit at/above +1R.
    SCRATCH = STOP exit with +0.25R < R < +1R, or a flatten between -0.25R and +1R.
    FAIL    = everything else (full-1R stop, break-even stop, faded flatten).
    """
    if exit_reason == "TAKE_PROFIT" or profit_r >= 1.0:
        return "WIN"
    if exit_reason == "STOP":
        return "SCRATCH" if profit_r > 0.25 else "FAIL"
    return "SCRATCH" if profit_r >= -0.25 else "FAIL"


def doctrine_metrics(trades: list[LabTrade]) -> dict:
    """Expectancy (R), payoff, PF, true win rate, stop rate, buckets, max drawdown."""
    n = len(trades)
    if n == 0:
        return {"n": 0, "net": 0.0, "pf": 0.0, "exp_r": 0.0, "payoff": 0.0, "true_wr": 0.0,
                "headline_wr": 0.0, "stop_rate": 0.0, "win": 0, "scratch": 0, "fail": 0,
                "tp_fills": 0, "max_dd": 0.0, "t_stat": 0.0, "sessions": 0, "avg_r_win": 0.0,
                "avg_r_loss": 0.0}
    pls = np.array([t.pl for t in trades], dtype=float)
    rs = np.array([t.profit_r for t in trades], dtype=float)
    buckets = [doctrine_bucket(t.exit_reason, t.profit_r) for t in trades]
    gross_win = float(pls[pls > 0].sum())
    gross_loss = float(pls[pls <= 0].sum())
    winners, losers = pls[pls > 0], pls[pls <= 0]
    avg_w = float(winners.mean()) if len(winners) else 0.0
    avg_l = float(losers.mean()) if len(losers) else 0.0
    ordered = sorted(trades, key=lambda t: t.exit_time)
    cum = np.cumsum([t.pl for t in ordered])
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    max_dd = float((cum - peak).min()) if n else 0.0
    std_r = float(rs.std(ddof=1)) if n > 1 else 0.0
    return {
        "n": n,
        "net": round(float(pls.sum()), 2),
        "pf": round(gross_win / abs(gross_loss), 2) if gross_loss < 0 else (99.0 if gross_win > 0 else 0.0),
        "exp_r": round(float(rs.mean()), 4),
        "avg_r_win": round(float(rs[rs > 0].mean()), 3) if (rs > 0).any() else 0.0,
        "avg_r_loss": round(float(rs[rs <= 0].mean()), 3) if (rs <= 0).any() else 0.0,
        "payoff": round(avg_w / abs(avg_l), 2) if avg_l < 0 else 0.0,
        "true_wr": round(100.0 * buckets.count("WIN") / n, 1),
        "headline_wr": round(100.0 * int((pls > 0).sum()) / n, 1),
        "stop_rate": round(100.0 * sum(t.exit_reason == "STOP" for t in trades) / n, 1),
        "win": buckets.count("WIN"),
        "scratch": buckets.count("SCRATCH"),
        "fail": buckets.count("FAIL"),
        "tp_fills": sum(t.exit_reason == "TAKE_PROFIT" for t in trades),
        "max_dd": round(max_dd, 2),
        "t_stat": round(float(rs.mean()) / (std_r / math.sqrt(n)), 2) if std_r > 0 else 0.0,
        "sessions": len({t.day for t in trades}),
    }


# --- Walk-forward selection and the gate ------------------------------------

def split_sessions(sessions: list[date], is_fraction: float = IS_FRACTION) -> tuple[list[date], list[date]]:
    """Chronological, disjoint in-sample / held-out session lists."""
    s = sorted(set(sessions))
    cut = int(round(len(s) * is_fraction))
    cut = min(max(cut, 1), max(len(s) - 1, 1))
    return s[:cut], s[cut:]


def param_grid(grid: dict[str, list]) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(grid[k] for k in keys))]


def select_in_sample(
    rule: str, trigger_fn, grid: dict[str, list], feats: dict[str, pd.DataFrame],
    is_days: list[date], equity: float, slippage_pct: float, mkt: pd.Series | None,
) -> tuple[dict | None, dict | None, list[dict]]:
    """Score every parameter set on the in-sample sessions; return the winner.

    Winner = highest expectancy (R) among sets with >= MIN_TRADES_IS trades and
    PF > 1; ties broken by t-stat. None when nothing qualifies. The full table is
    returned so the report can show how peaked (curve-fit) the surface is.
    """
    rows: list[dict] = []
    best: tuple[dict, dict] | None = None
    for params in param_grid(grid):
        m = doctrine_metrics(run_rule(rule, trigger_fn, params, feats, is_days, equity, slippage_pct, mkt))
        rows.append({"params": params, **m})
        if m["n"] >= MIN_TRADES_IS and m["pf"] > 1.0:
            if best is None or (m["exp_r"], m["t_stat"]) > (best[1]["exp_r"], best[1]["t_stat"]):
                best = (params, m)
    if best is None:
        return None, None, rows
    return best[0], best[1], rows


def gate(oos: dict, is_metrics: dict | None = None, incumbent_oos: dict | None = None) -> tuple[bool, list[str]]:
    """Ship/no-ship. Every reason is returned so a refusal is legible."""
    reasons: list[str] = []
    if oos["n"] < MIN_TRADES_OOS:
        reasons.append(f"held-out n={oos['n']} < {MIN_TRADES_OOS}")
    if oos["exp_r"] <= 0:
        reasons.append(f"held-out expectancy {oos['exp_r']:+.3f}R <= 0")
    if oos["pf"] < GATE_MIN_PF:
        reasons.append(f"held-out PF {oos['pf']} < {GATE_MIN_PF}")
    if is_metrics is not None and is_metrics["exp_r"] <= 0:
        reasons.append(f"in-sample expectancy {is_metrics['exp_r']:+.3f}R <= 0")
    if incumbent_oos is not None and incumbent_oos["n"] > 0 and oos["exp_r"] <= incumbent_oos["exp_r"]:
        reasons.append(f"does not beat incumbent held-out expectancy {incumbent_oos['exp_r']:+.3f}R")
    return (not reasons), reasons


# --- Incumbent baseline (the real signal stack, via bot.backtest) -----------

def incumbent_trades(
    all_bars: dict[str, pd.DataFrame], sessions: list[date] | set[date], equity: float,
    slippage_pct: float = 0.0,
) -> list[LabTrade]:
    """The LIVE entry (signals.evaluate → confidence → VWAP gate) over ``sessions``.

    Slow (~15 ms per bar per symbol: the real indicator + level stack runs at
    every bar). Slippage is charged post-hoc exactly as the walker charges it:
    entry fill and every market exit move against us by ``slippage_pct``.
    """
    def _vwap_gate(features: dict) -> bool:
        d = features.get("vwap_dist_pct")
        return d is None or d <= config.VWAP_MAX_DIST_PCT

    slip = slippage_pct / 100.0
    raw: list[LabTrade] = []
    for sym, bars in all_bars.items():
        if bars is None or bars.empty:
            continue
        days_here = sorted({ts.date() for ts in bars.index} & set(sessions))
        for d in days_here:
            for t in backtest.symbol_trades_for_day(sym, bars, d, equity, entry_filter=_vwap_gate):
                if t.stop_price is None:
                    continue
                dist = t.entry_price - t.stop_price
                if dist <= 0:
                    continue
                fill = round(t.entry_price * (1.0 + slip), 4)
                exit_px = t.exit_price if t.exit_reason == "TAKE_PROFIT" else round(t.exit_price * (1.0 - slip), 4)
                raw.append(LabTrade(
                    rule="incumbent", symbol=sym, day=t.day, entry_time=t.entry_time,
                    exit_time=t.exit_time, entry_price=fill, stop_price=round(fill - dist, 4),
                    take_profit_price=round(t.take_profit_price or 0.0, 4), exit_price=exit_px,
                    shares=t.shares, exit_reason=t.exit_reason,
                    pl=round((exit_px - fill) * t.shares, 2), profit_r=round((exit_px - fill) / dist, 4),
                ))
    return backtest.apply_concurrency(raw, config.MAX_CONCURRENT_POSITIONS)


# --- Report -------------------------------------------------------------------

def format_metrics_row(label: str, m: dict) -> str:
    return (f"{label:<26}{m['n']:>5}{m['net']:>10.2f}{m['pf']:>6.2f}{m['exp_r']:>8.3f}"
            f"{m['payoff']:>7.2f}{m['true_wr']:>7.1f}{m['stop_rate']:>7.1f}"
            f"{str(m['win']) + '/' + str(m['scratch']) + '/' + str(m['fail']):>11}"
            f"{m['max_dd']:>9.2f}{m['t_stat']:>7.2f}")


def metrics_header() -> str:
    return (f"{'rule / window':<26}{'n':>5}{'net$':>10}{'PF':>6}{'expR':>8}{'payoff':>7}"
            f"{'tWR%':>7}{'stop%':>7}{'W/S/F':>11}{'maxDD$':>9}{'t':>7}")
