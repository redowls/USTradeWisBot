"""Confidence scoring (todo.md Phase 5).

Fuses the component scores from bot.signals into a single 0-100 confidence number
using the theory-driven weights in config (summary.md §5.8):

    confidence = 100 * (0.35*breakout + 0.30*ma + 0.20*value + 0.15*momentum)
                 * regime_multiplier

Keep the weights few and theory-driven — every tuned weight is an overfitting
risk (summary.md §10).
"""

from __future__ import annotations

from . import config


def score(evaluation: dict) -> float:
    """Return 0-100 confidence from a bot.signals.evaluate() result dict."""
    blend = (
        config.WEIGHT_BREAKOUT * evaluation.get("breakout_score", 0.0)
        + config.WEIGHT_MA * evaluation.get("ma_score", 0.0)
        + config.WEIGHT_VALUE * evaluation.get("value_score", 0.0)
        + config.WEIGHT_MOMENTUM * evaluation.get("momentum_score", 0.0)
    )
    conf = 100.0 * blend * evaluation.get("regime_multiplier", 0.0)
    return round(max(0.0, min(100.0, conf)), 2)


def is_tradable(confidence: float) -> bool:
    """True only when confidence clears MIN_CONFIDENCE (summary.md §5.8)."""
    return confidence >= config.MIN_CONFIDENCE
