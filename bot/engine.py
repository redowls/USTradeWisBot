"""Scheduler / main loop (todo.md Phase 10).

Ties every module into one continuously-running process. During regular trading
hours each tick does:

    manage exits -> (before 15:30) ingest, evaluate, score, size, enter
                 -> (at/after 15:55) flatten everything
    -> log to SQL Server -> Telegram alerts

Outside RTH it sleeps until the next open. Heartbeats fire at startup and at the
open; each tick is wrapped so one symbol's error can't kill the loop; SIGINT/
SIGTERM shut it down gracefully. summary.md §4, §5.11.
"""

from __future__ import annotations

import signal
import time
import traceback
from datetime import date, datetime

from . import (
    broker, config, confidence, exits, execution, logbook, notify, signals, sizing,
)


class Engine:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.running = True
        self.market_was_open = False
        self.equity_open: float | None = None
        self.flattened_on: date | None = None
        self.summarized_on: date | None = None

    # --- logging ---
    def _log(self, msg: str) -> None:
        print(f"{datetime.now(config.MARKET_TZ):%Y-%m-%d %H:%M:%S %Z} | {msg}", flush=True)

    # --- exits ---
    def manage_exits(self) -> list[dict]:
        """Record any bracket TP/STOP fills for currently-open trades."""
        open_trades = logbook.get_open_trades()
        order_ids = [t["alpaca_order_id"] for t in open_trades if t.get("alpaca_order_id")]
        records = exits.detect_exits(order_ids)
        for rec in records:
            if self.dry_run:
                self._log(f"[dry] would record EXIT {rec['symbol']} {rec['exit_reason']} "
                          f"pl={rec['realized_pl']}")
                continue
            if logbook.record_exit(rec):
                notify.exit_alert(rec)
                self._log(f"EXIT {rec['symbol']} {rec['exit_reason']} "
                          f"pl=${rec['realized_pl']} ({rec['realized_pl_pct']}%)")
        return records

    # --- entries ---
    def consider_entries(self, now: datetime | None = None) -> list[dict]:
        """Evaluate the watchlist and open new bracket positions (before cutoff)."""
        now = now or exits.now_et()
        actions: list[dict] = []
        if not exits.entries_allowed(now):
            return actions

        acct = broker.account_summary()
        equity, buying_power = acct["equity"], acct["buying_power"]
        held = broker.open_position_symbols()
        open_count = len(held)

        scored = sorted(
            ((confidence.score(ev), ev) for ev in signals.evaluate_watchlist()),
            key=lambda x: x[0], reverse=True,
        )
        for conf, ev in scored:
            if open_count >= config.MAX_CONCURRENT_POSITIONS:
                break
            if conf < config.MIN_CONFIDENCE or not ev.get("signal_type"):
                continue
            plan = sizing.plan_position(
                ev["symbol"], conf, ev["close"] or 0.0, ev["atr"] or 0.0,
                equity, buying_power, held_symbols=held, open_positions_count=open_count,
            )
            if not plan.tradable:
                actions.append({"symbol": plan.symbol, "confidence": conf,
                                "action": "skip", "detail": plan.skip_reason})
                continue
            if self.dry_run:
                actions.append({"symbol": plan.symbol, "confidence": conf,
                                "action": "would_buy", "shares": plan.shares,
                                "stop": plan.stop_price, "tp": plan.take_profit_price})
                self._log(f"[dry] would BUY {plan.shares} {plan.symbol} @ {plan.entry_price} "
                          f"(conf {conf:.0f})")
                continue
            res = execution.submit_bracket_order(plan)
            if res["ok"]:
                trade_id = logbook.record_entry(ev, plan, res, confidence=conf)
                notify.entry_alert(plan, ev, conf)
                held.add(plan.symbol)
                open_count += 1
                actions.append({"symbol": plan.symbol, "confidence": conf,
                                "action": "bought", "order_id": res["order_id"],
                                "trade_id": trade_id})
                self._log(f"ENTRY {plan.shares} {plan.symbol} @ {plan.entry_price} "
                          f"(conf {conf:.0f}) order={res['order_id']}")
            else:
                actions.append({"symbol": plan.symbol, "confidence": conf,
                                "action": "rejected", "detail": res["error"]})
                self._log(f"ENTRY REJECTED {plan.symbol}: {res['error']}")
        return actions

    # --- end-of-day flatten ---
    def eod_flatten(self) -> None:
        """Force-close everything and mark open trades EOD_FLATTEN. Idempotent."""
        open_trades = logbook.get_open_trades()
        if self.dry_run:
            self._log(f"[dry] would flatten {len(open_trades)} open trade(s)")
            return
        snapshot = {s["symbol"]: s for s in exits.flatten_all("EOD_FLATTEN")}
        for t in open_trades:
            qty = int(t["qty"]) or 0
            entry = float(t["entry_price"])
            snap = snapshot.get(t["symbol"])
            mv = snap.get("market_value") if snap else None
            exit_price = abs(mv) / qty if (mv and qty) else entry
            pl, pct = exits.compute_pl(entry, exit_price, qty)
            logbook.update_trade_exit(t["trade_id"], round(exit_price, 4),
                                      exits.now_et(), pl, pct, "EOD_FLATTEN")
            notify.exit_alert({"symbol": t["symbol"], "qty": qty,
                               "exit_price": exit_price, "realized_pl": pl,
                               "realized_pl_pct": pct, "exit_reason": "EOD_FLATTEN"})
            self._log(f"FLATTEN {t['symbol']} pl=${pl} ({pct}%)")

    def post_close_summary(self) -> None:
        """Write + send the daily summary once after the close."""
        today = exits.now_et().date()
        if self.summarized_on == today or self.dry_run:
            return
        equity_close = broker.account_summary()["equity"]
        summ = logbook.write_daily_summary(today, equity_open=self.equity_open,
                                           equity_close=equity_close)
        notify.daily_summary_alert(summ)
        self.summarized_on = today
        self._log("daily summary written")

    # --- one tick (market open) ---
    def tick(self, now: datetime | None = None) -> None:
        now = now or exits.now_et()
        try:
            self.manage_exits()
            if exits.past_flatten_time(now):
                if self.flattened_on != now.date():
                    self.eod_flatten()
                    self.flattened_on = now.date()
            else:
                self.consider_entries(now)
        except Exception as exc:  # noqa: BLE001 - one bad tick must not kill the loop
            msg = f"tick error: {type(exc).__name__}: {exc}"
            self._log(msg)
            self._log(traceback.format_exc())
            notify.error_alert(msg)

    # --- shutdown ---
    def _install_signal_handlers(self) -> None:
        def handler(signum, _frame):
            self._log(f"signal {signum} received — shutting down")
            self.running = False
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _sleep(self, seconds: float) -> None:
        """Interruptible sleep so shutdown is responsive."""
        end = time.monotonic() + seconds
        while self.running and time.monotonic() < end:
            time.sleep(min(1.0, end - time.monotonic()))

    # --- main loop ---
    def run(self) -> None:
        self._install_signal_handlers()
        self._log(f"USTradeWisBot starting (dry_run={self.dry_run})")
        notify.heartbeat(f"USTradeWisBot started (paper={broker.account_summary()['paper']})")

        while self.running:
            try:
                clock = broker.get_clock()
                if clock.is_open:
                    if not self.market_was_open:
                        self.market_was_open = True
                        self.equity_open = broker.account_summary()["equity"]
                        self.summarized_on = None
                        self.flattened_on = None
                        notify.heartbeat(f"Market open — equity ${self.equity_open:,.2f}")
                        self._log("market open")
                    self.tick()
                    self._sleep(config.POLL_INTERVAL_SEC)
                else:
                    if self.market_was_open:
                        self.market_was_open = False
                        self.post_close_summary()
                        self._log("market closed")
                    # Sleep until next open (capped so shutdown stays responsive).
                    wait = (clock.next_open - clock.timestamp).total_seconds()
                    self._log(f"market closed — sleeping ~{max(0, int(wait))}s until next open")
                    self._sleep(min(max(wait, 30), 3600))
            except Exception as exc:  # noqa: BLE001 - loop must survive transient failures
                self._log(f"loop error: {type(exc).__name__}: {exc}")
                self._sleep(config.POLL_INTERVAL_SEC)

        notify.heartbeat("USTradeWisBot stopped")
        self._log("stopped")


def run(dry_run: bool = False) -> None:
    Engine(dry_run=dry_run).run()
