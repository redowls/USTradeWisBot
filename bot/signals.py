"""Signal / strategy engine (todo.md Phase 4).

Turns indicators + S/R levels into component scores (each 0-1). No orders here —
this layer only describes an opportunity. The buy decision is a funnel
(summary.md §5): regime gate -> breakout and/or MA trigger -> over-extension
check. Confidence fusion and sizing live in Phase 5.

`evaluate()` returns a dict with every component score, `regime_ok` + its
multiplier, the `signal_type` ('BREAKOUT' / 'MA' / 'BOTH' / None) and the broken
resistance level — enough for Phase 5 to compute confidence and for Phase 8 to
explain every trade.
"""

from __future__ import annotations

import math
from datetime import datetime, time

import pandas as pd

from . import config, data, indicators, levels

# Need enough history for the long EMA set + a slope window to be meaningful.
MIN_BARS = max(config.EMA_LONG) + config.SLOPE_LOOKBACK + 1


def _clip01(x: float) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.0
    return max(0.0, min(1.0, float(x)))


def _safe(x, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(v) else v


# --- Component scores -------------------------------------------------------

def breakout_score(
    df: pd.DataFrame, comp: pd.DataFrame, resistance: list[levels.Level]
) -> tuple[float, float | None]:
    """Score a fresh resistance breakout. Returns (score 0-1, broken_level|None).

    Requires (summary.md §5.4): the latest candle CLOSES above a resistance level
    by at least BREAKOUT_BUFFER, having been at/below it on the prior bar. Score
    rewards volume confirmation and prior touch count.
    """
    if len(df) < 2 or not resistance:
        return 0.0, None

    close = _safe(df["close"].iloc[-1])
    prev_close = _safe(df["close"].iloc[-2])
    rel_vol = _safe(comp["rel_vol"].iloc[-1])

    # Levels freshly broken on this bar (highest one is the most meaningful).
    broken = [
        lvl for lvl in resistance
        if prev_close <= lvl.price and close > lvl.price * (1 + config.BREAKOUT_BUFFER)
    ]
    if not broken:
        return 0.0, None
    level = max(broken, key=lambda l: l.price)

    # Volume confirmation: full credit at/above VOL_CONFIRM_MULT, scaled below.
    vol_component = _clip01(rel_vol / config.VOL_CONFIRM_MULT) if rel_vol > 0 else 0.0
    # Touch strength: more prior touches = stronger level.
    touch_component = _clip01(level.touches / (config.MIN_LEVEL_TOUCHES + 1))

    # A confirmed close-above-buffer break earns a base; volume + touches lift it.
    score = 0.45 + 0.35 * vol_component + 0.20 * touch_component
    return _clip01(score), level.price


def ma_score(comp: pd.DataFrame) -> float:
    """Short EMA set (8>10>20) alignment with slope & separation. summary.md §5.5."""
    k = config.SLOPE_LOOKBACK
    if len(comp) < k + 1:
        return 0.0
    s, m, l = (f"ema_{p}" for p in config.EMA_SHORT)
    e_s, e_m, e_l = _safe(comp[s].iloc[-1]), _safe(comp[m].iloc[-1]), _safe(comp[l].iloc[-1])

    full_stack = e_s > e_m > e_l
    partial = e_s > e_l and not full_stack

    # Slope: is the fast EMA rising over the lookback?
    slope_up = _safe(comp[s].iloc[-1]) > _safe(comp[s].iloc[-1 - k])
    # Separation: is the fast/slow gap widening (acceleration) and positive?
    gap_now = _safe(comp[s].iloc[-1]) - _safe(comp[l].iloc[-1])
    gap_prev = _safe(comp[s].iloc[-1 - k]) - _safe(comp[l].iloc[-1 - k])
    separating = gap_now > gap_prev and gap_now > 0

    if full_stack:
        return _clip01(0.6 + 0.2 * slope_up + 0.2 * separating)
    if partial:
        return _clip01(0.3 + 0.1 * slope_up)
    return 0.0


def value_score(comp: pd.DataFrame, df: pd.DataFrame) -> float:
    """Over-extension check (1 = good value, 0 = badly extended). summary.md §5.6."""
    close = _safe(comp["close"].iloc[-1])
    ema20 = _safe(comp[f"ema_{config.EMA_SHORT[-1]}"].iloc[-1])
    atr = _safe(comp["atr"].iloc[-1])
    rsi = _safe(comp["rsi"].iloc[-1], default=50.0)
    if atr <= 0:
        return 0.0

    # Distance above the 20-EMA in ATR multiples. At/below EMA = great value.
    ext = (close - ema20) / atr
    if ext <= config.EXT_ATR_PENALTY:
        ext_score = 1.0
    elif ext >= config.EXT_ATR_VETO:
        ext_score = 0.0
    else:
        span = config.EXT_ATR_VETO - config.EXT_ATR_PENALTY
        ext_score = 1.0 - (ext - config.EXT_ATR_PENALTY) / span

    # RSI overbought: lowers (does not veto) the score; in 70->100, factor 1->0.
    if rsi > config.RSI_OVERBOUGHT:
        rsi_factor = _clip01(1.0 - (rsi - config.RSI_OVERBOUGHT) / (100 - config.RSI_OVERBOUGHT))
    else:
        rsi_factor = 1.0

    # Aberrant range: if the latest bar's range dwarfs ATR, the easy move is done.
    tr = _safe((df["high"].iloc[-1] - df["low"].iloc[-1]))
    range_factor = _clip01(1.75 / (tr / atr)) if tr > 1.75 * atr else 1.0

    return _clip01(ext_score * rsi_factor * range_factor)


def momentum_score(comp: pd.DataFrame) -> float:
    """RSI + MACD support (0-1). summary.md §5.8 momentum component."""
    if len(comp) < 2:
        return 0.0
    rsi = _safe(comp["rsi"].iloc[-1], default=50.0)
    # RSI momentum: 0 at/below 50, ramping to 1 by 70 (bullish but not extreme).
    rsi_mom = _clip01((rsi - 50.0) / 20.0)

    macd = _safe(comp["macd"].iloc[-1])
    signal = _safe(comp["macd_signal"].iloc[-1])
    hist_now = _safe(comp["macd_hist"].iloc[-1])
    hist_prev = _safe(comp["macd_hist"].iloc[-2])
    macd_bull = macd > signal
    hist_rising = hist_now > hist_prev
    macd_mom = 0.6 * macd_bull + 0.4 * hist_rising

    return _clip01(0.5 * rsi_mom + 0.5 * macd_mom)


def regime(comp: pd.DataFrame) -> tuple[bool, float]:
    """Regime filter -> (regime_ok, multiplier). summary.md §5.7.

    Healthy when ADX >= ADX_MIN AND long EMA set stacked (21>34>55) -> mult 1.0.
    Only one of the two -> weak (0.5). Neither -> fail (0.0, suppress buys).
    """
    adx_ok = _safe(comp["adx"].iloc[-1]) >= config.ADX_MIN
    e21, e34, e55 = (_safe(comp[f"ema_{p}"].iloc[-1]) for p in config.EMA_LONG)
    long_stacked = e21 > e34 > e55

    if adx_ok and long_stacked:
        return True, config.REGIME_MULT_OK
    if adx_ok or long_stacked:
        return True, config.REGIME_MULT_WEAK
    return False, config.REGIME_MULT_FAIL


# --- IMP-059: opening-range breakout entry ------------------------------------

def completed_bars(df: pd.DataFrame, now: datetime | None) -> pd.DataFrame:
    """Drop the bar still forming at ``now`` so the rule reads CLOSED bars only.

    The bars endpoint returns the current 5-min bar too, with "close" = the last
    trade so far. bot/entry_lab.py entered at the close of a COMPLETED bar, so
    the live rule must judge the same bar: anything whose start lies inside the
    current 5-min bucket is not finished. ``now=None`` (backtest windows) keeps
    every bar — a window's last bar is by construction the bar being judged.
    """
    if now is None or df is None or df.empty:
        return df
    now_et = now.astimezone(config.MARKET_TZ)
    bucket = now_et.replace(minute=(now_et.minute // 5) * 5, second=0, microsecond=0)
    return df[df.index < bucket]


def _orb_cutoff() -> time:
    hh, mm = (int(x) for x in str(config.ORB_CUTOFF_ET).split(":"))
    return time(hh, mm)


def orb_features(df: pd.DataFrame) -> dict:
    """Opening-range-breakout state of the LAST bar of ``df`` (a closed bar).

    Mirrors bot.entry_lab.rule_orb exactly:
      * range     = high of the first ORB_RANGE_BARS bars of the session;
      * candidate = this bar closes above range*(1+ORB_BUFFER_PCT) AND the prior
                    bar closed at/below the range — a FRESH break, one trigger per
                    break, never on every bar that happens to sit above it;
      * signal    = candidate AND not after ORB_CUTOFF_ET AND rel_vol >=
                    ORB_MIN_REL_VOL AND (close > session VWAP if required).
    ``blocks`` names every failed condition so a refused candidate is auditable
    in dbo.entry_refusals. The market filter (index above its own VWAP) is
    applied in evaluate_watchlist, the only place that has the index bars.
    """
    out: dict = {"candidate": False, "signal": False, "blocks": [], "or_high": None,
                 "rel_vol": None, "bar_idx": None}
    if df is None or len(df) < 2:
        out["blocks"].append("no_bars")
        return out
    last_ts = df.index[-1]
    day = df[df.index.normalize() == last_ts.normalize()]
    k = int(config.ORB_RANGE_BARS)
    bar_idx = len(day) - 1
    out["bar_idx"] = bar_idx
    if bar_idx < k:
        out["blocks"].append("range_incomplete")
        return out
    or_high = _safe(day["high"].iloc[:k].max())
    close = _safe(day["close"].iloc[-1])
    prev_close = _safe(day["close"].iloc[-2])
    out["or_high"] = round(or_high, 4)
    if not close > or_high * (1.0 + float(config.ORB_BUFFER_PCT) / 100.0):
        out["blocks"].append("no_break")
        return out
    if not prev_close <= or_high:
        out["blocks"].append("not_fresh")
        return out
    out["candidate"] = True
    if last_ts.time() > _orb_cutoff():
        out["blocks"].append("after_cutoff")
    rel_vol = _safe(indicators.relative_volume(df["volume"]).iloc[-1])
    out["rel_vol"] = round(rel_vol, 3)
    if config.ORB_MIN_REL_VOL and not rel_vol >= float(config.ORB_MIN_REL_VOL):
        out["blocks"].append("low_volume")
    if config.ORB_REQUIRE_ABOVE_VWAP:
        vwap = _safe(indicators.session_vwap(df).iloc[-1])
        if not (vwap > 0 and close > vwap):
            out["blocks"].append("below_vwap")
    out["signal"] = not out["blocks"]
    return out


def orb_market_ok(bars: dict[str, pd.DataFrame], now: datetime | None) -> tuple[bool, str]:
    """Index-regime filter for ORB entries: the filter symbol's last CLOSED bar
    must close above its own session VWAP. Fails CLOSED (no entries) when the
    index bars are unavailable — the lab scored a missing market read as False.
    """
    sym = (config.ORB_MARKET_FILTER_SYMBOL or "").strip().upper()
    if not sym:
        return True, "market filter disabled"
    df = bars.get(sym)
    if df is None or df.empty:
        try:
            df = data.get_bars(sym, n_bars=120)
        except Exception as exc:  # transient data error: fail closed, say why
            return False, f"{sym} bars unavailable ({type(exc).__name__})"
    df = completed_bars(df, now)
    if df is None or df.empty:
        return False, f"{sym} has no completed bar yet"
    close = _safe(df["close"].iloc[-1])
    vwap = _safe(indicators.session_vwap(df).iloc[-1])
    if vwap <= 0:
        return False, f"{sym} VWAP undefined"
    ok = close > vwap
    return ok, f"{sym} {close:.2f} {'above' if ok else 'below'} VWAP {vwap:.2f}"


# --- Top-level evaluation -----------------------------------------------------

def _classify(bo_score: float, ma: float, value: float) -> str | None:
    has_breakout = bo_score > 0.0
    has_ma = ma >= config.MA_SIGNAL_MIN
    # Over-extension veto: a breakout that has already run too far above EMA20
    # (low value_score) is buying the spike top. Skip the entry entirely rather
    # than fall back to an MA entry on the same extended bar — buying extended is
    # the problem regardless of the MA component. Pure-MA signals (no breakout)
    # are left untouched. summary.md §5.6; analysis 2026-06-09 (BOTH went 0/5:
    # JPM/XOM/ABNB were badly extended yet still traded).
    if has_breakout and value < config.VALUE_VETO_FLOOR:
        return None
    # Strong-breakout ("fade") veto: a fresh breakout scoring at/above the ceiling
    # reliably fades (IMP-021, holdout-validated 2026-07-25 — the real-breakout leg
    # was the entire loss driver). Skip the entry entirely rather than fall back to
    # an MA entry on the same breakout bar; buying the breakout bar is the problem.
    if has_breakout and bo_score >= config.BREAKOUT_FADE_CEILING:
        return None
    if has_breakout and has_ma:
        return "BOTH"
    if has_breakout:
        return "BREAKOUT"
    if has_ma:
        return "MA"
    return None


def _null_result(symbol: str) -> dict:
    return {
        "symbol": symbol, "breakout_score": 0.0, "ma_score": 0.0,
        "value_score": 0.0, "momentum_score": 0.0, "regime_ok": False,
        "regime_multiplier": 0.0, "signal_type": None, "broke_level": None,
        "close": None, "atr": None, "session_vwap": None, "bars": 0, "orb": None,
    }


def evaluate(symbol: str, df: pd.DataFrame | None = None, n_bars: int = 120) -> dict:
    """Evaluate one symbol and return all component scores + signal classification.

    Pass `df` to score precomputed bars (testable, offline); otherwise bars are
    fetched via bot.data.
    """
    symbol = symbol.strip().upper()
    if df is None:
        df = data.get_bars(symbol, n_bars=n_bars)
    if df is None or len(df) < MIN_BARS:
        return _null_result(symbol)

    comp = indicators.compute(df)
    sr = levels.support_resistance(df)

    bo_score, broke_level = breakout_score(df, comp, sr["resistance"])
    ma = ma_score(comp)
    value = value_score(comp, df)
    mom = momentum_score(comp)
    regime_ok, regime_mult = regime(comp)
    # Current session VWAP (IMP-022): last value of the day-reset VWAP series;
    # the entry-quality gate in engine.consider_entries skips fills stretched too
    # far above it. NaN (thin/zero-volume session) -> None so the gate fails open.
    vwap_series = indicators.session_vwap(df)
    vwap_last = _safe(vwap_series.iloc[-1]) if len(vwap_series) else 0.0
    session_vwap = round(vwap_last, 4) if vwap_last and vwap_last > 0 else None
    signal_type = _classify(bo_score, ma, value)
    orb: dict | None = None
    if config.ENTRY_MODE == "orb":
        # IMP-059: the ORB rule replaces the MA/breakout classification as the
        # entry decision; the component scores are still computed and persisted
        # so every fill stays comparable with the pre-IMP-059 book.
        orb = orb_features(df)
        signal_type = "ORB" if orb["signal"] else None
        if orb["candidate"] and orb["or_high"]:
            broke_level = orb["or_high"]
    return {
        "symbol": symbol,
        "breakout_score": round(bo_score, 4),
        "ma_score": round(ma, 4),
        "value_score": round(value, 4),
        "momentum_score": round(mom, 4),
        "regime_ok": regime_ok,
        "regime_multiplier": regime_mult,
        "signal_type": signal_type,
        "orb": orb,
        "broke_level": round(broke_level, 4) if broke_level is not None else None,
        "close": round(_safe(df["close"].iloc[-1]), 4),
        "atr": round(_safe(comp["atr"].iloc[-1]), 4),
        "session_vwap": session_vwap,
        "bars": len(df),
    }


def evaluate_watchlist(n_bars: int = 120) -> list[dict]:
    """Evaluate every active watchlist symbol from one batched data fetch.

    In ORB mode (IMP-059) every symbol is judged on its last COMPLETED bar and
    the index market filter is applied here: a fresh break while the index sits
    below its own VWAP stays a *candidate* (so the refusal ledger records it)
    but is not a signal.
    """
    bars = data.get_watchlist_bars(n_bars=n_bars)
    if config.ENTRY_MODE != "orb":
        return [evaluate(sym, df=df, n_bars=n_bars) for sym, df in bars.items()]
    now = datetime.now(config.MARKET_TZ)
    mkt_ok, mkt_detail = orb_market_ok(bars, now)
    out: list[dict] = []
    for sym, df in bars.items():
        ev = evaluate(sym, df=completed_bars(df, now), n_bars=n_bars)
        orb = ev.get("orb")
        if orb is not None:
            orb["market"] = mkt_detail
            if orb.get("candidate") and not mkt_ok:
                orb["blocks"].append("market_filter")
                orb["signal"] = False
                ev["signal_type"] = None
        out.append(ev)
    return out
