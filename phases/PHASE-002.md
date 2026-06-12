# PHASE-002 — Underlying-equivalence guard (GOOG/GOOGL traded as one stock)

**Date:** 2026-06-12
**Type:** bugfix (risk gate) — entry-blocking only, cannot increase risk

## Objective

Stop the bot from treating share classes of the same company (GOOG / GOOGL) as
independent symbols. Holding or recently exiting any share class must block
entries in every other share class of that underlying.

## Analysis — today's evidence (2026-06-12)

7 closed trades, 4W:3L, net **−$166.39** (−1.99%). PF on the day < 1 despite a
positive win count because the three losers (−$142.35, −$128.79, −$121.86)
dwarfed the winners (avg +$56.65).

| # | sym | in | out | exit | P&L |
|---|-----|----|----|------|-----|
| 57 | TSM | 09:30 | 15:55 | EOD_FLATTEN | +34.39 |
| 58 | GOOG | 09:30 | 11:24 | TAKE_PROFIT | +119.97 |
| 59 | SE | 09:30 | 09:40 | STOP | −142.35 |
| 60 | META | 09:31 | 09:45 | STOP | −121.86 |
| 61 | BAC | 09:32 | 15:55 | EOD_FLATTEN | +23.25 |
| 62 | **GOOGL** | **11:25** | 12:02 | STOP | **−128.79** |
| 63 | INTC | 12:08 | 15:55 | EOD_FLATTEN | +49.00 |

Trade #62: GOOG hit take-profit at **11:24:48**; the bot entered **GOOGL at
11:25:27** — 39 seconds later, same company, at the local top of the very move
it had just sold. GOOGL then fell −1.6% to its stop. The 30-minute
`REENTRY_COOLDOWN_MIN` and `MAX_ENTRIES_PER_SYMBOL_PER_DAY` throttles never
fired because they key on the raw ticker, and `GOOG != GOOGL`.

## Root cause

The DB watchlist contains both GOOG and GOOGL. Three independent gates all key
on the literal ticker string:

1. Re-entry cooldown (`engine.consider_entries`, activity lookup by symbol)
2. Per-symbol daily entry cap (same lookup)
3. Already-held skip (`sizing.plan_position`, `symbol in held_symbols`)

Recurring damage (all GOOG/GOOGL trades, 06-09 → 06-12): **7 trades, −$407.48
combined.** Worst structural case: on 06-10 the bot held GOOG (10:18–10:45)
and GOOGL (09:58–10:48) **simultaneously** — double exposure to one company,
silently defeating the spirit of `MAX_CONCURRENT_POSITIONS=3` diversification.
Today's #62 is the cooldown variant of the same defect.

## Improvement

- `bot/config.py`: new `EQUIVALENT_UNDERLYINGS = [{"GOOG", "GOOGL"}]` plus
  `equivalent_symbols(symbol)` helper (returns the share-class group, or
  `{symbol}` itself).
- `bot/engine.py` (`consider_entries`): for each candidate,
  1. skip if any equivalent symbol is currently held
     (`detail="underlying_held_<sym>"`);
  2. apply the re-entry throttle to the activity aggregated across the
     equivalence group (entries summed, last_exit = max).

No other behavior changes. For every symbol without an equivalence group the
aggregation degenerates to the existing single-symbol logic.

## Expected impact

- Removes a recurring loss source: −$407 over 4 sessions (~22% of the account's
  total −$1,809 drawdown) came from GOOG/GOOGL, most of it from
  duplicate/instant-re-entry patterns this guard blocks (#62 today, both 06-10
  duplicates).
- Eliminates hidden 2× single-name concentration → lower drawdown variance.
- No effect on win rate of unrelated symbols; pure entry filter.

## Risk assessment

- Entry-blocking only — it can only *reduce* exposure. All capital-protection
  invariants untouched (paper endpoint, MAX_RISK_PCT, DAILY_LOSS_HALT_PCT 8.0,
  MAX_CONCURRENT_POSITIONS 3, no-overnight rules).
- Worst case: a genuinely good second-class signal is skipped — acceptable;
  the two classes are ~0.99 correlated, so no real opportunity is lost.
- Group list is explicit and tiny; no fuzzy matching, no surprise blocks.

## Validation plan

- New `tests/test_underlying_guard.py`: config helper unit tests + engine-level
  regression tests reproducing today's #62 (cooldown across classes) and the
  06-10 simultaneous-hold case, with a control proving unrelated symbols pass.
- Full pytest suite, `scripts.smoke_test`, import checks — no regressions.
