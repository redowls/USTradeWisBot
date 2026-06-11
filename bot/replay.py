"""Trade replay & exit-rule what-if analysis (PHASE-001).

Replays every CLOSED trade in the DB against the 5-minute bars for its session
and answers two questions:

  1. Fidelity — does a bar-level replay of the CURRENT bracket (stop / take-
     profit / EOD flatten) reproduce the recorded P&L? The gap between
     "replayed baseline" and "actual" is the simulation error budget; any
     what-if improvement smaller than that budget is noise, not signal.
  2. What-if — what would P&L have been under a candidate exit rule (e.g.
     move the stop to breakeven once price reaches +N R)? Used to justify or
     reject exit-logic phases with recorded data instead of intuition.

Bar-level caveats (be honest with yourself before acting on the output):
  - Within a single 5-min bar we cannot know whether the stop or the target
    was touched first, so the simulator assumes STOP FIRST (conservative).
  - Entries/exits happened at intrabar prices the bars cannot reproduce, so
    per-trade deltas of a few dollars are expected even for a perfect rule.

The simulation core is pure (DataFrame in, result out) so it is unit-testable
with synthetic bars; only the loaders touch the DB / Alpaca data API.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import db
from .data import get_bars_for_symbols

# Bars to request per symbol: ~78 RTH 5-min bars/day, keep ~2 weeks of context.
REPLAY_N_BARS = 900


# --- Pure simulation core ----------------------------------------------------

@dataclass
class SimResult:
    exit_price: float
    exit_reason: str            # 'STOP' / 'TAKE_PROFIT' / 'EOD_FLATTEN'
    mfe: float                  # max favorable excursion, $/share vs entry
    mae: float                  # max adverse excursion, $/share vs entry (<= 0)
    breakeven_armed: bool       # did the what-if rule ever move the stop?


def simulate_bracket(
    bars: pd.DataFrame,
    entry_price: float,
    stop_price: float,
    take_profit_price: float | None,
    fallback_exit_price: float,
    *,
    breakeven_at_r: float | None = None,
) -> SimResult:
    """Walk the bars of one trade and return how the bracket would have exited.

    `bars` must cover entry..exit (high/low columns, chronological order).
    `fallback_exit_price` is used when neither leg triggers (EOD flatten).
    `breakeven_at_r`: optional what-if — once the bar high reaches
    entry + N * R (R = entry - stop), move the stop to the entry price.
    Within a bar the stop is always checked before the target (conservative).
    """
    risk = entry_price - stop_price
    stop = stop_price
    armed = False
    mfe = 0.0
    mae = 0.0

    for _, bar in bars.iterrows():
        high = float(bar["high"])
        low = float(bar["low"])
        mfe = max(mfe, high - entry_price)
        mae = min(mae, low - entry_price)

        if low <= stop:
            return SimResult(stop, "STOP", mfe, mae, armed)
        if take_profit_price is not None and high >= take_profit_price:
            return SimResult(take_profit_price, "TAKE_PROFIT", mfe, mae, armed)
        if (
            breakeven_at_r is not None
            and not armed
            and risk > 0
            and high >= entry_price + breakeven_at_r * risk
        ):
            stop = entry_price
            armed = True

    return SimResult(fallback_exit_price, "EOD_FLATTEN", mfe, mae, armed)


# --- Loaders (DB + Alpaca bars) ----------------------------------------------

def load_closed_trades() -> list[dict]:
    """All CLOSED trades with the fields the replay needs, oldest first."""
    return db.query(
        "SELECT trade_id, symbol, qty, entry_price, entry_time, stop_price, "
        "take_profit_price, exit_price, exit_time, realized_pl, exit_reason "
        "FROM trades WHERE status = 'CLOSED' ORDER BY entry_time"
    )


def bars_for_trade(all_bars: dict[str, pd.DataFrame], trade: dict) -> pd.DataFrame | None:
    """The trade's session bars between entry and exit (inclusive), ET."""
    df = all_bars.get(trade["symbol"])
    if df is None or df.empty:
        return None
    day = trade["entry_time"].strftime("%Y-%m-%d")
    times = df.index.strftime("%Y-%m-%d %H:%M")
    window = df[times.str.startswith(day)]
    window = window[window.index.strftime("%H:%M") >= trade["entry_time"].strftime("%H:%M")]
    if trade["exit_time"] is not None:
        window = window[window.index.strftime("%H:%M") <= trade["exit_time"].strftime("%H:%M")]
    return window if not window.empty else None


# --- Analysis ------------------------------------------------------------------

def replay_trades(
    trades: list[dict],
    all_bars: dict[str, pd.DataFrame],
    *,
    breakeven_at_r: float | None = None,
) -> dict:
    """Replay every trade; return aggregate + per-trade rows.

    With breakeven_at_r=None this is the fidelity baseline (current bracket).
    """
    rows: list[dict] = []
    for t in trades:
        bars = bars_for_trade(all_bars, t)
        if bars is None:
            continue
        entry = float(t["entry_price"])
        stop = float(t["stop_price"])
        tp = float(t["take_profit_price"]) if t["take_profit_price"] else None
        qty = float(t["qty"])
        actual_pl = float(t["realized_pl"])
        risk = entry - stop

        sim = simulate_bracket(
            bars, entry, stop, tp,
            fallback_exit_price=float(t["exit_price"]),
            breakeven_at_r=breakeven_at_r,
        )
        rows.append({
            "trade_id": t["trade_id"],
            "symbol": t["symbol"],
            "day": t["entry_time"].strftime("%Y-%m-%d"),
            "actual_reason": t["exit_reason"],
            "actual_pl": actual_pl,
            "sim_reason": sim.exit_reason,
            "sim_pl": round((sim.exit_price - entry) * qty, 2),
            "mfe_r": round(sim.mfe / risk, 2) if risk > 0 else 0.0,
            "mae_r": round(sim.mae / risk, 2) if risk > 0 else 0.0,
            "breakeven_armed": sim.breakeven_armed,
        })

    n = len(rows)
    actual_total = sum(r["actual_pl"] for r in rows)
    sim_total = sum(r["sim_pl"] for r in rows)
    return {
        "rows": rows,
        "trades": n,
        "actual_pl": round(actual_total, 2),
        "sim_pl": round(sim_total, 2),
        "delta": round(sim_total - actual_total, 2),
        "abs_error": round(sum(abs(r["sim_pl"] - r["actual_pl"]) for r in rows), 2),
        "reached_half_r": sum(1 for r in rows if r["mfe_r"] >= 0.5),
        "reached_one_r": sum(1 for r in rows if r["mfe_r"] >= 1.0),
        "losers_reached_one_r": sum(
            1 for r in rows if r["actual_pl"] < 0 and r["mfe_r"] >= 1.0
        ),
    }


def load_all_bars(trades: list[dict]) -> dict[str, pd.DataFrame]:
    symbols = sorted({t["symbol"] for t in trades})
    return get_bars_for_symbols(symbols, n_bars=REPLAY_N_BARS)
