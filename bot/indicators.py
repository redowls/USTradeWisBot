"""Technical indicators (todo.md Phase 3).

Pure functions over OHLCV DataFrames (as produced by bot.data) — no I/O, easy
to unit-test. EMA (not SMA) is used throughout because it reacts faster, which
suits intraday trading (summary.md §5.2). ATR/RSI/ADX use Wilder's smoothing.

A DataFrame here has columns open/high/low/close/volume and an ET DatetimeIndex.
Each function returns a pandas Series aligned to that index (NaN where there is
not yet enough history).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average (recursive form, adjust=False)."""
    return series.ewm(span=period, adjust=False).mean()


def _wilder(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing == EMA with alpha = 1/period (adjust=False)."""
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    """True Range: max(H-L, |H-prevC|, |L-prevC|)."""
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = config.ATR_PERIOD) -> pd.Series:
    """Average True Range (Wilder)."""
    return _wilder(true_range(df), period)


def rsi(close: pd.Series, period: int = config.RSI_PERIOD) -> pd.Series:
    """Relative Strength Index (Wilder). 0-100; 100 when there are no losses."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = _wilder(gain, period)
    avg_loss = _wilder(loss, period)
    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 the stock only rose -> RSI = 100.
    out = out.where(avg_loss != 0, 100.0)
    # When both are 0 (flat) RSI is undefined -> neutral 50.
    out = out.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    return out


def adx(
    df: pd.DataFrame, period: int = config.ADX_PERIOD
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Average Directional Index. Returns (adx, +DI, -DI). summary.md §5.7."""
    high, low = df["high"], df["low"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index
    )

    atr_ = _wilder(true_range(df), period)
    plus_di = 100.0 * _wilder(plus_dm, period) / atr_
    minus_di = 100.0 * _wilder(minus_dm, period) / atr_

    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    adx_ = _wilder(dx.fillna(0.0), period)
    return adx_, plus_di, minus_di


def relative_volume(
    volume: pd.Series, lookback: int = config.REL_VOL_LOOKBACK
) -> pd.Series:
    """Current bar volume / average of the prior `lookback` bars' volume."""
    avg = volume.shift(1).rolling(lookback).mean()
    return volume / avg


def macd(
    close: pd.Series,
    fast: int = config.MACD_FAST,
    slow: int = config.MACD_SLOW,
    signal: int = config.MACD_SIGNAL,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD. Returns (macd_line, signal_line, histogram)."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line


def compute(df: pd.DataFrame) -> pd.DataFrame:
    """Return df augmented with all indicator columns (full history)."""
    out = df.copy()
    for period in [*config.EMA_SHORT, *config.EMA_LONG]:
        out[f"ema_{period}"] = ema(df["close"], period)
    out["atr"] = atr(df)
    out["rsi"] = rsi(df["close"])
    adx_, plus_di, minus_di = adx(df)
    out["adx"] = adx_
    out["plus_di"] = plus_di
    out["minus_di"] = minus_di
    out["rel_vol"] = relative_volume(df["volume"])
    macd_line, signal_line, hist = macd(df["close"])
    out["macd"] = macd_line
    out["macd_signal"] = signal_line
    out["macd_hist"] = hist
    return out


def snapshot(df: pd.DataFrame) -> dict | None:
    """Latest indicator values as a flat dict, or None if df is empty.

    Returned keys: close, ema_8/10/20/21/34/55, atr, rsi, adx, plus_di,
    minus_di, rel_vol. Values may be NaN if history is too short.
    """
    if df is None or df.empty:
        return None
    out = compute(df).iloc[-1]
    keys = ["close", *[f"ema_{p}" for p in (*config.EMA_SHORT, *config.EMA_LONG)],
            "atr", "rsi", "adx", "plus_di", "minus_di", "rel_vol",
            "macd", "macd_signal", "macd_hist"]
    return {k: (float(out[k]) if pd.notna(out[k]) else float("nan")) for k in keys}
