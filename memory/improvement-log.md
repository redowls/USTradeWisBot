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
