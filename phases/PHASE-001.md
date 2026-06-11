# PHASE-001 — Test suite foundation + trade-replay / what-if harness

**Date:** 2026-06-11
**Type:** Tooling only — no strategy change

## Objective

Stand up the validation infrastructure the repo lacked (no tests, no backtest
capability) so future strategy phases can be justified and regression-tested
against recorded data instead of intuition. Capture today's findings.

## Analysis — session 2026-06-11

- 3 closed trades, 1W/2L, net **−$8.50 (−0.10%)** — calmest session yet
  (vs −4.15%, −9.37%, −3.87% the prior three days).
- All 3 signals were MA-type (conf 61.0–62.8), fired 09:30:12–09:57:03 ET;
  all three exited via the 15:55 EOD flatten. **No stop or target fired all
  day** — the bcfdf0e stop-widening (3×ATR, 1.5% floor) is doing its job
  (06-10 had 7/8 stop-outs under 0.8%).
- MAE/MFE from 5-min bars after entry:
  - WMT  120.56 → MFE **+1.05%** @13:30, exit −0.10% (gave back all of it)
  - AAPL 293.56 → MFE **+1.17%** @13:30, exit +0.50% (gave back 0.67pp)
  - COST 985.93 → MFE −0.17% (never positive), exit −0.97% — entered near the
    day high at 09:47, drifted down all session.
- All 3 position slots (MAX_CONCURRENT_POSITIONS=3) were occupied from 09:57
  to 15:55. Only 3 signals fired so nothing was blocked today, but dead
  all-day holds now monopolize capacity under the wide-stop regime.

## Root cause of today's (small) losses

Winners fade un-protected: targets sit at RR 1.5 (+2.25% here) while both
green trades peaked ≈ +0.7R at 13:30 and bled into the flatten. There is no
mechanism between "fixed bracket" and "EOD flatten" — exit reasons in 54
all-time trades are only STOP 40 / TAKE_PROFIT 8 / EOD_FLATTEN 6.

## Why no strategy change tonight

One quiet 3-trade day is not evidence to retune exits, and an ad-hoc
simulation showed bar-level replay noise comparable to the effect size.
Per the ground rules, the highest-impact data-justified phase is the named
tooling option: build the harness that makes the next change provable.

## What was built

- `bot/replay.py` — pure bar-walk simulation core (`simulate_bracket`:
  stop / take-profit / EOD-flatten, optional breakeven-at-+NR what-if;
  stop checked before target within a bar = conservative), plus DB/bars
  loaders and aggregate replay. Unit-testable without network.
- `scripts/replay.py` — CLI: replays all closed trades, prints a **fidelity
  baseline** (replayed current bracket vs recorded P&L = the noise budget)
  and what-if rows for breakeven rules.
- `tests/` (pytest, 22 tests): exits time-gates (15:30 cutoff / 15:55
  flatten invariants), `compute_pl` (incl. today's recorded WMT numbers),
  exit-reason classification, `build_exit_record` on fake orders, sizing
  risk caps (MAX_RISK_PCT ≤ 2.0 invariant, skip funnel, MIN_STOP_PCT floor
  regression for bcfdf0e), and the replay core on synthetic bars + the
  recorded WMT fade scenario.

## Harness output on the full history (52 trades with bars)

```
baseline (current)   sim −$1,410.91  delta vs actual +$152.85  sum|err| $573.95
breakeven at +0.5R   sim   −$847.79  (+$563.12 vs baseline sim)
breakeven at +1.0R   sim −$1,227.09  (+$183.82 vs baseline sim)
27/52 trades reached +0.5R; 15 reached +1R; 7 losers saw +1R before stopping.
```

## Expected impact

No P&L change tonight (tooling only). Enables PHASE-002 (breakeven stop at
+0.5R, sim-to-sim +$563 / ≈ +36% of historical losses recovered) to be
implemented with regression tests and an honest noise budget. Test suite
locks the capital-protection invariants against accidental weakening.

## Risk assessment

Zero runtime risk: no module the service imports was modified; `bot/replay.py`
is new and only imported by the new script/tests. Validation: 22/22 tests
pass, smoke_test ALL GREEN, `import bot.engine` OK. Service restart is a
formality on unchanged runtime code.
