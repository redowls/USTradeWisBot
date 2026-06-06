"""Market-data ingestion (todo.md Phase 2).

Pulls intraday OHLCV bars from Alpaca's Market Data API for watchlist symbols
and returns clean, ET-indexed pandas DataFrames.

Feed: free IEX for now. IEX is only ~2% of total market volume, which weakens
the volume-confirmation filter and can mis-place S/R levels (summary.md §10).
TODO(SIP): revisit subscribing to SIP for full-volume data before trusting
volume spikes in live trading.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from functools import lru_cache
from math import ceil

import pandas as pd
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from . import config, db, secrets

# Canonical OHLCV columns we expose downstream.
OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]

# Approx regular-session bars per day for a 1-min timeframe (6.5h = 390 min),
# used to size the historical lookback window when fetching "the last N bars".
_RTH_MINUTES_PER_DAY = 390

# US regular trading hours (ET). A 5-min bar stamped 15:55 is the last RTH bar;
# anything stamped >= 16:00 or < 09:30 is extended-hours (thin on IEX).
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)

_UNIT_MAP = {
    "min": TimeFrameUnit.Minute,
    "minute": TimeFrameUnit.Minute,
    "hour": TimeFrameUnit.Hour,
    "day": TimeFrameUnit.Day,
    "week": TimeFrameUnit.Week,
    "month": TimeFrameUnit.Month,
}

_UNIT_MINUTES = {
    TimeFrameUnit.Minute: 1,
    TimeFrameUnit.Hour: 60,
    TimeFrameUnit.Day: _RTH_MINUTES_PER_DAY,
}


@lru_cache(maxsize=1)
def data_client() -> StockHistoricalDataClient:
    """Cached historical-data client (same Alpaca keys as the trading client)."""
    return StockHistoricalDataClient(
        api_key=secrets.ALPACA_API_KEY,
        secret_key=secrets.ALPACA_SECRET_KEY,
    )


@lru_cache(maxsize=8)
def parse_timeframe(text: str) -> TimeFrame:
    """Parse a config string like '5Min', '1Hour', '1Day' into a TimeFrame."""
    match = re.fullmatch(r"\s*(\d+)\s*([A-Za-z]+)\s*", text)
    if not match:
        raise ValueError(f"Unrecognized timeframe: {text!r}")
    amount = int(match.group(1))
    unit = _UNIT_MAP.get(match.group(2).lower())
    if unit is None:
        raise ValueError(f"Unrecognized timeframe unit in {text!r}")
    return TimeFrame(amount, unit)


def _feed() -> DataFeed:
    try:
        return DataFeed(config.DATA_FEED.lower())
    except ValueError:
        return DataFeed.IEX


def _timeframe_minutes(tf: TimeFrame) -> int:
    """Approximate minutes per bar (used only to size the lookback window)."""
    return tf.amount_value * _UNIT_MINUTES.get(tf.unit_value, 1)


def _lookback_days(tf: TimeFrame, n_bars: int) -> int:
    """Calendar days to request so ~n_bars regular-session bars are available.

    Pads generously for weekends/holidays so a request late on a Friday (or a
    weekend) still returns the most recent session's bars.
    """
    bars_per_day = max(1, _RTH_MINUTES_PER_DAY // max(1, _timeframe_minutes(tf)))
    trading_days = ceil(n_bars / bars_per_day)
    # ~1.5x for weekends/holidays, plus a 5-day floor and a 2-day pad.
    return max(5, ceil(trading_days * 1.5) + 2)


def _to_et(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with a tz-aware ET DatetimeIndex named 'timestamp'."""
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is None:
        idx = idx.tz_localize(timezone.utc)
    df = df.copy()
    df.index = idx.tz_convert(config.MARKET_TZ)
    df.index.name = "timestamp"
    return df


def _filter_rth(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only regular-trading-hours bars: 09:30 <= t < 16:00 ET."""
    if df.empty:
        return df
    t = df.index.time
    mask = (t >= RTH_OPEN) & (t < RTH_CLOSE)
    return df[mask]


def get_bars_for_symbols(
    symbols: list[str],
    n_bars: int = 50,
    timeframe: str | None = None,
    regular_hours_only: bool = True,
) -> dict[str, pd.DataFrame]:
    """Fetch the most recent `n_bars` bars for each symbol.

    Returns {symbol: DataFrame[open, high, low, close, volume]} indexed by ET
    timestamp, oldest→newest. Symbols with no data map to an empty DataFrame.
    With `regular_hours_only` (default), thin extended-hours bars are dropped so
    only 09:30–16:00 ET bars reach the strategy (summary.md §10).
    """
    symbols = [s.strip().upper() for s in symbols if s and s.strip()]
    if not symbols:
        return {}

    tf = parse_timeframe(timeframe or config.BAR_TIMEFRAME)
    intraday = tf.unit_value in (TimeFrameUnit.Minute, TimeFrameUnit.Hour)
    end = datetime.now(timezone.utc)
    # Fetch extra days when filtering to RTH, since each day loses pre/post bars.
    days = _lookback_days(tf, n_bars)
    if regular_hours_only and intraday:
        days = ceil(days * 1.4) + 1
    start = end - timedelta(days=days)

    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=tf,
        start=start,
        end=end,
        feed=_feed(),
    )
    barset = data_client().get_stock_bars(request)

    # Always return an entry per requested symbol (empty if no data came back).
    result: dict[str, pd.DataFrame] = {
        s: pd.DataFrame(columns=OHLCV_COLUMNS) for s in symbols
    }

    raw = barset.df
    if raw is None or raw.empty:
        return result

    # BarSet.df is a (symbol, timestamp) MultiIndex frame.
    for symbol in symbols:
        if symbol not in raw.index.get_level_values(0):
            continue
        sdf = raw.xs(symbol, level=0)
        cols = [c for c in OHLCV_COLUMNS if c in sdf.columns]
        sdf = _to_et(sdf[cols]).sort_index()
        if regular_hours_only and intraday:
            sdf = _filter_rth(sdf)
        result[symbol] = sdf.tail(n_bars)

    return result


def get_bars(
    symbol: str,
    n_bars: int = 50,
    timeframe: str | None = None,
    regular_hours_only: bool = True,
) -> pd.DataFrame:
    """Fetch the most recent `n_bars` bars for a single symbol."""
    return get_bars_for_symbols(
        [symbol], n_bars=n_bars, timeframe=timeframe,
        regular_hours_only=regular_hours_only,
    ).get(symbol.strip().upper(), pd.DataFrame(columns=OHLCV_COLUMNS))


def get_watchlist_bars(
    n_bars: int = 50,
    timeframe: str | None = None,
    regular_hours_only: bool = True,
) -> dict[str, pd.DataFrame]:
    """Fetch recent bars for every active watchlist symbol (one batched call)."""
    symbols = [row["symbol"] for row in db.get_active_watchlist()]
    return get_bars_for_symbols(
        symbols, n_bars=n_bars, timeframe=timeframe,
        regular_hours_only=regular_hours_only,
    )
