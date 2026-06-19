# Weekly Review

Friday recap for USTradeWisBot, written by the `uswisbot-weekly-review` routine
(Friday 22:30 UTC) after the daily review. Each entry grades the week with a
**letter grade (A–F)** for both results and process.

Grading guide:
- **A** — profitable week, rules followed, improvements validated, no system errors.
- **B** — flat-to-positive, minor process slips, clear lessons captured.
- **C** — small loss within risk limits OR profitable but rules broken.
- **D** — meaningful loss, repeated mistakes, or unvalidated changes shipped.
- **F** — large loss, risk-limit breach, or system failure (crash, naked positions,
  daily-loss halt tripped repeatedly).

Entry template:

## Week ending YYYY-MM-DD — Grade: X

### Stats
(trades, win rate, net P&L $, profit factor, equity start → end, best/worst trade)

### Grade rationale
(why this grade — results AND process)

### What worked / what didn't
### Improvements shipped this week
(from memory/improvement-log.md, with observed effect)

### Focus for next week

---

## Week ending 2026-06-19 — Grade: F

*(First weekly review under the IMP-NNN model — no prior week's entry/focus to check against. Trading week was 4 sessions: Mon 06-15 → Thu 06-18, with Fri 06-19 closed for Juneteenth.)*

### Stats
- **Closed trades this week (by exit_time): 9** — 3W / 5L / 1 zero (AMZN $0.00, a misrecord, see below). Win rate ~38% of decided trades.
- **Net realized P&L: −$66.04.** Profit factor **0.64** (gross win $118.16 / gross loss $184.20). Avg win +$39.39 / avg loss −$36.84.
- **Best:** TSLA +$90.87 (the only clean winner, conf 97 BOTH, carried to EOD flatten). **Worst:** ENPH −$87.36 (the duplicate-entry leg, 06-15).
- Per symbol: TSLA +$90.87 · NFLX +$7.04 · C +$4.32 (2t) · AMZN $0.00 · BAC −$15.18 · MU −$35.50 · ENPH −$117.59 (2t).
- **Equity: $8,205.71 → $7,838.56** (Mon open vs Fri/now), **−$367.15 / −4.47%** on the week. Note the gap: realized closed-trade P&L was only −$66, but equity fell −$367 — the difference is unrealized markdown on the C/AMZN/BAC positions held naked across 06-16→06-18 (06-17 alone bled −$85 with zero trades) plus the AMZN P&L that was lost to the entry-price fallback. **YTD −21.6% from $10K.**
- Circuit breaker: NOT tripped (worst day −0.45%, far from the −8% halt). Service active all week; journal clean — zero errors/failures, only scheduled clean pre-market restarts.

### Grade rationale
**Results were a small, controlled loss (−$66 realized, −4.5% equity, no halt) — on their own roughly a C.** But the grade is governed by process, and the process produced the single worst failure mode for a no-overnight intraday bot: **a naked-overnight breach.** Positions opened Tue 06-16 (C/AMZN/BAC) were held NAKED for **two consecutive overnights** (06-16→06-17→06-18) — the 15:55 EOD flatten silently failed three sessions running, flagged by pre-market research on three separate mornings before the code fix landed. The grading guide names "naked positions" as an explicit **F** condition, and this was not a one-off glitch — it recurred across the week. A **second** independent capital-protection bug also fired live the same week (the 06-15 ENPH double-entry, −$117.59, the largest single loss). Plus a data-integrity loss (AMZN exit P&L overwritten by the entry-price fallback). Two distinct capital-protection defects reaching live paper trading in one week, one of them a multi-night naked hold, is an F — non-negotiable, regardless of how small the realized loss happened to be (we got lucky the carried names drifted roughly flat). The honest call is **F**.

What keeps this from being a hopeless F is the *remediation* quality — but remediation is next week's grade, not this one's.

### What worked / what didn't
- **Worked:** Disciplined diagnosis and validated fixes — both bugs were root-caused precisely (unfilled-order race; fire-and-forget bulk flatten racing async cancel + unconditional `flattened_on`) and fixed with regression tests (IMP-001 +1 test, IMP-002 +6 tests; full suite 35 passed, smoke/check-engine green, clean restarts). Watchlist discipline was good: minimal, well-reasoned parks (BIRD/BABA day 1; JPM 06-18; C 06-19), every park trigger respected, deferrals justified by catalyst/lock, zero churn or overtrading. Risk limits held (no halt). TSLA remains the lone reliable edge (high-conf BOTH signals). The bot correctly did nothing on the holiday and went into the long weekend flat and broker-confirmed flat.
- **Didn't:** The no-overnight invariant — the bot's core safety contract — was broken for two straight nights before being contained. The EOD flatten had no verification/retry and declared success on failure. The de-dup guard trusted only filled-position state. Underlying strategy edge remains weak (all-time PF 0.33, 78% false-breakout, expectancy −$26.79/trade); this week's 9 trades at PF 0.64 are consistent with that — the bugs were the acute problem, but the strategy itself is still not profitable.

### Improvements shipped this week
- **IMP-001 (5d908bb, 06-15)** — de-dup guard now counts open *logbook* trades, not just filled Alpaca positions, killing the unfilled-order double-entry race. **Observed effect:** no same-symbol double-entry has recurred, but only lightly exercised (one fresh entry all week) — confirmed not-broken, not yet stress-tested.
- **IMP-002 (427ab21, 06-18)** — verified, retried EOD flatten: cancel working orders first, close each position individually, mark CLOSED only on broker confirmation, leave `flattened_on` unset + alert on any survivor. **Observed effect:** NOT yet validated in production — shipped *after* the breach; the 06-18 flatten cleared the legacy stranded book under the new code but no position has been opened-and-flattened same-day under it yet. First true test is Mon 06-22.

### Focus for next week
**Validate IMP-002 live on Mon 06-22** — confirm every position opened intraday is broker-confirmed flat by 15:55 ET with zero carry into Tue 06-23 (this is the gate that turns this week's F into a recovery); secondarily, with capital-protection bugs (hopefully) closed, refocus on the real problem — the strategy's negative expectancy (PF 0.33, 78% false-breakout) — starting with the MA-only near-floor (conf 60–62) entries and the MU/AMD/WPM/GOOGL park reassessments due Monday.

---
