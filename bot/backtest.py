"""From-scratch N-day intraday backtest of the WHOLE USTradeWisBot logic.

Unlike ``bot.replay`` (which re-simulates trades already RECORDED in the DB),
this generates the trades from scratch over historical 5-min bars, so it answers
"what would the current strategy have done over the last N days on these symbols?"

For each session it walks the bars and, at each bar inside the entry window
(09:30–15:30 ET), asks the real decision stack what it would have done:

    signals.evaluate(df)  ->  confidence.score(ev)  ->  sizing.plan_position(...)

The first bar whose signal_type is set and confidence clears MIN_CONFIDENCE
becomes an entry at that bar's close; the bracket is then simulated bar-by-bar
with the live exit rules — ATR×3 stop (floored at MIN_STOP_PCT), 1.5R take-
profit, the IMP-013 breakeven(+0.5R)→trail(+1R) ratchet, and the 15:55 EOD
flatten. Per-symbol entries honor MAX_ENTRIES_PER_SYMBOL_PER_DAY and the
re-entry cooldown; MAX_CONCURRENT_POSITIONS is applied across symbols as a
second pass. The IMP-021 strong-breakout veto is automatic (it lives in
signals._classify).

Honest simulation caveats (do not read the output as a P&L promise):
  * Entries fill at the signal-bar CLOSE — no live slippage, and the IMP-008/009
    gap guard is a live-vs-signal check that is a no-op here.
  * Within a single 5-min bar the STOP is checked before the TARGET
    (conservative), and the trailing stop ratchets on the bar HIGH.
  * MAX_CONCURRENT is enforced by interval scheduling after the fact, so a
    dropped 4th concurrent entry does not free a slot for a later one.
The win/lose split is therefore directional, not exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import pandas as pd

from . import config, confidence, exits, signals, sizing

# Bars of context handed to signals.evaluate at each decision point — matches the
# live fetch (signals.evaluate default n_bars) so EMAs/levels see the same window.
EVAL_BARS = 120

ENTRY_START = time(9, 30)          # regular open; WisBot has no opening blackout
ENTRY_CUTOFF = time(15, 30)        # exits.past_entry_cutoff — no new entries after
RTH_CLOSE = time(16, 0)


@dataclass
class BtTrade:
    symbol: str
    day: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    shares: int
    confidence: float
    exit_reason: str
    pl: float

    @property
    def win(self) -> bool:
        return self.pl > 0


def simulate_exit(
    bars_after_entry: pd.DataFrame,
    entry: float,
    initial_stop: float,
    take_profit: float,
    eod_close: float,
) -> tuple[float, str, datetime | None]:
    """Walk the post-entry bars and return (exit_price, reason, exit_time).

    Mirrors the live bracket: within each bar the stop is checked before the
    target (conservative); then the IMP-013 breakeven→trail ratchet moves the
    stop up using the bar HIGH as the favorable price. Falls back to the EOD
    flatten at ``eod_close`` when neither leg triggers.
    """
    stop = initial_stop
    last_ts: datetime | None = None
    for ts, bar in bars_after_entry.iterrows():
        last_ts = ts
        low = float(bar["low"])
        high = float(bar["high"])
        if low <= stop:
            return stop, "STOP", ts
        if high >= take_profit:
            return take_profit, "TAKE_PROFIT", ts
        new_stop = exits.compute_trailed_stop(entry, initial_stop, stop, high)
        if new_stop is not None:
            stop = new_stop
    return eod_close, "EOD_FLATTEN", last_ts


def _session_dates(bars: pd.DataFrame, days: int) -> list[date]:
    """Unique ET session dates within the last ``days`` calendar days."""
    if bars is None or bars.empty:
        return []
    cutoff = bars.index.max().date() - timedelta(days=days)
    all_days = sorted({ts.date() for ts in bars.index})
    return [d for d in all_days if d > cutoff]


def symbol_trades_for_day(
    symbol: str,
    bars: pd.DataFrame,
    day: date,
    equity: float,
) -> list[BtTrade]:
    """Every entry the strategy would have taken on ``symbol`` on ``day``.

    Scans the entry-window bars in order; on the first qualifying signal it
    enters at that bar's close and simulates the bracket to the EOD flatten,
    then resumes scanning after the exit + re-entry cooldown, up to the daily
    per-symbol cap.
    """
    day_mask = [ts.date() == day for ts in bars.index]
    day_bars = bars[day_mask]
    if day_bars.empty:
        return []
    eod_close = float(day_bars.iloc[-1]["close"])

    positions = [bars.index.get_loc(ts) for ts in day_bars.index]
    trades: list[BtTrade] = []
    entries_used = 0
    cooldown_until: datetime | None = None

    i = 0
    while i < len(day_bars):
        if entries_used >= config.MAX_ENTRIES_PER_SYMBOL_PER_DAY:
            break
        ts = day_bars.index[i]
        t = ts.time()
        if t < ENTRY_START or t >= ENTRY_CUTOFF:
            i += 1
            continue
        if cooldown_until is not None and ts < cooldown_until:
            i += 1
            continue

        pos = positions[i]
        window = bars.iloc[max(0, pos - EVAL_BARS + 1): pos + 1]
        ev = signals.evaluate(symbol, df=window)
        if not ev.get("signal_type"):
            i += 1
            continue
        conf = confidence.score(ev)
        if conf < config.MIN_CONFIDENCE:
            i += 1
            continue
        plan = sizing.plan_position(
            symbol, conf, ev["close"] or 0.0, ev["atr"] or 0.0,
            equity, equity, held_symbols=set(), open_positions_count=0,
        )
        if not plan.tradable:
            i += 1
            continue

        # Enter at this bar's close; simulate the bracket over the rest of RTH.
        after = day_bars[[bt.time() < RTH_CLOSE for bt in day_bars.index]].iloc[i + 1:]
        exit_price, reason, exit_ts = simulate_exit(
            after, plan.entry_price, plan.stop_price, plan.take_profit_price, eod_close,
        )
        exit_ts = exit_ts or ts
        pl = round((exit_price - plan.entry_price) * plan.shares, 2)
        trades.append(BtTrade(
            symbol=symbol, day=str(day), entry_time=ts, exit_time=exit_ts,
            entry_price=plan.entry_price, exit_price=round(exit_price, 4),
            shares=plan.shares, confidence=round(conf, 1), exit_reason=reason, pl=pl,
        ))
        entries_used += 1
        cooldown_until = exit_ts + timedelta(minutes=config.REENTRY_COOLDOWN_MIN)
        # Resume scanning at the bar after the exit.
        j = i + 1
        while j < len(day_bars) and day_bars.index[j] <= exit_ts:
            j += 1
        i = j

    return trades


def apply_concurrency(trades: list[BtTrade], max_concurrent: int) -> list[BtTrade]:
    """Drop entries that would exceed MAX_CONCURRENT open positions.

    Interval scheduling: process entries in chronological order and admit one
    only when fewer than ``max_concurrent`` already-admitted trades are open
    (entry_time <= t < exit_time) at its entry instant.
    """
    admitted: list[BtTrade] = []
    for tr in sorted(trades, key=lambda x: x.entry_time):
        open_now = sum(
            1 for a in admitted if a.entry_time <= tr.entry_time < a.exit_time
        )
        if open_now < max_concurrent:
            admitted.append(tr)
    return admitted


def run_backtest(
    all_bars: dict[str, pd.DataFrame],
    symbols: list[str],
    days: int,
    equity: float,
) -> dict:
    """Run the full backtest and return an aggregate summary + the trade list."""
    raw: list[BtTrade] = []
    session_days: set[date] = set()
    for sym in symbols:
        bars = all_bars.get(sym)
        if bars is None or bars.empty:
            continue
        for d in _session_dates(bars, days):
            session_days.add(d)
            raw.extend(symbol_trades_for_day(sym, bars, d, equity))

    trades = apply_concurrency(raw, config.MAX_CONCURRENT_POSITIONS)

    n = len(trades)
    wins = sum(1 for t in trades if t.win)
    losses = n - wins
    total_pl = round(sum(t.pl for t in trades), 2)
    gross_win = sum(t.pl for t in trades if t.pl > 0)
    gross_loss = sum(t.pl for t in trades if t.pl <= 0)

    by_reason: dict[str, dict] = {}
    for t in trades:
        b = by_reason.setdefault(t.exit_reason, {"n": 0, "pl": 0.0, "wins": 0})
        b["n"] += 1
        b["pl"] = round(b["pl"] + t.pl, 2)
        b["wins"] += int(t.win)

    by_symbol: dict[str, dict] = {}
    for t in trades:
        b = by_symbol.setdefault(t.symbol, {"n": 0, "pl": 0.0, "wins": 0})
        b["n"] += 1
        b["pl"] = round(b["pl"] + t.pl, 2)
        b["wins"] += int(t.win)

    sess = sorted(session_days)
    return {
        "symbols": symbols,
        "days_requested": days,
        "sessions": len(sess),
        "window": (f"{sess[0]}..{sess[-1]}" if sess else "n/a"),
        "trades": n,
        "wins": wins,
        "losses": losses,
        "win_pct": round(100.0 * wins / n, 1) if n else 0.0,
        "total_pl": total_pl,
        "avg_win": round(gross_win / wins, 2) if wins else 0.0,
        "avg_loss": round(gross_loss / losses, 2) if losses else 0.0,
        "profit_factor": round(gross_win / abs(gross_loss), 2) if gross_loss < 0 else 0.0,
        "by_reason": by_reason,
        "by_symbol": by_symbol,
        "equity": equity,
        "trade_rows": trades,
    }
