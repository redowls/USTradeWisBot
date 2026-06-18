# Improvement Log

Audit trail of every code/config change shipped by the `uswisbot-daily-review`
routine. One compact entry per improvement (≤15 lines), numbered IMP-001, IMP-002, …
The weekly review reads this to judge whether shipped changes actually helped, and
the pre-market routine reads it for strategy context.

> Prior improvement history (before this model) is in `phases/PHASE-NNN.md` and the
> "Improvement Log" section of `summary.md`. Numbering here starts fresh at IMP-001.

Entry template:

## IMP-NNN — YYYY-MM-DD

- **Problem:** (what today's trades showed)
- **Root cause:**
- **Change:** (files modified, one-line description)
- **Validation:** (tests run, results)
- **Expected impact:**
- **Commit:** (hash)
- **Observed effect:** (filled in by a later review once data exists)

---

## IMP-001 — 2026-06-15

- **Problem:** ENPH was entered twice 74s apart (trades #65 @09:31:22 and #66 @09:32:36, same 55.59/stop 54.44/qty 71). Both stopped out by 09:39 for a combined −$117.59 — the entire day's net loss (−$35.61). Two concurrent positions in one name = doubled, unintended single-name risk.
- **Root cause:** `Engine.consider_entries` derives the de-dup/concurrency guard from `held = broker.open_position_symbols()`, which lists only *filled* Alpaca positions. With `POLL_INTERVAL_SEC=60`, the first ENPH bracket hadn't filled when the next tick queried `held`, so ENPH wasn't seen as held; the entry-count cap (1 < 2) and cooldown (no exit yet) also didn't block it. An unfilled-order race.
- **Change:** `bot/logbook.py` — new `open_trade_symbols()` returning symbols with status OPEN. `bot/engine.py` — `held = broker.open_position_symbols() | logbook.open_trade_symbols()` so a submitted-but-unfilled bracket counts as held. Pure tightening of exposure control; no risk limit altered (paper endpoint, MAX_RISK_PCT, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all untouched).
- **Validation:** Added regression test `test_unfilled_open_trade_blocks_re_entry` (06-15 ENPH replay) to `tests/test_underlying_guard.py`; harness extended with `open_trades` param. Full suite **29 passed**, `scripts.smoke_test` ALL GREEN, `scripts.check_engine` ALL GREEN. Service restarted clean.
- **Expected impact:** Eliminates same-symbol double-entries from fill latency. On today's data this alone removes the −$87.36 duplicate leg → day swings from −$35.61 toward roughly breakeven/positive.
- **Commit:** 5d908bb
- **Observed effect:** (filled in by a later review once data exists)

---

## IMP-002 — 2026-06-18

- **Problem:** Positions opened 06-16 (C/AMZN/BAC) were held for **TWO overnights** (06-16→06-18) — a repeated breach of the no-overnight invariant, flagged by pre-market research three days running. Alpaca order history: at 06-16 15:55 ET **no sell orders fired at all**; at 06-17 15:55 the flatten ran chaotically (burst of ~10 duplicate AMZN market-sells, most auto-canceled, one filled; C/BAC stops canceled but positions NOT liquidated); only 06-18 closed C/BAC. AMZN's logbook P&L was misrecorded as $0.00 (its broker position closed 06-17 but the logbook trade was swept 06-18 with the entry-price fallback).
- **Root cause:** `exits.flatten_all` called fire-and-forget bulk `broker.close_all_positions(cancel_orders=True)`, which (a) races the async order-cancel so `held_for_orders` blocks the liquidation, (b) returns a 207 multi-status the SDK does not raise on (partial failure invisible), and (c) `engine.tick` then set `self.flattened_on = now.date()` **unconditionally** after `eod_flatten()` returned — so a flatten that left positions open was never retried, and the day was declared flat.
- **Change:** `bot/broker.py` — new `close_position(symbol)` (per-symbol DELETE /v2/positions/{symbol}). `bot/exits.py` — `flatten_all` now cancels working orders FIRST, then closes each position individually (so a still-working bracket leg can't block its own liquidation). `bot/engine.py` — `eod_flatten()` returns bool: it re-queries `open_position_symbols()` after liquidation, marks a logbook trade CLOSED **only** once its broker position is confirmed gone, leaves any unconfirmed position OPEN + fires `error_alert`, and returns False; `tick()` sets `flattened_on` **only when `eod_flatten()` returns True** → an incomplete flatten retries next tick instead of stranding overnight. No risk limit altered (paper endpoint, MAX_RISK_PCT, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight rules all untouched — this strengthens the no-overnight rule).
- **Validation:** New `tests/test_eod_flatten.py` (6 tests) replays the 06-16→06-18 scenario: cancel-before-close ordering, one position raising must not stop the rest, BAC-stays-open→retry/alert, C-confirmed-flat→closed at recorded 143.765, dry-run no-op, and tick-gating retry. Full suite **35 passed**; `scripts.smoke_test` ALL GREEN; `scripts.check_engine` ALL GREEN. Service restarted clean.
- **Expected impact:** Eliminates silent naked-overnight holds: any position that does not confirm flat at 15:55 keeps being re-liquidated each tick and raises an alert, instead of being declared flat and stranded. Directly prevents the repeat of the 06-16 two-night hold.
- **Commit:** 427ab21
- **Observed effect:** (filled in by a later review once data exists)

---
