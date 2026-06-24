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
        self.halted_on: date | None = None

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
        today = now.date()

        # --- #1 Daily-loss circuit breaker: halt new entries once the day's
        # realized loss reaches DAILY_LOSS_HALT_PCT of session-open equity. ---
        baseline = self.equity_open or equity
        realized = logbook.get_today_realized_pl(today)
        halt_at = -abs(baseline * config.DAILY_LOSS_HALT_PCT / 100.0)
        if baseline > 0 and realized <= halt_at:
            if self.halted_on != today:
                self.halted_on = today
                msg = (f"Daily-loss halt: realized ${realized:,.2f} "
                       f"({realized / baseline * 100:+.2f}%) hit the "
                       f"-{config.DAILY_LOSS_HALT_PCT:.1f}% limit — no new entries today.")
                self._log(msg)
                notify.error_alert(msg)
            return actions

        # Held = filled Alpaca positions UNION symbols with an OPEN logbook trade.
        # The logbook union closes the unfilled-order race: a bracket submitted on
        # one tick may not yet be a filled Alpaca position on the next, which on
        # 2026-06-15 let ENPH be entered twice 74s apart (-$117.59). IMP-001.
        held = broker.open_position_symbols() | logbook.open_trade_symbols()
        open_count = len(held)

        # --- #2 Re-entry throttle inputs: per-symbol entry count + last exit. ---
        activity = logbook.get_symbol_activity_today(today)
        now_naive = now.astimezone(config.MARKET_TZ).replace(tzinfo=None)

        scored = sorted(
            ((confidence.score(ev), ev) for ev in signals.evaluate_watchlist()),
            key=lambda x: x[0], reverse=True,
        )
        for conf, ev in scored:
            if open_count >= config.MAX_CONCURRENT_POSITIONS:
                break
            if conf < config.MIN_CONFIDENCE or not ev.get("signal_type"):
                continue
            # Underlying-equivalence guard (#3): share classes count as one
            # stock for the held-skip, the daily cap and the cooldown.
            equiv = config.equivalent_symbols(ev["symbol"])
            held_equiv = equiv & held
            if held_equiv:
                actions.append({"symbol": ev["symbol"], "confidence": conf,
                                "action": "skip",
                                "detail": f"underlying_held_{sorted(held_equiv)[0]}"})
                continue
            # Re-entry throttle: daily per-symbol cap + cooldown after last
            # exit, aggregated across the equivalence group.
            acts = [activity[s] for s in equiv if s in activity]
            if acts:
                entries = sum(a["entries"] for a in acts)
                if entries >= config.MAX_ENTRIES_PER_SYMBOL_PER_DAY:
                    actions.append({"symbol": ev["symbol"], "confidence": conf,
                                    "action": "skip", "detail": "max_entries_per_symbol"})
                    continue
                exits_seen = [a["last_exit"] for a in acts if a["last_exit"] is not None]
                if exits_seen:
                    mins_since = (now_naive - max(exits_seen)).total_seconds() / 60.0
                    if mins_since < config.REENTRY_COOLDOWN_MIN:
                        wait = int(config.REENTRY_COOLDOWN_MIN - mins_since)
                        actions.append({"symbol": ev["symbol"], "confidence": conf,
                                        "action": "skip", "detail": f"cooldown_{wait}m"})
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
    def eod_flatten(self) -> bool:
        """Force-close everything; mark confirmed-flat trades EOD_FLATTEN.

        Returns True only when the broker is verified flat (no positions left).
        A trade is closed in the logbook ONLY once its broker position is gone;
        any position that did not liquidate stays OPEN and raises an alert, and
        the caller leaves flattened_on unset so the next tick retries instead of
        stranding it overnight (the 06-16 C/AMZN/BAC two-night naked hold). IMP-002.
        """
        open_trades = logbook.get_open_trades()
        if self.dry_run:
            self._log(f"[dry] would flatten {len(open_trades)} open trade(s)")
            return True
        snapshot = {s["symbol"]: s for s in exits.flatten_all("EOD_FLATTEN")}
        remaining = {s.upper() for s in broker.open_position_symbols()}
        for t in open_trades:
            if t["symbol"].upper() in remaining:
                continue  # liquidation unconfirmed — leave OPEN, retry next tick
            qty = int(t["qty"]) or 0
            recorded_entry = float(t["entry_price"])
            # Price the entry off the REAL bracket fill, not the recorded signal
            # price. On 2026-06-24 BAC/CRM/WMT filled 0.04-0.69 above their
            # recorded entries, so the DB booked -$61.34 while the broker truth
            # was -$87.08 (~42% of the loss hidden). detect_exits already prices
            # STOP/TP off the parent fill; this gives the flatten path parity.
            # Falls back to the recorded entry if the lookup yields nothing. IMP-005.
            entry_fill = broker.entry_fill_price(t.get("alpaca_order_id"))
            entry = entry_fill if entry_fill is not None else recorded_entry
            # Record the REAL liquidation fill. The prior market-value/entry
            # fallback booked SPY/QQQ/TSM at exit==entry ($0.00) on 2026-06-22
            # while the actual flatten sells filled at 744.12/737.18/466.222
            # (~$60 hidden loss in one day). Order-lookup first, then the
            # pre-flatten market-value approximation, then entry. IMP-003.
            fill = broker.latest_filled_exit_price(t["symbol"])
            snap = snapshot.get(t["symbol"])
            mv = snap.get("market_value") if snap else None
            if fill is not None:
                exit_price = fill
            elif mv and qty:
                exit_price = abs(mv) / qty
            else:
                exit_price = entry
            pl, pct = exits.compute_pl(entry, exit_price, qty)
            corrected_entry = (round(entry, 4)
                               if entry_fill is not None and round(entry, 4) != round(recorded_entry, 4)
                               else None)
            logbook.update_trade_exit(t["trade_id"], round(exit_price, 4),
                                      exits.now_et(), pl, pct, "EOD_FLATTEN",
                                      entry_price=corrected_entry)
            notify.exit_alert({"symbol": t["symbol"], "qty": qty,
                               "exit_price": exit_price, "realized_pl": pl,
                               "realized_pl_pct": pct, "exit_reason": "EOD_FLATTEN"})
            self._log(f"FLATTEN {t['symbol']} pl=${pl} ({pct}%)")
        if remaining:
            msg = (f"EOD flatten incomplete — {len(remaining)} position(s) still "
                   f"open after liquidation: {sorted(remaining)}. Retrying next tick.")
            self._log(msg)
            notify.error_alert(msg)
            return False
        return True

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
                    # Only mark the day flattened once the broker is verified
                    # flat; an incomplete flatten retries on the next tick rather
                    # than stranding a position overnight (IMP-002).
                    if self.eod_flatten():
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
                        self.halted_on = None
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
