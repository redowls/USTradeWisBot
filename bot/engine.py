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
    broker, config, confidence, data, exits, execution, logbook, notify, signals,
    sizing,
)

# 1-min bars pulled per tick for the break-even high-water mark (IMP-031). A
# regular session is 390 minutes, so this always spans the whole day back to the
# earliest possible entry, and the batched call covers at most
# MAX_CONCURRENT_POSITIONS symbols.
RATCHET_HIGH_BARS = 390


def _px(value) -> str:
    """Price for a log/alert line, never raising on a missing or odd value."""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "unknown"


class Engine:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.running = True
        self.market_was_open = False
        self.equity_open: float | None = None
        self.flattened_on: date | None = None
        self.summarized_on: date | None = None
        self.halted_on: date | None = None
        # (trade_date, symbol) already alerted as unprotected — one Telegram
        # alert per position, not one per 60s poll. IMP-038.
        self._naked_alerted: set[tuple[date, str]] = set()

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

    # --- break-even / trailing stop (IMP-013) ---
    def manage_stops(self, now: datetime | None = None) -> list[dict]:
        """Ratchet bracket stop legs up on trades that are in profit.

        +0.5R -> stop to entry (break-even); +1R -> trail 1R below the live
        price. State lives at the broker: the current stop is read off the leg
        (following the replace chain) every tick, so nothing is lost across the
        nightly restart, and the DB stop_price stays the ORIGINAL plan stop —
        it is the risk anchor that defines 1R.

        The break-even test reads the highest price PRINTED since entry, not
        just this tick's last trade (IMP-031) — one batched 1-min bar call for
        the <= MAX_CONCURRENT_POSITIONS open symbols. Fails open: no bars means
        no `high_price`, i.e. exactly the previous last-trade-only behaviour.

        A stop leg that will not resolve is NOT the same thing as a closed
        position: Alpaca's OCO releases the stop the moment the take-profit
        limit becomes marketable, and on 10 of the book's 27 TAKE_PROFIT exits
        the limit then took 0.8s-26m34s to fill, leaving a live long with no
        working stop. That state is now checked against the broker's own
        position list and enforced rather than skipped in silence. IMP-038.

        A stop leg that FILLED is not that state and is skipped before the
        position list is consulted: the stop is what closed the trade, and the
        position list lags it by a fraction of a second (UNH #275, 2026-08-21).
        IMP-039.
        """
        if not config.TRAILING_STOP_ENABLED:
            return []
        actions: list[dict] = []
        open_trades = logbook.get_open_trades()
        if not open_trades:
            return actions
        held: set[str] | None = None  # broker positions, fetched at most once
        try:
            session_bars = data.get_bars_for_symbols(
                sorted({t["symbol"] for t in open_trades}),
                n_bars=RATCHET_HIGH_BARS, timeframe="1Min",
            )
        except Exception as exc:  # noqa: BLE001 - the ratchet must still run
            self._log(f"manage_stops bar fetch failed: {type(exc).__name__}: {exc}")
            session_bars = {}
        for t in open_trades:
            oid = t.get("alpaca_order_id")
            if not oid:
                continue
            try:
                parent = execution.get_order(oid)
                entry_fill = parent.filled_avg_price
                if entry_fill is None:
                    continue  # entry not filled yet — nothing at risk
                entry = float(entry_fill)
                stop_leg = exits.resolve_stop_leg(parent, execution.get_order)
                if stop_leg is None:
                    # The leg is gone. Either the position closed (the ordinary
                    # TP/STOP path) or it is open and unprotected. IMP-038.
                    if exits.stop_leg_filled(parent, execution.get_order):
                        # ...or the stop itself is what closed it, and the
                        # broker's position list has not caught up yet. That is
                        # an exit in progress, not a naked long. IMP-039.
                        continue
                    if held is None:
                        held = self._held_symbols()
                    act = self._handle_naked_position(t, parent, held)
                    if act is not None:
                        actions.append(act)
                    continue
                current_stop = float(stop_leg.stop_price)
                live = data.latest_trade_price(t["symbol"])
                peak = exits.peak_high_since(
                    session_bars.get(t["symbol"]), t.get("entry_time"),
                )
                new_stop = exits.compute_trailed_stop(
                    entry, float(t["stop_price"]), current_stop, live, peak,
                )
                if new_stop is None:
                    continue
                if self.dry_run:
                    self._log(f"[dry] would raise stop {t['symbol']} "
                              f"{current_stop:.2f} -> {new_stop:.2f}")
                    continue
                res = execution.replace_stop_order(str(stop_leg.id), new_stop)
                if res["ok"]:
                    actions.append({"symbol": t["symbol"], "action": "stop_raised",
                                    "from": current_stop, "to": new_stop,
                                    "order_id": res["order_id"]})
                    self._log(f"STOP RAISED {t['symbol']} {current_stop:.2f} -> "
                              f"{new_stop:.2f} (live {live:.2f}, "
                              f"peak {peak if peak is None else round(peak, 2)}, "
                              f"entry {entry:.2f})")
                else:
                    # Old stop still working — position stays protected; retry
                    # next tick off the freshly-resolved leg.
                    self._log(f"STOP RAISE FAILED {t['symbol']}: {res['error']}")
            except Exception as exc:  # noqa: BLE001 - one symbol must not stop the rest
                self._log(f"manage_stops error {t.get('symbol')}: "
                          f"{type(exc).__name__}: {exc}")
        return actions

    # --- naked-position protection (IMP-038) ---
    def _held_symbols(self) -> set[str]:
        """Symbols the BROKER says we are long right now; empty set on failure.

        Failing to an empty set is deliberate: it reproduces the pre-IMP-038
        behaviour (treat a missing stop leg as a closed position) rather than
        alerting or liquidating on an API hiccup.
        """
        try:
            return {s.upper() for s in broker.open_position_symbols()}
        except Exception as exc:  # noqa: BLE001 - never break the ratchet loop
            self._log(f"naked-position check failed: {type(exc).__name__}: {exc}")
            return set()

    def _handle_naked_position(self, trade: dict, parent, held: set[str]) -> dict | None:
        """Alert on — and if price has breached, close — an unprotected long.

        Enforcement is deliberately narrow: it fires only when the tape is
        already at or below the trade's ORIGINAL plan stop, i.e. only when the
        broker's stop would have fired had it still existed. It never invents a
        tighter stop, never touches a protected position, and never widens risk.

        The sibling limit leg is cancelled FIRST — a working bracket leg holds
        the shares (held_for_orders) and would reject the liquidation, which is
        the 2026-06-16 C/AMZN/BAC failure that IMP-002 fixed for the EOD path.
        Cancelling before selling also rules out both legs filling, which would
        flip the account short.

        The DB exit record is left to the existing 15:55 flatten path, which
        prices any trade whose broker position is gone off the REAL fill
        (IMP-003/IMP-005). That books it as EOD_FLATTEN rather than STOP —
        accepted knowingly: the P&L is correct and same-session, and inventing
        a second booking path for a branch that has never fired in 256 trades
        is how the flatten path earned five separate bug fixes.
        """
        symbol = str(trade["symbol"]).upper()
        live = data.latest_trade_price(symbol)
        plan_stop = trade.get("stop_price")
        action = exits.naked_position_action(symbol in held, live, plan_stop)
        if action == exits.NAKED_NONE:
            return None
        live_txt = _px(live)
        stop_txt = _px(plan_stop)
        msg = (f"UNPROTECTED {symbol}: position open with no working bracket "
               f"stop leg (live {live_txt}, plan stop {stop_txt})")
        key = (exits.now_et().date(), symbol)
        if key not in self._naked_alerted:
            self._naked_alerted.add(key)
            self._log(msg)
            if not self.dry_run:
                notify.error_alert(msg)
        if action != exits.NAKED_ENFORCE:
            return None
        if self.dry_run:
            self._log(f"[dry] would enforce plan stop on {symbol}")
            return None
        limit_leg_id = exits.resolve_limit_leg_id(parent)
        if limit_leg_id:
            try:
                execution.cancel_order(limit_leg_id)
            except Exception as exc:  # noqa: BLE001 - the close below is the priority
                self._log(f"naked-position cancel failed {symbol}: "
                          f"{type(exc).__name__}: {exc}")
        try:
            broker.close_position(symbol)
        except Exception as exc:  # noqa: BLE001 - retried on the next poll
            self._log(f"SOFT STOP FAILED {symbol}: {type(exc).__name__}: {exc}")
            return None
        self._log(f"SOFT STOP {symbol}: liquidated at market — live {live_txt} "
                  f"at/below plan stop {stop_txt} with no stop leg")
        return {"symbol": symbol, "action": "soft_stop",
                "live": live, "plan_stop": float(plan_stop)}

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
            # --- Eligibility BEFORE quality (IMP-042) ---
            # The held-skip, the daily cap and the cooldown answer "could this
            # candidate be bought at all?"; the VWAP gate answers "is this a good
            # price?". Asking the second question first is outcome-identical (both
            # branches `continue`) but it MIS-ATTRIBUTES the refusal: an ineligible
            # symbol that happens to be stretched is logged and recorded as a VWAP
            # refusal, and IMP-033's refused-candidate replay in
            # scripts/gate_monitor.py then prices a counterfactual entry the engine
            # could never have taken. 2026-08-26: TSM was in the book from 09:36 to
            # the 15:55 flatten, and the gate still logged 9 `ENTRY SKIPPED TSM`
            # lines (13:57-14:25) — 29% of the session's 31 refusals — with the
            # 13:57 one becoming that day's `_first_blocked` TSM candidate. Over the
            # 8 sessions of retained logs, 4 of 45 first-blocked candidates (8.9%)
            # and 37 of 389 raw refusal lines (9.5%) were symbols the bot already
            # held. Eligibility first makes the gate's workload and its measured
            # opportunity cost mean what every review has been reading them as.
            # Strictly a measurement fix: no entry is gained or lost by it, so
            # IMP-040's open ratchet window is untouched.
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
            # --- VWAP entry-quality gate (IMP-022) ---
            # Skip fills stretched more than VWAP_MAX_DIST_PCT above the symbol's
            # session VWAP: entry-vs-session-VWAP is the one clean separator of the
            # open-fade leak (recorded-trade holdout IMP-019/020 + a from-scratch
            # 30-day backtest both agree). Fills at/below VWAP hold; stretched-above
            # fills fade to the stop. Fail-open when VWAP is undefined.
            vwap_dist = sizing.vwap_distance_pct(ev.get("close"), ev.get("session_vwap"))
            if vwap_dist is not None and vwap_dist > config.VWAP_MAX_DIST_PCT:
                actions.append({"symbol": ev["symbol"], "confidence": conf,
                                "action": "skip",
                                "detail": f"above_vwap_+{vwap_dist:.2f}%"})
                self._log(f"ENTRY SKIPPED {ev['symbol']}: entry {ev['close']:.2f} is "
                          f"+{vwap_dist:.2f}% above session VWAP "
                          f"{ev['session_vwap']:.2f} (>{config.VWAP_MAX_DIST_PCT}% — "
                          f"stretched fill, fades)")
                continue
            plan = sizing.plan_position(
                ev["symbol"], conf, ev["close"] or 0.0, ev["atr"] or 0.0,
                equity, buying_power, held_symbols=held, open_positions_count=open_count,
            )
            if not plan.tradable:
                actions.append({"symbol": plan.symbol, "confidence": conf,
                                "action": "skip", "detail": plan.skip_reason})
                continue
            # --- Stale-signal / gap guard (IMP-008; symmetric IMP-009) ---
            # entry/stop/TP are anchored to the signal-bar close, but the order
            # is a MARKET buy filling at the live price. If the live price has
            # moved more than MAX_ENTRY_SLIPPAGE_PCT from the signal close in
            # EITHER direction the bracket is mispriced against the real fill:
            #   * gap UP   -> the TP (>= ~entry*1.0225) can land below the live
            #     price and Alpaca 422s the whole bracket (AMD 06-30: signal
            #     ~542, live 554.29, entry silently lost).
            #   * gap DOWN -> the stop (anchored ~1.5% below the signal close)
            #     lands at/above the live price and Alpaca 422s it just the same
            #     (NVDA 07-01: base_price 195.02, "stop_loss.stop_price must be
            #     <= base_price - 0.01"); a shallower down-gap is accepted but
            #     the stop is compressed to a hair-trigger AND the breakout
            #     premise has already failed (price back below the level).
            # Either way skip the chase. Fail-open: a missing live price leaves
            # prior behavior unchanged.
            live = data.latest_trade_price(plan.symbol)
            slip = sizing.entry_slippage_pct(live, plan.entry_price)
            if slip is not None and abs(slip) > config.MAX_ENTRY_SLIPPAGE_PCT:
                direction = "up" if slip > 0 else "down"
                actions.append({"symbol": plan.symbol, "confidence": conf,
                                "action": "skip",
                                "detail": f"stale_signal_gap_{direction}_{slip:+.2f}%"})
                self._log(f"ENTRY SKIPPED {plan.symbol}: live {live:.2f} is "
                          f"{slip:+.2f}% vs signal entry {plan.entry_price:.2f} "
                          f"(|move|>{config.MAX_ENTRY_SLIPPAGE_PCT}% — stale-signal "
                          f"gap {direction}; stop/TP would be mispriced)")
                continue
            # --- Live-risk re-size (IMP-037) ---
            # The bracket is anchored to the signal close but fills live, so an
            # accepted up-move inside the guard band above leaves the stop
            # further from the real fill than the sizer assumed — risk per share
            # becomes stop_distance + move while the share count still divides
            # by stop_distance. IMP-008 named this ("silently inflating
            # per-share risk above the plan") and fixed only the skip case.
            # 106 of 253 closed trades (41.9%) risked more than their budget,
            # worst +72.5%. Clamped to min(planned, live-risk) so it can only
            # ever REDUCE size; a favourable fill never buys more.
            resized = sizing.resize_for_live_risk(plan, live, equity)
            if not resized.tradable:
                actions.append({"symbol": resized.symbol, "confidence": conf,
                                "action": "skip", "detail": resized.skip_reason})
                continue
            if resized.shares != plan.shares:
                self._log(f"SIZE REDUCED {plan.symbol}: {plan.shares} -> "
                          f"{resized.shares} shares (live {live:.2f} vs signal "
                          f"{plan.entry_price:.2f}; real risk/share "
                          f"{live - plan.stop_price:.4f} vs planned "
                          f"{plan.stop_distance:.4f})")
            plan = resized
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
        # A rejected liquidation used to be swallowed silently, which is how a
        # 100%-failure-rate first pass hid for 10 straight sessions. IMP-033.
        for sym, snap in snapshot.items():
            if snap.get("flatten_error"):
                self._log(f"FLATTEN REJECTED {sym}: {snap['flatten_error']}")
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

    def flatten_watchdog(self) -> None:
        """Clock-independent EOD flatten, for ticks the main loop never reached.

        `broker.get_clock()` gates every tick from OUTSIDE `tick()`'s own error
        handling, so a transient API failure in the 15:55-16:00 window skips the
        flatten entirely — that window is only five ticks wide, and bursts of 8+
        consecutive loop failures are on record (2026-08-01). The first true
        intraday failures landed 2026-08-05 13:55/13:56 ET; the same burst an
        hour later would have carried QQQ/WMT overnight, and today's flatten
        already needed three attempts. Falls back to the local ET wall clock so
        the no-overnight rule never depends on a network call. Never raises — a
        failed retry must not kill the loop. IMP-026.
        """
        if not self.market_was_open:
            return  # no session in progress — nothing can be stranded
        now = exits.now_et()
        if self.flattened_on == now.date() or not exits.past_flatten_time(now):
            return
        self._log("flatten watchdog — loop failed inside the flatten window, "
                  "flattening on the local ET clock")
        try:
            if self.eod_flatten():
                self.flattened_on = now.date()
        except Exception as exc:  # noqa: BLE001 - watchdog must never kill the loop
            self._log(f"flatten watchdog error: {type(exc).__name__}: {exc}")

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
                self.manage_stops(now)
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
                # The failure above may have been get_clock() itself, which means
                # tick() — and with it the EOD flatten — never ran. IMP-026.
                self.flatten_watchdog()
                self._sleep(config.POLL_INTERVAL_SEC)

        notify.heartbeat("USTradeWisBot stopped")
        self._log("stopped")


def run(dry_run: bool = False) -> None:
    Engine(dry_run=dry_run).run()
