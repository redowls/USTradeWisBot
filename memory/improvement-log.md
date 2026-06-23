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
- **Observed effect:** (weekly review 2026-06-19) No same-symbol double-entry has recurred since the fix. Caveat: only lightly exercised — the rest of the week produced just one fresh entry (MU 06-16, single, no dup) before the book went quiet (06-17 no entries, 06-18 only the legacy carried closes, 06-19 holiday). Confirmed not-broken, not yet stress-tested at entry volume. Re-confirm Mon 06-22+.

---

## IMP-002 — 2026-06-18

- **Problem:** Positions opened 06-16 (C/AMZN/BAC) were held for **TWO overnights** (06-16→06-18) — a repeated breach of the no-overnight invariant, flagged by pre-market research three days running. Alpaca order history: at 06-16 15:55 ET **no sell orders fired at all**; at 06-17 15:55 the flatten ran chaotically (burst of ~10 duplicate AMZN market-sells, most auto-canceled, one filled; C/BAC stops canceled but positions NOT liquidated); only 06-18 closed C/BAC. AMZN's logbook P&L was misrecorded as $0.00 (its broker position closed 06-17 but the logbook trade was swept 06-18 with the entry-price fallback).
- **Root cause:** `exits.flatten_all` called fire-and-forget bulk `broker.close_all_positions(cancel_orders=True)`, which (a) races the async order-cancel so `held_for_orders` blocks the liquidation, (b) returns a 207 multi-status the SDK does not raise on (partial failure invisible), and (c) `engine.tick` then set `self.flattened_on = now.date()` **unconditionally** after `eod_flatten()` returned — so a flatten that left positions open was never retried, and the day was declared flat.
- **Change:** `bot/broker.py` — new `close_position(symbol)` (per-symbol DELETE /v2/positions/{symbol}). `bot/exits.py` — `flatten_all` now cancels working orders FIRST, then closes each position individually (so a still-working bracket leg can't block its own liquidation). `bot/engine.py` — `eod_flatten()` returns bool: it re-queries `open_position_symbols()` after liquidation, marks a logbook trade CLOSED **only** once its broker position is confirmed gone, leaves any unconfirmed position OPEN + fires `error_alert`, and returns False; `tick()` sets `flattened_on` **only when `eod_flatten()` returns True** → an incomplete flatten retries next tick instead of stranding overnight. No risk limit altered (paper endpoint, MAX_RISK_PCT, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight rules all untouched — this strengthens the no-overnight rule).
- **Validation:** New `tests/test_eod_flatten.py` (6 tests) replays the 06-16→06-18 scenario: cancel-before-close ordering, one position raising must not stop the rest, BAC-stays-open→retry/alert, C-confirmed-flat→closed at recorded 143.765, dry-run no-op, and tick-gating retry. Full suite **35 passed**; `scripts.smoke_test` ALL GREEN; `scripts.check_engine` ALL GREEN. Service restarted clean.
- **Expected impact:** Eliminates silent naked-overnight holds: any position that does not confirm flat at 15:55 keeps being re-liquidated each tick and raises an alert, instead of being declared flat and stranded. Directly prevents the repeat of the 06-16 two-night hold.
- **Commit:** 427ab21
- **Observed effect:** (weekly review 2026-06-19) NOT yet validated in production. Shipped 06-18, *after* the 06-16→06-18 breach it targets. The 06-18 15:55 flatten that finally cleared the legacy carried book (C/BAC) ran under the new code and succeeded, but that was closing stranded positions, not the real test: no position has been opened-and-flattened same-day under this logic yet (06-18 took no new entries; 06-19 Juneteenth holiday). First true test is Mon 06-22 — verify any position opened then is confirmed flat by 15:55 ET with no carry into Tue 06-23. Verdict pending. **→ VALIDATED 2026-06-22:** SPY/QQQ/TSM were opened intraday and the 15:56:50 ET flatten market-sold all three (cancel-legs-first, then per-symbol close), Alpaca confirmed 0 open positions, no carry into 06-23. The 06-16→06-18 naked-hold class did not recur. ✅ PASS.

---

## IMP-003 — 2026-06-22

- **Problem:** 06-22 was the first session with same-day EOD flattens under IMP-002. The 3 EOD_FLATTEN trades (SPY #77, QQQ #78, TSM #79) were each recorded with **exit_price == entry_price → $0.00 P&L**, so the DB reported the day as **+$238.05 / 2W2L**. Alpaca's filled SELL orders show the real flatten fills were SPY @744.12, QQQ @737.18, TSM @466.222 — a combined **−$60.38** that was booked as zero. Broker equity moved +$176.67 (7838.56→8015.23) while the DB claimed +$238.05: a ~$61 P&L overstatement in one day. This corrupts the evidence base every routine reads (daily review, report, pre-market) and masked the conf-60–63 MA-only drag.
- **Root cause:** `engine.eod_flatten` derived the exit price from a pre-liquidation `_position_snapshot` `market_value` (`exit_price = abs(mv)/qty`) and fell back to the **entry price** when `mv` was missing/zero — `exit_price = abs(mv)/qty if (mv and qty) else entry`. For all 3 trades the `else entry` branch fired (exit==entry to the penny), and even when `mv` is present it is only a pre-flatten approximation, not the actual fill. The real liquidation fill was never consulted. (This is backlog item 0a, deferred from IMP-002 to keep that change focused; AMZN's 06-18 $0.00 was the same bug, first instance.)
- **Change:** `bot/broker.py` — new `latest_filled_exit_price(symbol)` (GET /v2/orders, CLOSED + SELL, newest-first; returns the first `filled_avg_price`, skipping canceled bracket legs that carry none). `bot/engine.py` — `eod_flatten` now records `exit_price = real fill if available, else market_value/qty, else entry` (the mv/entry paths are last-resort fallbacks only). Pure measurement-integrity fix — no risk limit touched (paper endpoint, MAX_RISK_PCT, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all unchanged). Also backfilled today's 3 trade rows + re-aggregated daily_summary to the true fills (gross +$177.67, 2W/5L, +2.27%).
- **Validation:** `tests/test_eod_flatten.py` +2 tests (37 passed total): `test_eod_flatten_records_real_fill_not_entry_price` replays SPY 06-22 (no mv in snapshot → must book the real 744.12 fill, P&L −15.06, never the entry-price $0.00) and `test_eod_flatten_real_fill_overrides_market_value` (real fill wins over a stale mv estimate). Existing mv-fallback tests preserved (harness defaults `latest_filled_exit_price`→None). `scripts.smoke_test` ALL GREEN, `scripts.check_engine` ALL GREEN. **CORRECTION (2026-06-23 00:58 UTC):** the "restarted clean" claim made on 06-22 did not take effect — the live process kept running pre-fix code (systemd ActiveEnterTimestamp stayed at 06-22 11:48 UTC, before the 21:29 engine.py edit), so the 0.0%-fallback bug remained live through the 06-22 close. The IMP-003 fix only went live on the 06-23 00:57:56 UTC restart (verified: new start time > engine.py mtime, clean startup log, 8/8 tests pass). Next EOD flatten will record real fills.
- **Expected impact:** Every EOD_FLATTEN exit is now recorded at its actual broker fill, so daily P&L / win-loss / expectancy are truthful. No effect on trade selection or risk — purely fixes the books the whole improvement loop reads.
- **Commit:** (filled below)
- **Observed effect:** (pending — re-confirm on the next session that has EOD flattens that the recorded exit matches the Alpaca fill.) **→ VERIFIED 2026-06-23:** all 3 EOD_FLATTEN trades (XOM/BAC/WMT) booked their real Alpaca sell fills (140.12 / 57.91 / 119.81), no exit==entry $0.00. ✅ PASS.

---

## IMP-004 — 2026-06-23

- **Problem:** The standing "next to act on" candidate — *raise `MIN_CONFIDENCE` for the MA-only class to ~65* (flagged 06-15 & 06-22 as "the conf-60–63 MA-only drag") — would have been a harmful change, and the daily report was missing the metrics that prove it. On 06-23 **all 4 winners were MA-only at conf 60–62** (XOM 62.0/+19.57, BAC 61.0/+16.56, CRM 61.5/+57.69, WMT 60.2/+1.98) = 100% of a +$95.80 day. Full-history check: **MA-only is the least-bad bucket** (PF 0.75, exp −$4.75) and **no MA signal has ever scored ≥64**, so a 65 floor disables the entire MA book (kills all 16 MA winners); simulating "drop MA<65" worsens the portfolio (exp −$19.78 → −$41.64, PF 0.45 → 0.31). The confidence→quality axis is inverted from the old read: the 66+ band (all BOTH) lost −$1,227/PF 0.31 while 62–64 is ~break-even (PF 1.06). The report's "By signal type" table (no PF, no confidence bands) hid all of this, letting a harmful candidate survive 3 sessions.
- **Root cause:** Missing measurement. `analytics.compute_metrics` exposed per-signal-type win%/total$/exp$ but **no profit factor and no confidence-band breakdown**, so reviews leaned on within-day anecdote (TSLA-the-BOTH-winner) and mislabeled MA-only as the drag / BOTH as the edge. An evidence gap, not a trading bug.
- **Change:** `bot/analytics.py` — new `_bucket()` helper (win%/total$/exp$/**profit_factor** over any P&L slice); `by_signal_type` now carries `profit_factor`; new `by_confidence_band` metric over `CONFIDENCE_BANDS` (<60 / 60-62 / 62-64 / 64-66 / 66+). `scripts/report.py` — prints a **PF** column in the by-signal-type table and a new **"By confidence band"** section. `todo.md` — recorded the refuted candidate under a new "Refuted / closed candidates" section so it can't be silently reopened. Pure measurement/tooling — NO entry logic, NO sizing, NO risk limit touched (paper endpoint, MAX_RISK_PCT, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all unchanged).
- **Validation:** New `tests/test_analytics.py` (5 tests) replays the real 06-23 scenario: today's 4 MA winners land in the 60-62/62-64 bands, the 64-66/66+ bands are empty, "raise floor to 65 drops every trade", MA PF > BOTH PF, empty-input safety. Full suite **42 passed** (was 37). `scripts.report --selftest` ALL GREEN, `scripts.smoke_test` ALL GREEN. Live `scripts.report` renders both new sections correctly.
- **Expected impact:** No effect on trade selection or P&L — it fixes the evidence base every routine reads, retires a refuted (harmful) candidate, and surfaces the inverted confidence→performance relationship for genuine future strategy work.
- **Commit:** f324b14
- **Observed effect:** (n/a — reporting change; confirm future reviews cite PF-by-type / confidence bands instead of re-proposing a confidence floor.)

---
