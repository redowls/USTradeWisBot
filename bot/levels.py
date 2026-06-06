"""Support / resistance detection (todo.md Phase 3).

Levels come from swing pivots (Williams fractals): a bar is a resistance pivot
if its high is strictly above the highs of `lookback` bars on each side; a
support pivot is the mirror (lowest low). Nearby pivots are clustered into a
handful of clean levels, and each level's touch count = how many pivots merged
into it (more touches = stronger level). summary.md §5.3.

Pivots only confirm `lookback` bars after they form, so the most recent
`lookback` bars can never be pivots — they are confirmation, not prediction.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import config


@dataclass
class Level:
    price: float        # clustered level price (mean of merged pivots)
    touches: int        # number of pivots merged into this level
    last_touch: pd.Timestamp  # most recent pivot timestamp in the cluster

    def __repr__(self) -> str:  # compact, for printed sanity checks
        return f"Level({self.price:.2f}, touches={self.touches})"


def find_pivots(
    df: pd.DataFrame, lookback: int = config.PIVOT_LOOKBACK
) -> tuple[list[tuple[float, pd.Timestamp]], list[tuple[float, pd.Timestamp]]]:
    """Return (resistance_pivots, support_pivots) as (price, timestamp) lists."""
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    times = df.index
    n = len(df)

    resistance: list[tuple[float, pd.Timestamp]] = []
    support: list[tuple[float, pd.Timestamp]] = []

    for i in range(lookback, n - lookback):
        left = slice(i - lookback, i)
        right = slice(i + 1, i + 1 + lookback)
        if highs[i] > highs[left].max() and highs[i] > highs[right].max():
            resistance.append((float(highs[i]), times[i]))
        if lows[i] < lows[left].min() and lows[i] < lows[right].min():
            support.append((float(lows[i]), times[i]))

    return resistance, support


def cluster_levels(
    pivots: list[tuple[float, pd.Timestamp]],
    cluster_pct: float = config.LEVEL_CLUSTER_PCT,
) -> list[Level]:
    """Merge pivots whose prices fall within `cluster_pct` of the cluster mean."""
    if not pivots:
        return []

    ordered = sorted(pivots, key=lambda p: p[0])
    clusters: list[list[tuple[float, pd.Timestamp]]] = [[ordered[0]]]
    for price, ts in ordered[1:]:
        ref = sum(p for p, _ in clusters[-1]) / len(clusters[-1])
        if abs(price - ref) <= cluster_pct * ref:
            clusters[-1].append((price, ts))
        else:
            clusters.append([(price, ts)])

    levels: list[Level] = []
    for cluster in clusters:
        prices = [p for p, _ in cluster]
        stamps = [t for _, t in cluster]
        levels.append(
            Level(
                price=sum(prices) / len(prices),
                touches=len(cluster),
                last_touch=max(stamps),
            )
        )
    return levels


def support_resistance(
    df: pd.DataFrame,
    lookback: int = config.PIVOT_LOOKBACK,
    cluster_pct: float = config.LEVEL_CLUSTER_PCT,
) -> dict[str, list[Level]]:
    """Full S/R detection -> {'resistance': [...], 'support': [...]} by price asc."""
    if df is None or len(df) < 2 * lookback + 1:
        return {"resistance": [], "support": []}
    res_pivots, sup_pivots = find_pivots(df, lookback)
    return {
        "resistance": sorted(cluster_levels(res_pivots, cluster_pct), key=lambda l: l.price),
        "support": sorted(cluster_levels(sup_pivots, cluster_pct), key=lambda l: l.price),
    }


def nearest_resistance_above(levels: list[Level], price: float) -> Level | None:
    """Lowest resistance level strictly above `price` (the next one to break)."""
    above = [l for l in levels if l.price > price]
    return min(above, key=lambda l: l.price) if above else None


def nearest_support_below(levels: list[Level], price: float) -> Level | None:
    """Highest support level strictly below `price`."""
    below = [l for l in levels if l.price < price]
    return max(below, key=lambda l: l.price) if below else None
