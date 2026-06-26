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

## Week ending 2026-06-26 — Grade: A−

*(Recovery week after last week's F. 5 sessions Mon 06-22 → Fri 06-26. Checked against last week's focus: "Validate IMP-002 live Mon 06-22 … then refocus on the strategy's negative expectancy" — honored in full, see below.)*

### Stats
- **Closed trades this week (by exit_time): 21** — 9W / 12L, win rate **42.9%** (up from last week's ~38%).
- **Net realized P&L: +$42.72** — first positive week of incubation. Profit factor **1.12** (gross win $387.91 / gross loss $345.19). Avg win **+$43.10** / avg loss **−$28.77**.
- **Best:** TSLA +$203.49 (06-22, conf 84.5 BOTH, hit TP). **Worst:** ENPH −$132.44 (06-26, conf 81.89 BOTH false breakout, stopped).
- Per-day gross: 06-22 **+$177.67** · 06-23 **+$95.80** · 06-24 −$87.08 · 06-25 −$3.69 · 06-26 −$139.98. The week was made Mon–Tue (+$273) and bled most of it back Wed–Fri (−$231); net just green.
- **Equity: $7,838.56 → $7,873.54** (Mon open vs now), **+$34.98 / +0.45%**; 0 open positions, account ACTIVE. **−21.3% YTD** ($374 above the −25%/$7,500 strategy-review flag — cushion thinned from $514 as Friday gave back gains).
- Circuit breaker: NOT tripped (worst day −1.75%, far from the −8% halt). Service active all 5 sessions; clean pre-market restarts; one transient non-fatal pre-open `APIError` 06-24 (loop survived). Journal clean — no crashes, no halts, **no naked overnights any session**.

### Grade rationale
**This is the textbook recovery from last week's F, and the process was clean across the board — A− on results AND process.** The single thing that made last week an F (the 06-16→06-18 two-night naked-overnight breach) was the explicit focus for this week, and **IMP-002 validated 5/5 sessions**: every position opened intraday was broker-confirmed flat by ~15:56 ET, Alpaca showed 0 open every night, and the `held_for_orders` race self-healed via per-tick retry on the 06-24 losing day. No naked overnight, no risk event, no halt, no crash. Both fill-accuracy fixes shipped this week were validated live (IMP-003 on 06-23, IMP-005 on 06-25 — daily DB gross now ties to the broker equity move to the penny), and the two tooling IMPs (004, 006) refuted *harmful* candidates against the full dataset rather than acting on within-day anecdote. The 06-26 review's discipline — rigorously refuting all three actionable levers rather than overfitting to one ENPH loss — is exactly the process this mandate wants. Last week's focus was honored in full.

**Why A− and not a clean A:** the profit is real but thin and concentrated — strip the single TSLA +$203 trade and the week is ~−$160 (red). Four of the five IMPs were measurement/tooling integrity, not edge; the strategy's core problem is untouched: all-time PF **0.42**, expectancy **−$20.14/trade**, false-breakout rate **68%**, and IMP-006 localised the entire bleed to the STOP/false-breakout bucket (PF 0.01, −$2,872). The week's gain came from execution integrity + a favourable Mon/Tue regime, not a proven edge — and the identified real lever (an intraday market-regime / breakout-quality gate) is scoped but not yet built. Clean process + marginal profit + unsolved edge = A−, not A.

### What worked / what didn't
- **Worked:** Capital-protection invariant held 5/5 (IMP-002). Fill accuracy now truthful and broker-tied (IMP-003 exit + IMP-005 entry). Measurement discipline (IMP-004 PF-by-type/confidence bands; IMP-006 by-exit-reason) retired two mis-aimed candidates and re-aimed strategy work at the real leak. Watchlist discipline excellent: WPM parked (structural mismatch, 0 signals all-time), MU event-parked 06-24 then re-enabled 06-25 on the resolved bullish gap — every park trigger respected, zero churn/overtrading; AMD's 06-25 win correctly cleared its park watch. The high-conf BOTH edge still works when it works (TSLA +$203). No system errors.
- **Didn't:** The edge itself remains negative. The same false-breakout STOP that defines the all-time bleed produced the week's worst trade (ENPH −$132, conf 81.89 — and the `CONFIDENCE_RISK_TABLE` escalated risk into the empirically-worst bucket). Wed–Fri gave back most of Mon–Tue's gains drifting long into a rotating/choppy tape with no regime gate. The strategy still has no down-day filter — it takes opening longs regardless of broad direction (clearest 06-24: 3 longs into a −0.76% tape, all faded).

### Improvements shipped this week
- **IMP-003 (06-22 → live 06-23)** — real-fill exit price on the EOD_FLATTEN path. **Observed effect:** VERIFIED and held all week — every EOD_FLATTEN exit 06-23→06-26 booked its real Alpaca fill (no $0.00 fallback); daily DB gross tied to broker equity to the penny 06-25 & 06-26.
- **IMP-004 (06-23)** — PF-per-signal-type + confidence-band reporting; retired the (harmful) "raise the MA-only confidence floor" candidate. **Observed effect:** confirmed — 06-24/25/26 reviews all cited PF-by-type/bands and never re-proposed the floor; surfaced the inverted confidence→quality relationship that IMP-006 and the 06-26 refutations built on.
- **IMP-005 (06-24 → live 06-25)** — real entry-fill price on the EOD_FLATTEN path (the entry half of IMP-003). **Observed effect:** VERIFIED 06-25 — entries AND exits both booked at real fills, day gross matched broker to the penny; held 06-26.
- **IMP-006 (06-25)** — by-exit-reason P&L/PF reporting; proved the STOP/false-breakout bucket (PF 0.01) is the entire all-time leak, not flatten-drift. **Observed effect:** confirmed — the 06-26 review cited STOP PF 0.01 as the real leak, demoted the breakeven/trailing-on-flatten candidate, and elevated the market-regime gate to the #1 strategy lever.
- *(06-26: no code change — three actionable candidates refuted as overfit/regime-specific; correct call.)*

### Focus for next week
**Stop giving green-day gains back on red/choppy days — start the one real strategy lever: design + replay-validate an intraday market-regime / breakout-quality entry gate** (e.g. only take longs when SPY/QQQ is above a short intraday MA/VWAP; filter the worst false-breakout setups) over the post-06-15 history, aimed at the STOP-bucket bleed (PF 0.01) without killing green-day MA winners — a deliberate build, NOT a one-shot post-close hack. Keep the validated capital-protection invariants (IMP-002/003/005) green every session, and watch the −25% ($7,500) flag now that the cushion is down to $374.

---
