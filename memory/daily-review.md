# Daily Review

Post-close trade review for USTradeWisBot. **One dated entry per trading day**, written
by the `uswisbot-daily-review` routine (21:25 UTC, Mon–Fri) after the US close.
Every trade taken today is reviewed: why it won or lost, and what concrete change
would improve the win rate. This file is the evidence base the improvement work and
the next morning's pre-market research build on.

> Improvement history before this model lived in `phases/PHASE-NNN.md` + the
> "Improvement Log" section of `summary.md` (frozen). New improvements are now
> tracked as IMP-NNN in `memory/improvement-log.md`.

Entry template:

## YYYY-MM-DD — Daily Review

### Stats
(trades, wins/losses, net P&L $, win rate, avg win vs avg loss, profit factor,
account equity; "no trades today" + why is a valid entry)

### Trade-by-trade review
(per trade: symbol, entry/exit time & price, confidence score, exit reason
(stop/trail/target/time-flatten), P&L, and the root cause — false breakout,
stop too tight vs ATR, late entry, re-entry after stop, regime, slippage, exit logic)

### What worked / what didn't
(patterns across today's trades)

### Lessons & improvement candidates
(ranked by expected impact; feeds the improvement step)

### Notes for pre-market research
(watchlist-level observations: symbols that chopped, gapped, or never signaled —
the pre-market routine reads this section the next morning)

---

## 2026-08-12 — Daily Review

### Stats
- Trades: **4 closed (2W / 2L)**, win rate **50.0%**. Net **+$30.44 (+0.407%)**. Winners WMT **+$49.26**, BAC **+$25.08**; losers QCOM **−$40.76**, SPY **−$3.14**.
- Avg winner **+$37.17** / avg loser **−$21.95** → **payoff 1.69**, **profit factor 1.69** (gross win $74.34 / gross loss $43.90). The best payoff of the incubation, and the first day since 07-31 with both a positive PF and >1 winner.
- Exit mix: **EOD_FLATTEN 3 (+$71.20)**, **STOP 1 (−$40.76)**. No take-profit — not one of the four came within 0.1% of its TP. All-time TP rate now **25/236 (10.6%)**.
- Holding times: WMT **6h14m**, BAC **6h09m**, SPY **5h11m**, QCOM **47m**. Entries at 09:43 / 09:47 / 09:56 / 10:46 ET.
- Intraday equity (broker portfolio-history, 15-min): peak **$7,515.69 (+$33.22)** at 15:45, trough **$7,477.15 (−$5.32)** at 10:15 → **max intraday drawdown $26.17 (−0.35%)**, measured off the 10:00 interim peak of $7,503.32. The 8% daily-loss halt was never in play (worst point of the day −0.07%).
- **Equity closed $7,512.91 — back ABOVE the $7,500 / −25% line, at −24.87%.** Yesterday's close ($7,482.47 on the broker) tripped that flag; today's +$30.44 recovers $12.91 of headroom. **This does NOT un-trip the escalation** — the formal strategy review is a human decision point and remains open. Recording the level honestly in both directions is the point; a $12.91 cushion is not a reprieve.
- Sizing matched the confidence plan exactly. All four signals scored **60.06–61.69**, the bottom confidence band, and all four sized to the smallest ladder rung: risk was **$36.00 / $35.34 / $38.81 / $34.84 = 0.47–0.52% of equity** per trade, against a `MAX_RISK_PCT` cap of 2.0. No limit was approached, let alone touched.
- Broker-reconciled via the `alpaca` MCP **to the cent**: last_equity 7,482.47 → equity 7,512.91 = **+$30.44**, matching DB `daily_summary` exactly. Cash $7,512.91, long_market_value 0, **0 positions**, ACTIVE, not blocked. All four buy fills and all four sell fills tie to the DB entry/exit prices exactly. Every unused bracket leg was cancelled at 19:55:25–27Z — **no orphans**.
- Reliability: **zero loop errors**, NRestarts=0, clean 11:50:49 UTC start. **No naked overnight — ~40 consecutive clean sessions.** The 15:55 flatten again took **three ticks** (15:55:25 incomplete → 15:56:28 BAC → 15:57:31 WMT+SPY) — IMP-002 retry working as designed.
- Only slippage of note: QCOM's stop leg was placed at **162.07 and filled at 161.94** (−$0.13/share = **−$1.95**, 4.8% of that trade's loss). Entry fills match the recorded prices to six decimals.

### Market context
**A gap-up-and-fade that still closed green — and the fade is the whole story of today's one real loss.** July CPI landed exactly on consensus (**+0.1% m/m, 3.4% y/y headline**, down from 3.5%; **core +0.2% m/m / 2.5% y/y**, shelter about two-thirds of the monthly rise). The tape gapped up on it, the Nasdaq was briefly **+1%**, and then the indexes gave back most of the pop: **S&P 500 +0.26% to 7,748.50, Nasdaq Composite +0.54% to 26,588.49, Dow −0.04%.** My own IEX bars agree to the decimal: **SPY 770.52 → 772.54 (+0.26%), opening at 774.73 which was also the session HIGH, low 771.30**; **QQQ 718.30 → 723.61 (+0.74%), open 726.99, high 727.16, low 722.95**. NVDA **+2.7%** (the single biggest index contributor) on SMCI's blowout (**+17%**), CRWV **+18%**, MSFT **−2.1%**.
**The regime read that matters: the open was the high, and the names that had NOT participated in the gap were the ones that trended.** WMT and BAC — a staple and a bank, neither in the AI/semi bid — were bought at 09:43 and 09:47 and ground higher all session (373/374 and 350/365 green minutes). QCOM was bought at 09:56 **into the fade of the tech pop** and never printed green once. That is a clean, mechanical explanation of a 2W/2L day and it required no per-name story.
⚠️ **Sonar: EIGHTH consecutive unreliable session, and this one was INVERTED — the worst failure mode.** It reported the S&P "closed lower … finishing at 7,728.20 after a 0.32% decline" and the Nasdaq "down 0.60% at 26,445.45", and characterised the day as "choppy-to-risk-off". **Those are 08-11's closes, verbatim** — the same two figures the 08-12 pre-market research log recorded that morning as *yesterday's* numbers — re-served as today's, with the **sign of the day reversed**. It identified no catalyst for any of WMT / BAC / QCOM / SPY. The only part it got right was the CPI direction (cooler-than-feared, taken positively), which WebSearch independently confirms. **Running record: 08-03 stale, 08-04 inverted, 08-06 empty, 08-07 fabricated+inverted, 08-11am empty, 08-11pm recycled, 08-12am recycled+stale+missed CPI, 08-12pm recycled+INVERTED.** Both the pre-market and daily routines have now escalated this on consecutive days; **this entry is the fourth escalation in three days — drop sonar or demote it below WebSearch.** Every index figure above is from Alpaca bars + WebSearch, not from sonar.

### Trade-by-trade review
MFE/MAE from real 1-min IEX bars over each trade's entry→exit window. **MFE_R** = MFE ÷ the live 1R (fill − plan stop). "Green min" counts minutes whose CLOSE was above the fill.

| # | Sym | Entry (ET) | Exit (ET) | conf | MFE_R | MAE_R | green min | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|-------|-------|-----------|------|-----|------------|
| 247 | WMT | 09:43 @113.494 | 15:57 @115.84 | 60.78 | **+1.41R** | −0.06R | **373/374** | EOD_FLATTEN | **+$49.26** | **The day's thesis, working.** A non-participant in the tech gap; went green on the entry bar and stayed there all session. Ratchet armed break-even 09:52 and walked the stop up six times to 114.76. MAE was −0.06R, on the entry bar. TP 116.03 missed by **$0.09** (MFE 115.94) — the flatten at 115.84 banked +2.07% anyway. |
| 248 | BAC | 09:47 @64.12 | 15:56 @64.78 | 61.54 | +0.89R | −0.10R | 350/365 | EOD_FLATTEN | **+$25.08** | Same archetype, smaller amplitude. Sat below the +0.5R trail trigger until **11:43** (its first ratchet was a trail-stage move straight to 64.16, skipping the break-even stage entirely), then four more raises to 64.48. Never near TP. |
| 249 | QCOM | 09:56 @164.657 | 10:43 @161.94 | 60.06 | **−0.05R** | −1.03R | **0/44** | **STOP (full 1R)** | **−$40.76** | **The one real loss, and it is an ENTRY loss, not an exit loss.** Its session high over the entire hold was **164.53 — below the 164.657 fill**. It never traded green for a single minute. Bought at 09:56 into the fade of the opening tech pop, on the lowest confidence of the day (60.06, the floor). **No exit mechanism — break-even, trail, tighter stop, IMP-031's printed-high — can rescue a trade that never goes green.** Post-exit it recovered to 163.22 by 15:55, so holding would have been −$21.56 (still a loss). |
| 250 | SPY | 10:46 @773.123 | 15:57 @772.077 | 61.69 | +0.04R | −0.13R | 58/312 | EOD_FLATTEN | −$3.14 | **A structurally dead trade that held a slot for 5h11m.** Its 1R was pinned at the `MIN_STOP_PCT` **1.50% floor** (11.61 pts) and its TP at +2.25% — but SPY's ENTIRE daily range was **771.30–774.74 = 0.45%**. Neither leg could physically trigger, so the outcome was a guaranteed flatten coin-flip. Cost only $3.14, but it occupied 1 of 3 concurrency slots for the whole afternoon. |

Grouped by root cause: **1 entry-quality loss (QCOM, −$40.76, 93% of the day's gross loss)**, **1 structurally-inert index-ETF trade (SPY, −$3.14)**, and **2 clean trend-holds that the ratchet managed correctly (+$74.34)**. There was no stop-too-tight loss, no re-entry, no bad bar, no rejected order, no code error, and no slot contention — the fourth slot request never came.

### IMP-031's first live session — the read the pre-market routine asked for
IMP-031 (break-even armed off the highest price **printed** since entry, not the ~60s poll sample) **was live all session and logged its `peak` input on every ratchet**, but it **decided nothing today**, in either direction:
- **WMT armed break-even at 09:52:40 with `live 114.36` ABOVE `peak 114.27`** — the live sample was already the higher of the two, so the old mechanism would have armed on the same tick. Not a rescue.
- **BAC's first raise (11:43:19) was a trail-stage move**, which by design reads the live price, not the peak.
- **QCOM never printed green**, so no arming mechanism of any kind could engage.
- **SPY peaked at +0.04R**, nowhere near the +0.5R trigger.
- Its worked example, NFLX, did not trade.
**Verdict: n=0 decisive cases. No harm, no measured benefit, evidence still pending.** One structural note worth recording now, because it bounds how much IMP-031 can ever deliver: with `BREAKEVEN_TRIGGER_R == TRAIL_TRIGGER_R == 0.5`, the peak input only changes an outcome when **peak ≥ +0.5R AND live < +0.5R** — a between-poll spike that has *already retraced* by the time the tick fires. That is exactly the NFLX #244 case it was built for, so it is not useless, but it is a narrow window, and one green session is not evidence. **Let it run.**

### What worked / what didn't
- **Worked:** every risk control (0 positions overnight, no halt, all four sized at ~0.5% risk, books reconcile to the cent). The ratchet did its job on both winners — WMT's stop was walked from 111.78 to 114.76, converting an unmanaged trend-hold into a protected one. And the day's *thesis* worked: on a gap-and-fade tape, the two names that had not participated in the gap were the two that paid.
- **Didn't:** the QCOM entry. Confidence 60.06 is the absolute floor of the band, it was the third slot spent inside 13 minutes, and it bought a semi at 09:56 while the semi complex was giving back a +1% opening pop. The VWAP gate did not veto it (it was not stretched above VWAP — it was simply early into a reversal), which is a reminder that the gate screens *extension*, not *direction*.
- **Neither:** SPY. It lost almost nothing, but it also could not have won anything — see the structural note above. Worth naming as a category, not a mistake.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED — IMP-032, measurement only]** Today's QCOM loss suggested an obvious lever, so I tested it against the whole post-gate book before touching anything, and **the data refuted it.** Hypothesis: *"cut trades that never go green — they become the full-1R stops."* **Refuted.** Of 47 post-gate trades only **2 never printed green**; and of the **19 post-gate STOP exits, 18 DID print green first.** The losses are not trades that go straight down — they go green, then reverse. A time-based scratch what-if peaks at **+$44.90 on 4 scratched trades (T=15min)** and collapses to +$3.84 at T=45 — a 2-to-6-trade sample with a non-monotone response, i.e. noise. **No scratch rule shipped.**
2. **The real concentration, and what I did ship.** Splitting the 19 post-gate stops by whether they ever reached the +0.5R break-even trigger: the **10 that armed cost −$15.77 in total**; the **9 that never armed cost −$330.71** — essentially the entire post-gate stop loss. Their peaks cluster *just under* the trigger (+0.42R, +0.39R, +0.28R, +0.18R). That makes `BREAKEVEN_TRIGGER_R` the highest-leverage parameter in the exit stack — **and `scripts/exit_geometry.py`'s what-if grid had never swept it**, only the trail. IMP-032 adds that sweep.
3. **Its first run is a stop sign, and that is the value.** The naive "stops rescued" count says lowering the trigger to 0.25R avoids **$116.37** of stop loss. The properly-priced sweep — which also charges for winners scratched at entry — says: **0.5R → −$63.30, 0.4R → −$73.86, 0.35R → −$17.18, 0.3R → −$19.49, 0.25R → −$41.49, 0.2R → −$38.12.** That response is **non-monotone**, swinging $56 between adjacent triggers on a 47-trade book, and **every row (including the live baseline, and every row of the trail grid) sits inside the $248.18 noise budget.** **Do not ship a break-even-trigger change on this evidence.** The honest conclusion is that the post-gate sample is too small and the IEX-bar simulation too coarse to resolve *any* exit-geometry change right now — which also retroactively weakens the basis for IMP-029.
4. **The strategy verdict, stated plainly.** All-time: **236 trades, 38.6% win, −$2,191.29, PF 0.61.** One green day does not change that, and today's +$30.44 came from two low-confidence MA signals on names that simply trended — not from a demonstrated edge. **The confidence score remains inverted or flat** (60–62 band: 42.6% win; 66+ band: 35.4% win, −$1,634.55), and **not one of today's four trades was a breakout** (`breakout_score = 0.00` on all four) — the "intraday breakout bot" has now gone many sessions without taking a breakout at all. The bot is currently an MA-crossover holder with a good exit ratchet. That is worth saying out loud in the same entry that reports a profit.

### Notes for pre-market research
- **Equity $7,512.91 (−24.87%) — back above the $7,500 line by $12.91.** State this at the top tomorrow and say whether it is above or below. **The tripped-flag escalation stands regardless** — one +$30 day does not resolve it. Posture unchanged: do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols.
- **Record what July PPI prints Thu 08-13 at 08:30 ET** — tomorrow's routine has the same pre-open blind spot this one had for CPI. **Retail sales + UMich land Fri 08-14.** Today's CPI was in line (+0.1% m/m / 3.4% y/y, core 2.5% y/y) and the tape gapped up then faded; September-hike odds stayed live, with commentary framing the print as *"narrowly meets the bar to hold rates steady"*.
- **QCOM — new fader watch, and the day's only real loss.** −$40.76, filled 09:56 @164.657 and **never traded green for one minute** (session high over the hold 164.53, below the fill). Post-gate it is now **0W/2, both full-1R stops** (#194 and #249, MFE −0.01R and −0.05R — it has never once been green after entry). It is still below both MAs (−1.1% / −13.7%). **Not yet a park** — but this is a concrete, twice-repeated signature rather than the "no fill in N sessions" quietness that the SE precedent forbids acting on. **Pre-registered trigger: one more never-green full-1R stop parks QCOM.**
- **SPY / QQQ — a structural question for the weekly, not a park.** Post-gate the two index ETFs are **6 trades, ALL SIX exiting EOD_FLATTEN, net −$7.04**. Their stops sit at the `MIN_STOP_PCT` 1.50% floor and their TPs at +2.25%, while SPY's *entire* range today was 0.45% — so neither leg can physically fire and every ETF trade is a guaranteed multi-hour flatten coin-flip occupying 1 of only 3 slots. They lose almost nothing; they also cannot win. **Do not park them unilaterally** — this is a sizing/stop-geometry mismatch owned by the engine, and it is now logged in `todo.md` for the weekly.
- **WMT — today's best trade (+$49.26), and it reports Q2 FY27 PRE-OPEN on Thu 2026-08-20.** That is the one-day event-park decision flagged for next Wednesday's run. Today it was the cleanest trend-hold of the incubation (373/374 green minutes) — do not read the 08-20 event risk as a reason to touch it now.
- **BAC quietly continues to be the best name on the board** — +$25.08 today, now **4W/4 post-gate**. No action needed; noting it because the review file is full of losers and the one consistent winner deserves a line.
- **Gap-and-fade regime note for the morning gate.** Today the open WAS the high on both indexes, and the two winners were the names *outside* the gap (a staple and a bank) while the loser was bought into the fading side of it. If tomorrow gaps up on PPI, the same asymmetry is worth expecting: **the VWAP gate screens extension, not direction, and it did not veto QCOM.**
- **AMD is still fill-less** (six sessions since the 08-06 re-enable). The pre-registered question stands for **Mon 08-17 / 10 sessions**, and it is a weekly question, not a unilateral park.

---

## 2026-08-11 — Daily Review

### Stats
- Trades: **3 closed (1W / 2L)**, win rate **33.3%**. Net **−$52.47 (−0.696%)**. Winner WMT **+$5.52**; losers NFLX **−$44.55**, COST **−$13.44**.
- Avg winner **+$5.52** / avg loser **−$29.00** → **payoff 0.19**, **profit factor 0.10** (gross win $5.52 / gross loss $57.99). The worst payoff of the incubation on a 3-trade day.
- Exit mix: **STOP 1 (−$44.55, a full 1R)**, **EOD_FLATTEN 2 (−$7.92)**. No take-profit; TP-hit rate all-time now **25/232 (10.8%)**.
- Holding times: COST **6h25m**, WMT **6h24m**, NFLX **3h28m**. All three entered inside the first 10 minutes (09:31:24 / 09:32:34 / 09:39:23 ET).
- Intraday equity (broker portfolio-history, 15-min): peak **$7,547.37 (+$12.25)** at 09:45, trough **$7,459.80 (−$75.32)** at 13:15 → **max intraday drawdown $87.57 (−1.16%)**. The 8% daily-loss halt was never remotely in play (worst −1.00%).
- ⚠️⚠️ **EQUITY CLOSED $7,482.65 — THE −25% / $7,500 FORMAL STRATEGY-REVIEW FLAG HAS TRIPPED.** −25.17% YTD. Monday's cushion was $35.33; today's −$52.47 spent it. **This is a human decision point, not something this routine resolves** — it is escalated here, to the improvement log, and to tomorrow's pre-market notes. The bot has NOT been halted and no risk limit was touched: `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, paper endpoint, no-overnight rules all unchanged.
- Broker-reconciled via the `alpaca` MCP **to the cent**: last_equity 7,535.12 → equity 7,482.65 = **−$52.47**, matching DB `daily_summary` exactly. Cash 7,482.65, long_market_value 0, **0 positions**, ACTIVE, not blocked. All 3 buy fills and all 3 sell fills tie to the DB entry/exit prices exactly; every unused bracket leg was cancelled at 19:55:30Z, **no orphans**.
- Reliability: **zero loop errors**, NRestarts=0. **No naked overnight — ~39 consecutive clean sessions.** The 15:55 flatten again needed **two ticks** (15:55:31 incomplete → 15:56:43/44 confirmed flat) — IMP-002 retry working as designed.
- **The VWAP gate (IMP-021/022) blocked ABNB 20 times** between 13:56 and 14:45 ET at +1.22% to +1.50% above session VWAP, on the most extended name on the board. A slot was free from 13:07 (NFLX's stop) and the gate correctly refused to fill it.

### Market context
**A gap-up-and-fade, no-trend tape ahead of tomorrow's July CPI — the exact regime that punishes a first-ten-minutes long.** Measured off IEX daily bars (authoritative here, see the sonar note): **SPY 773.02 → 770.52 (−0.32%)**, opening at **774.515** (above the prior close) and closing near the session low of 769.415; **QQQ 720.805 → 718.30 (−0.35%)**, opening 723.01, low 715.84. So the index gapped up, gave the gap back within the first hour, and ground lower all day.
That single fact explains all three trades without needing any per-name story: **the bot bought strength in the first 10 minutes of a session whose high was in the first 10 minutes.** COST's MFE (+0.193R) and WMT's (+0.161R) both landed early and neither ever recovered; NFLX's +0.519R peak at 09:56 was the last gasp of the opening push.
⚠️ **Sonar: sixth consecutive unreliable session, and this one failed by recycling.** It reported the S&P at "7,753.11 (−0.06%)" and the Nasdaq at "26,605.36 (−0.32%)" — **those are Monday 08-10's closes**, quoted verbatim from the same figures the 08-11 research log recorded that morning; it then hedged with a second, different pair of numbers from "later wire reporting" and identified **no catalyst for any of COST / WMT / NFLX / ABNB**. It did get the *regime* right (choppy, pre-CPI positioning, faded close), which is the only part used above. **Running record: 08-03 stale, 08-04 inverted, 08-06 empty, 08-07 fabricated+inverted, 08-11am empty, 08-11pm recycled.** The pre-market routine has already escalated "drop or demote sonar" to the weekly; **this entry seconds it.** Index levels here come from SPY/QQQ bars, not from sonar.

### Trade-by-trade review
MFE/MAE from real 1-min IEX bars over each trade's entry→15:55 window. **MFE_R** = MFE ÷ the live 1R (fill − plan stop). "Intent" is the signal-bar price the bracket was anchored to, recovered exactly as `(tp + RR·stop)/(1+RR)` — see the slippage note below.

| # | Sym | Entry (ET) | Exit (ET) | conf | mom | MFE_R | MAE_R | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|-----|-------|-------|------|-----|------------|
| 244 | NFLX | 09:39 @76.19 | 13:07 @74.84 | 61.27 | 0.75 | **+0.52R** | −1.27R | **STOP (full 1R)** | **−$44.55** | **The day, and a mechanism failure — see below.** Peaked 76.89 at 09:56 against a break-even trigger of 76.865. **Exactly one 1-min bar's HIGH cleared it and not a single 1-min CLOSE did**, so the ~66 s poll never saw it, the stop never armed, and a trade that had earned its break-even rode to the full stop 3h11m later. Only **36 of 376** minutes closed green. |
| 242 | COST | 09:31 @951.35 | 15:56 @944.63 | 60.25 | 0.68 | +0.19R | −0.86R | EOD_FLATTEN | −$13.44 | **Opening-drive fade, never remotely armable.** Bought 84 seconds after the bell at the confidence floor; high 954.30 (+0.19R) inside the first hour, then a 6h25m grind. **15 of 271** green minutes. Nothing the exit logic could have saved — this is an entry-timing loss. |
| 243 | WMT | 09:32 @112.93 | 15:56 @113.18 | 61.87 | 0.87 | +0.16R | −0.34R | EOD_FLATTEN | **+$5.52** | The day's only green, and it is noise: MFE +0.16R over 6h24m, **44 of 378** green minutes, +0.22% on the flatten. A slot held all session for a quarter of one percent. |

**All three were MA-only signals (`breakout_score = 0.00`) at confidence 60.25–61.87 — the bottom band.** No breakout fired all day. Grouped by root cause: **1 mechanism failure (NFLX, −$44.55, 85% of the loss)** and **2 opening-drive fades on a fading tape (−$7.92 combined)**. There was no stop-too-tight loss, no re-entry, no bad bar, no rejected order, no code error, and no slot contention (the free slot after 13:07 was refused by the VWAP gate, correctly).

### Root cause of the day's loss — two defects, compounding, both found tonight

**(1) The break-even stop is tested against a ~60 s point SAMPLE, not against the tape.** `engine.manage_stops` polls `data.latest_trade_price` once per `POLL_INTERVAL_SEC`; the stop only moves up, so arming is a latch on *sampled* prices. Meanwhile **every piece of exit-geometry evidence this bot has ever shipped on — IMP-028, IMP-029, IMP-030 and the whole what-if grid — comes from `exit_sim.simulate_exit`, which ratchets off the bar HIGH.** The model and the machine are different mechanisms, and the model is the more generous one.
*Falsifiable test, run tonight:* rebuild the same replay with the ratchet observing the bar CLOSE (a fair proxy for a discrete poll) instead of the HIGH. If the diagnosis is right the close-sampled model must fit the recorded book better. It does, on both books:

| model | post-gate (43) sim | \|sim−actual\| | all-time-with-bars (62) sim | \|sim−actual\| |
|---|---|---|---|---|
| actual recorded | **−$197.10** | — | **−$389.78** | — |
| HIGH-sampled (what the sim assumes) | −$67.92 | $218.10 | −$275.73 | $257.37 |
| CLOSE-sampled (what the bot really does) | **−$128.13** | **$158.13** | **−$279.44** | **$209.58** |

So the live bot under-arms relative to its own model, and **the honest post-gate baseline under the shipped geometry is ≈−$128, not the −$68 the tool prints.** IMP-029's headline "+$65.16 and +5 wins" was measured on a machine we are not running; its *direction* survives (the reverted 1R/1R geometry is still worse) but its magnitude is overstated. Recorded here so no future run re-uses the −$68 figure.

**(2) Entry slippage silently inflates 1R, which pushes the break-even trigger further away.** The bracket's stop/TP are anchored to the signal-bar close while the order is a market buy — a documented design note in `engine.consider_entries`, but its consequence for the *ratchet* had not been measured. NFLX filled at 76.19 against an intent of 75.976 (**+0.282%**), so 1R went 1.136 → 1.350 (**+18.8%**) and the trigger moved **10.7 cents higher**, from 76.758 to 76.865. At the planned trigger, **4 bar highs and 3 bar closes** cleared it — a polling bot would very likely have armed. At the inflated trigger, 1 high and 0 closes.
**New measurement capability:** the signal-bar intent price is exactly recoverable for every trade in the book as `(tp + RR·stop)/(1+RR)`, with no schema change (verified to the cent against all three of today's log lines). This retires the "only trades with a logged intent can be checked for slippage" limitation the 08-10 entry recorded.

### What worked / what didn't
- **Worked:** the VWAP gate (20 correct ABNB refusals on the board's most extended name); the flatten retry; broker reconciliation to the cent; zero errors; no overnight. **Risk control was flawless — the loss is a strategy loss, not a control failure.**
- **Didn't:** the break-even stage, for the reason above. And, structurally, **entering all three positions in the first ten minutes and then holding for six hours on a tape that topped in the first ten minutes.** Three trades used all three slots by 09:39 and the book was frozen for the rest of a session that offered nothing.
- **Honest verdict on the strategy itself, restated:** all-time **232 trades, 38.4% win, −$2,221.73, PF 0.60**. STOP exits are **−$4,616.55 across 103 trades at a 7.8% win rate**, and **82 of them are full-1R** (−$4,664.63, avg −$56.89). TAKE_PROFIT (+$2,033.75) and EOD_FLATTEN (+$361.07) together do not cover it. **The entry signal has no demonstrated edge** — six discriminators are refuted (confidence, volume, entry extension, time-of-day, index regime, momentum) — and the only working lever found so far is exit geometry. Tonight's finding is that the exit geometry has been half-connected. That is worth fixing before concluding the exit lever is exhausted too, but it does not make the entry edge appear.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED — IMP-031] Arm the break-even stop off the highest price PRINTED since entry, not off the 60 s sample.** Scoped to the break-even stage only. On the entire recorded book with bars (62 trades) it changes **exactly 2 trades, both favourably, zero hurt**: NFLX #244 −$44.55 → **$0.00**, META #223 +$1.04 → +$2.48. Post-gate delta **+$45.99**. Detail and caveats in `memory/improvement-log.md`.
2. **[MEASURED AND DECLINED] Anchor the ratchet's 1R to the planned stop distance instead of `fill − plan stop`.** Correct in principle (it is why NFLX's trigger sat 10.7¢ too high) but worth only **+$5.05 post-gate / +$5.46 all-time across 6–7 trades** — far inside the $218 noise budget. Not a lever on its own; revisit only if a slippage regime shifts. The recovery formula is now in the review so it can be re-measured cheaply.
3. **[MEASURED AND DECLINED] Extending the high-water mark to the TRAIL stage.** Tested: **+$60.21 post-gate but only +$3.71 all-time**, because it cut two winners (**AMD #179 −$48.06**, BAC #189 −$9.23). Trailing off the running high tightens the trail, and tightening is exactly what sparse IEX bars bias optimistic (`bot/exit_sim.py` docstring). **Deliberately not shipped; do not re-propose without a held-out split.**
4. **Book-wide entry slippage is NOT a leak — hypothesis refuted tonight, do not re-open.** Across all 232 trades: mean **+0.008%**, median **0.000%**, **85 adverse / 85 favourable / 62 flat**, net **−$119.04** (i.e. mildly *favourable*), and actual aggregate dollar risk is **0.96% BELOW** plan. Today's uniformly adverse +0.264% mean was a 3-trade tail, not a regime.
5. **The opening-window / slot-allocation question is now the strongest un-refuted entry-side idea, and it is still not ready.** Three sessions running (08-10 QQQ+SPY, 08-11 COST+WMT+NFLX) the bot has committed every slot inside the first ten minutes and then sat frozen through a day that went the other way. But an opening-range blackout copied from the sibling bot is **REFUTED on this book** (IMP-030 note: all-time 09:30–09:59 is the *better* bucket). The live idea is therefore **not** "skip the open" but "do not spend all three slots in ten minutes" — a concurrency-pacing rule, which is a different mechanism and needs its own in-sample/held-out pass. **n=3 sessions; gather more before proposing.**
6. **The ★ never-green time-stop remains the #1 un-shipped lever** (39 trades, 0% win, −$833.59 all-time; COST #242 today joins it at 15/271 green minutes). Not tonight — it is a second exit change and IMP-029/IMP-030 both pre-registered that stacking destroys attribution. It also needs re-measuring now that the model/machine gap is known.

### Notes for pre-market research
- **⚠️⚠️ THE −25% / $7,500 REVIEW FLAG HAS TRIPPED. Equity closed $7,482.65 (−25.17%).** State this at the very top of tomorrow's entry. It is a **human** decision point. Until a human rules, the standing posture is unchanged and conservative: **do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols to "get back to flat".**
- **⚠️ JULY CPI PRINTS WED 08-12 AT 08:30 ET, before the pre-market routine's decisions are final and before the open.** Consensus 3.4% headline / ~2.51% core, September hike ~52% priced. The routine runs ~07:46 ET and **will not have seen the number** — record that limitation explicitly again. Pre-open release ⇒ gap risk; the bot's first entry is after 09:30 and it holds nothing overnight.
- **NFLX — do NOT park, and do not read −$44.55 as a name defect.** It was the day's best-behaved *signal* (MFE +0.52R, the only trade to earn its break-even) and the loss is the mechanism failure IMP-031 fixes. Post-gate it is still the best name on the list (3W/0 before today). **Tomorrow is IMP-031's first live session and NFLX is its worked example** — leave it enabled.
- **COST — new fader watch, trigger pre-registered.** 15 of 271 green minutes, MFE +0.19R, a textbook never-green clock-out; 2W/0 post-gate before today so the record is still fine. **Trigger: the next full-1R STOP fade parks it.** Do not park on this EOD_FLATTEN drift alone.
- **WMT — flag, don't park.** Two post-gate trades are now +$5.52 (6h24m, +0.22%) and a prior fade; it occupies a slot for hours to produce noise. 0W/2 → 1W/3. No trigger fired.
- **ABNB was blocked 20 times today at +1.22% to +1.50% above VWAP** — the gate working exactly as designed on the most extended name on the board (+22% vs its MAs). **Blocked ≠ park** (SE precedent). It has still never had a post-gate fill.
- **AMZN's park trigger (next full-1R STOP fade) is still live and still un-fired** — no trade today. Same for **AAPL** (close below the 50MA on elevated volume), **GOOGL** (same test), **QCOM** (no trade since 07-27) and **AMD** (still zero fills since the 08-06 re-enable — a park needs a fill).
- **SE stays parked.** Nothing today changes the 0-for-5 record it was parked on.
- **⚠️ Sonar is now 6-for-6 unreliable and today it recycled Monday's index closes as today's.** Treat as an unverified lead only. **Index levels are cheaper and correct from SPY/QQQ daily bars via the `alpaca` MCP — use those.** Escalated to the weekly for the second time today: drop it or demote it below WebSearch.
- **Structural note for the weekly, not for the watchlist:** the bot has now spent all three slots inside the first ten minutes on three consecutive sessions. **Do not park names to work around it** — it is engine work (concurrency pacing), owned by the daily/weekly review.

---

## 2026-08-10 — Daily Review

### Stats
- Trades: **4 closed (1W / 3L)**, win rate **25.0%**. Net **+$3.76 (+0.050%)**. **First green day since 08-04** and the end of a four-red run (08-05 −$95.95, 08-06 −$92.27, 08-07 −$16.45).
- Winner: MSFT **+$17.54**. Losers: SE **−$9.24**, QQQ **−$3.89**, SPY **−$0.65**. Avg winner **+$17.54** / avg loser **−$4.59**; **payoff 3.82**, **profit factor 1.27** (gross win $17.54 / gross loss $13.78). The first PF > 1 since 08-04.
- **The whole day is one trade, and it is the trade IMP-029 was built for.** MSFT is +466% of the net; the other three net −$13.78.
- Exit mix: **STOP 1 (+$17.54)** — a *profitable* stop, the ratchet firing above entry — and **EOD_FLATTEN 3 (−$13.78)**. No take-profit; TP-hit rate all-time now **25/235 (10.6%)**.
- Worst mark-to-market ≈ **−$25** (SE's −0.57R MAE dominating); the 8% daily-loss halt was never remotely approached (worst ≈ −0.3%).
- Account equity close **$7,535.33**. Broker-reconciled via `alpaca` MCP **to the cent**: last_equity 7,531.57 → equity 7,535.33 = **+$3.76**, matching DB `daily_summary` exactly. Cash 7,535.33, long_market_value 0, **0 positions**, ACTIVE, not blocked. All 4 buy fills and all 4 sell fills tie to the DB entry/exit prices exactly; every bracket leg was cancelled at the flatten, **no orphans**.
- ⚠️ **Cushion is $35.33 above the −25% / $7,500 strategy-review flag** — up from $31.57 on Friday, still the thinnest band of the incubation. **−24.65% YTD.** One average red day of last week (−$92 to −$96) still trips the formal review.
- Reliability: **zero loop errors**, NRestarts=0, service `active` since the 08-08 20:09 UTC weekly restart. **No naked overnight — ~38 consecutive clean sessions.** The 15:55 flatten again needed **two ticks** (15:55:29 incomplete → 15:56:31–43 confirmed flat) — IMP-002 retry working as designed.
- Slippage: only SE has a logged intent — signalled 114.97, filled **115.08 (+0.096% adverse)**. MSFT's protective stop sat at 509.76 and filled **509.25 (−0.10%)**, normal for a market-triggered stop.

### Market context
**A trending, risk-on tape — the regime this strategy exists to capture.** S&P 500 **+0.62% to 7,757.64**, a record close; Nasdaq Composite **+1.30% to 26,690.61**, tech-led (Perplexity `sonar`; no stock-specific catalyst found for MSFT or SE). The bot netted **+0.05%** against an index up 0.62% — directionally right, hugely under-participating.
**The index trades explain the under-participation and are the day's structural lesson.** QQQ and SPY were both entered **in the first 90 seconds (09:30 / 09:31)** and both bled all session on a day their underlying indices rose ~1%. That is only possible because **the entire index gain was the overnight gap**: the bot bought the gap-up open print and the cash session went nowhere (QQQ MFE +0.23R, SPY +0.20R over 6.4 hours). Buying the open on an index ETF is buying the one part of the move that already happened.

### Trade-by-trade review
MFE/MAE from real 5-min IEX bars over each trade's entry→exit window; **MFE_R** = MFE ÷ initial 1R stop distance (+0.5R arms break-even, and since IMP-029 also arms the trail).

| # | Sym | Entry (ET) | Exit (ET) | conf | mom | MFE_R | MAE_R | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|-----|-------|-------|------|-----|------------|
| 240 | MSFT | 09:37 @504.865 | 10:53 @509.25 | 61.05 | 0.99 | **+1.14R** | −0.17R | **STOP (trail)** | **+$17.54** | **The IMP-029 trade.** Ran to +1.14R in 53 min, the trail ratcheted the stop up **seven times** (497.12 → 504.91 → 505.73 → 506.41 → 507.07 → 507.88 → 508.69 → **509.76**, broker-confirmed replace chain) and banked **+0.57R**. 100% of its bars closed green. Nothing to fix. |
| 238 | QQQ | 09:30 @722.207 | 15:56 @720.91 | 62.96 | 0.86 | +0.23R | −0.18R | EOD_FLATTEN | −$3.89 | **Bought the gap-up open.** Never reached +0.5R, so no ratchet stage ever armed; only 33% of bars closed green. Held 6h26m to die on the clock. Not a stop-placement or signal-quality failure — an **entry-timing** failure. |
| 239 | SPY | 09:31 @772.793 | 15:56 @772.577 | 62.77 | 0.85 | +0.20R | −0.08R | EOD_FLATTEN | −$0.65 | Same trade as #238 one minute later — **duplicate exposure to a single index bet**. 74% of bars green yet MFE never cleared +0.25R: pure drift, no impulse. Effectively a scratch. |
| 241 | SE | 14:32 @115.08 | 15:56 @114.64 | 60.00 | 0.67 | +0.14R | **−0.57R** | EOD_FLATTEN | −$9.24 | **Never green** — 1 of 17 bars closed above entry. Lowest confidence (60.00, the floor) and weakest momentum (0.67) of the day, entered late (14:32) with only 83 min of runway. Textbook member of the ★ never-green cohort. |

### IMP-029 verdict — first live session (the point of today)
IMP-029 (weekly, shipped 08-08: `TRAIL_TRIGGER_R` and `TRAIL_DISTANCE_R` 1.0 → 0.5) pre-registered its pass condition as *"fewer trades peaking ≥+0.5R and banking ~$0"*. Today:
- **Exactly one trade armed the trail (MSFT #240), and it passed.** Honest full-session counterfactual: under the pre-IMP-029 1R/1R geometry MSFT's stop would have sat at **505.98** and been taken out for **+$4.46**; the shipped 0.5R/0.5R geometry stopped at **509.85** for **+$17.54**. **+$13.08 attributable to IMP-029 on one trade** — and it is the difference between a green day (+$3.76) and a red one (−$9.32).
- **The give-back cohort did not grow**: still n=6, none from today. No trade peaked ≥+0.5R and banked ~$0.
- **The fail condition (winners cut short) did not trigger.** MSFT banked +0.57R of a +1.14R peak; the geometry it replaced would have banked +0.14R of the same peak.
- **Honest caveat: n=1 armed trade.** This is a pass, not a confirmation. IMP-029 stays; no stacking. The book-level read (below) is the stronger evidence.

### What worked / what didn't
- **Worked:** the exit ratchet, unambiguously and for the first time in live trading. A *profitable STOP exit* is a new event in this bot's history — every prior STOP bucket entry was a loss. The 08-08 weekly change is doing exactly what it was shipped to do.
- **Worked:** risk discipline. 4 trades, max 3 concurrent, no halt, no overnight, no errors, flatten clean.
- **Didn't work:** **entry timing at the open on index ETFs.** QQQ+SPY = 2 of 4 trades, both filled inside 90 seconds of the bell, both buying an overnight gap, both dead money for 6.4 hours. They also consumed 2 of the 3 concurrent-position slots for the entire session, so the book could not take anything else until SE at 14:32.
- **Didn't work:** the never-green cohort, again. SE was the largest loser and never traded above entry after the first bar.
- **Unchanged concern:** `breakout_score = 0.0000` and `broke_level = NULL` on **all four** trades. Every entry today — as on recent sessions — was an MA + momentum drift entry, not a breakout. The "breakout bot" has not taken a breakout in some time; the edge it is actually trading is MA drift. This is a *strategy-premise* question, not a parameter question, and it belongs to the weekly.
- The **IMP-022 VWAP gate** again did most of the filtering: ~50 logged vetoes across **AMZN, ABNB, CRM, WMT, XOM** (ABNB repeatedly at +0.8–1.5% above VWAP). None of the vetoed names were traded; the gate's cost/benefit remains the open question IMP-025 instrumented.

### Lessons & improvement candidates
Ranked by expected impact. **Today shipped IMP-030 (measurement only) and deliberately did NOT touch trading logic** — Monday is IMP-029's first clean live session and stacking a second exit change would destroy attribution, exactly as IMP-029's own note pre-registered.
1. **★★ Never-green time-stop** — still the #1 remaining lever (all-time: 39 trades that never closed a bar above entry, 0% win, −$833.59; SE #241 today adds to it). Now measurable honestly for the first time thanks to IMP-030. **Needs its own in-sample/held-out pass; candidate for the next engine change once IMP-029 has ~a week of live reads.**
2. **★★ Opening-print entries on index ETFs (QQQ/SPY).** New evidence today. Note this is **NOT** the sibling bot's opening-range blackout: the all-time entry-hour split here shows **09:30–09:59 n=127, −$1,045.52, avg −$8.23** vs **≥10:00 n=102, −$1,123.74, avg −$11.02**, and post-gate **09:30–09:59 avg −$3.99 vs ≥10:00 avg −$3.11** — i.e. **a blanket opening blackout is NOT justified on this book and must not be copied from USTradeBot's IMP-017.** The narrower, better-supported idea is **gap-aware entry on index ETFs specifically** (skip an ETF entry whose session has already gapped and whose first bars are flat vs VWAP). Needs a proper sample before shipping — recorded, not actioned.
3. **★ Duplicate index exposure.** QQQ and SPY inside 90 seconds is one bet held twice and cost 2 of 3 position slots all day. A correlation/one-index-ETF-at-a-time cap is cheap and risk-*reducing*, but today is n=1; gather more sessions.
4. **Strategy premise: zero breakout scores.** Escalate to the weekly review — if the bot never takes a breakout, the breakout scoring and the false-breakout verdict in `scripts.report` are measuring something the strategy no longer does.
5. **Grid observation, explicitly NOT actioned:** post-IMP-030 the what-if grid likes tighter trails (`trail@1R-0.25R` → sim −$20.18 vs live −$62.12). **Every one of those deltas is inside the $171.43 noise budget and the whole grid is in-sample.** Do not chase it; it is a weekly question with a held-out split, not a daily one.

### Notes for pre-market research
- **MSFT — today's only winner and the cleanest trend entry of the week** (+1.14R MFE, 100% green bars, conf 61). Behaved exactly as the strategy intends. **Keep, high priority.**
- **QQQ / SPY — flag for gap handling, do not park.** Both gapped up and then went flat for the whole cash session; the bot bought the open both times. Tomorrow, if either shows a large pre-market gap, prefer *not* opening at the bell — and note they are **one bet, not two**: consider holding at most one index ETF at a time so they don't eat the 3-slot book.
- **SE — chronic-loser watch escalates.** Now **0W/5** with today's −$9.24 (prior: −$4.56 on 08-04). Entered at the confidence floor (60.00) with the weakest momentum of the day, and never traded green. It is also the lowest-liquidity ADR on the list. **Recommend parking SE** unless pre-market shows a specific catalyst.
- **Chopped above VWAP, never entered (gate did its job): ABNB** (repeatedly +0.8–1.5% above VWAP, the most persistent all day), **CRM** (+0.95–1.10%), **AMZN** (+0.76–0.84%), **WMT** (+0.42–0.55%, ~20 vetoes), **XOM** (+0.57%). All five trended up but never offered a fill at/below VWAP — these are the names the gate is costing us on if it is costing anything. Worth a look at whether any deserve a pullback-entry variant.
- **AMZN** remains 0W/5 all-time and did not trade again today (gate-blocked, not signal-less) — the standing park candidate.
- Tape was trending risk-on to record highs; if that persists, expect more above-VWAP vetoes and few fills. The book had only 1 free slot from 09:37 to 15:56.

---

## 2026-08-07 — Daily Review

### Stats
- Trades: **6 closed (2W / 4L)**, win rate **33.3%**. Net **−$16.45 (−0.218%)**. Tenth live session under IMP-021 + IMP-022. Third consecutive red day (08-05 −$95.95, 08-06 −$92.27) — but a **shallow** one, and the shape is completely different from the prior two.
- Winners: AAPL **+$7.49**, NVDA #235 **+$6.02**. Losers: TSM **−$23.30**, TSLA −$6.47, NVDA #232 −$0.11, META #233 −$0.08. Avg winner **+$6.76** / avg loser **−$7.49**; profit factor **0.45**.
- **The whole day is one trade.** TSM −$23.30 is **142% of the net loss**; the other five net **+$6.85**. Two of the four "losses" are IMP-013 break-even scratches worth −$0.19 combined.
- Exit mix: **STOP 3 (−$23.49)**, **EOD_FLATTEN 3 (+$7.04)**. **No take-profit** — TP-hit rate all-time now **25/231 (11%)**.
- Max intraday drawdown ≈ −$30 (post-TSM); the daily-loss halt (8%) was never remotely approached (worst ≈ −0.4%).
- Account equity close **$7,531.89**. Broker-reconciled via Alpaca REST **to the penny**: last_equity 7,548.34 → equity 7,531.89 = −$16.45, matching DB and `daily_summary` exactly. Cash 7,531.89, long_market_value **0**, **0 open positions**, ACTIVE, not blocked, **0 rejects**. **12 fills** (6 entries + 6 exits), every one tying to a DB row. **~37th straight no-overnight session.**
- ⚠️ **Cushion is now $31.89 above the −25% / $7,500 strategy-review flag — the thinnest of the entire incubation** (prior lows $48.34 on 08-07 open, $78.78 on 07-29). **−24.68% YTD.** A single average red day (−$92 to −$96 this week) trips the formal review.
- Reliability: **zero loop errors**, NRestarts=0, service `active`. The 15:55 flatten again needed **three ticks** (15:55:14 incomplete → 15:56:15 incomplete → 15:57:17–19 confirmed flat) — IMP-002's retry did its job and IMP-026's watchdog correctly stayed silent, but this is the **second session running** that the flatten consumed 3 of its 5 available ticks. Noted, not yet actionable.
- Slippage **favourable on 5 of 6 entries** (intended → fill): TSM 422.72 → 420.97 (−0.41%), META 591.60 → 590.40 (−0.20%), AAPL 313.34 → 313.04 (−0.10%), NVDA#235 223.13 → 222.99 (−0.06%), TSLA 328.99 → 328.95 (−0.01%); only NVDA#232 221.78 → 221.82 (+0.02%) adverse. Sizing matched plan: all six at the floor 0.5% tier (conf 60.21–64.17), exactly as IMP-027 documented.

### Market context
**A trending, risk-on tape — and this matters for the verdict.** July payrolls printed *weak* (net job losses) at 08:30 ET, which cut September rate-hike odds and turned the tape risk-on. Measured off Alpaca's own bars, **SPY 771.00 → 773.11 (+0.27%), closing at 82% of its day range; QQQ 720.22 → 722.89 (+0.37%), closing at 89% of range** — an up day that finished near its highs, not a chop. *(Perplexity `sonar` returned a directionally consistent but unverified account — "S&P +0.6% to a record 7,757.6, Nasdaq +1.3%" — and again produced "no catalyst identified" for all five tickers. Its **fifth** consecutive unreliable session; the index figures above are mine, from Alpaca, not its.)*
**Four of the five names traded closed GREEN:** AAPL **+0.61%**, META **+1.04%**, NVDA **+1.06%**, TSLA **+1.92%**; only **TSM −1.04%**. The bot was long the right names on the right day and still finished red. **Regime is not the excuse today.**

### Trade-by-trade review
MFE/MAE from real 1-min IEX bars over each trade's entry→exit window; **MFE_R** = MFE ÷ initial 1R stop distance (+0.5R is what arms IMP-013).

| # | Sym | Entry (ET) | Exit (ET) | conf | mom | MFE% / MFE_R | MAE_R | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|-----|--------------|-------|------|-----|------------|
| 230 | AAPL | 09:36:54 @313.04 | 15:57:17 @313.98 | 64.17 | 1.00 | +0.56% / 0.40R | −0.52R | EOD_FLATTEN | **+$7.49** | Textbook drift-up winner harvested by the clock. Peaked below +0.5R so the ratchet never armed; held 6h20m for +0.30%. Working as designed. |
| 231 | TSM | 09:36:55 @420.97 | 10:02:01 @416.31 | 61.48 | 0.89 | +0.46% / 0.42R | **−1.04R** | STOP | **−$23.30** | **The day's only material loss, and the only name that closed red (−1.04%).** Classic sub-0.5R fader: peaked at +0.42R — *just under* the arm threshold — then straight through the stop in 25 min. Same nine-week population. |
| 232 | NVDA | 09:39:08 @221.82 | 13:00:24 @221.81 | 61.98 | 0.80 | **+1.33% / 0.88R** | −0.26R | **STOP (break-even)** | **−$0.11** | **GIVE-BACK.** Armed break-even 10:51:12. Peaked **+0.88R = $32.34 of open profit**, never cleared the +1.0R trail trigger, and returned **100%** of it. IMP-013 prevented a −$37 loss; the geometry banked nothing. |
| 233 | META | 10:08:01 @590.40 | 14:46:33 @590.38 | 60.21 | 0.68 | **+1.40% / 1.07R** | −0.12R | **STOP (break-even)** | **−$0.08** | **GIVE-BACK, and the decisive case.** Armed break-even 10:34:30; **cleared the +1.0R trail trigger** at 10:57 and peaked **+1.07R = $32.96 of open profit** — yet the trail was blocked **by two cents** (candidate 590.97 vs the 590.99 the ratchet min-step required). Banked −$0.08. See root cause #1. |
| 234 | TSLA | 15:16:26 @328.95 | 15:57:18 @328.03 | 62.42 | 0.83 | +0.02% / 0.01R | −0.42R | EOD_FLATTEN | **−$6.47** | Never-green late entry with only 41 min before the flatten. TSLA closed **+1.92%** on the day — the bot bought the one pullback that didn't resume before the clock ran out. |
| 235 | NVDA | 15:16:27 @222.99 | 15:57:18 @223.54 | 60.76 | 0.95 | +0.50% / 0.35R | −0.18R | EOD_FLATTEN | **+$6.02** | Re-entry of a symbol that had already stopped out at 13:00 — and it worked. No re-entry defect to report. |

**Loss decomposition:** TSM alone is −$23.30. The two give-backs cost **−$0.19 realized** but left **$65.30 of peak open profit** on the table. TSLA/AAPL/NVDA#235 net +$7.04.

### What worked / what didn't
- **Worked — IMP-013, again, decisively.** It armed on 2 of 6 trades and converted two would-be full-1R losses (~−$37 and ~−$33) into −$0.11 and −$0.08. **Without it today is roughly −$86 instead of −$16.45.** This is the single most valuable mechanism in the bot.
- **Worked — the gates.** IMP-022 blocked **33 stretched-above-VWAP attempts across 5 symbols** (BAC×15, NFLX×11, ABNB×3, QCOM×3, MSFT×1). ABNB behaved *exactly* as the 08-07 pre-market note predicted: re-enabled into a +8% post-earnings gap, and the VWAP gate vetoed it all day (+0.56% to +0.67% above VWAP) rather than trading it — **that is the gate working, not a park trigger.** IMP-021 held: all six entries `breakout_score` **0.0000**.
- **Worked — capital protection.** Flat into the close, books penny-tied, 0 rejects, 0 loop errors, watchdog silent by design.
- **Didn't — the exit geometry, and today it is unambiguous.** Two trades reached +0.88R and +1.07R and banked **−$0.19**. On a day when four of five names closed green, the bot's problem was not picking them; it was **keeping** anything.
- **Didn't — the sub-0.5R fader still writes the losses.** TSM peaked at +0.42R, below the threshold at which any protection engages, and paid the full 1R. IMP-013 structurally cannot help this cohort. It remains the other half of the leak.

### Lessons & improvement candidates
1. **★★★ NEW — the trail has a structural dead zone, and it is now measured (shipped as IMP-028, as the instrument).** `TRAIL_TRIGGER_R` **and** `TRAIL_DISTANCE_R` are both **1.0**, so at the trigger the trail candidate (`live − 1.0R`) **equals the entry price** — precisely the level the break-even stage already set — and `STOP_RATCHET_MIN_PCT` (0.10% of entry) blocks the replace until roughly **+1.08R**. **Across the entire +0.5R..+1.08R band the protective stop is pinned at entry and captures nothing.** META #233 cleared 1.0R and was still blocked by **two cents**. Post-gate (36 trades): 6 trades peaked ≥+0.5R with **$174.12** of peak open profit and banked **−$5.29 (capture −3.0%)**; the +0.5R..+1.0R band captures **16.3%** against **52.0%** for trades clearing +1.0R; the whole book captures **−22.2%** of $667.55. **This is a design flaw, not a parameter preference** — a stage of the ratchet that cannot fire in the region it was written for.
2. **The fix was deliberately NOT shipped tonight, and the conditions are pre-registered in `todo.md` so the next run executes a rule, not a hunch.** Three reasons, all evidential: (a) the 2026-08-01 weekly's bar is **~40–60 post-gate trades and the count is 36** — two sessions away, and I have no new evidence that overturns a rule I would be breaking by four trades; (b) the what-if grid is **in-sample only and every single value "wins"** (+$27.61 to +$73.62), which is itself grounds for suspicion — IMP-022 only shipped after an explicit in-sample/held-out split, and that precedent should hold here; (c) **IEX bar sparsity biases any stop-tightening what-if optimistic** (bars miss minutes and understate true ranges, so simulated stops fire *less* often than real ones — META's own window is 270 bars for 279 minutes, and IEX never printed the tick that filled its stop). With the cushion at **$31.89**, shipping an unvalidated exit change four trades short of a pre-registered bar is the wrong risk posture.
3. **Regime is refuted as today's excuse — and that sharpens the diagnosis.** The tape trended up and closed near its highs; 4 of 5 names traded closed green. Previous red sessions could be attributed to a choppy/risk-off tape (08-05, 08-06). Today cannot. **The bot selected correctly and the exits gave it back.** That is the strongest single piece of evidence yet that the remaining problem is exit geometry rather than signal quality.
4. **The sub-0.5R fader (TSM) is the other half and is still un-addressed.** Nothing in the ratchet engages below +0.5R, so this cohort always pays the full 1R. The **★ never-green time-stop** is its designated lever and remains **correctly blocked** on the same 40–60 bar. Do not conflate the two: the give-back cohort and the never-green cohort need different fixes.
5. **Two late-day entries (TSLA/NVDA at 15:16) had 41 minutes to work.** Net −$0.45 — immaterial today, and NOT actioned. But a trade entered near the cutoff can realistically only reach the stop, not the 1.5R target, before the 15:55 flatten. Recorded as an observation to test *after* the exit-geometry work, not as a candidate now — and note IMP-016 already refuted time-of-day in its "skip the first N minutes" form.
6. **The 15:55 flatten took 3 of its 5 ticks for the second session running.** IMP-002's retry loop handled it and IMP-026's watchdog is the backstop, so there is no live risk today. But if it reaches 4 ticks, revisit before it becomes an invariant problem.

### Notes for pre-market research
- ⚠️ **CUSHION IS $31.89 — the thinnest of the incubation, and one average red day trips the −25% / $7,500 formal strategy review.** State it at the top of Monday's entry. **Do not widen risk, do not add names, do not manufacture activity.** If the flag trips, that is a human decision point, not something the pre-market routine resolves.
- **The July jobs number resolved risk-ON**: weak payrolls (net job losses) cut September hike odds and the tape closed near its highs (SPY +0.27%, QQQ +0.37%). Monday's entry should record **where September-hike odds actually settled** (they were ~54% *for* a hike pre-print) — that repricing is the dominant macro variable and it moved in the bot's favour for the first time in weeks.
- **ABNB — the gate handled it exactly as predicted; no action.** Re-enabled into a +8% post-earnings gap and the VWAP gate vetoed it all day (3 blocked attempts, +0.56% to +0.67% above VWAP). It **never traded**, so per the pre-registered rule (and the SE precedent) this is **not** a park trigger — blocked-attempt counts measure gate cycles, not dormancy. Its 0W4L all-time record stands unchanged.
- **TSM is the name to watch** — the only holding that closed red (−1.04%) and the day's single material loss (−$23.30, a −1.04R full stop). It was also the standout *blocked* name on 08-06 (33 vetoes) and got through today at VWAP, then faded. **Not a park candidate on one fill**, but if it produces a second full-1R fade it belongs on the fader watch ahead of UNH.
- **BAC (15 vetoes) and NFLX (11) were today's most-blocked names**, both sitting +0.41% to +0.47% above their own VWAP for hours. Both are *green* all-time contributors (BAC +$44.74, NFLX +$46.23) — this is the gate refusing stretched fills on names that otherwise work, which is the intended behaviour. **Do not park either.**
- **QCOM: the trigger is unchanged and still un-fired.** Still no trade since **07-27** (3 blocked attempts today, at +1.08% to +1.10% above VWAP — the most stretched name on the board). **Do not park it on quietness**; the trigger remains a full-1R fade.
- **AMD still has not had its first post-re-enable fill** (re-enabled 08-06) and produced no attempts today. Keep watching; a park needs a fill.
- **TSLA closed +1.92%** — the strongest name on the list — and the bot still lost on it by entering at 15:16 with 41 minutes left. Nothing to park; a note that late-session entries into a strong name are a timing problem, not a selection problem.
- **⚠️ Sonar is now 5-for-5 unreliable** (08-03 stale, 08-04 inverted, 08-06 empty, 08-07 fabricated, 08-07-close "no catalyst identified" for all five tickers plus unverified index levels). **Treat it as an unverified lead only, and prefer Alpaca's own bars for anything numeric.** The 08-07 pre-market entry's suggestion to stop leading with it still stands.
- **Strategy posture:** analysis-only accrual continues, now at **36 of the 40–60 post-gate bar** — **it will very likely be crossed on Monday or Tuesday.** The next qualifying run should execute the pre-registered ★★★ trail-dead-zone change in `todo.md` (conditions: ≥40 post-gate trades, in-sample/held-out split, IEX-sparsity discount). `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, paper endpoint and the no-overnight rules all untouched.

---

## 2026-08-06 — Daily Review

### Stats
- Trades: **5 closed (1W / 4L)**, win rate **20%**. Net **−$92.27 (−1.21%)**. Ninth live session under IMP-021 + IMP-022. Second consecutive red day (08-05 −$95.95).
- Only "winner" is META **+$0.13** — a break-even stop, not a real win. Avg loser **−$23.10**; **profit factor 0.0014**. Losers: NVDA −$36.23, WMT −$36.96, AMZN −$18.78, AAPL −$0.43.
- Exit mix: **STOP 3 (−$73.06)**, **EOD_FLATTEN 2 (−$19.21)**. **No take-profit, no trail.** One break-even arm (META). TP-hit rate all-time now **25/224 (11%)**.
- Max intraday drawdown ≈ the full −$92.27; equity fell monotonically. **Daily-loss halt (8%) never approached** — worst point ≈ −1.2%.
- Account equity close **$7,548.63**. Broker-reconciled via `alpaca` MCP **to the penny**: last_equity 7,640.90 → equity 7,548.63 = −$92.27, matching DB and `daily_summary` exactly. Positions **flat (0 overnight)**, cash 7,548.63, long_market_value 0, ACTIVE, not blocked. **~36th straight no-overnight session.**
- ⚠️ **Cushion is now $48.63 above the −25% / $7,500 strategy-review flag — the thinnest of the entire incubation** (prior low $78.78 on 07-29). **−24.5% YTD.**
- Reliability: **zero loop errors today** (the two `ConnectionError`/`APIError` rows in the log are 08-05's). **IMP-026's flatten watchdog correctly never fired** — verify-by-absence held, exactly as pre-registered. Service `active`, NRestarts=0, 0 rejects/422.
- Slippage negligible on all five (worst +0.036% AMZN; META filled −0.053% favourable). Sizing matched plan: every trade 0.447–0.496% of equity.

### Trade-by-trade review
MFE/MAE from real 1-min IEX bars; **MFE_R** = MFE ÷ initial 1R stop distance (the +0.5R threshold is what arms IMP-013).

| # | Sym | Entry (ET) | Exit (ET) | conf | mom | MFE% / MFE_R | MAE% | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|-----|--------------|------|------|-----|------------|
| 223 | META | 09:42:37 @589.83 | 10:13:13 @589.86 | 60.74 | 0.72 | **+0.92% / 0.64R** | −0.16% | **STOP (break-even)** | **+$0.13** | **IMP-013 working exactly as designed.** Reached +0.64R → `STOP RAISED 581.29 → 589.83` at 09:55:09 → faded back and scratched. A would-be full-1R loss (~−$34) converted to +$0.13. **Not a strategy failure — the rescue is the intended behaviour.** |
| 224 | NVDA | 09:43:46 @222.31 | 10:37:39 @219.02 | 60.70 | 0.71 | +0.58% / **0.39R** | −1.52% | STOP | **−$36.23** | **Full-1R fader.** Never reached +0.5R, so IMP-013 structurally could not arm. Faded from entry to the stop in 54m. |
| 225 | WMT | 09:48:25 @112.88 | 13:13:32 @111.20 | 60.06 | 0.67 | +0.27% / **0.18R** | −1.49% | STOP | **−$36.96** | **Full-1R fader.** Barely green at any point; bled for 205m into the stop. Lowest momentum of the day (0.67, just over the 0.667 floor). |
| 226 | AMZN | 11:27:19 @274.35 | 15:56:36 @272.26 | 60.20 | 0.68 | **+0.04% / 0.03R** | −1.18% | EOD_FLATTEN | **−$18.78** | **Never-green "faded flatten."** MFE +0.04% — literally never green beyond noise — then held **4h29m** and handed to the clock at −0.76%. Textbook member of the all-time 39-trade / 0%-win / −$833.59 faded-flatten bucket. |
| 227 | AAPL | 15:06:14 @312.42 | 15:56:37 @312.37 | 62.65 | 0.84 | +0.16% / 0.11R | −0.20% | EOD_FLATTEN | **−$0.43** | Dead-flat 50m (range −0.20%/+0.16%), flattened for a scratch. Highest momentum of the day (0.84) and it did nothing — **momentum refuted again.** Harmless. |

**Loss decomposition:** the two full-1R faders (NVDA + WMT) are **−$73.19 = 79% of the day's loss**; the never-green flatten (AMZN) is **−$18.78 = 20%**. META and AAPL are noise. This is the same leak that has defined the drawdown for nine weeks.

### What worked / what didn't
- **Worked — the gates.** IMP-022 skipped **100 stretched-above-VWAP attempts across 8 symbols** (TSM×33, MSFT×21, QCOM×20, XOM×18, INTC×3, NVDA×3, AVGO×1, AMD×1). Replaying all 8 distinct blocked candidates under the real bracket: **2W/6L, avg −0.66%/trade, sum −5.29%** → **verdict ✅ gate PAID.** IMP-021 held: **0 strong-breakout trades got through**, every entry `breakout_score` 0.0000. NVDA is the instructive case — the gate blocked it three times at +0.26/+0.32/+0.38% above VWAP, then let it in at 09:43 when it was at VWAP, and it *still* lost. **The gate is filtering the right thing; what survives simply has no edge.**
- **Worked — capital protection.** Flat into the close, books penny-tied, no halt, no rejects, zero loop errors, watchdog silent by design.
- **Didn't — the surviving population.** 4 of 5 trades never reached +0.5R (MFE_R 0.39 / 0.18 / 0.03 / 0.11). IMP-013 can only rescue trades that go green first, so it armed once out of five. The bot bought five names into a **choppy/risk-off tape** (Perplexity: S&P −0.2% to 7,709.96, Nasdaq −0.1% to 26,348.35, communication services the day's laggard, pressured by higher bond yields and crude; **no company-specific catalyst on any of the five**) and every one faded. This is regime + no-edge, not a defect.
- **IMP-025 gate series** now reads **PAID / COST / COST / PAID** — genuinely tape-dependent, as designed. Keep accruing; do not act on it yet.

### Lessons & improvement candidates
1. **★ The never-green time-stop remains the #1 edge lever — and remains correctly BLOCKED.** AMZN is a picture-perfect case (MFE +0.04%, held 4h29m, −$18.78). But the 2026-08-01 weekly set an explicit bar: **do not touch entry or exit logic until the post-gate sample is decidable at ~40–60 trades.** Post-IMP-021 count is now **30** (was 16). Shipping today would be thrashing against a pre-registered decision rule I have no new evidence to overturn. **Deferred on purpose, not by omission.**
2. **NEW FINDING — the confidence→risk ladder is structurally INERT (shipped as IMP-027).** Post-IMP-021 every entry scores `breakout_score = 0.0` *exactly* (the score is bimodal: across 219 recorded trades it is 0.0 or ≥0.5, never in between; ≥0.5 is vetoed). So confidence = `100·(0.30·ma + 0.20·val + 0.15·mom)`, ceiling **65**, and `CONFIDENCE_RISK_TABLE`'s 70/80/90 tiers are **unreachable**. Verified empirically: all **30** post-veto trades sit in **conf 60.06–63.29** and **100% sized at the floor 0.5% tier** (today 0.447–0.496%). `summary.md §5.9` "more confidence = more money" documents a mechanism that no longer runs. **The failure is SAFE (risk pinned at the floor, never the ceiling) so nothing was re-sized** — but it was invisible, and reviews have repeatedly reasoned about "conf 60–62" as if it discriminated anything.
3. **Momentum is REFUTED — the fifth failed per-trade discriminator.** It is now the *only* varying input to confidence, and its **Pearson r with realized P&L is 0.0001 over n=145** MA-type trades. Buckets are non-monotonic and flip sign between eras (0.85+ is +$120 all-time but −$47 recent). Today's own evidence agrees: lowest-momentum WMT (0.67) and highest-momentum AAPL (0.84) both went nowhere. **Consequence: the entry decision is now a pure AND-gate — `ma == 1.0` AND `value == 1.0` AND `momentum ≥ 0.667`, then the two gates. There is nothing left to tune per-trade.** Confidence (IMP-004), volume, entry extension (IMP-007/010), time-of-day (IMP-016), index-regime (IMP-015/018) and now momentum are all dead. **Future runs: stop looking for per-trade filters. That ground is exhausted — put everything on exit geometry.**
4. **⚠️ Recorded so it is never shipped: IMP-021's own registered follow-up is a capital-protection TRAP.** It reads "down-weight `WEIGHT_BREAKOUT` in the confidence blend now that its leg is gated out." Renormalizing the remaining three weights to sum to 1.0 lifts today's real META signal from **60.74 → ~92**, which lands on the **2.0% `MAX_RISK_PCT` cap — a 4× risk widening** with no edge behind it, dressed up as a tidy-up. **Never ship that form.** Locked as a failing-if-violated test.
5. **Time-of-day is refuted *here*, despite working on the sibling bot.** USTradeBot shipped an opening-range blackout (its IMP-017) after finding its entire lifetime loss pre-10:00 ET. Tested on this bot's data: MA-type pre-10:00 **PF 0.82 (n=75)** vs 10:00+ **PF 0.81 (n=70)** — indistinguishable. **The sibling's fix does not transfer; do not import it.** (Consistent with IMP-016's original refutation.)
6. **Honest verdict on the strategy.** Nine sessions post-gate: 30 trades, still net-negative, 11% TP rate all-time. The gates demonstrably remove losers (today's replay: blocked set −0.66%/trade) but **the kept book has no demonstrated edge** — it is a long-only MA-continuation book whose winners are harvested by the 15:55 clock and whose losers run to a full 1R. That asymmetry, not signal selection, is the problem. The next real change must be **exit geometry**, and it must wait for the sample bar.

### Notes for pre-market research
- **RE-ENABLE ABNB** (parked 08-06 for last night's Q2 print — one-day event park). Check the after-hours reaction first. Its independent weaknesses stand: **0W4L all-time (−$186.30), thinnest name at $22.3M/day** — if it gapped down hard *and* liquidity thinned, converting the event park into a structural one is defensible. Say which, explicitly.
- **⚠️ FRIDAY 08-07 IS THE JULY JOBS REPORT, 8:30 ET** — verified three times this week, lands before the open, so it is **gap** risk not intraday-halt risk. ADP already printed below forecast. **Read the number before deciding any one-day park.**
- **TSM is the day's standout blocked name — 33 VWAP vetoes**, running +0.92% to +1.05% above its own VWAP all morning. Persistently stretched, never eligible. Not a park candidate (the gate is doing its job) but worth noting it consumed a third of the day's blocked attempts. **MSFT×21, QCOM×20, XOM×18** likewise.
- **NVDA chopped hard around its VWAP** — blocked 3×, admitted once at VWAP, then stopped for −$36.23. No NVDA-specific catalyst per Perplexity; chip strength intraday faded into the close. Nothing to park, but do not expect the VWAP gate to save NVDA on a choppy tape.
- **AMD did not trade** (re-enabled 08-06) and produced 1 blocked attempt. Still the highest-ATR name on the list (8.66%) and third-worst all-time (−$315.09). **Watch — it has not yet had its first post-re-enable session.**
- **QCOM remains the standing #1 park candidate** — −19.2% vs 50MA, 1W5L all-time, still no trade since 07-27 (20 blocked attempts today). **Park on the next full-1R fade**; do not park on blocked-attempt counts alone (the SE precedent).
- **WMT and AMZN both faded from entry today** on no catalyst. Not park candidates on one session, but note WMT entered at the momentum floor (0.667) and AMZN never went green — if either repeats, they join the fader watch.
- ⚠️ **Cushion is $48.63 above the $7,500 flag — thinnest ever.** Two more average red days trips the formal strategy review. **Do NOT widen risk, do NOT add names to manufacture activity.** If the jobs number is ugly, a smaller, higher-quality watchlist is the right posture.

---

## 2026-08-05 — Daily Review

### Stats
- Trades: **4 closed (0W / 4L)**, win rate **0%**. Net **−$95.95 (−1.24%)**. Eighth live session under IMP-021 + IMP-022. Worst session since 07-22.
- Avg loser **−$23.99**; no winner → **profit factor 0.00**. Losers by size: META −$41.07, GOOGL −$31.13, QQQ −$23.35, WMT −$0.40.
- Exit mix: **STOP 2 (−$72.20)**, **EOD_FLATTEN 2 (−$23.75)**. No take-profit, no trail, no break-even arm.
- Max intraday drawdown ≈ the full −$95.95; equity fell monotonically. **Daily-loss halt (8%) never approached** — worst point ≈ −1.3%.
- Account equity close **$7,641.12**. Broker-reconciled via `alpaca` MCP **to the penny**: last_equity 7,737.07 → equity 7,641.12 = −$95.95, matching DB and `daily_summary` exactly. Positions **flat (0 overnight)**, cash 7,641.12, long_market_value 0. Broker shows 4 bracket buys + 4 exits, no orphan legs, no qty drift, no missed fill. ~35th straight no-overnight session.
- Slippage: GOOGL −0.103%, QQQ −0.011%, WMT −0.099% (all favourable), **META +0.226% adverse** (signal 595.14 → fill 596.4875, +$1.35/sh ≈ $5.39 of the −$41.07). Net slippage a non-factor.
- Cushion: **$141.12 above the −25% ($7,500) flag** — thinnest since the 07-29 low of $78.78.

### Trade-by-trade review

| Sym | In (ET) | Entry | Stop | stop% | stop/ATR | MFE | MAE | Out | Exit | P&L | Hold |
|-----|---------|-------|------|-------|----------|-----|-----|-----|------|-----|------|
| GOOGL | 09:36 | 381.85 | 376.51 | 1.40% | 5.5× | **+0.11%** | −1.59% | 11:56 | STOP 376.66 | −$31.13 | 140m |
| QQQ | 09:41 | 726.85 | 716.03 | 1.49% | 14.9× | **+0.22%** | −1.36% | 15:57 | FLATTEN 719.06 | −$23.35 | 376m |
| META | 09:41 | 596.49 | 586.21 | 1.72% | 7.7× | **+0.48%** | −1.76% | 11:28 | STOP 586.22 | −$41.07 | 107m |
| WMT | 12:16 | 112.36 | 110.78 | 1.40% | 9.8× | **+0.09%** | −0.88% | 15:57 | FLATTEN 112.34 | −$0.40 | 221m |

**The single decisive number is the MFE column: +0.11%, +0.22%, +0.48%, +0.09%.** Not one of the four trades ever went half a percent green. Every entry was wrong essentially from the fill.

- **All four were pure `MA` signals** (`breakout_score = 0.0000` on every one — zero breakouts fired all day; IMP-021 ✅ held). Confidence 60.5–63.3, i.e. all in the *lowest* band, which is historically the *least* bad one (60–62: PF 0.92).
- **GOOGL −$31.13 (STOP)** — bought 09:36 @381.85, six minutes after the open, near the session high (384.44). GOOGL then fell **−5.39% on the day** (7.21% range, closing at 20% of range). Root cause: **directional/regime failure, not stop placement** — and the stop was the hero here: exiting at 376.51 avoided the further ~5.4% slide to 362.38. Holding would have cost ~$116 instead of $31.
- **META −$41.07 (STOP)** — bought 09:41 @596.49, MFE +0.48%, stopped 11:28 at −1.72%. Only trade with adverse slippage (+0.226%). META closed −1.94%. Same cause: bought strength into a fading tape.
- **QQQ −$23.35 (FLATTEN)** — bought 09:41 @726.85, held 6h16m, never green beyond +0.22%, flattened −1.07%. Sat just above its 716.03 stop all afternoon. This is the **"faded" flatten bucket** (all-time: 39 trades, 0% win, −$833.59) — a slow bleed the stop never catches and the clock ends.
- **WMT −$0.40 (FLATTEN)** — bought 12:16 @112.36, MFE +0.09%, flattened −0.02%. A pure scratch; correctly sized (22 sh on a 0.14% ATR name) and correctly harmless.
- **IMP-013 break-even/trail correctly did nothing.** It arms at +0.5R; with stops at 1.40–1.72%, +0.5R ≈ +0.70–0.86%. The best MFE all day was +0.48%. Not a defect — there was simply never a profit to protect.

### Market context
Genuine **trend-down / risk-off tape, not chop**: SPY **−0.79%** closing at **4% of its daily range**, QQQ **−1.27%** closing at **1% of range** — both finished on the low after sliding all session. GOOGL was the day's disaster (−5.39%). Perplexity `sonar` returned self-contradicting index closes and no per-ticker catalysts (logged as unreliable); the numbers above are computed directly from the bot's own IEX 5-min bars and are authoritative. The bot went long four names into a session that never had an up-leg.

### What worked / what didn't
**Worked:**
- **Risk discipline was flawless.** Four losers, worst −1.72%, total −1.24% of equity. Position sizing matched the confidence plan on all four; MAX_CONCURRENT (3 open at a time) respected; no re-entry of a stopped symbol; no entries after 15:30.
- **The stops paid for themselves.** GOOGL alone: stopping at −1.36% instead of riding to −5.39% saved ~$85.
- **IMP-022 VWAP gate blocked 65 attempts / 4 distinct names** (NVDA×39, INTC×20, SE×5, NFLX×1).
- **Books reconcile perfectly**; flat into the close for the 35th straight session.

**Didn't:**
- **Entry direction.** 4/4 immediately red. No pre-trade filter in the bot looked at what the index was doing.
- **The "faded flatten" bucket struck again** (QQQ): a position that is never green and never stopped just bleeds until 15:55.
- **First-ever intraday loop failures** (see defect below).
- **IMP-022 opportunity cost — `gate COST` again today:** replay of the 4 blocked candidates → **3W/1L, avg +0.29%/trade, sum +1.18%** (best NFLX +0.86%, worst NVDA −0.61%; all EOD). Running series: 07-31 gate PAID (dodged 4×1R), 08-03 gate COST (+0.22%/trade), **08-05 gate COST (+0.29%/trade)**. Two of three readings now say the gate is leaving money on the table, and both COST readings came on days the gate blocked NVDA/INTC-type names that then trended. Not yet decisive (IMP-025 asked for ~10 sessions) but the tell it predicted — *cost on trend-ish names, paid on chop* — is starting to show.

### Root cause (one line)
**All four losses share one cause: long entries into a session-long index downtrend** (SPY/QQQ closing on their lows), with MFE ≤ +0.48% on every trade — a directional failure, not a stop, sizing, slippage, exit-logic or code failure.

### ⚠️ Defect found — and it is the reason today shipped a change
The bot logged its **first two true intraday loop errors ever** at **13:55:19 ET** (`ConnectionError` on `/v2/clock`, connection refused) and **13:56:27 ET** (`APIError`). Every other loop error in the bot's entire log history (120 of them) fell outside RTH or on a weekend.

This matters because of *where* `broker.get_clock()` sits: it gates the whole tick from **outside** `tick()`'s own `try/except`. When it throws, `tick()` never runs — **and neither does `eod_flatten()`**. The 15:55→16:00 flatten window is only **five ticks** wide at `POLL_INTERVAL_SEC=60`; **today's flatten already consumed three of them** (15:55:19 incomplete → 15:56:20 incomplete → 15:57:23 confirmed). Bursts of **8+ consecutive** loop failures are on record (2026-08-01, 14:01→14:10 and 15:14→15:33). **An 8-cycle burst starting at 15:55 would have consumed the entire window and carried QQQ and WMT naked overnight** — breaching the one capital-protection invariant that cannot fail.

The 2026-08-01 weekly review pre-registered this exact trigger: *"if they recur intraday, hardening the flatten path becomes the priority over any edge work."* They recurred intraday today. → **IMP-026.**

### Lessons & improvement candidates (ranked)
1. **[SHIPPED — IMP-026] Clock-independent flatten watchdog.** The no-overnight rule must not depend on a network call. Highest impact because it protects capital and was pre-registered by the weekly.
2. **[REFUTED AGAIN — do not ship] The market-regime entry gate.** Today *looks* like the perfect argument for "don't go long when the index is below its VWAP/EMA9". It is not. `scripts/regime_analysis` over all 214 trades returns **GATE VERDICT: REFUTED** — under QQQ-EMA9 bearish trades **win more** than bullish (43.9% vs 35.3%, PF 0.64 vs 0.60) and under SPY-VWAP PF 0.64 vs 0.60. The bot loses in bullish regimes too (bullish −$1,401, PF 0.62). **Shipping a regime gate on today's session would be textbook overfitting to one day against 214 trades of contrary evidence.** This is the fourth failed pre-trade discriminator after confidence (IMP-004), volume, and entry extension (IMP-010). Backlog ★'s *skip-bearish* formulation should now be considered dead; only a genuinely different regime construction could revive it.
3. **[NEXT, when the sample allows] The "faded flatten" / never-green trade.** QQQ sat 6h16m never exceeding +0.22%. A **time-stop on trades that have not reached +0.25R by N minutes** targets the 39-trade / −$833.59 bucket directly and is the standing #1 edge lever. Blocked by the weekly's 40–60-post-gate-trade bar (now **25**) — do not ship on this session.
4. **[WATCH] IMP-022 gate is now 2-of-3 "COST".** Keep accruing `--replay-skips` per IMP-025's rule; if trend-day COST persists, the indicated fix is regime-*aware relaxation* of `VWAP_MAX_DIST_PCT`, not removal.

### Independent verdict on the strategy
Stated plainly, as standing policy requires: **this strategy still has no demonstrated edge.** All-time 214 trades, **PF 0.62**, expectancy **−$9.65/trade**, equity 10,000 → 7,641 (**−23.6%**). The entire loss is one bucket — **STOP: 95 trades, 6.3% win, −$4,492.99, PF 0.02** — against **TAKE_PROFIT: 25 trades, 100% win, +$2,034** and **EOD_FLATTEN: 94 trades, PF 1.47, +$395**. Four independent pre-trade discriminators (confidence, volume, entry extension, market regime) have now each been tested and each **failed to separate winners from losers**. The honest reading is that entry selection carries no information and whatever edge exists lives in exit management.
The one genuinely encouraging signal is the post-gate era: **25 trades since 07-25, 52.0% win, PF 0.85, net −$39.67** — materially better than lifetime and the only trend pointing the right way. It is still 25 trades against a 40–60 bar, and today's −$95.95 is most of its deficit. **The correct posture remains: protect capital, accrue the sample, ship defect fixes only.** That is precisely what today did.

### Notes for pre-market research
- **GOOGL — handle with care.** Fell **−5.39%** today on a 7.21% range, closing at 20% of range, after the bot bought it 6 min after the open. No catalyst confirmable from `sonar`; **the pre-market routine should establish whether this was news-driven before GOOGL is traded again.** GOOG is also on the watchlist — same underlying, correlated double-exposure risk.
- **QQQ + SPY both closed on their lows** (1% and 4% of range). Index-tracking names gave no intraday up-leg at all; QQQ specifically produced a 6h16m never-green hold.
- **NVDA — 39 blocked attempts, the day's most-rejected name** (persistently +0.64% to +0.80% above VWAP), yet it closed **+1.07%** and the replay says the blocked NVDA entry would have lost −0.61%. Gate behaved correctly on NVDA today.
- **INTC — 20 blocked attempts** at an extreme +1.73% to +1.78% above VWAP; closed **+1.51%**. A persistent gap-and-go profile that this bot's VWAP gate will essentially always refuse — worth asking whether INTC is a structural mismatch for the strategy.
- **NFLX — 1 blocked attempt, and it was the best blocked candidate (+0.86%).** Watch it.
- **SE — 5 blocked attempts, closed +1.95% (99% of range).** SE has been flagged blocked-only since 07-31 and has still never produced a filled trade. It is now a genuine **park candidate**: it consumes gate cycles and has contributed nothing.
- **WMT** behaved exactly as designed (0.14% ATR → 22 sh → −$0.40 scratch). No concern.
- Watch the **August jobs report, Friday 08-07 08:30 ET** — flagged by last week's weekly review; verify timing each morning.
- **Tape regime note:** today was a clean trend-down day, the opposite of the chop the gates were tuned on. Two consecutive sessions (08-03 trend-up, 08-05 trend-down) have now produced `gate COST` readings.

### Ops note (outside the bot repo)
**The 2026-08-04 daily review silently did not run** — `/root/claude-routines/logs/uswisbot-daily-review.20260804-212501.log` shows `timeout: failed to run command 'claude': No such file or directory`, **rc=127**. That is the **third** silent no-run in ~3 weeks (07-29 rc=1, 08-04 rc=127); 08-04's session (4 trades, 3W/1L, +$29.48) therefore has **no review entry** and this file jumps 08-03 → 08-05. The improvement engine is only as reliable as the routine that drives it. Recorded in `todo.md`; the fix is a PATH/binary issue in the cron wrapper, outside `/root/USTradeWisBot`, and needs a human or an infra-scoped run.

---

## 2026-08-03 — Daily Review

### Stats
- Trades: **1 closed (0W / 1L)**, win rate **0%**. Net **−$5.09 (−0.066%)**. Sixth live session under IMP-021 breakout-fade veto + IMP-022 VWAP entry gate. Effectively a **flat session** — the loss is 1/15th of one average loser.
- Avg loser **−$5.09**; no winner → profit factor **0.00** (gross win $0 / gross loss $5.09). A single 0.2% scratch, not a drawdown.
- Max intraday drawdown: negligible. The one position' worst mark was **MAE −0.55%** against a −1.52% stop; it never went materially red.
- Account equity close **$7,707.65** (broker-confirmed via `alpaca` MCP: last_equity 7,712.74 → equity 7,707.65 = **−$5.09**, matches DB **to the penny**). Positions **flat (0 overnight)**, cash 7,707.65, long_market_value 0. Broker shows **exactly 2 orders** all day (1 bracket buy + 1 sell-to-close); both bracket legs (TP 290.92, stop 280.25) were **cancelled at 19:55:06/19:55:11Z before** the market-sell flatten filled at 19:56:09Z — no orphans, no naked exposure. ~33rd straight no-overnight session.
- Slippage: signal price 284.52 → fill **284.5778** = **+0.020%** (+$0.058/sh). Negligible; not a factor.
- Cumulative post-gate scorecard (`gate_monitor --since 2026-07-25`, 6 sessions): **17 trades, 10W/7L (58.8%), net +$26.80, PF 1.17**, avg win $18.39 vs avg loss $22.44. Still **positive but thin** — the weekly's decidability bar is ~40–60 trades; we are at 17.

### Trade-by-trade review
| # | Sym | Entry | Exit | Conf | Type | Reason | P&L | Root cause |
|---|-----|-------|------|------|------|--------|-----|------------|
| 210 | AMZN | 14:57:40 @284.5778 (9 sh) | 15:57:09 @284.0122 | 60.54 | MA | EOD_FLATTEN | **−$5.09** (−0.199%) | Pure-MA (breakout 0.0000, ma 1.0, value 1.0, momentum 0.7026) → IMP-021 held. Stop 280.25 (1R = 1.52%), TP 290.92 (+2.23%). **Neither leg was ever threatened: MFE +0.46%, MAE −0.55%** over a 59-minute hold. Root cause is **not** stop placement, slippage, signal quality or a bug — it is **timing/participation**: AMZN closed **+2.02%** on the day (278.49 → 284.12) and had already printed its session high **287.17 before the entry**. The bot bought the late-stage flat spot after the move, then chopped sideways into the flatten. IMP-013 break-even never armed (never reached +0.5R). Correct behaviour by every rule the bot has; the trade simply had no move left to capture. |

### What worked / what didn't
- **Worked — reconciliation, risk and exit machinery, again flawless.** Broker/DB agree to the penny, brackets cancelled before liquidation, flat overnight, no circuit-breaker events, no errors inside market hours. The two `EOD flatten incomplete … Retrying next tick` lines at 15:55:06 / 15:56:07 are **IMP-002 working as designed** (async leg-cancel lag), and the position was closed at 15:56:09Z — well inside the window. Not a defect.
- **Didn't work — participation on the day the strategy was built for.** Today was a clean **trend-up tape**: SPY **+1.10%** (749.49 → 757.72, closing 0.11% off its high), QQQ **+1.72%** (688.29 → 700.10). The bot's MA-drift edge should eat this. It took **one** trade, at **14:57**, for −0.2%.
- **The reason is structural, and today quantifies it for the first time.** The IMP-022 VWAP gate blocked **172 entry attempts across 17 distinct symbols** — every single candidate the bot generated except AMZN. On a trending day, "stretched above session VWAP" *is* the trend: price sits above VWAP all day by construction, so the gate's veto rate rises precisely when the edge is most available. **17 of 18 distinct candidates (94%) were vetoed.**
- **Counterfactual (new instrument, IMP-025 below) — today the gate COST money.** Replaying all 17 blocked candidates from their *first* skip print against real 1-min bars under the bot's own bracket (−1.50% floor stop / +2.25% target / 15:55 flatten): **9W/8L, avg +0.22% per trade, sum +3.76%, and ZERO stop-outs.** Two would have reached target (**NVDA** 10:01 @202.47 → TP at 11:04; **META** 09:30 @556.60 → TP at 09:33). Worst blocked was **AAPL −1.44%** — which still did not hit the stop. Because the replay uses the *floor* stop (real stops are ≥ the floor), this is a **lower bound** on what the gate cost.
- **This is the exact opposite of 07-31**, where the same replay showed the gate dodging **4 full 1R stop-outs** (MSFT×3, META). **Both readings are correct.** The gate is tape-dependent by design: it pays on round-trip/chop tapes and it costs on one-way trend tapes. Two anecdotes pointing opposite ways is not a verdict — it is the reason a running series is now recorded rather than re-derived by hand each night.
- **Confidence remains a constant** (60.54 today; 60.5–62.5 all of last week), as the weekly diagnosed: `WEIGHT_BREAKOUT = 0.35` is 35% of the blend and is identically 0 on every trade the bot can now take, pinning every entry to the smallest 0.5%-risk bucket (9 shares / $2,561 notional here). Left alone deliberately — renormalising would both admit marginal candidates and inflate sizing. It is an accidental brake, not a working signal.

### Lessons & improvement candidates
1. **The VWAP gate's opportunity cost is now the #1 open question — and it must be answered by a series, not a session.** Two sessions replayed, pointing opposite ways (07-31: gate saved ~4×1R; 08-03: gate cost +0.22%/trade). **Shipped tonight as measurement, not as a strategy change** (IMP-025). The decision rule to apply once ~10 sessions have accrued: if the blocked set is *persistently* positive on trend days, the fix is **not** to remove the gate but to make it **regime-aware** (e.g. relax `VWAP_MAX_DIST_PCT` only when the index is trending and the name is above a rising VWAP), so chop-day protection is preserved.
2. **"Late entry" was tested as today's obvious culprit and REFUTED — do not pursue it.** AMZN entered with only 58 minutes of runway before the 15:55 flatten, which looks like the cause. It is not: bucketing all 206 closed trades by *runway* (minutes from entry to flatten), the **<60m band is the best bucket all-time** (n=6, 33% win but **+$11.45/trade**, PF 6.33), while 60–120m is the worst (n=8, 0% win, −$26.28/trade). Separately, TP-reaching trades hit target in a **median 45 min** (p25 16 min), so a short runway does not preclude a winner. **No case for tightening `ENTRY_CUTOFF_ET` from 15:30.** Recorded so no future review re-proposes it.
3. **Exit geometry remains the standing #1 *strategy* lever** (weekly 2026-08-01), unchanged tonight: only **12.1% of all trades (25/206) ever reach the target**, and today added another clock-exit. Still correctly deferred — the only valid sample is the 17-trade post-gate book, and the weekly set the bar at 40–60. Do not fit an exit change to pre-07-25 breakout trades the bot can no longer take.
4. **Housekeeping gap now four weeks old:** `bot/analytics.py`, `bot/replay.py`, `scripts/replay.py`, `tests/test_replay.py` remain uncommitted (someone else's work-in-progress; left untouched and unstaged per standing rule). This still blocks retiring the **structurally frozen** "false-breakout rate 52.7% ≥ 40.0%" verdict in `report.py`, which tonight *again* printed `NEEDS WORK` on a metric computed over a trade class that can never be added to.
5. **Perplexity `sonar` returned stale data** — it reported Friday's close (S&P 7,489.72) as "today". Today's tape in this entry is taken from **Alpaca 1-min bars directly** (authoritative). Treat the sonar market read as unreliable for same-day close context; prefer bars.

### Notes for pre-market research
- **Tape:** strong one-way trend-up day. SPY +1.10% (757.72), QQQ +1.72% (700.10), both closing within ~0.2% of session highs. Semis/AI led. If tomorrow opens in the same regime, expect the VWAP gate to veto most candidates again — **that is expected behaviour, not a fault**; do not react by widening risk.
- **Blocked all day, never traded (17 names):** AAPL, AMD, AVGO, BAC, GOOG, GOOGL, INTC, META, MSFT, MU, NVDA, QCOM, QQQ, SE, SPY, TSLA, TSM. These are **not** bad names — the gate blocked them for being *extended above VWAP*, and 9 of 17 would have finished green. **Do not park any of them on the strength of today.**
- **Best blocked candidates:** NVDA (would have hit target by 11:04), META (target by 09:33), QCOM (+0.63%), TSLA (+1.25% from its 10:10 print). **Worst:** AAPL (−1.44%), AMD (−1.05%), INTC (−0.61%).
- **Most-attempted blocks** (gate re-fires ~60s, so attempts ≫ opportunities): QQQ×20, AVGO×20, TSLA×19, QCOM×19, MSFT×14, MU×14, META×13, GOOGL×12, NVDA×11. **MU was stretched +3.30–3.77% above VWAP all afternoon** and AMD/INTC +2.5–2.8% — those are genuinely extended, correctly blocked.
- **SE:** 7 blocked attempts, 0 entries again (+0.16% if taken). Now several sessions of blocked-only history. Still no losses attributable to it — **watch, do not park yet**, per 07-31.
- **AMZN** traded today (only fill): closed +2.02% but printed its high at 287.17 *before* the 14:57 entry. Fine name; the issue was timing, not selection.
- **Equity cushion:** $7,707.65, **$207.65 above** the −25% ($7,500) flag. Thinnest-ever remains $78.78 (07-29). **Never widen risk to chase it back.**
- **Calendar:** August jobs report **Friday 08-07, 8:30 ET** (weekly flagged; verify each morning). Tail of Q2 earnings ongoing.
- **Overnight infra note:** one `ConnectTimeout` to `paper-api.alpaca.markets` at **02:46 ET** (outside market hours, self-healed on the next tick). Consistent with the burst the weekly flagged. **Still zero occurrences inside market hours** — the 15:55 flatten has never been threatened. Keep watching; if these ever appear intraday, hardening the flatten path outranks all edge work.

---

## 2026-07-31 — Daily Review

### Stats
- Trades: **3 closed (3W / 0L)**, win rate **100%**. Net **+$71.17 (+0.93%)**. **Fifth live session under IMP-021 breakout-fade veto + IMP-022 VWAP entry gate**, and the second green day running.
- Avg win **+$23.72** (NVDA +$44.87, SPY +$16.87, BAC +$9.43); **no loser** → profit factor undefined (gross win $71.17 / gross loss $0).
- Max intraday drawdown: negligible — no position went materially red; all three exited above entry.
- Account equity close **$7,712.77** (broker-confirmed via `alpaca` MCP: last_equity 7,641.60 → equity 7,712.77 = **+$71.17**, matches DB **to the penny**). Positions **flat (0 overnight)**, 0 orphan orders — all three bracket legs (TP limit + stop) were cancelled at 19:55:40Z before the market-sell flatten. All fills reconcile exactly (BAC 61.87→62.10, NVDA 198.010833→201.75, SPY 742.55→748.173333). ~32nd straight no-overnight session.
- Cumulative post-gate scorecard (`gate_monitor --since 2026-07-25`, 5 sessions): **16 trades, 10W/6L (62.5%), net +$31.89, PF 1.21** (07-27 −72.52 / 07-28 +31.64 / 07-29 −61.24 / 07-30 +62.84 / 07-31 +71.17). **The post-gate book has crossed into positive territory at the ~15–20-trade decision point flagged on 07-30.**

### Trade-by-trade review
| # | Sym | Entry | Exit | Conf | Type | Reason | P&L | Root cause |
|---|-----|-------|------|------|------|--------|-----|------------|
| 205 | BAC | 10:32:25 @61.87 | 15:55:40 @62.10 | 60.6 | MA | EOD_FLATTEN | **+$9.43** (+0.37%) | Pure-MA entry at/below session VWAP; stop 60.97 (1R = 1.45%). Only ever reached +0.26R so IMP-013's break-even never armed. Slow positive drift with the financials; correct hold, small reward (41 sh, smallest 0.5% risk bucket). |
| 206 | NVDA | 10:44:12 @198.0108 | 15:56:42 @201.75 | 62.5 | MA | EOD_FLATTEN | **+$44.87** (+1.89%) | Day's best. Stop 194.89 (1R = 3.12 = 1.58%). **IMP-013 textbook:** at 13:37:16 (live 199.73 = +0.55R) the broker-side stop ratcheted 194.89 → **198.01 (break-even)**; at 15:50:35 (live 201.72 = +1.19R) it trailed to **198.60**, locking +0.19R. Exit at 201.75 was within **0.32% of the 202.40 TP limit** and essentially at the session high — near-zero give-back. |
| 207 | SPY | 10:51:47 @742.55 | 15:56:43 @748.1733 | 60.6 | MA | EOD_FLATTEN | **+$16.87** (+0.76%) | Stop 731.27 (1R = 11.28 = 1.52%). Reached +0.51R only at 15:45:30 → stop raised to break-even 742.55, then flattened. Broad-index drift-up; correct hold. |

All three were **pure-MA** (breakout_score 0.0000, ma_score 1.0, value_score 1.0, momentum 0.70–0.83) → **IMP-021 held, 0 strong-breakout leaks**. All three entered in a **19-minute window (10:32–10:51 ET)**, all at/below session VWAP.

### What worked / what didn't
- **Worked — and this is today's headline finding: the IMP-022 VWAP gate demonstrably SAVED money on a green tape.** It blocked **25 entry attempts across 4 distinct symbols** (MSFT×13, SE×6, NVDA×5, META×1). Replaying those skipped fills against real 1-min bars with the bot's own ~1.5% floor stop and a 15:55 flatten:
  - **MSFT** 09:39 @459.03 → MAE **−1.81%**, **stops out −1.50%**; 09:50 @460.04 → MAE −2.02%, **stops −1.50%**; 10:01 @461.58 → MAE −2.35%, **stops −1.50%**. (MSFT *closed* at 466.44, up on the day — but it round-tripped to a 449.87 session low first, so every stretched entry would have been chopped out before the rally. The gate did not miss a winner; it dodged three stop-outs.)
  - **META** 10:51 @551.74 → MAE −2.08%, **stops −1.50%**.
  - **SE** 10:45 @106.85 → +0.15% EOD; 10:51 @107.25 → −0.22% EOD (two scratches).
  - Net: **4 of 6 skipped opportunities were full 1R losers, 2 were scratches, 0 were winners.** This directly **retires the ⚠️ tape-dependence flag** raised on IMP-022 ("could saw off drift-up winners on a green tape") — today WAS the green tape (S&P +0.7%, Nasdaq +1.0%) and the gate's veto set was all-loser.
- **Worked:** IMP-013's break-even/1R-trail armed correctly on the two trades that earned it (NVDA at +0.55R and again at +1.19R; SPY at +0.51R) and correctly stayed passive on BAC (+0.26R, never earned it). Zero give-back: NVDA exited within 0.32% of its TP.
- **Didn't — a MEASUREMENT defect, not a trading defect.** `scripts/gate_monitor.py` reported "🚫 skipped **0** stretched-above-VWAP entries / entries logged: 0" for today, while the bot's own log recorded **25 skips and 3 entries**. Root cause: the unit sets `StandardOutput=append:/var/log/ustradewisbot/bot.log` (deploy/ustradewisbot.service:22), so **journald holds only systemd lifecycle lines** (9 lines all day) — and the monitor was counting from journald. It has therefore reported "skipped 0" on **every session since IMP-022 shipped**. Verified against the rotated logs: real skips were **07-27: 125, 07-28: 4, 07-29: 168, 07-30: 126, 07-31: 25 — 448 total, all previously reported as 0.** The 07-30 daily-review sentence "the gate skipped **0** entries today, so it cost nothing on the green tape" was **wrong on the count** (it skipped 126 across 9 symbols); the conclusion happens to be right, but it was drawn from a blind instrument. **Fixed as IMP-024 below.**
- No defect, no bug, no risk event in the trading path: 0 rejects, no halt, no circuit-breaker, no slippage issue (DB entry/exit prices match broker fills to 6 dp), books tie to the penny.
- Tape context (Perplexity): **choppy-but-higher, not a clean trend** — S&P 500 **+0.7%** to 7,489.72, Nasdaq **+1.0%** to 25,373.85, the index "veered between gains and losses through the day" with a late-day rally; broad rotation rather than one-directional risk-on. No single-name catalyst surfaced for BAC/NVDA/SPY/MSFT/SE/META. That chop is exactly why the stretched above-VWAP entries would have been shaken out while the at-VWAP entries drifted up.

### Lessons & improvement candidates
1. **[SHIPPED IMP-024] The monitor watching the bot's two most important changes was blind.** Highest-impact item available today: no trading-logic change is justified by a single 3W/0L session (that would overfit), but an instrument that reports 0 for a gate firing 448 times is actively corrupting the evidence base every review reads — including yesterday's. Fixed by reading the real log file.
2. **The gates are earning their keep — keep them, do not tune them.** The 07-30 note set a decision point at ~15–20 post-gate trades: we are at **16 trades, 62.5% win, +$31.89, PF 1.21**, and today's skip-replay shows the VWAP gate removing 4 full-R losers on the exact tape type that was flagged as its risk case. The disciplined move is to let the sample keep accruing, not to touch entry logic on a green streak.
3. **Standing structural note (not actionable today):** all three fills sat in the [60,65] confidence / smallest 0.5%-risk bucket (the known IMP-022 follow-up consequence), so a 3W/0L day still only sizes to +$71. That caps upside as much as it caps downside. Revisit sizing **only** after the post-gate book proves positive over a materially larger sample — and never by widening `MAX_RISK_PCT`.
4. **Exit mix worth watching:** post-gate exits are 8 EOD_FLATTEN (+$81.57), 7 STOP (−$105.40), 1 TAKE_PROFIT (+$55.72). Winners are still mostly harvested by the clock rather than by a profit-taking rule — NVDA today ran to within 0.32% of its TP and still exited on the flatten. Not enough evidence yet, but if the EOD_FLATTEN bucket keeps carrying the winners, a tighter/scaled take-profit is the next logic question after the gates finish proving out.

### Notes for pre-market research
- **MSFT — the day's most instructive name.** It gapped and ran early, triggering **13 blocked entry attempts** between 09:39 and 10:01 ET (all +0.29% to +0.85% above session VWAP), then round-tripped to a 449.87 low before closing at 466.44. Every blocked fill would have stopped out. **Keep MSFT — it is not a bad name, it is a name the open-fade gate handles correctly.** Expect it to keep generating blocked attempts on gap-up mornings; that is the gate working, not a curation problem.
- **SE — still marginal.** Six blocked attempts today (+0.66% to +1.05% above VWAP), and both would-be entries were scratches (+0.15% / −0.22%). It has now been **dormant for tradeable purposes since 07-13** while generating gate noise. Not a park trigger yet (no losses, no structural mismatch), but it is the weakest name on the list — flag if it produces another week of blocked-only activity.
- **META** — one blocked attempt at 10:51 (+0.55% above VWAP) that would have lost a full 1R (MAE −2.08%) before closing green. Post-earnings drift is still choppy, as the 07-30 note predicted. Keep, keep watching.
- **NVDA, BAC, SPY** — all three today's winners on clean at/below-VWAP MA entries. NVDA in particular behaved exactly as the strategy intends (trended, armed the trail, exited near the high). No action.
- **Re-enable XOM Monday 08-03** as the 07-31 research entry planned — its Q2 print is now digested (one-day event park only).
- **AMZN did not trade today** on its first post-print (+9% gap-up) session; **AAPL** likewise produced no fill after its −4% gap-down. Both re-enabled 07-31, so tomorrow is effectively still their first clean read — watch reaction quality.
- Equity **$7,712.77 (−22.9% YTD), now ~$213 above the −25% ($7,500) review flag** — cushion improved two sessions running (+$134 over 07-30/07-31). Still protect aggressively; two green days do not undo a −23% drawdown.

---

## 2026-07-30 — Daily Review

### Stats
- Trades: **2 closed (2W / 0L)**, win rate **100%**. Net **+$62.84 (+0.83%)**. **Fourth live session under IMP-021 breakout-fade veto + IMP-022 VWAP entry gate — and the first TAKE_PROFIT of the post-gate era.**
- Avg win **+$31.42** (INTC +$55.72, SPY +$7.12); **no loser today** → profit factor undefined/∞ (gross win $62.84 / gross loss $0). One clean green day — treat as favorable-tape confirmation, not proof of edge.
- Max intraday drawdown: negligible — neither name went materially red (INTC ran straight up to TP; SPY only ever +0.3%).
- Account equity close **$7,641.62** (broker-confirmed via `alpaca` MCP: last_equity 7578.78 → equity 7641.62 = **+$62.84**, matches DB **to the penny**). Positions **flat (0 overnight)**, 0 orphan orders; both fills reconcile exactly (INTC 86.5564→91.6218, SPY 738.84→741.2133). ~31st straight no-overnight session.
- Cumulative post-gate scorecard (`gate_monitor --since 2026-07-25`, 4 sessions): **13 trades, 7W/6L, net −$39.28, PF 0.74** (07-27 −72.52 / 07-28 +31.64 / 07-29 −61.24 / 07-30 +62.84). Still net-negative but climbing off the bottom; thin sample — judge on trend.

### Trade-by-trade review
- **INTC** — BUY 11 @ 86.5564 (09:36:39 ET), stop 83.44 (−3.6%, ~ATR), TP 91.62. Exit **91.6218 @ 10:01:15 ET TAKE_PROFIT**, **+$55.72 (+5.85%)**, held ~25 min. Pure-MA entry (conf 61.43, breakout_score 0 → passed IMP-021), filled at/below session VWAP (0 IMP-022 skips). **IMP-013 worked textbook-perfect:** as price ran, the broker-side stop ratcheted 83.44 → 86.56 → 87.28 → 87.60 → 87.73 → **88.22** (locking profit above entry) before the TP limit filled at 91.62. **Root cause of win: clean near-VWAP MA entry into a chip name that trended hard on the risk-on tape — exactly what the gates select for.** Day's best and the era's first TP.
- **SPY** — BUY 3 @ 738.84 (10:29:43 ET), stop 727.96 (−1.47%), TP 755.68. Exit **741.2133 @ 15:56:48 ET EOD_FLATTEN**, **+$7.12 (+0.32%)**. Same profile (pure-MA, conf 61.20, at/below VWAP). Reached only +0.32% so IMP-013's break-even/trail never armed; drifted up with the broad rally and flattened green at the close. **Root cause: shallow but positive drift on a rising index; correct hold, small reward.**

### What worked / what didn't
- **Worked:** the whole gate + exit stack fired cleanly on a favorable tape. Both fills were pure-MA (IMP-021 held — 0 strong-breakout leaks), both at/below session VWAP (IMP-022 rejected 0 — nothing stretched). **IMP-013 delivered its first post-gate TAKE_PROFIT** by ratcheting INTC's stop into profit. Books tie to the broker to the penny; 0 rejects, 0 overnight.
- **Didn't (nothing broke):** no defect, no bug, no risk-control event. The only structural note is the survivor bucket is narrow — both entries sit in the [60,65] confidence / smallest 0.5% risk band (the IMP-022 follow-up's known consequence), so a green day is capped small (SPY's +0.3% only sized to +$7). Not a defect; a deliberate brake.
- **⚠️ Tape-dependence watch (from IMP-022 obs):** today was the green/trending tape flagged as the VWAP gate's risk case ("could saw off drift-up winners"). Result: the gate skipped **0** entries today (both fills were near/below VWAP), so it **cost nothing on the green tape** — one reassuring data point that the gate isn't reflexively vetoing winners on up-days. Keep watching.
- Tape context (Perplexity): **risk-on / trending** — S&P **+1.7%**, Nasdaq **+2.8%**, a broad tech-led rebound from Wednesday's Fed-driven selloff (rates held; post-Fed repositioning + Big-Tech-earnings digestion). INTC rode the **chip-stock rebound / tech rotation** (no INTC-specific catalyst surfaced). The bot's two MA entries drifted/ran up with the tape — regime-consistent.

### Lessons & improvement candidates
- **No change warranted today.** A single 2W/0L day on a favorable trending tape, fully broker-reconciled, with every gate and exit behaving as designed, gives **no data justification** for a trading-logic change — making one would overfit one good day and violate the ground rules (never overfit to one day, never random changes). Respectable "reviewed, no change" outcome; the disciplined move is to keep accruing the post-gate sample.
- Standing open item (not today's): the cumulative post-gate book is still −$39 over 13 trades — the gates "stop the bleed" but haven't yet proven a positive edge (per IMP-021/022 honest caveats). Decision point remains ~15–20 trades; if it stays net-negative, revisit whether the pure-MA-near-VWAP survivor set has real positive expectancy or merely less bleed (would be the next IMP, once the sample justifies it — not today).
- **Housekeeping gap:** there is **no 07-29 entry in this file** — that post-close review evidently didn't append (07-29 traded 1W/2L −$61.24 per `report`; captured in the cumulative scorecard above). Flagging so the sequence gap is visible; not backfilled here.

### Notes for pre-market research
- **INTC** — big intraday winner (+5.85% to TP in 25 min) riding the chip/tech rotation, no single-name catalyst. Momentum name; keep on the watchlist but expect mean-reversion after a one-day +5.85% run — don't chase a gap-up open tomorrow.
- **SPY** — index proxy behaved as a slow-drift hold on the rally; fine to keep as a low-vol MA vehicle but it only ever sized/paid small (+0.3%).
- Tape was strongly risk-on today (rebound from the Fed selloff); watch whether tomorrow gives back — a mean-reversion/red open would test the gates on the *un*favorable side. No watchlist change requested from the daily side.

## 2026-07-28 — Daily Review

### Stats
- Trades: **3 closed (2W / 1L)**, win rate **66.7%**. Net **+$31.64 (+0.42%)**. **Second live session under the IMP-021 breakout-fade veto + IMP-022 VWAP entry gate.** Small green day that recovers ~44% of Friday-through-Monday's give-back.
- Avg win **+$16.06** (GOOG +$25.90, AAPL +$6.22) vs avg loss **−$0.48** (MSFT, a break-even scratch). Profit factor **≈ 66.9** (gross win $32.12 / gross loss $0.48) — flattered by the tiny loss; treat as "no real loser today," not a repeatable PF.
- Max intraday drawdown: negligible — MSFT never went materially red (IMP-013 break-even stop held it at −$0.02%).
- Account equity close **$7,640.06** (broker-confirmed, was $7,608.42 → +$31.64, matches DB **to the penny**). ~29th straight no-overnight session; account flat at the close, **broker reconciles exactly** (0 positions, 0 orphan orders).
- Cumulative post-gate scorecard (`gate_monitor --since 2026-07-27`, the new IMP-023 view): **8 trades, 4W/4L, net −$40.88, PF 0.48** across the 2 sessions — still net-negative but thin; judge on the trend, not either day.

### Trade-by-trade review
- **GOOG** — BUY 7 @ 328.65 (09:37:47 ET), stop 323.29 (−1.63%, ~3×ATR), TP 335.59. Exit **332.35 @ 15:57 EOD_FLATTEN**, **+$25.90 (+1.13%)**. Pure-MA entry near/below session VWAP (passed IMP-022), breakout_score 0 (passed IMP-021). Drifted up all session; never reached the +1R trail-arm nor TP, flattened green at the close. **Root cause of win: clean near-VWAP MA entry into a name that trended up — exactly what the gates select for.** Day's best.
- **AAPL** — BUY 7 @ 338.88 (09:41:00 ET), stop 333.65, TP 346.35. Exit **339.77 @ 15:57 EOD_FLATTEN**, **+$6.22 (+0.26%)**. Same profile (pure-MA, at/below VWAP). Marginal up-drift — barely green, held to flatten. HSBC upgrade (Buy, $366 PT) noted premarket; no intraday catalyst per Perplexity. **Root cause: shallow but positive drift; correct hold, small reward.**
- **MSFT** — BUY 6 @ 394.68 (09:46:27 ET), stop 389.04, TP 403.85. Exit **394.60 @ 15:13 STOP**, **−$0.48 (−0.02%)**. This is **IMP-013 working as designed**: MSFT reached +0.5R, the stop ratcheted to ~break-even, price pulled back and scratched it out — a would-be full-1R loser (~−$34 at the original stop) converted to a −$0.48 nick. **Root cause: not a strategy failure — the break-even rescue is the intended behaviour on a fade-after-green.**

### What worked / what didn't
- **Worked:** the full gate stack fired cleanly. All 3 fills were pure-MA (IMP-021 held — 0 strong-breakout leaks) and at/below session VWAP (IMP-022 skipped 0 — nothing stretched to reject). IMP-013 turned the one fader into a scratch instead of a −$34 stop. Books tie to the broker to the penny; 0 rejects, 0 overnight.
- **Didn't (nothing broke):** no defect today. Only nit — both winners (GOOG, AAPL) rode to the 15:57 EOD flatten rather than to TP or the +1R trail; the trail never armed on GOOG despite +1.13% (its +1R ≈ 334.01 vs a 332.35 close, so it genuinely didn't reach the arm point). No action — that's the trail behaving correctly on a slow drift, not a leak.
- Tape context (Perplexity): **choppy / risk-off-for-tech** — S&P +0.2% (7,428.78), Nasdaq −0.2% (24,876.91), AI/chip names sold off ahead of MSFT/META (Wed AMC) and AAPL (Thu AMC) prints; no single-name catalyst on GOOG/AAPL/MSFT. The bot's mega-cap MA entries drifted up despite the soft chip tape — regime-consistent, not luck-dependent.

### Lessons & improvement candidates
1. **No trading-logic change warranted today** — a single +$31.64 day on the gates' 2nd live session is not a mandate to touch entry/exit/sizing; that would overfit. The disciplined move is to accrue the post-gate sample and let it speak. **(chosen outcome)**
2. **Highest-impact done → IMP-023 (tooling):** `gate_monitor.py` was per-day only, so answering "are IMP-021/022 net-delivering?" meant hand-summing daily runs, and the script had **zero tests**. Added a cumulative `--since DATE` post-gate scorecard (total W/L, net, **PF**, by-exit split, per-session net, IMP-021-hold check across the window) + first pytest coverage (9 tests) built on today's real 3-trade session. Capital-neutral, no trading logic touched.
3. **Still watching (needs more sessions, do NOT act yet):** cumulative post-gate is −$40.88/8 trades — if it stays net-negative past ~15–20 trades, revisit whether the pure-MA-near-VWAP survivor set has genuine positive expectancy or just less bleed. The residual open-fade leak (full-1R faders that never reach +0.5R) remains the strategic target; VWAP replay + regime_analysis unchanged.

### Notes for pre-market research
- **GOOG** — clean up-drift winner on a soft-tech tape; behaving well under the gates. Keep.
- **AAPL** — only marginally green (+0.26%); HSBC Buy/$366 PT premarket. **Reports Thu 07-30 AMC** — no intraday risk (flatten 15:55 ET), but expect a post-close gap Thu; no park needed.
- **MSFT** — **reports Wed 07-29 AMC** (along with META, QCOM). Today's entry scratched at break-even. WisBot flattens before the print, so no overnight gap risk, but Wednesday's session will be pre-earnings jittery — normal.
- Tape is **choppy / risk-off-for-tech into FOMC (decision Wed 2pm ET) + the mega-cap prints**. AI-capex/chip scrutiny is the dominant driver. No watchlist symbol chopped into a bad fill today; nothing gapped that needs parking. 3 signals from 26 active names — gates are (correctly) keeping the book selective.

---

## 2026-07-27 — Daily Review

### Stats
- Trades: **5 closed (2W / 3L)**, win rate **40%**. **First live session under the IMP-021 breakout-fade veto + IMP-022 VWAP entry gate** (both shipped Sat 07-25). Gives back Fri's +$87 green day on a choppy tech-off tape.
- Net P&L: **−$72.52** (day **−0.944%**). Equity close **$7,608.45** (from $7,680.97 open). **Alpaca reconciles to the penny** (PA3ESJUO8RU0 equity $7,608.45 = DB close; last_equity $7,680.97 = prior close; **0 open positions — no naked overnight** (~28th straight clean session); all 5 buys (AAPL 335.41, NFLX 70.478056, QCOM 169.904, META 606.83, COST 950.64) + all 5 sells (AAPL stop 335.382857, NFLX stop 70.59, QCOM stop 167.26, META stop 597.35, COST flatten 951.25) match DB fills exactly; account ACTIVE, not blocked).
- Avg winner **+$2.63** (NFLX +4.03, COST +1.22); avg loser **−$25.92** (QCOM −39.66, META −37.92, AAPL −0.19 break-even scratch). Profit factor (day) = 5.25 / 77.77 = **0.07**.
- Exit reasons: **4 STOP** (AAPL −0.19 IMP-013 break-even, NFLX +4.03 IMP-013 trailed-win, QCOM −39.66 full-1R, META −37.92 full-1R), **1 EOD_FLATTEN** (COST +1.22 drift). Circuit breaker NOT tripped (−0.94% << −8.0% halt). Service active all session (up since the 07-25 15:15 UTC restart), **0 errors/exceptions**.
- ⚠️ **Equity $7,608.45 = −23.92% YTD, now $108.45 above the −25% ($7,500) strategy-review flag** — cushion thinned from $181 (07-24) back toward the 07-23 low. Protect aggressively into the FOMC/PCE/Mag-7 week.

### ★ Gate verification (first live session under IMP-021/022)
- **The gates fired exactly as designed.** All 5 entries were **pure-MA, breakout_score = 0.0000, confidence 60.5–61.6** — i.e. the exact survivor set the two gates intend to keep (the `by_stop_protection` follow-up finding: post-veto every taken trade is pure-MA capped at conf-65). **IMP-021 breakout veto: 0 strong-breakout trades got through** (nothing to veto — the choppy tape produced no ≥0.5 breakout signals). **IMP-022 VWAP gate: 0 stretched-above-VWAP entries skipped** — all 5 fills were **at/below their session VWAP**, so the gate correctly passed every one (nothing to skip). No regression, no false skip, no misfire; books reconcile to the penny. Gate-monitor (`gate_monitor.log` 20:30 UTC) agrees: 5 through, 0 vetoed, 0 skipped.
- **Consequence:** today's loss was NOT an above-VWAP open-fade (the leak IMP-019/020/022 target). It was the **residual at/below-VWAP MA-fader** — the "still-unfound discriminator" flagged in IMP-021's held-out note (07-22 ENPH/UNH). The VWAP gate can't catch these (they ARE at/below VWAP); neither new gate addresses them. This is the honest limit both gates were shipped with ("removes the losers, not yet a proven money-maker").

### Trade-by-trade review
| # | Sym | Signal | Entry (ET) | Exit (ET) | Conf | Mom | bo | Exit | P&L | % | Root cause |
|---|-----|--------|-----------|-----------|------|-----|----|------|-----|---|-----------|
| 192 | AAPL | MA | 09:43:00 @335.41 | 13:51:15 @335.38 | 61.57 | **0.96** | 0.00 | STOP (break-even) | **−$0.19** | −0.01% | Reached +0.5R → **IMP-013 ratcheted the stop 330.37→335.41 (break-even)**; faded back and hit it → −$0.19 scratch instead of a full ~−$35 1R. Highest momentum of the day yet only scratched — **momentum refuted again as a separator.** Filled at/below VWAP. |
| 193 | NFLX | MA | 09:46:17 @70.4781 | 15:10:32 @70.59 | 61.07 | 0.74 | 0.00 | STOP (trailed) | **+$4.03** | +0.16% | Reached +1R → **IMP-013 trailed the stop 69.46→70.48→70.58** (above entry); faded to the trailed stop → locked **+$4.03** (a STOP exit *in profit*). Textbook trail. |
| 194 | QCOM | MA | 10:03:32 @169.904 | 10:28:15 @167.26 | 60.52 | 0.70 | 0.00 | STOP (full-1R) | **−$39.66** | −1.56% | Pure-MA conf-60 at/below VWAP; **faded straight from entry, never reached +0.5R** (IMP-013 couldn't arm), full 1R stop in 24 min. **Day's biggest loss.** The residual at/below-VWAP MA-fader. |
| 195 | META | MA | 11:24:04 @606.83 | 12:16:27 @597.35 | 60.72 | 0.72 | 0.00 | STOP (full-1R) | **−$37.92** | −1.56% | Same pattern as QCOM — conf-60 MA at/below VWAP, faded from entry to the full 1R stop in 52 min, never armed IMP-013. Second half of the day's loss. |
| 196 | COST | MA | 13:12:32 @950.64 | 15:57:15 @951.25 | 60.97 | 0.73 | 0.00 | EOD_FLATTEN | **+$1.22** | +0.06% | Low-conf MA drift; held ~flat all afternoon, captured a tiny green at the flatten. The benign drift bucket. |

### What worked / what didn't
- **Worked — the two new gates passed their first live session cleanly.** 0 breakout entries (veto held), 0 above-VWAP entries (all 5 at/below VWAP → nothing to skip). No regression, no false skip, no misfire — exactly the pure-MA at/below-VWAP survivor set the gates are meant to keep. First live confirmation that IMP-021/022 don't break anything.
- **Worked — IMP-013 rescued 2 of 5.** AAPL ratcheted to break-even (330.37→335.41) and scratched at −$0.19 (a full ~−$35 1R avoided); NFLX trailed 69.46→70.58 and locked **+$4.03** — a trailed-STOP win. Broker order-replace chains confirmed, 0 rejects, no 422 loop. Without IMP-013 the day is materially worse.
- **Worked — every capital-protection invariant held.** 0 open positions (no naked overnight — ~28th straight clean session); books reconcile to Alpaca to the penny (IMP-003/005/010); no circuit breaker, no bug, no slippage defect.
- **Didn't — 2 at/below-VWAP MA-faders drove 100% of the loss.** QCOM (−$39.66) and META (−$37.92) were conf-60 pure-MA entries filled at/below their session VWAP that faded straight to the full 1R stop, never reaching +0.5R. **Neither new gate targets this population** (they ARE at/below VWAP; they are NOT breakouts). This is the residual leak both gates were shipped with an honest caveat about.
- **No new discriminator surfaced.** Momentum is refuted *again* — AAPL (mom 0.96, the day's highest) scratched while the two full-1R losers had mid momentum (0.70/0.72); confidence is flat across all 5 (60.5–61.6); all bo=0; all at/below VWAP. There is no recorded feature that separates today's 2 faders (QCOM/META) from the drift (COST) or the rescues (AAPL/NFLX).
- **Tape context (Perplexity `sonar`, corroborated):** S&P essentially **flat** (~7,413, <+0.1%), **Nasdaq −0.2%** — a **choppy, risk-off-to-neutral** tech-underperforming tape (chip/AI weakness) as the market positioned ahead of the Mag-7 gauntlet (MSFT/META Wed AMC, AAPL/AMZN Thu AMC) + FOMC Wed + Core PCE. Iran-pause/lower-oil supported breadth but tech lagged. **No name-specific catalyst** on any of the 5 traded → today's MA drift-fades were **regime** (heavy tech tape), the mirror of 07-24's firming-tape drift-up wins, not a name or signal defect.

### Lessons & improvement candidates (ranked)
1. **No code change warranted — analysis-only run (mirrors 07-21 / 07-24).** Today is the **first live session under two brand-new entry gates** (IMP-021/022, 2 days old), and the decision-relevant finding is confirmatory: **the gates fired correctly** (0 inappropriate entries; the 5 survivors were exactly the pure-MA at/below-VWAP set they intend to keep), IMP-013 rescued 2 trades, and the −$72 loss was 2 residual at/below-VWAP MA-faders on a choppy tech-off tape — regime, not a defect, with **no new discriminator** (momentum refuted again; every per-trade axis still refuted). Layering a **third entry change** on top of two 2-day-old gates after a single −$72 session — into an FOMC/PCE/Mag-7 binary week, at a −23.9% drawdown with only **$108 of cushion** above the −25% flag — would be reckless and textbook overfitting. **Disciplined outcome: reviewed, no change.** Full suite green (132 passed); service active & healthy.
2. **The residual at/below-VWAP MA-fader is now the top OPEN strategy question** — the leak neither new gate addresses. QCOM/META today join 07-22's ENPH/UNH and 07-20's QCOM/MU as conf-60 MA entries that fade to a full 1R stop despite filling at/below VWAP. No recorded feature (confidence, momentum, extension, time-of-day, index-regime, VWAP-distance) separates them from the at/below-VWAP winners — **all six per-trade discriminators refuted.** The honest read: on a choppy/heavy tape even the gate-approved MA survivors fade; on a firming tape they drift up (07-24). This is fundamentally a **tape/regime** problem, and every index-regime proxy is also refuted (IMP-015/018). Do NOT invent a new per-trade filter on it — that ground is exhausted. Best next step is to **accrue more post-IMP-021/022 sessions** and let the gate-monitor scorecard show whether the kept book trends ≥ break-even across a *range* of tapes, per both gates' shipping plan. Nothing to ship today.
3. **⚠️ Traceability flag (NOT acted on — pre-existing uncommitted rule):** `bot/analytics.py`, `bot/replay.py`, `scripts/replay.py`, `tests/test_replay.py` + `backtest_result.json`/`gate_monitor_result.json` remain **uncommitted** in the tree (the long-standing offline-tooling work flagged every review since 07-20). Left untouched/unstaged this run per the ground rules (never `git add` files I did not modify this run). Queued in `todo.md` for a human / code-capable run to finalize. No live-bot impact (offline tooling; suite passes with them present).

### Notes for pre-market research
- **QCOM** — day's biggest loss (−$39.66): conf-60 MA, filled at/below VWAP, faded straight to the full 1R stop in 24 min on the tech-off tape. Not a name defect (liquid, fits strategy); the residual at/below-VWAP MA-fade. QCOM **reports Wed 07-29 AMC** → gaps Thu (no overnight risk, but wide Thu range).
- **META** — −$37.92, same at/below-VWAP MA-fade pattern as QCOM. **Reports Wed 07-29 AMC** → gaps Thu; expect a wide post-earnings range (no overnight risk for an EOD-flatten bot).
- **AAPL** — IMP-013 break-even scratch (−$0.19) despite the day's highest momentum (0.96); a would-be −$35 loss avoided. **Reports Thu 07-30 AMC** → gaps Fri. Keep.
- **NFLX** — IMP-013 trailed-STOP **win** (+$4.03); the trail did its job on a fader. Keep.
- **COST** — benign flat drift (+$1.22); no read. Keep.
- **Tape choppy / tech-off** (S&P flat, Nasdaq −0.2%, chips/AI lagged) into a **Mag-7 + FOMC (Wed) + Core PCE** gauntlet. On a heavy/choppy tape even gate-approved at/below-VWAP MA survivors fade; on a firming tape (07-24) they drift up — **regime, not name.** Do NOT chase into the binaries this week.
- Equity **$7,608.45 (−23.92% YTD)** — cushion thinned to **$108 above the −25% ($7,500) flag** (from $181). Protect aggressively; the bounce is risk-on but unconfirmed into Fed/PCE/Mag-7.

---

## 2026-07-24 — Daily Review

### Stats
- Trades: **3 closed (3W / 0L)**, win rate **100%**. **Green day** breaking a four-red-in-five run; second clean 3W/0L sweep of the month (cf. 07-21 +$78.41), both on a firming/bounce tape.
- Net P&L: **+$87.13** (day **+1.147%**). Equity close **$7,681.00** (from $7,593.87 open). **Alpaca reconciles to the penny** (PA3ESJUO8RU0 equity $7,681.00 = DB close; last_equity $7,593.87 = prior close; **0 open positions — no naked overnight** (~26th straight clean session); all 3 buys (BAC 61.44878, COST 929.342, NFLX 69.31) + all 3 flatten sells at 15:55 ET (61.98 / 935.932 / 70.21) match DB fills exactly; account ACTIVE, not blocked).
- Avg winner **+$29.04**; no losers. Profit factor (day) = **∞** (zero gross loss).
- Exit reasons: **3 EOD_FLATTEN (all drifted-up / captured green)** — no STOP, no TP hit. IMP-013 armed on **BAC** (stop 60.50→61.45 break-even after +0.5R) and **NFLX** (stop trailed 68.19→69.31→69.38→69.52) — both protected, drifted up regardless; COST correctly did NOT arm (+0.71% at exit, just shy of +0.5R). Circuit breaker NOT tripped (+1.15% << −8.0% halt). Service active all session (07:00 UTC nightly restart, clean), **0 errors/exceptions** in journal.
- **Equity $7,681.00 = −23.19% YTD, now $181.00 above the −25% ($7,500) strategy-review flag** — recovered $87 off the 07-23 low; cushion improved from the thinnest-ever $93.96 but still thin. Protect.

### Trade-by-trade review
| # | Sym | Signal | Entry (ET) | Exit (ET) | Conf | Mom | VWAP dist | Exit | P&L | % | Root cause |
|---|-----|--------|-----------|-----------|------|-----|-----------|------|-----|---|-----------|
| 189 | BAC | MA | 09:36:56 @61.4488 | 15:56:28 @61.98 | 61.59 | 0.77 | **−0.23%** | EOD_FLATTEN | **+$21.78** | +0.86% | MA-only 60-62 band, healthy momentum; drifted up on the bounce, **IMP-013 armed break-even** (stop 60.50→61.45), captured green at flatten. Filled **below VWAP — the safe side** of the ★★ gate. *Lost −$5.33 on 07-23; won today — same name, opposite tape.* |
| 190 | COST | BOTH | 09:43:36 @929.342 (broke 926.815) | 15:56:29 @935.932 | 73.16 | 0.98 | **+0.34%** | EOD_FLATTEN | **+$32.95** | +0.71% | Breakout, strong momentum (0.98); drifted up all session, captured at flatten. Filled **+0.34% ABOVE VWAP — a winner the ★★ VWAP gate (skip >+0.25%) would have SKIPPED.** |
| 191 | NFLX | MA | 10:09:25 @69.31 | 15:56:30 @70.21 | 60.53 | 0.70 | **+0.63%** | EOD_FLATTEN | **+$32.40** | **+1.30%** | Low-conf MA-only near the 60 floor; **day's best % mover**. Filled **+0.63% above VWAP (≥+0.50% band) — the second winner the gate would have SKIPPED.** IMP-013 trailed the stop 68.19→69.52. *Lost −$15.48 on 07-23; won today.* |

### What worked / what didn't
- **Worked — the drifted-up EOD_FLATTEN bucket did exactly its job on a stabilization bounce.** All 3 entries (2 MA-only 60-62 + 1 BOTH conf-73) drifted up on a firming tape and were captured green at the 15:56 flatten — the **mirror image of the 07-23 faded-flatten losses** (same signal classes, same exit mechanism, opposite tape). Notably **BAC and NFLX both LOST on 07-23 and WON today** — the cleanest possible confirmation that the leak is *regime* (heavy vs firming tape), not name quality.
- **Worked — IMP-013 armed correctly.** BAC ratcheted to break-even (60.50→61.45) and NFLX trailed up (68.19→69.52) after each reached its trigger; broker order-replace confirmed, neither stop hit (both drifted up). COST correctly did NOT arm (never reached +0.5R). Zero rejected stop-replaces, no 422 loop.
- **Worked — every capital-protection invariant held.** 0 open positions (no naked overnight); books reconcile to Alpaca to the penny (IMP-003/005); no circuit breaker, no bug, no slippage defect.
- **★ Decisive analytic finding — today is a clean OUT-OF-SAMPLE COUNTEREXAMPLE to the ★★ VWAP gate.** 2 of 3 winners were fills **>+0.25% above session VWAP** (COST +0.34%, NFLX +0.63%) that the gate would have **skipped, removing +$65.35 of genuine profit** (turning +$87.13 into +$21.78). The held-out check (`scripts/replay.py`, split at 07-23) now shows the gate's **out-of-sample delta collapsed to just +$4.50** over the 07-23+07-24 window — 07-23's saved faders (−$69.85) are **nearly cancelled by today's above-VWAP winners (+$65.35)**. **The gate is TAPE-DEPENDENT** — it saves heavy-tape faders but saws off green bounce-day winners — the *same* tape-dependence that refuted the skip-bearish index-regime gate (IMP-011/012/015/018). This materially **tempers the 07-23 "strongest evidence yet" framing**: the gate is a partial, regime-conditional mitigant, NOT an unconditional cure.
- **Tape context:** Perplexity `sonar` returned **stale/conflicting data** (it quoted 07-23's close, S&P 7,408.30 / −1.21%, not today's) → treated as unreliable and discarded; the morning research had Fri futures +0.11% (stabilization bounce after Thu's AI-capex rout). The bot's own green book + 3 drifted-up captures confirm the intraday tape firmed enough for MA/BOTH drift-ups to work. No name-specific catalyst on BAC/COST/NFLX — a broad firming/bounce, not news.

### Lessons & improvement candidates (ranked)
1. **No code change warranted — analysis-only run (mirrors 07-21).** Clean 3W/0L green day, zero defect, zero loss to root-cause, books reconcile to the penny, no risk event. Today's single decisive finding — the ★★ VWAP gate is **tape-dependent and would have COST +$65.35 today** — argues for *more* caution on the pending gate, not for shipping anything. Every per-trade discriminator (confidence IMP-004, volume, extension IMP-007, time-of-day IMP-016) and index-regime proxy (IMP-015/018) stays refuted. Inventing a change on a defect-free green day would overfit. **Disciplined outcome: reviewed, no change.**
2. **★★ VWAP gate — today weakens the unconditional-gate case.** Out-of-sample delta is now only **+$4.50** over the 07-23+07-24 held-out window (vs the +$599 in-sample framing). It reinforces IMP-021's held-out caveat: the gate is a **partial, tape-conditional mitigant**, not a cure. If it ever ships (human sign-off), it should likely be **conditioned on tape/regime**, not applied unconditionally — otherwise it removes green bounce-day profit. Escalate this nuance in `todo.md` alongside the existing gate proposal. Still an entry-logic change AWAITING HUMAN SIGN-OFF — not shippable here.
3. **⚠️ Traceability flag (NOT acted on — pre-existing uncommitted rule):** `bot/analytics.py`, `bot/replay.py`, `scripts/replay.py`, `tests/test_replay.py` still sit **uncommitted** in the tree — the IMP-021 (held-out check) + IMP-022 (breakout-momentum analytics) work prior reviews declared "SHIPPED" but never committed (last committed IMP = IMP-020 / 23c9692). Left untouched/unstaged this run per the ground rules (never `git add` files I did not modify this run). Any new tooling change would also land in these files and entangle with the uncommitted work — a further reason today is analysis-only. **Queued in `todo.md` for the next code-capable run / human to finalize the IMP-021/022 commits + log entries.**

### Notes for pre-market research
- **BAC** — won today (+$21.78, MA drift-up, filled below VWAP) after losing 07-23 (−$5.33); regime not name. Keep, top-of-list on a firming tape.
- **COST** — clean BOTH breakout drift-up (+$32.95, strong mom 0.98); filled above VWAP but won on the bounce. Keep.
- **NFLX** — **day's best % (+1.30%)**, low-conf MA-only; won today after losing 07-23 (−$15.48). Same name, opposite tape — the regime read, not a name defect. Keep.
- **Tape firmed to a stabilization bounce** after Thu's AI-capex rout — if the bid holds, MA/BOTH drift-ups on liquid names keep working. **But this is a bounce, not a confirmed trend:** fresh Trump Section 301 tariffs, 10Y >4.7% (hawkish), and AI-capex ROI scrutiny still overhang. Don't chase stretched above-VWAP breakouts into any re-heavying of the tape.
- **Mon 07-27: Mag-7 earnings ramp** (MSFT/META/AAPL/AMZN over the coming sessions) — re-scan the intraday-earnings calendar each morning and park any on-list name that shifts to reporting *during* market hours (AMC/BMO gaps carry no overnight risk for an EOD-flatten bot).
- Equity **$7,681.00 (−23.19% YTD)** — recovered $87 off the low; now **$181.00 above the −25% ($7,500) strategy-review flag** (was $93.96). Cushion improved but still thin; protect.

---

## 2026-07-23 — Daily Review

### Stats
- Trades: **5 closed (0W / 5L)**, win rate **0%**. Fourth red day in the last five sessions (07-22 −$165, 07-20 −$88, 07-17 −$211), only 07-21 green (+$78).
- Net P&L: **−$70.18** (day **−0.916%**). Equity close **$7,593.96** (from $7,664.14 open). **Alpaca reconciles to the penny** (PA3ESJUO8RU0 equity $7,593.96 = DB close; **0 open positions — no naked overnight** (~25th straight clean session); all 5 entries + all 5 exits match DB fills exactly; account ACTIVE, not blocked).
- Avg loser **−$14.04**; no winners. Profit factor (day) = **0.00**.
- Exit reasons: **2 STOP** (MU #184 trailed-to-breakeven −$0.33 via IMP-013; MU #186 full-1R −$18.80), **3 EOD_FLATTEN** (XOM −30.24, NFLX −15.48, BAC −5.33 — all faded, wide stops never hit). Circuit breaker NOT tripped (−0.92% << −8.0% halt). Service active all session (up 5 days, no restart), **0 errors/exceptions**.
- ⚠️ **Equity $7,593.96 = −24.06% YTD, only $93.96 above the −25% ($7,500) strategy-review flag** — the thinnest cushion yet (was $164 on 07-22). One more ~$100 day trips the review threshold. Protect capital aggressively.

### Trade-by-trade review
| # | Sym | Signal | Entry (ET) | Exit (ET) | Conf | Mom | VWAP dist | Exit | P&L | % | Root cause |
|---|-----|--------|-----------|-----------|------|-----|-----------|------|-----|---|-----------|
| 184 | MU | MA | 09:51:25 @986.85 | 10:54:56 @986.52 | 61.99 | 0.80 | **+0.10%** | STOP (trailed) | **−$0.33** | −0.03% | Reached +1R; **IMP-013 ratcheted the stop 969.42→986.85 (breakeven)** — faded back, hit the breakeven stop → −$0.33 scratch instead of a full loss. Trail working as designed (broker order replace verified). |
| 185 | XOM | **BOTH** | 11:19:13 @158.43 (broke 158.155) | 15:56:32 @156.54 | 68.08 | 0.70 | **+0.60%** | EOD_FLATTEN | **−$30.24** | −1.19% | Breakout **chased +0.60% above session VWAP**; faded straight from entry, wide stop (155.97) never hit, bled to the flatten. **Day's biggest loss.** Note: XOM the *stock* closed +1.8% (oil/Mideast) — but the bot's intraday breakout-spike entry mean-reverted. Open/breakout-fade leak. |
| 186 | MU | MA | 12:36:56 @1008.12 | 14:09:32 @989.32 | 60.55 | 0.91 | **+1.83%** | STOP (full-1R) | **−$18.80** | −1.86% | **Re-entry** of MU after #184 scratched; filled **+1.83% above VWAP** (most-stretched fill of the day), faded to the full 1R stop. The above-VWAP open-fade-to-full-stop leak. |
| 187 | NFLX | MA | 14:09:10 @69.29 | 15:56:33 @68.86 | 60.86 | 0.76 | **+0.92%** | EOD_FLATTEN | **−$15.48** | −0.62% | Low-conf MA-only, filled +0.92% above VWAP; faded into the flatten. Residual faded-flatten drag. |
| 188 | BAC | MA | 15:27:14 @61.42 | 15:56:45 @61.29 | 63.50 | 0.90 | **+0.59%** | EOD_FLATTEN | **−$5.33** | −0.21% | **Late entry — 15:27, only 3 min before the 15:30 cutoff**; 29-min hold, no room to work, small flatten loss. |

### What worked / what didn't
- **Worked — IMP-013 on MU #184.** Stop ratcheted from the 969.42 anchor up to 986.85 (breakeven) after +1R, converting a potential ~−$17 loss into a −$0.33 scratch (broker order-replace confirmed: 969.42→986.85, filled 986.52). Textbook trail.
- **Worked — every capital-protection invariant held.** 0 open positions (no naked overnight — ~25th straight clean session under IMP-002); books reconcile to Alpaca to the penny (IMP-003/005); no circuit breaker, no bug, no slippage defect. All five losses were controlled to their planned 1R or better.
- **Didn't — the open-fade leak, this time mostly MA-only.** 4 of 5 losers faded straight from entry (3 into EOD_FLATTEN with wide stops un-hit, 1 to the full stop). Only XOM was a BOTH breakout; four were MA-only. **Decisive VWAP read: 4 of the 5 fills were >+0.25% above their session VWAP** (XOM +0.60, MU#186 +1.83, NFLX +0.92, BAC +0.59) — only the −$0.33 MU scratch was at/below the +0.25% edge (+0.10%). **The pending ★★ VWAP entry-quality gate (skip >+0.25% above VWAP) would have skipped all four faders and avoided −$69.85 of the −$70.18 day.** Strongest single-day evidence for the gate yet.
- **Tape context (Perplexity, corroborated):** S&P −0.1% (7,498.96), Nasdaq −0.6% (25,690.90), **choppy / mildly risk-off** — negative breadth (Nasdaq decliners 1.86:1), defensive bid into utilities, growth/communication-services lagging, caution into the mega-cap prints. **GOOGL −~5% AH** (raised 2026 capex, first negative FCF quarter since IPO), **TSLA −~3% AH** (margin/profit miss). **No name-specific catalyst on MU/NFLX/BAC**; XOM's +1.8% was sector-driven (oil/Mideast) but the bot's intraday breakout entry still faded. → today's failures were regime (heavy, two-sided tape) + the strategy's own above-VWAP open-fade leak, not news.

### Lessons & improvement candidates (ranked)
1. **No code change warranted — analysis-only run.** Today's one data-justified lever is the **★★ VWAP entry-quality gate (IMP-019/020)**, and today is its **strongest single-day evidence yet** (4/5 fills >+0.25% above VWAP; the gate would have turned −$70.18 into −$0.33). But it is an **entry-logic change AWAITING HUMAN SIGN-OFF** (ground-rule: entry gates need explicit human approval) — I cannot ship it. Every other per-trade discriminator stays refuted (confidence IMP-004, volume, extension IMP-007, time-of-day IMP-016) and every index-regime proxy is refuted (IMP-015/018). Inventing a *new* untested gate on a −$70 chop day — with the account $93.96 above its strategy-review floor and pre-existing uncommitted code in the tree — would be reckless/overfit. Re-escalated the gate in `todo.md` with today's decisive numbers. **Disciplined outcome: reviewed, no change.**
2. **Held-out caveat still stands (the gate is a strong-but-PARTIAL mitigant).** On the 07-22+07-23 held-out window the skip side removes net-losers, but the **kept book stays net-negative (−$41.69)** — 07-22's losers (ENPH/UNH) were filled *at/below* VWAP and slip under the gate. So the gate would have hugely helped *today* but is not a complete fix; the residual at/below-VWAP faders (07-22) need a different, still-unfound discriminator.
3. **⚠️ Traceability flag (NOT acted on — pre-existing uncommitted rule):** `bot/analytics.py`, `bot/replay.py`, `scripts/replay.py`, `tests/test_replay.py` sit **uncommitted** in the working tree — the IMP-021 (held-out check) + IMP-022 (breakout-momentum analytics) work the 07-20/07-22 reviews declared "SHIPPED" but never committed (last committed IMP = IMP-020 / 23c9692; IMP-021/022 absent from `improvement-log.md`). Left untouched/unstaged this run per the ground rules. **Queued in `todo.md` for the next code-capable run / human to finalize the IMP-021/022 commits + log entries.** Tests pass with them present; offline tooling only, no live-bot impact.

### Notes for pre-market research
- **XOM** — day's biggest loss (−$30.24): the *stock* rose +1.8% (oil/Mideast) but the bot **chased the breakout +0.60% above VWAP** and it mean-reverted. Energy strength is real; the breakout-chase into it is the problem. Not a name defect — watch, don't over-weight the breakout.
- **MU** — traded **twice** (both small losses); #186 re-entered at 12:36 filled +1.83% above VWAP → full stop. ~$1,000/sh so qty=1 (tiny $ position). Re-entries into a fading tape keep losing.
- **NFLX** — MA-only, faded to flatten (−$15.48); +0.92% above VWAP. Regime, not name.
- **BAC** — **entered 15:27, only 3 min before the 15:30 cutoff** → 29-min hold, no room, −$5.33 flatten. Late-day entries near the cutoff rarely work; flag for the entry-timing backlog item.
- **Tape choppy/risk-off into mega-cap earnings:** GOOGL −~5% AH (capex/FCF), TSLA −~3% AH (margins) → **both gap Fri 07-24; expect wide post-earnings ranges** (no overnight risk for an EOD-flatten bot). Favor **at/below-VWAP MA drift-ups on green pockets**; avoid chasing breakouts stretched above VWAP into a heavy tape.
- Equity **$7,593.96 (−24.06% YTD)** — **only $93.96 above the −25% ($7,500) strategy-review flag.** Thinnest cushion yet; protect aggressively.

---

## 2026-07-22 — Daily Review

### Stats
- Trades: **5 closed (2W / 3L)**, win rate **40%**. Gives back the 07-21 green day (and more) on a risk-off tape.
- Net P&L: **−$165.52** (day **−2.114%**). Equity close **$7,664.14** (from $7,829.68 open). **Alpaca reconciles to the penny** (PA3ESJUO8RU0 equity $7,664.14 = DB close; last_equity $7,829.66 ≈ prior close; **0 open positions — no naked overnight**; account ACTIVE, not blocked).
- Avg winner **+$19.66** (AMD +20.79, BAC +18.52); avg loser **−$68.28** (ENPH −124.80, UNH −59.88, QCOM −20.15). Profit factor (day) = 39.31 / 204.83 = **0.19**.
- Exit reasons: **1 STOP full-1R (ENPH), 1 STOP trailed (AMD, +profit via IMP-013), 3 EOD_FLATTEN (BAC drifted-up / UNH+QCOM faded)**. Circuit breaker NOT tripped (−2.11% << −8.0% halt). Service active all session, **0 errors/exceptions** in journal.
- ⚠️ **Equity $7,664.14 = −23.4% YTD, only $164.14 above the −25% ($7,500) strategy-review flag** — thinnest cushion yet. Protect capital aggressively.

### Trade-by-trade review
| # | Sym | Signal | Entry (ET) | Exit (ET) | Conf | Mom | Exit | P&L | % | Root cause |
|---|-----|--------|-----------|-----------|------|-----|------|-----|---|-----------|
| 179 | AMD | BOTH | 09:36:24 @542.99 (broke 542.89) | 10:06:08 @545.30 | 76.98 | 0.36 | STOP (trailed) | **+$20.79** | +0.43% | Breakout, modest momentum; reached +1R so **IMP-013 trailed the stop above entry** → locked +$20.79 (a "STOP" exit *in profit*). The trail working as designed. |
| 180 | BAC | MA | 09:46:20 @61.37 | 15:56:54 @61.81 | 62.52 | 0.83 | EOD_FLATTEN | **+$18.52** | +0.72% | MA-only, healthy momentum (0.83); drifted up on the one green pocket, captured at flatten. The good drifted-up bucket. |
| 181 | UNH | BOTH | 09:47:38 @434.99 (broke 433.75) | 15:57:15 @430.00 | 73.00 | **0.00** | EOD_FLATTEN | **−$59.88** | −1.15% | Breakout (bo=1.0) with **momentum_score = 0.00 — dead momentum**; faded down all day into the flatten, wide stop never hit. **Second instance of the weak-momentum-breakout-fades-to-flatten pattern** (07-20 INTC mom 0.17 → −$22.12). |
| 182 | ENPH | BOTH | 10:07:24 @40.79 (broke 40.75) | 10:15:52 @40.14 | 83.11 | 0.92 | STOP (full-1R) | **−$124.80** | −1.59% | High-conf BOTH, **strong** momentum (0.92) — but a genuine **false breakout**: reversed immediately, hit its full 1R stop in 8 min. **Day's biggest loss (75% of gross loss).** The above-VWAP open-fade-to-full-1R-stop leak — momentum did NOT protect it. |
| 183 | QCOM | MA | 10:21:04 @177.15 | 15:57:29 @175.60 | 60.19 | 0.68 | EOD_FLATTEN | **−$20.15** | −0.88% | Low-conf MA-only near the 60 floor; faded to a small flatten loss. The residual faded-flatten drag. |

### What worked / what didn't
- **Worked — IMP-013 on AMD.** AMD reached +1R and the broker-side trail ratcheted the stop above entry, converting what could have faded into a **+$20.79 locked gain** (exit_reason STOP but P&L positive). Textbook trail capture. BAC's MA-only drift-up (+$18.52, mom 0.83) also did its job.
- **Worked — every capital-protection invariant held.** 0 open positions (no naked overnight — 20+ straight clean sessions under IMP-002); books reconcile to the penny (IMP-003/005); no circuit breaker, no bug, no slippage defect. Losses were controlled to their planned 1R.
- **Didn't — two breakout (BOTH) failures drove 91% of the gross loss.** ENPH (−$124.80, false breakout to full-1R stop *despite* strong momentum 0.92) and UNH (−$59.88, breakout with momentum 0.00 that faded to the flatten). The MA-only book was net-flat (BAC +18.52 / QCOM −20.15). **The leak today was the BOTH/breakout class, not MA-only.**
- **Tape context (Perplexity, corroborated):** S&P −0.1%, Nasdaq −0.6%, **choppy-to-risk-off** — rising oil (WTI >$85, Iran day 12) + higher yields + AI/tech weakness, into the first Mag-7 prints (GOOGL/TSLA AMC). **No name-specific catalyst** on any of the 5 traded → today's breakout failures were regime (heavy tape) + the strategy's own open-fade leak, not news. This is the mirror of 07-21's drifted-up green day: same signal classes, opposite tape.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-022 — measurement/tooling only]** Today surfaced a **new, discrete, non-confidence discriminator that is NOT in the refuted list**: **breakout (BOTH) signals with near-zero momentum_score.** UNH today (mom 0.00 → −$59.88) is the second clear instance after 07-20 INTC (mom 0.17 → −$22.12). Full-book analysis: **BOTH signals with momentum_score < 0.1 are 0W/4L, −$194.19 (exp −$48.55/trade, PF 0.00) — the single worst discrete bucket in the entire book.** But (a) n=4 is thin, and (b) today's *biggest* loss, ENPH (−$124.80), had momentum 0.92 — so a momentum floor would NOT have caught the day's main damage. At a −23.4% drawdown with $164 of cushion, shipping a **live entry-logic change on n=4 would be reckless/overfit** and contradicts this project's governance (the ★★ VWAP gate is *still* awaiting human sign-off). Disciplined move, per the IMP-004/007/016/020 measurement-first pattern: **institutionalize the momentum discriminator as a standing report/analytics breakdown** (`by_breakout_momentum`) so the finding can't be silently lost and accrues more samples, and **queue the momentum-floor entry gate in `todo.md` for human sign-off.** No risk limit, no entry logic touched.
2. **★★ The real, strategy-wide fix remains the VWAP entry-quality gate (IMP-020), blocked on human sign-off.** ENPH (−$124.80) is exactly its target: an open-window breakout that fails fast to a full-1R stop. Re-escalated in `todo.md`. Watchlist churn cannot fix it.
3. **Do NOT act on MA-only via confidence** (refuted IMP-004) — today MA-only was net-flat (BAC +18.52 / QCOM −20.15). The leak was BOTH/breakout, not MA-only.

### Notes for pre-market research
- **ENPH** — high-conf BOTH (83) that was a fast false breakout (−1.59%, full-1R stop in 8 min) on the risk-off tape. Not a name defect (liquid, fits strategy); the open-fade leak. Watch, don't over-weight breakouts into a heavy tape.
- **UNH** — BOTH breakout with **zero momentum** that bled to the flatten (−$59.88); 0W-in-series continues. Flag: weak-momentum breakouts keep fading (see also 07-20 INTC).
- **AMD** — behaved best (IMP-013 trail locked +$20.79); modest-momentum breakout that worked. Keep.
- **BAC** — clean MA-only drift-up (+$18.52, mom 0.83). Keep.
- **QCOM** — low-conf MA-only near the floor, small fade (−$20.15). Chronic 0W-ish; regime, not name.
- **Tape flipped back risk-off** (S&P −0.1%, Nasdaq −0.6%, oil >$85, AI/tech weak) into the Mag-7 prints. **GOOGL + TSLA reported AMC today → both gap Thu 07-23; INTC reports Thu.** Expect wide post-earnings ranges (no overnight risk for an EOD-flatten bot). Favor MA-only drift-ups on green pockets over chasing breakouts into a heavy tape.
- Equity **$7,664.14 (−23.4% YTD)** — **only $164 above the −25% ($7,500) strategy-review flag.** Cushion is the thinnest yet; protect aggressively.

---

## 2026-07-21 — Daily Review

### Stats
- Trades: **3 closed (3W / 0L)**, win rate **100%**. **First green session after three straight red days** (07-15 −$252, 07-17 −$211, 07-20 −$88).
- Net P&L: **+$78.41** (day **+1.012%**). Equity close **$7,829.68** (from $7,751.29 open). **Alpaca reconciles to the penny** (PA3ESJUO8RU0 equity $7,829.68 = DB close; last_equity $7,751.27 ≈ DB open; **0 open positions — no naked overnight**; all 6 fills — 3 buys + 3 flatten sells at 15:55:58 ET — match DB entries/exits exactly).
- Avg winner **+$26.14**; no losers. Profit factor (day) = **∞** (zero gross loss).
- Exit reasons: **3 EOD_FLATTEN (all drifted-up / captured green)** — no STOP, no TP hit (INTC missed its TP by $0.85). Circuit breaker NOT tripped (+1.01% << −8.0% halt). Service active all session, **0 errors/exceptions** in journal.

### Trade-by-trade review
| # | Sym | Signal | Entry (ET) | Exit (ET) | Conf | Mom | Exit | P&L | % | Root cause |
|---|-----|--------|-----------|-----------|------|-----|------|-----|---|-----------|
| 176 | AVGO | MA | 09:42:29 @384.58 | 15:57 @386.81 | 61.53 | 0.87 | EOD_FLATTEN | **+$13.38** | +0.58% | MA-only conf-61, healthy momentum; drifted up on the recovering chip tape, captured at flatten (never reached TP 393.18). Textbook drifted-up flatten. |
| 177 | QQQ | MA | 10:03:04 @704.12 | 15:57 @709.45 | 60.19 | 0.68 | EOD_FLATTEN | **+$16.00** | +0.76% | Low-conf MA-only index ETF; rode the broad up-day, drifted up and flattened green. |
| 178 | INTC | MA | 10:04:23 @101.94 | 15:57 @105.71 | 60.40 | 0.69 | EOD_FLATTEN | **+$49.03** | **+3.70%** | Day's engine — INTC ran +3.7% on the chip recovery; MA-only conf-60 held all day, captured at flatten just $0.85 shy of TP (106.56). |

### What worked / what didn't
- **Worked — the drifted-up EOD_FLATTEN bucket did exactly its job.** All 3 entries were MA-only conf 60-62 that drifted up on a bullish/recovering tape and were captured green at the 15:57 flatten. This is the **mirror image of the 07-15/-17/-20 red-tape faded-flatten losses**: same signal class, same exit mechanism, opposite tape → all-time drifted-up bucket (+$977 / exp +$23.83 / 95% win) grows, faded bucket untouched. Reinforces IMP-004's finding that **MA-only conf 60-62 is the least-bad band** (all-time PF 0.92) — today it was 100% of the trades and 100% of a green day.
- **Worked — every capital-protection invariant held.** IMP-002 flatten fired cleanly (0 open positions, no naked overnight — the 20th+ straight clean session); IMP-003/IMP-005 fill accuracy held (all 6 fills tie to the broker to the penny); no circuit breaker, no bug, no slippage defect.
- **Didn't (minor, by design) — capture efficiency.** INTC ran to +3.70% intraday but was carried to flatten $0.85 under its TP rather than locking the gain; AVGO/QQQ drifted modestly. Not a defect — the EOD_FLATTEN drifted-up bucket is the design outcome on a trending-up day, and it was net-positive. No loser to root-cause today.
- **Tape context:** S&P ~+0.9% / Nasdaq ~+1.0-1.4% (Perplexity, corroborated) — a recovering chip/AI up-day after three risk-off sessions. **No high-conf BOTH breakout fired today** — the open-fade leak names (high-conf BOTH that fade to a full-1R stop) simply didn't appear on the calmer up-tape, so today adds no new evidence on the ★★ VWAP gate either way.

### Lessons & improvement candidates (ranked)
1. **No code change warranted — analysis-only run.** Clean 3W/0L green day, zero defect, zero loss to root-cause, books reconcile to the penny, no risk event. Today's data justifies no new lever; forcing a change on a defect-free green day would risk overfitting. The candidate landscape is unchanged: the ★★ VWAP entry-quality gate remains a *partial mitigant only* (IMP-021's held-out finding — kept book stays net-negative out of sample), and every per-trade discriminator (confidence IMP-004, volume, extension IMP-007, time-of-day IMP-016) stays refuted. Today's positive contribution is **confirming evidence**: MA-only 60-62 on a bullish tape is genuinely profitable — do NOT filter that band.
2. **⚠️ Process/traceability flag (NOT acted on — pre-existing uncommitted changes rule):** the 07-20 review declared **"[SHIPPED IMP-021 today]"** but IMP-021 was **never committed** — `bot/replay.py`, `scripts/replay.py`, `tests/test_replay.py` sit uncommitted in the working tree and **IMP-021 is absent from `memory/improvement-log.md`** (last committed IMP is IMP-020, 23c9692). Per the ground rules I left those three files untouched/unstaged this run. Tests pass (116) with them present and they are offline replay tooling (no live-bot impact), so this is a bookkeeping/traceability gap, not a health risk. **Queued in todo.md for the next code-capable run / human to finalize the IMP-021 commit + log entry.**

### Notes for pre-market research
- **INTC** — best name today (+3.70%, MA-only, nearly tagged TP) on the chip recovery; strong momentum, keep top-of-list.
- **AVGO** — MA-only drift-up, modest (+0.58%), healthy momentum (0.87); benign, keep.
- **QQQ** — index ETF drift-up (+0.76%); rode the broad tape, no name-specific read.
- **Tape flipped green** (S&P ~+0.9%, Nasdaq ~+1%) — recovering chip/AI tape after 3 risk-off sessions. If the bid holds, MA-only drift-ups on liquid names should keep working; watch for the return of high-conf BOTH breakouts (none fired today — the open-fade leak was simply absent).
- Equity **$7,829.68 (−21.7% YTD)** — recovered $78 off the 07-20 low; the −25% ($7,500) strategy-review flag is $330 below.

---

## 2026-07-20 — Daily Review

### Stats
- Trades: **4 closed (0W / 4L)**, win rate 0%.
- Net P&L: **−$87.86** (day −1.121%). Equity close **$7,751.29** (from $7,839.17). Alpaca reconciles to the penny (PA3ESJUO8RU0 equity $7,751.29 = DB close; all 4 fills match DB; **0 overnight positions**, all flat by the close).
- Avg loser −$21.97; no winners. Profit factor (day) = 0.00.
- Circuit breaker NOT tripped (−1.12% << −8.0% halt). Service active all session, no errors/exceptions in journal. Exit reasons: 3 STOP (QCOM, MU, AVGO), 1 EOD_FLATTEN (INTC).
- Third red session in a row (07-15 −$252, 07-17 −$211, 07-20 −$88) — a risk-off chip/AI tape; but note the loss size is shrinking and today had no bug, no risk breach, no slippage defect.

### Trade-by-trade review
| # | Sym | Signal | Entry (ET) | Exit (ET) | Conf | Exit | P&L | VWAP dist | Root cause |
|---|-----|--------|-----------|-----------|------|------|-----|-----------|-----------|
| 172 | QCOM | MA | 09:36 @173.00 | 15:25 @170.12 | 64.0 | STOP | −$40.32 | **−0.16%** | MA-only, momentum 0.94; held ~6h then faded to a late-afternoon stop. Filled BELOW VWAP — not an above-VWAP stretch. |
| 173 | MU | MA | 09:48 @891.52 | 10:21 @866.34 | 61.6 | STOP | −$25.18 | **+0.04%** | MA-only near the 60–62 floor; stopped in 33 min. Filled essentially AT VWAP. |
| 174 | INTC | BOTH | 10:24 @98.54 | 15:57 @96.96 | 63.3 | EOD_FLATTEN | −$22.12 | **−0.63%** | Breakout (broke 98.04) but **momentum only 0.17** — weak; drifted down all day, flattened at close (open-fade into flatten). Filled WELL BELOW VWAP. |
| 175 | AVGO | MA | 10:30 @380.24 | 14:33 @380.20 | 63.4 | STOP | −$0.24 | +0.27% | Reached +0.5R so **IMP-013 armed the break-even stop** → exited a scratch (−$0.24) instead of a full 1R loss. The one fill above the +0.25% gate line; also the only one the protection worked on. |

### What worked / what didn't
- **Worked:** IMP-013's break-even rescue on AVGO — reached +0.5R, stop trailed to entry, cut a would-be full-1R loss to −$0.24. Risk controls all held (no halt, no overnight, books reconcile to the penny). Losses are shrinking session-over-session.
- **Didn't:** Every entry lost. But the notable finding is **where** they lost: **3 of the 4 fills (QCOM −0.16%, MU +0.04%, INTC −0.63%) were AT or BELOW their session VWAP** — the *safe* side of the pending ★★ VWAP entry-quality gate. That gate (skip fills >+0.25% above VWAP) would have skipped **only AVGO** (a −$0.24 scratch) and **kept all three real losers (−$87.62)**. So today is a clean out-of-sample counter-example: the leak was NOT an above-VWAP stretch today.
- Signal-quality thread: 3 of 4 were MA-only entries in the low-conf 61–64 band (all-time that band is the weakest, PF ~0.5–0.7); the one breakout (INTC) had very weak momentum (0.17) and faded to the flatten. Consistent with the residual open-fade leak, just from the below-VWAP side today.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-021 today]** Build **step (2) of the ★★ VWAP-gate pre-ship checklist — held-out (out-of-sample) validation.** Today is the first genuinely out-of-sample session after IMP-020's in-sample window, and it materially changes the gate's story: on the held-out window (07-17 + 07-20, 9 trades) the skip side still removes net-losers (delta +$211.72, kept 3 / skipped 6) **but the kept book stays net-negative (−$87.62)** — the "kept book flips positive" claim from IMP-020 does **not** carry out of sample because today's losers were filled at/below VWAP. Pure measurement/tooling; directly informs the human sign-off decision (the gate is a partial mitigant, not a cure).
2. **MA-only entries in the 60–64 confidence band** (QCOM, MU, AVGO today; NFLX/C historically) keep bleeding — candidate: raise the MA-only confidence floor or require a volume/momentum confirm. Still needs more days of evidence and is an entry-logic change (human sign-off). Left in `todo.md`, not acted on today.
3. **Weak-momentum breakouts** (INTC momentum 0.17) that fade to the flatten — candidate discriminator once the VWAP question is resolved; do not stack two entry changes at once.

### Notes for pre-market research
- **QCOM** — MA-only conf-64 long faded all day to a late stop (below VWAP); chippy, no clean trend. Watch, don't chase MA-only.
- **MU** — priced ~891 in our data (check for a split/data quirk vs the ~$100 street price); stopped in 33 min. Low-conf (61.6) MA entry near the floor — low quality.
- **INTC** — breakout broke 98.04 but momentum was near-zero (0.17) and it drifted down into the flatten. A breakout without momentum = no-go; flag for a momentum-confirm filter.
- **AVGO** — behaved best (scratch via break-even); MA-only, no follow-through though.
- Tape context: three straight risk-off chip/AI sessions. If SPY/QQQ stay heavy pre-open, expect more MA-only fades — favour high-conf BOTH names with real momentum over low-conf MA-only breakouts.

---

## 2026-06-15 — Daily Review

### Stats
- Trades: 5 closed (2W / 3L), win rate 40%.
- Net P&L: **−$35.61** (day −0.434%). Equity close **$7,965.95** (from $8,205.71 / −18% YTD).
- Avg winner +$48.96 (TSLA +90.87, NFLX +7.04); avg loser −$44.51 (ENPH −30.23, ENPH −87.36, C −15.93).
- Profit factor (day): 97.91 / 133.52 = **0.73**.
- Circuit breaker NOT tripped (−0.43% << −8.0% halt). Service active all session, no errors. No overnight positions (all flat by 15:55 EOD_FLATTEN).
- Exit reasons: 2 STOP (both ENPH), 3 EOD_FLATTEN (TSLA, NFLX, C).

### Trade-by-trade review
| # | Sym | Entry (ET) | Exit (ET) | Conf | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|------|-----|-----------|
| 64 | TSLA | 09:30:17 @406.54 | 15:55 @410.04 | 97 | EOD_FLATTEN | **+$90.87** | Clean breakout, conf 97, held all day, only real winner. Carried to flatten (never hit +TP 415.69). |
| 65 | ENPH | 09:31:22 @55.59 | 09:39:55 | 74 | STOP | −$30.23 | False breakout, stopped in 8 min. |
| 66 | ENPH | **09:32:36** @55.59 | 09:39:21 | 74 | STOP | **−$87.36** | **DUPLICATE ENTRY** — second ENPH 74s after #65, same price/stop/qty, both open at once. Bug, not strategy. |
| 67 | NFLX | 09:41:15 @81.28 | 15:55 @81.50 | 61 | EOD_FLATTEN | +$7.04 | Weak MA-only signal (conf 61), drifted ~flat all day, no follow-through. |
| 68 | C | 09:45:29 @141.83 | 15:55 @140.95 | 61 | EOD_FLATTEN | −$15.93 | Weak MA-only signal (conf 61), faded; C now 0W in its series. |

### What worked / what didn't
- **Worked:** TSLA (conf 97, BOTH signal) again the only consistent earner — matches the 15-day record (TSLA 3W0L / +$257). High-confidence BOTH signals are the edge. Risk controls held: no halt, no overnight, stops fired correctly.
- **Didn't:** The day's *entire* loss is one bug. ENPH was entered **twice 74 seconds apart** (09:31:22 and 09:32:36) at the same 55.59/stop 54.44 — two concurrent positions in one name (−$117.59 combined). The de-dup guard reads `held` from `broker.open_position_symbols()`, which lists only *filled* Alpaca positions; the first bracket hadn't filled when the next 60s tick ran, so ENPH wasn't seen as held. Without the duplicate the day is roughly breakeven-to-positive (winners +$97.91 vs single ENPH −$30 + C −$15.93).
- Low-confidence MA-only entries (NFLX 61, C 61) added no value — both drifted to a flat/negative EOD flatten. Consistent with all-time: MA-only exp −$8.66/trade.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-001]** Close the unfilled-order race: the held/de-dup guard must count symbols with an OPEN logbook trade, not just filled Alpaca positions. Highest impact — it caused 100% of today's net loss and is a pure capital-protection fix (no risk-limit change).
2. Re-examine MA-only entries near MIN_CONFIDENCE (60–62): all-time negative expectancy. Candidate: raise the floor for MA-only signals or require a volume/breakout confirm. *Needs more days of evidence before acting — not today's biggest lever.*
3. TSLA hit neither TP nor stop and was flattened +0.86% — TP at 415.69 (+2.2%) may be too far for a low-vol regime; trailing-stop capture could lock more. *Watch; single-sample, defer.*

### Notes for pre-market research
- **TSLA** remains the franchise name (only winner again today, conf 97). Keep top-of-list.
- **ENPH** chopped hard at the open (false breakout, stopped in ~8 min) — low-quality breakout today; note the double-entry was a bot bug now fixed, not an ENPH-specific problem.
- **NFLX, C** generated only weak MA-only signals (conf 61) that went nowhere — both flat/negative to EOD. C continues a losing series. Watch C for the park-threshold per last research note (0W4L cluster).
- Loser cluster from research (MU/AMD/JPM/C 0W4L, GOOGL 0W3L): only C signaled today and lost again — still broad-regime weakness, not yet name-specific park triggers. Reassess later this week.
- Quiet pre-FOMC tape (FOMC decision Wed Jun 17 2PM ET) — expect continued low-conviction, choppy breakouts until Warsh presser digested.

---

## 2026-06-18 — Daily Review

### Stats
- Trades: **0 new entries**; 3 positions CLOSED (all carried-overnight from 06-16). Recorded 1W / 1L (+ 1 zero-P&L sweep).
- Net realized P&L: **+$5.07** (day +0.064%). Equity close **$7,838.59** (−21.6% YTD; equity_open 7,927.57 — the carried positions bled unrealized through the session).
- Closes: C **+$20.25**, BAC **−$15.18**, AMZN **$0.00** (misrecorded — see below). All exit_reason EOD_FLATTEN.
- Circuit breaker NOT tripped. Service active all session; clean pre-market restart 11:49 UTC. **But: capital-protection breach — see root cause.**

### Trade-by-trade review
| # | Sym | Entry (ET) | Exit (ET) | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|-----|-----------|
| 70 | C | **06-16** 09:41 @142.64 | **06-18** 15:55 @143.77 | EOD_FLATTEN | **+$20.25** | Held **2 overnights** — flatten failed 06-16 & 06-17, finally closed today. Lucky it drifted up. |
| 72 | BAC | **06-16** 10:24 @56.53 | **06-18** 15:55 @56.20 | EOD_FLATTEN | −$15.18 | Same 2-night naked hold; closed flat-ish today. |
| 71 | AMZN | **06-16** 09:41 @247.10 | logbook 06-18 15:55 | EOD_FLATTEN | **$0.00 (WRONG)** | Broker actually SOLD AMZN 06-17 15:55:58; logbook trade stayed OPEN until today's sweep, which had no position to price → fell back to entry (P&L lost). |

### What worked / what didn't
- **Worked:** The 06-18 flatten itself executed cleanly (right after the fresh pre-market restart) and finally cleared the book; no new entries on a relief-bounce day (no qualifying breakout cleared the gate) = no fresh losses. Risk limits intact, no halt.
- **Didn't — the headline failure:** positions opened **06-16 (C, AMZN, BAC) were held for TWO overnights** (06-16→06-18), a direct breach of the no-overnight invariant flagged by pre-market research **three days running**. Alpaca order history is decisive: at 06-16 15:55 **no sell orders were submitted at all** (flatten never fired); at 06-17 15:55 the flatten ran chaotically (a burst of ~10 duplicate AMZN market-sells, most auto-canceled, one filled; C/BAC stops canceled but the positions NOT liquidated); only 06-18 closed C/BAC. Root cause: `flatten_all` used fire-and-forget bulk `close_all_positions(cancel_orders=True)`, which (a) races the async order-cancel → `held_for_orders` blocks liquidation, (b) does not raise on per-position failure, and (c) the engine then **unconditionally set `flattened_on = today`**, so a failed flatten was never retried. AMZN's $0.00 is the secondary symptom: its broker position closed 06-17 but the logbook trade was swept only 06-18 with the entry-price fallback (real fill lost).

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-002]** Verified, retried EOD flatten. Cancel working orders FIRST, then close each position individually, re-query positions, mark a logbook trade CLOSED only once its broker position is confirmed gone, and leave `flattened_on` unset (→ retry next tick) + alert when any position survives. Highest impact — pure capital-protection fix for a repeated naked-overnight breach. No risk limit touched.
2. **EOD-flatten P&L accuracy** (AMZN $0.00): the snapshot/entry-price fallback misrecords the exit when the position is already gone. Candidate: look up the actual EOD market-sell fill (or detect_exits on the flatten order) instead of the entry-price fallback. *Logged to todo.md — secondary to the breach, defer to a future IMP to keep this change focused.*
3. **Flatten after the 16:00 close:** the loop only flattens while `clock.is_open`, so if every tick in 15:55–16:00 fails the position strands. Candidate: a short post-close grace window for flatten. *Logged to todo.md; IMP-002's cancel-first + per-tick retry already removes the dominant failure mode.*

### Notes for pre-market research
- **C (trade 70) and BAC (trade 72) are now FLAT** — C's open-position lock is released, so the long-deferred C park (0W5L) can be executed Mon 06-22 per the standing plan.
- No new entries fired today on the post-FOMC relief bounce — the gate stayed conservative (no clean breakout cleared MIN_CONFIDENCE). Not a watchlist problem; regime was a sharp bounce, not a trend.
- INTC (+9% on the Apple deal) and the semis (MU/AMD/NVDA/AVGO/TSM) were the day's strength but generated no qualifying entry — note for whether the breakout gate is too slow to catch gap-and-go opens.
- MU/AMD held on the semi catalyst (per 06-18 pre-market) — neither signaled today, so the "park if they lose again" test did not trigger; carry the reassessment to Mon 06-22.
- Equity $7,838.59 (−21.6%) — approaching the −25% ($7,500) strategy-review flag.

---

## 2026-06-19 — Daily Review

### Stats
- **No trades today — US market CLOSED (Juneteenth holiday).** Alpaca clock `is_open=false`, next open **Mon 2026-06-22 09:30 ET**. No `daily_summary` row for 06-19 (report ends at 06-18); no rows in `trades` with an 06-19 entry/exit.
- Equity **$7,838.56** (cash $7,838.56, buying power $31,354, account ACTIVE, paper PA3ESJUO8RU0) — flat vs 06-18 close $7,838.59 (the $0.03 is just intraday quote rounding; nothing traded). −21.6% YTD from $10K.
- **Positions: zero open** (broker `open_position_symbols()` → empty set). No naked-overnight carry — clean book into the long weekend. ✅
- Circuit breaker not engaged (no trading). Service **active** all day; only journal events are the 11:47:38 UTC pre-market restart (clean Stop→Start, no errors, no entries/exits).

### Trade-by-trade review
None — market closed. Nothing to root-cause at the trade level.

### What worked / what didn't
- **Worked / nothing to fault:** the bot correctly did nothing on a closed market — no spurious entries, no errors, no stranded positions. The book is flat and confirmed flat on the broker side, exactly as the no-overnight design intends going into a 3-day weekend.
- **Root cause of zero trades:** calendar (federal holiday), not a strategy/gate/watchlist defect. This is the expected and desired outcome; no improvement is warranted by today's (non-existent) data. Manufacturing a code change here would risk overfitting with zero supporting evidence — explicitly declined.
- IMP-002 (verified/retried EOD flatten, 427ab21) has **not yet been exercised in live trading** — Mon 06-22 is its first real test (06-18 had no fresh entries, only the legacy carried positions cleared). Watch it then.

### Lessons & improvement candidates (ranked)
- **No code change this run.** "Reviewed, no change warranted" — today produced no trade evidence, and the capital-protection invariants and recent fixes (IMP-001 dedup, IMP-002 flatten) are already in place and unexercised. Acting today would be a random/unjustified change.
- Standing candidates carried (NOT acted on today, awaiting live data): (1) **validate IMP-002 in production Mon 06-22** — confirm any position opened Monday is flat by 15:55 ET; (2) the open todo.md items from IMP-002 (EOD-flatten P&L accuracy for already-gone positions; post-16:00 grace-window flatten) remain queued behind real recurrence evidence; (3) MA-only near-floor (conf 60–62) negative-expectancy entries — still needs more days before a gate change is justified.

### Notes for pre-market research
- **Holiday — no new trade-level observations.** Watchlist state is exactly as the 06-19 pre-market curation left it: 27 active (C parked 06-19; JPM parked 06-18).
- **Due Mon 06-22 (carried, unchanged):** MU (0W5L) / AMD (0W4L) semi-catalyst reassessment — park if either signals and loses again; WPM zero-signal park decision; GOOGL 0W3L (one more loss → consolidate to GOOG only).
- **Monday is the first live session under IMP-002** — verify EOD flatten closes everything by 15:55 ET (no carry into Tue 06-23).
- TSLA remains the only consistent earner (franchise name). Equity $7,838.56 (−21.6%) — strategy-review flag at −25% ($7,500), $338 of headroom.

---

## 2026-06-22 — Daily Review

### Stats
- Trades: **7 closed (2W / 5L)**, win rate **28.6%**. First positive session since incubation began.
- Net realized P&L: **+$177.67** (day **+2.27%**). Equity close **$8,015.23** (from $7,838.56 open; +$176.67 broker truth — matches). −19.8% YTD (back above the −20% line, $515 above the −25% strategy-review flag).
- ⚠️ **The DB first reported +$238.05 / 2W2L — that was WRONG (an EOD-flatten P&L recording bug, root-caused & fixed today as IMP-003).** SPY/QQQ/TSM were booked at exit==entry ($0.00) when their real flatten sells lost ~$60 combined. Corrected in the DB to the true +$177.67 / 2W5L.
- Avg winner **+$128.62** (TSLA +203.49, ENPH +53.74); avg loser **−$15.91** (QQQ −22.68, TSM −22.64, SPY −15.06, META −12.14, AVGO −7.04). Winners ~8× the avg loser — the day was carried by 2 clean trades; losses were all small/controlled.
- Profit factor (day): 257.23 / 79.56 = **3.23**. Exit reasons: 2 TAKE_PROFIT, 2 STOP, 3 EOD_FLATTEN.
- Circuit breaker NOT tripped (+2.27% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight.** ✅ Service active all session; clean 11:48:39 UTC pre-market restart.

### Trade-by-trade review
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 73 | ENPH | 09:30:05 @52.29 | 09:46:12 @53.60 | 61.5 | MA | TAKE_PROFIT | **+$53.74** | Clean MA breakout, hit TP in 16 min. ENPH redeemed itself vs its 06-15 chop. |
| 74 | META | 09:30:06 @577.29 | 10:20:38 @568.59 | 60.8 | MA | STOP | −$12.14 | Low-conf (60.8) MA-only at the open; faded to stop. Small, controlled loss (−0.53%). |
| 75 | AVGO | 09:30:07 @411.07 | 09:40:21 @402.59 | 60.3 | MA | STOP | −$7.04 | Low-conf (60.3) MA-only; false start, stopped in 10 min. −0.29%. |
| 76 | TSLA | 09:40:37 @401.78 | 10:05:02 @411.08 | **84.5** | **BOTH** | TAKE_PROFIT | **+$203.49** | Franchise name + only BOTH signal today. Broke level 398.77, conf 84.5, hit TP (+2.68%) in 24 min. The day's engine. |
| 77 | SPY | 09:48:09 @749.14 | 15:56:50 @**744.12** | 62.4 | MA | EOD_FLATTEN | **−$15.06** | Low-conf MA-only index ETF; drifted, flattened at a small loss. *(DB had booked $0.00 — IMP-003 fix.)* |
| 78 | QQQ | 10:06:02 @744.74 | 15:56:49 @**737.18** | 62.3 | MA | EOD_FLATTEN | **−$22.68** | Low-conf MA-only index ETF; same drift-and-flatten. *(was $0.00 — IMP-003.)* |
| 79 | TSM | 10:20:47 @470.75 | 15:56:51 @**466.22** | 62.9 | MA | EOD_FLATTEN | **−$22.64** | Low-conf MA-only; held all day, flattened at a loss. *(was $0.00 — IMP-003.)* |

### What worked / what didn't
- **Worked — IMP-002 VALIDATED in production (first live test).** This was the first session that opened-and-flattened positions under the rewritten EOD flatten. Alpaca confirms **0 open positions**; the flatten fired at 15:56:50 ET and market-sold SPY/QQQ/TSM (canceled bracket legs first, then closed each), all filled. No carry into Tue 06-23. The 06-16→06-18 two-night naked-hold class of failure did not recur. ✅
- **Worked — the high-confidence BOTH edge held again.** TSLA (conf 84.5, BOTH, broke 398.77) was the single biggest contributor (+$203.49), consistent with the all-time record (BOTH earns when confidence is high). ENPH's conf-61 MA also won this time (+$53.74), hitting TP fast.
- **Didn't — low-confidence MA-only entries (conf 60–63) remain a drag.** All 5 of today's losers were MA-only with confidence 60.3–62.9: META, AVGO (quick stops) and SPY/QQQ/TSM (drift to a losing EOD flatten). Combined −$79.56. SAME pattern flagged on 06-15 (NFLX 61 / C 61 went nowhere) and matches all-time MA expectancy (−$5.99/trade). The 2 winners carried the day, but the conf-60–63 MA bucket is structurally negative.
- **Didn't — the P&L evidence base was corrupted by the EOD-flatten recording bug** (3 of 7 trades booked at $0.00). Root-caused and fixed (IMP-003). Without the fix, tomorrow's pre-market would have read a falsely rosy +$238.05/2W2L day and under-counted the MA-only drag.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-003]** EOD-flatten P&L accuracy. `eod_flatten` derived the exit from a pre-liquidation `market_value` snapshot, falling back to the *entry* price — and today it fell to entry for all 3 EOD trades (exit==entry → $0.00), misstating the day by ~$61. Fix: look up the **real flatten fill** (`broker.latest_filled_exit_price`) and record that; mv/entry are last-resort only. Highest-impact today: pure measurement-integrity fix, no risk limit touched, protecting every downstream decision (this review, the report, pre-market). Backfilled today's 3 rows + daily_summary to the true fills.
2. **Low-confidence MA-only entries (conf 60–63) — negative expectancy, now TWO sessions of evidence** (06-15: NFLX/C; 06-22: META/AVGO/SPY/QQQ/TSM, all 5 losers). Candidate: raise `MIN_CONFIDENCE` for the MA-only class, or require a volume/breakout confirm. *This is the next improvement to act on — but it changes entry behavior and deserves a `scripts/replay.py` pass over history first (does lifting the MA-only floor to ~65 cut the losers without killing winners like today's ENPH conf-61?). Defer ONE run to validate; do not change entry logic the same day as IMP-003.*
3. TSLA hit TP cleanly (+2.68%) — TP placement looked right today (unlike the 06-15 low-vol drift to flatten). No change.

### Notes for pre-market research
- **MU/AMD reassessment (due today per the standing plan):** NEITHER signaled today — no MU or AMD trade fired (today's names: ENPH/META/AVGO/TSLA/SPY/QQQ/TSM). The "park if they signal and lose again" test did NOT trigger. MU stays 0W5L, AMD 0W4L — carry the reassessment forward. (Reminder: **MU earnings Wed 06-24 after close → MU gaps Thu 06-25**, trade with caution.)
- **GOOGL** did not signal today — still 0W3L, park trigger (0W4L) not matured. Hold.
- **Index ETFs SPY/QQQ + TSM** all produced low-conf (62–63) MA-only entries that drifted to a losing EOD flatten — consistent low-quality MA-only signals. Not a watchlist removal (liquid, fit the strategy); flagged to the strategy side (candidate #2), not pre-market.
- **ENPH and TSLA were the day's quality** — ENPH redeemed its 06-15 chop with a fast TP win; TSLA remains the franchise BOTH name. Keep both top-of-list.
- Equity **$8,015.23 (−19.8%)** — climbed back above the −20% line; $515 of headroom to the −25% ($7,500) strategy-review flag.

---

## 2026-06-23 — Daily Review

### Stats
- Trades: **4 closed (4W / 0L)**, win rate **100%**. Second straight positive session — first back-to-back green days of incubation.
- Net realized P&L: **+$95.80** (day **+1.195%**). Equity close **$8,104.37** (from $8,015.20 open; +$89.17 broker truth ≈ matches realized within quote rounding). **−19.0% YTD**, $604 above the −25% ($7,500) strategy-review flag.
- Avg winner **+$23.95** (CRM +57.69, XOM +19.57, BAC +16.56, WMT +1.98); **no losers**. Profit factor (day): ∞ (zero gross loss).
- Exit reasons: **1 TAKE_PROFIT (CRM), 3 EOD_FLATTEN (XOM/BAC/WMT)**. **IMP-003 VERIFIED:** all 3 EOD_FLATTEN exits recorded their real Alpaca fills (XOM 140.12, BAC 57.91, WMT 119.81), not exit==entry $0.00 — the bug fixed 06-23 00:57 UTC did not recur. ✅
- Circuit breaker NOT tripped (+1.2% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight.** ✅ IMP-002 held a 3rd straight session. Service active all session (since 00:57:56 UTC restart); journal clean, no errors.

### Trade-by-trade review
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 80 | XOM | 09:36:28 @139.09 | 15:57:19 @140.12 | 62.0 | MA | EOD_FLATTEN | **+$19.57** | Clean MA breakout, mom 0.80; drifted up +0.74%, captured at flatten (never reached TP 142.22). |
| 81 | BAC | 09:41:42 @57.55 | 15:57:19 @57.91 | 60.96 | MA | EOD_FLATTEN | **+$16.56** | Low-conf MA, mom 0.73; steady +0.63% hold to flatten. |
| 82 | CRM | 09:46:05 @151.71 | 13:18:56 @155.15 | 61.53 | MA | TAKE_PROFIT | **+$57.69** | Day's engine: MA, mom 0.77, hit TP (+2.24%) at 13:18. Only TP of the day. |
| 83 | WMT | 13:52:54 @119.72 | 15:57:20 @119.81 | 60.22 | MA | EOD_FLATTEN | **+$1.98** | Late entry (13:52), mom 0.68; basically a scratch (+0.08%) held to flatten. |

### What worked / what didn't
- **Worked — every winner was an MA-only signal scored conf 60–62.** XOM 62.0, BAC 61.0, CRM 61.5, WMT 60.2. This is exactly the "low-confidence MA-only drag" bucket flagged 06-15 and 06-22 as the next thing to filter out. Today it produced **100% of the trades and 100% of the profit.** Single best argument against acting on that candidate.
- **Worked — IMP-002 (no-overnight) and IMP-003 (real-fill EOD P&L) both verified live.** 0 open positions on the broker; all 3 EOD_FLATTEN trades booked their true sell fills (no $0.00 fallback). The two most recent fixes are now confirmed in production.
- **Didn't — capture efficiency on the EOD_FLATTEN names was thin.** XOM/BAC/WMT were carried to the 15:57 flatten rather than hitting TP; WMT (+$1.98) was a near-scratch late entry. The day was carried by one TP (CRM). Not a defect — consistent with a directionless, low-vol tape (per 06-23 research) — but a reminder that the EOD_FLATTEN bucket is low-yield. (Backlog item #1, breakeven/trailing stop, is the queued lever here; not today's change.)
- **No losers, no bugs, no risk events.** Nothing to root-cause at the loss level today.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-004]** The "raise the MA-only confidence floor to ~65" candidate (queued as "next to act on" since 06-22) is **REFUTED by the full dataset**, and today is the disproof. Bucket analysis over all 81 trades: **MA-only is the least-bad bucket (PF 0.75, exp −$4.75); no MA signal has ever scored ≥64** (MA tops ~63), so a 65 floor disables the entire MA book — killing all 16 MA winners (today's 4 + TSLA's 3 + ENPH 06-22, etc.). Simulating "drop MA<65" worsens the portfolio (exp −$19.78 → −$41.64, PF 0.45 → 0.31). The confidence→quality relationship is in fact **inverted**: the 66+ band (all BOTH) lost −$1,227 / PF 0.31 (concentrated in the 06-08/09 overtrading days), while 62–64 is ~break-even (PF 1.06). Action: institutionalize this in `scripts/report.py` (add **profit-factor per signal type** + a **confidence-band breakdown**) so the refuted candidate can't be silently reinstated and future strategy work sees the real distribution. Pure measurement/tooling — no entry logic, no risk limit touched.
2. **Do NOT act on the MA-only bucket via confidence.** Any future MA-quality improvement must use a *non-confidence* discriminator (volume confirm, regime filter, entry-timing). Needs replay validation first — not today.
3. **EOD_FLATTEN capture efficiency** (3 of 4 today carried to flatten, WMT near-scratch): backlog #1 (breakeven-at-+0.5R / trailing stop) remains the queued lever to convert these drift-up holds into locked gains. Replay-validated already (+$563 sim) but deferred — do NOT stack it the same day as a tooling change; act on it on a day its evidence is the day's story.

### Notes for pre-market research
- **MA-only conf 60–62 names are NOT low quality** — XOM/BAC/CRM/WMT all won today; the "park the low-conf MA-only bucket" idea is refuted (see IMP-004). Keep these liquid names on the list.
- **CRM** was today's best (+$57.69, hit TP) after being a zero-signal name all incubation — it signaled and delivered. Note it as a fresh contributor.
- **WMT** late entry (13:52) barely moved — a post-13:00 MA entry on a directionless tape added almost nothing; watch whether late-session entries are worth taking on flat days.
- **MU earnings Wed 06-24 AFTER close → MU gaps Thu 06-25**; FedEx reported tonight (06-23). **PCE Thu 06-25.** Event-heavy back-half of the week — keep adds conservative.
- **GOOGL** did not signal today — still 0W3L, park trigger (0W4L) un-matured; hold. **MU/AMD** (0W5L/0W4L) did not signal — reassessment still gated on a fresh signal+loss; carry forward.
- TSLA did NOT trade today (no BOTH signal fired) — still the franchise name; equity $8,104.37 (−19.0%), $604 to the −25% flag.

---

## 2026-06-24 — Daily Review

### Stats
- Trades: **3 closed (0W / 3L)**, win rate **0%**. First red session since 06-16; ends the 2-day green streak.
- Net realized P&L: **−$87.08** (day **−1.075%**). Equity close **$8,017.26** (from $8,104.34 open; **−$87.08 broker truth — matches exactly**). **−19.8% YTD**, $517 above the −25% ($7,500) strategy-review flag.
- ⚠️ **The DB first reported −$61.34 — that was WRONG (an ENTRY-fill recording bug, root-caused & fixed today as IMP-005).** BAC/CRM/WMT were each booked at their *signal* entry price, not the actual bracket fill (which slipped 0.04–0.69 higher on a fast open), hiding ~$25.74 (42%) of the day's loss. Corrected in the DB to the true −$87.08 / equity-matched.
- Avg loser **−$29.03** (CRM −41.48, WMT −27.41, BAC −18.19); no winners. Profit factor (day): **0.00** (zero gross win).
- Exit reasons: **3 EOD_FLATTEN** (none hit STOP, none hit TP — all 3 drifted and were flattened). Circuit breaker NOT tripped (−1.07% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight.** ✅ IMP-002 held a 4th straight session. Service active all session (since 11:48:31 UTC restart); one pre-open transient `APIError <html>` at 05:33 EDT (non-fatal, loop survived), no in-session errors.

### Trade-by-trade review
*(entry = real Alpaca bracket fill; R measured off the real fill; MFE/MFE from IEX 5-min bars)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | MFE / MAE | Root cause |
|---|-----|-----------|-----------|------|------|------|-----|-----------|-----------|
| 84 | BAC | 09:30 @**58.215** (sig 57.93) | 15:57 @57.82 | 60.32 | MA | EOD_FLATTEN | **−$18.19** | +0.10R / −0.71R | Low-conf MA at the open; never went anywhere positive, drifted down with the tape, flattened. |
| 85 | CRM | 09:38 @**155.17** (sig 154.48) | 15:57 @152.73 | 68.99 | BREAKOUT | EOD_FLATTEN | **−$41.48** | **+0.59R** / −1.35R | Real breakout (broke 154.285), popped to 156.94 (+0.59R) then **fully round-tripped** and faded to flatten (−1.57%). Day's worst. (IEX low 151.11 < stop 152.16 but the broker stop never filled — thin-IEX print vs SIP; flattened EOD instead.) |
| 86 | WMT | 09:41 @**120.33** (sig 120.29) | 15:57 @119.08 | 62.31 | MA | EOD_FLATTEN | **−$27.41** | +0.03R / −0.76R | Low-conf MA at the open; faded with the tape, never positive, flattened. |

### What worked / what didn't
- **Worked — capital protection held cleanly on a losing day.** IMP-002 fired exactly as designed: the 15:55 & 15:56 liquidations reported "incomplete — 3 positions still open" (the `held_for_orders` race), retried, and all three confirmed flat by 15:57 — Alpaca shows **0 open positions, no naked overnight** (4th straight clean session). IMP-003's real-exit-fill recording also held (exits booked at 57.82/152.73/119.0841). No circuit-breaker, no risk event; each loss was small and controlled (worst −1.57%).
- **Didn't — 3-for-3 longs into a falling tape.** The day was a broad **−0.76% down session** (semis still weak after Tue's −2% plunge); the bot opened three long breakouts/MA-stacks in the first 11 minutes and all three faded with the market. None hit its stop (3×ATR/1.5% floor stops are wide → trades survive noise but ride the drift down to the flatten), none hit TP. This is the **EOD_FLATTEN-drift bucket on a red day** — the mirror image of 06-23 (same bucket, but the tape was green so they drifted *up* into small wins). The strategy has **no down-day / regime gate**: it takes longs at the open regardless of broad direction.
- **Didn't — the entry-fill measurement bug (IMP-005).** The DB recorded entries at the signal price, so the flatten path computed P&L off 57.93/154.48/120.29 instead of the real fills 58.215/155.17/120.33 — booking −$61.34 vs the broker's −$87.08 (a 42% understatement in one day). This corrupted the evidence base the same way the IMP-003 exit bug did; STOP/TP exits were already immune (they price off the parent fill), so the hole was the flatten path only.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-005]** ENTRY-fill P&L accuracy on the EOD_FLATTEN path. `eod_flatten` priced the entry off the stored *signal* price (`t["entry_price"]`); on a fast open the bracket buy slips (today 0.04–0.69 higher), so realized P&L was understated by $25.74 (42%) today and silently on every prior slipped flatten. Fix: new `broker.entry_fill_price(order_id)` looks up the parent bracket's real `filled_avg_price`; `eod_flatten` now prices the entry off it (falling back to the recorded entry) and corrects the stored `entry_price` so the row stays self-consistent. This is the unfinished half of IMP-003 (which fixed the *exit* fill) — `detect_exits` already priced STOP/TP off the real parent fill, so only the flatten path was wrong. Pure measurement-integrity fix; **no risk limit, no entry logic touched** (paper endpoint, MAX_RISK_PCT, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all unchanged). Backfilled today's 3 rows + daily_summary to the true −$87.08.
2. **Down-day / market-regime gate — the recurring strategy lever.** Today is the cleanest illustration yet: 3 longs at the open on a −0.76% tape, all faded; 06-23 was the same bucket on a green tape and won. The edge is **directional-with-the-tape, not symbol-specific** — a broad-regime filter (e.g. only take longs when SPY/QQQ are above a short intraday MA, or skip the first N minutes on a gap-down open) is the highest-potential *strategy* change. **NOT acted on today** — it changes entry behavior and needs a `scripts/replay.py` pass over history (does a SPY-above-VWAP/MA long-only gate cut red-day losers without killing green-day winners like 06-23?). One run to validate first; do not stack a behavior change on the same day as a measurement fix.
3. **Breakeven stop at +0.5R (backlog #1)** — CRM hit +0.59R (156.94) then round-tripped to −1.57%: a breakeven-at-+0.5R stop would have saved ~$41 on CRM. But BAC (+0.10R) and WMT (+0.03R) never reached +0.5R, so it helps only 1 of 3 today — today is *not* cleanly "the breakeven day." Remains replay-validated (+$563 sim) and queued; act on it on a day its evidence is the dominant story, and not stacked with another change.

### Notes for pre-market research
- **CRM** was a genuine BREAKOUT (conf 69, broke 154.285) that popped +1.1% then **fully round-tripped** to a −1.57% flatten — breakouts are failing/mean-reverting on this choppy, semi-led-down tape. Watch CRM; it was 06-23's hero (+$57.69 TP) and 06-24's worst (−$41.48) — same name, opposite regime.
- **BAC / WMT** were low-conf (60–62) MA drifters that simply faded with the broad tape — no name-specific problem, pure down-day regime. Keep on the list.
- **All 3 entries fired 09:30–09:41** (open cycle) on a red open and rode the drift down all day — note for whether early longs on a gap-down/weak open are worth taking (ties to the regime-gate candidate #2).
- **MU** stays **parked** (earnings tonight after close, ~14% implied move) — re-enable Thu/Fri once the 06-25 gap settles, per the standing plan. **PCE inflation Thu 06-25** — do not add names into the event.
- **GOOGL** 0W3L / **AMD** 0W4L — still gated on a fresh signal+loss; neither signaled today → hold.
- TSLA did NOT trade today (no BOTH signal). Equity **$8,017.26 (−19.8%)**, $517 to the −25% ($7,500) flag.

---

## 2026-06-25 — Daily Review

### Stats
- Trades: **3 closed (2W / 1L)**, win rate **66.7%**. Day essentially flat.
- Net realized P&L: **−$3.69** (day **−0.046%**). Equity close **$8,013.54** (from $8,017.23 open; **−$3.69 broker truth — matches to the penny**, last_equity confirms). **−19.9% YTD**, $514 above the −25% ($7,500) strategy-review flag.
- Avg winner **+$14.62** (AMD +19.61, QCOM +9.62); single loser **−$32.92** (TSM). Profit factor (day): 29.23 / 32.92 = **0.89**.
- Exit reasons: **3 EOD_FLATTEN** (none hit STOP, none hit TP — all three drifted to the 15:55 ET flatten). Circuit breaker NOT tripped (−0.05% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight.** ✅ IMP-002 held a **5th straight session**.
- **Fill accuracy verified live again:** the day's gross (−$3.69) equals the broker equity move exactly because entries AND exits were booked at the real Alpaca fills — QCOM buy 203.815715 / sell 205.19, TSM 442.55 / 434.32, AMD 520.87 / 530.675 (matches DB). IMP-003 (exit) + IMP-005 (entry) both confirmed. Service active all session (since 11:49:25 UTC pre-market restart); no in-session errors.

### Trade-by-trade review
*(entry/exit = real Alpaca bracket fills; R measured off the real fill)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 87 | QCOM | 10:04:55 @203.8157 | 15:56:55 @205.19 | 76.92 | BOTH | EOD_FLATTEN | **+$9.62** | Day's gap-up name (+11.7% pre-mkt on raised guide). Broke 203.68 *34 min after the open* — most of the gap move was already gone; drifted +0.67% and was captured at flatten. TP 221.22 (+8.5%) never remotely in play on a post-gap day. Highest-conf signal (BOTH 76.92) → it won. |
| 88 | TSM | 10:10:12 @442.55 | 15:56:55 @434.32 | 67.98 | BREAKOUT | EOD_FLATTEN | **−$32.92** | Day's only loser. Broke 440.065, immediately reversed and faded to −1.86%. Stop 431.92 (−2.40%, the wide 3×ATR/1.5% floor) never filled → rode the drift down to flatten. Classic **false breakout**; semis were bid (MU-led) but TSM did not participate. |
| 89 | AMD | 10:10:13 @520.87 | 15:56:56 @530.675 | 60.75 | BREAKOUT | EOD_FLATTEN | **+$19.61** | Broke 515.70, drifted +1.88% and captured at flatten. **AMD's first signal since 06-09 — it WON.** The standing "park AMD if it signals and loses again" trigger is therefore NOT triggered (signaled + won → thesis holds, AMD stays). TP 548.07 (+5.2%) not reached. |

### What worked / what didn't
- **Worked — capital protection + fill accuracy, a 5th clean session.** 0 open positions on Alpaca (no naked overnight); the 15:55 flatten canceled the working bracket legs first, then market-sold all three (IMP-002). Day gross == broker equity move to the penny (IMP-003 exit fills + IMP-005 entry fills both verified). No circuit-breaker, no risk event, each loss small/controlled.
- **Worked — the highest-confidence signal won.** QCOM (BOTH 76.92) and AMD both green; only the mid-conf BREAKOUT (TSM 67.98) failed.
- **Didn't — flat on a +2.1% Nasdaq up-day.** A strong semi-rally tape (MU blowout) and the bot netted ~$0 from 3 longs — the recurring "entries don't capture broad up-moves" theme (first flagged 06-16). All 3 entries fired 10:04–10:10 ET, **34–40 min after the open**, after the gap-and-go had largely played out (QCOM had only +0.67% left in it). The gate is slow on gap opens (standing observation since 06-18).
- **Didn't — TSM false breakout.** Broke 440.065 and reversed instantly; the (correctly) wide stop meant it bled to flatten rather than stopping out — the −$32.92 wiped the two small winners.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-006] By-exit-reason P&L attribution.** Today's 3/3 EOD_FLATTEN exits reignited the recurring "EOD_FLATTEN drift is a low-yield drag" framing (06-23/06-24) and primed the queued "convert flatten holds via breakeven/trailing" lever. The report only showed exit-reason *counts*, so I computed the all-time split for the first time — and it **refutes the framing**: **STOP exits (48 trades) carry the ENTIRE bleed: −$2,739.74, PF 0.01, 2.1% win** (the false-breakout losses), while **EOD_FLATTEN (27 trades) is net POSITIVE: +$72.53, PF 1.29**, and TAKE_PROFIT +$974.44. The queued breakeven/trailing candidate targets the one already-profitable bucket; the real leak is false breakouts that hit the stop. Added `by_exit_reason` to `analytics.compute_metrics` (reusing IMP-004's `_bucket`) + a "By exit reason" section to `scripts/report.py`, so this attribution is institutionalised — exactly the IMP-004 pattern (surface the metric so a mis-aimed candidate can't be silently acted on). Pure measurement/tooling: **no entry logic, no sizing, no stop, no risk limit touched.**
2. **The real strategy problem is the false-breakout STOP bucket (PF 0.01), not the flatten bucket.** Any future strategy work should attack breakout *quality* (volume/momentum confirm, regime filter) to cut the −$2,739 STOP bleed — NOT chase flatten-drift capture. Needs `scripts/replay.py` validation; not today's change.
3. **Down-day/regime gate + entry-timing-on-gap-opens** remain queued strategy levers (need replay). Today (mixed-up tape, flat result, late gap entries) supports the "late entry misses the move" half but isn't a clean down-day case. Defer.

### Notes for pre-market research
- **AMD signaled (first since 06-09) and WON (+$19.61)** — the "park AMD if it signals and loses again" trigger did NOT fire; AMD stays, thesis (broad-regime, not name-quality) supported. Drop the AMD park watch.
- **MU re-enabled today did NOT signal** — no MU trade fired on its +15% earnings-gap day; the gap-day-breakout question is still untested. Keep MU; watch tomorrow.
- **QCOM** broke out (+catalyst, BOTH 76.92) but the bot entered 34 min late and captured only +0.67% — note the gate is slow to catch gap-and-go opens (recurring). **TSM** false-broke and faded −1.86% — semis were mixed (MU/QCOM/AMD up, TSM down); not a name-park, just a failed breakout.
- No watchlist change warranted by today. Equity **$8,013.54 (−19.9%)**, $514 to the −25% ($7,500) flag.

---

## 2026-06-26 — Daily Review

### Stats
- Trades: **4 closed (1W / 3L)**, win rate **25%**.
- Net realized P&L: **−$139.98** (day **−1.747%**). Equity close **$7,873.54** (from $8,013.52 open; Alpaca last_equity 8013.52 → equity 7873.54 = **−$139.98 broker truth, matches to the penny**). **−21.3% YTD**, $374 above the −25% ($7,500) strategy-review flag.
- The **entire day is one trade: ENPH STOP −$132.44** (95% of the loss). The other 3 (COST/META/TSLA) netted −$7.54 combined — drift-to-flatten noise.
- Avg loser **−$48.54** (ENPH −132.44, COST −7.50, META −5.69); single winner **+$5.65** (TSLA). Profit factor (day): 5.65 / 145.63 = **0.04**.
- Exit reasons: **1 STOP (ENPH), 3 EOD_FLATTEN** (COST/META/TSLA, all drifted, none hit TP). Circuit breaker NOT tripped (−1.75% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight.** ✅ IMP-002 held a **6th straight session**. Fill accuracy: realized_pl computed off the real Alpaca fills (ENPH buy 48.11/sell-stop 46.57 → −132.44; matches broker move). Service active all session (since 06-25 21:34 UTC restart); no in-session errors.

### Trade-by-trade review
*(entry/exit = real Alpaca bracket fills; R measured off the real fill)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 90 | COST | 09:42:01 @953.49 | 15:56:18 @949.74 | 60.23 | MA | EOD_FLATTEN | **−$7.50** | Low-conf MA (qty 2 @ 0.5% risk); drifted −0.39% with the megacap-tech rotation, flattened. Tiny. |
| 91 | ENPH | 09:44:21 @**48.11** (sig 48.04) | 11:12:14 @46.57 | **81.89** | **BOTH** | **STOP** | **−$132.44** | **The day.** BOTH signal broke 47.985 on **below-average volume (rel_vol ~0.40)**, fully reversed, stopped −3.20% at 11:12. Textbook **false breakout**. Conf 81.89 → 1.5% risk tier → qty 86 (3× the other trades) → 3× the loss. |
| 92 | META | 10:51:47 @552.31 | 15:57:21 @550.89 | 60.84 | MA | EOD_FLATTEN | **−$5.69** | Low-conf MA (qty 4 @ 0.5% risk); −0.26% drift into the megacap bleed (META −2.7% tape), flattened. Tiny. |
| 93 | TSLA | 11:14:30 @379.715 | 15:57:31 @380.66 | 60.14 | MA | EOD_FLATTEN | **+$5.65** | Low-conf MA (qty 6 @ 0.5% risk); +0.25% scratch, the only green. |

### What worked / what didn't
- **Worked — capital protection + fill accuracy, a 6th clean session.** 0 open positions on Alpaca (no naked overnight); the 15:56 flatten cleared COST/META/TSLA, ENPH's stop fired correctly at 11:12. Day gross == broker equity move to the penny. No circuit-breaker, no risk event. ENPH's −3.20% is the worst single loss of incubation but was still bounded by the stop and the 1.5% risk tier (~−1.6% of equity).
- **Didn't — one high-confidence false-breakout STOP carried the whole loss.** ENPH (conf 81.89, BOTH) broke 47.985 and instantly round-tripped through its stop. This is the **STOP/false-breakout bucket** that IMP-006 proved is the *entire* all-time leak (STOP exits PF 0.01, −$2,872). The 3 MA-only trades behaved exactly as the least-bad bucket does — small drift, ~scratch.
- **Didn't — the sizing table amplified the worst bucket.** ENPH got the 80-90 conf tier (1.5% risk → qty 86) while the three MA trades got 0.5% (qty 2/4/6). So the single trade in the empirically-worst bucket (per IMP-004, 66+ band PF 0.28) was sized 3× the others and produced 95% of the loss. The confidence→quality relationship is inverted, yet `CONFIDENCE_RISK_TABLE` still escalates risk with confidence.

### Lessons & improvement candidates (ranked)
**No code change today — "reviewed, no change warranted."** Today's loss is a single high-confidence false-breakout STOP, and I rigorously tested all three actionable levers against the full record and **refuted every one** — shipping any of them would be overfitting to one trade / one dead regime, violating "protect capital, never random, never overfit":

1. **Breakeven-stop at +0.5R (backlog #1) — REFUTED on post-fix data.** `scripts/replay` over the 44 trades with bars: only **1 loser ever saw +1R before stopping**, and the +0.5R sim delta (+$103) is far *inside* the simulation noise budget (sum|error| $714). False-breakout losers (ENPH today included) reverse immediately — they don't run favorably first, so a breakeven/trailing stop can't rescue them. The old "+$563 sim" was on the pre-fix 52-trade window dominated by the 06-08→06-12 overtrading days. Demoted in todo.md.
2. **Flatten the `CONFIDENCE_RISK_TABLE` (size down the high-conf tier) — REFUTED as regime-overfit.** Simulating flat-0.5% risk improves *all-time* P&L (−$1,832 → −$1,076, saving $756) — BUT that gain comes **entirely from shrinking the pre-fix 06-08/09/10/12 overtrading-regime blowups** (AMD/C/GOOGL/SE/META, all conf 80-90). On the **post-06-15 regime it makes things WORSE** (−$23 → −$85), because there the high-conf trades were TSLA's big winners (+$203 / +$91). The circuit-breaker + re-entry-throttle + dedup already structurally fixed the regime that made the high-conf tier toxic. Acting now = fighting the last war. Recorded refuted in todo.md.
3. **Volume-confirmation gate on breakouts — REFUTED as non-discriminating.** Reconstructed rel_vol at entry for every breakout-containing trade: volume does **not** separate winners from losers. SE #59 broke out on **6.15× volume and lost −$142**; META #60 on 2.26× lost −$122; AMD #89 on 0.59× **won +$20**; TSM #57 on 0.43× **won +$34**. A rel_vol≥1.0 gate would have skipped ENPH today (0.40) but also two real winners, and missed the biggest losers (all high-volume). Only 17 of 38 breakout trades even have reconstructable bars, and the "low-vol loses" read is driven by today's ENPH itself. Recorded refuted in todo.md.
4. **The genuine remaining lever is a market-regime / breakout-quality entry gate** (recurring since 06-24/06-25) — the edge is directional-with-the-tape, not symbol- or score-specific, and no *pre-trade* score (confidence, value, momentum, volume) reliably flags a false breakout. This needs intraday SPY/QQQ regime infrastructure + a proper multi-day replay, i.e. a deliberate build, **not** a one-shot post-close change. Elevated to the top of the strategy backlog in todo.md with the validation plan. Do NOT hack it from one day's ENPH.

### Notes for pre-market research
- **ENPH** was a genuine BOTH breakout (conf 81.89, broke 47.985) that **fully round-tripped −3.20% to a stop** on weak (~0.40×) volume — a clean false breakout on a two-sided tape. Same failure mode it showed 06-15 (chopped, stopped) and the opposite of its 06-22 fast-TP win — name behaves with the regime, not a name-specific park (1W/4L all-time, −$249, but every loss is a regime/false-breakout event, not a liquidity/quality defect). Keep, watch.
- **COST / META / TSLA** were all low-conf (60) MA drifters — COST/META faded with the megacap-tech rotation (AAPL/MSFT/AMZN/META all red), TSLA scratched green. No name-specific signal; pure regime. Keep all.
- **Two-sided megacap-rotation tape played out as the 06-26 pre-market expected** — megacaps bled, the bot's longs into them drifted down (COST/META), and the one aggressive breakout (ENPH) failed. This is the *down/choppy-day, longs-fade* regime case again (06-24 was the cleanest prior instance) — reinforces the regime-gate as the #1 strategy lever, NOT any single-day entry/exit tweak.
- **GOOGL joins the Dow before the 06-29 open** (per 06-26 research) — watch Monday for an inclusion bid; GOOGL still 0W3L (one more loss → consolidate-to-GOOG-only). **MU** still has not produced a live signal since its 06-24 blowout — gap/post-earnings breakout behavior still untested.
- Equity **$7,873.54 (−21.3%)**, **$374 to the −25% ($7,500) strategy-review flag** — the cushion has thinned (was $514); a regime-gate that cuts red-day/false-breakout entries is now the most important capital-protective work.

---

## 2026-06-29 — Daily Review

### Stats
- Trades: 5 closed (**4W / 1L**), win rate **80%**.
- Net P&L: **+$126.49** (day **+1.607%**). Equity close **$8,000.00** (from $7,873.54). Best day since 06-23.
- Avg winner **+$60.76** (TSLA +106.87, INTC +85.79, GOOG +40.90, SPY +9.48); the single loser −$116.55 (AAPL).
- Profit factor (day): 243.04 / 116.55 = **2.09**.
- Circuit breaker NOT tripped (+1.61% vs −8.0% halt). Service active all session, no errors. **0 open positions — no overnight carry (Alpaca confirmed).** DB equity_close $8,000.00 == broker equity to the penny; all 5 exit fills tie to Alpaca.
- Exit reasons: 1 STOP (AAPL), 1 TAKE_PROFIT (TSLA), 3 EOD_FLATTEN (SPY/GOOG/INTC).

### Trade-by-trade review
| # | Sym | Entry (ET) | Exit (ET) | Conf/type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|-----------|------|-----|-----------|
| 94 | AAPL | 09:31:25 @286.37 (fill 286.51) | 10:27:18 @280.96 | 81.5 BOTH | STOP | **−$116.55** | False breakout at the open on a gapped-up megacap; filled **1.62% above** broken level 281.81 (day's most-extended fill) and reversed straight to its 1.88%-ATR stop. Lone loser. |
| 95 | SPY | 09:36:54 @737.22 | 15:56 @740.38 | 63.0 MA | EOD_FLATTEN | +$9.48 | Weak MA-only; rode the green tape, small gain held to flatten. |
| 96 | GOOG | 09:36:55 @344.70 | 15:56 @351.52 | 61.3 MA | EOD_FLATTEN | +$40.90 | MA-only; Dow-inclusion bid + risk-on, ran +1.98% but never reached TP 354.00 → held to close. |
| 97 | TSLA | 10:29:23 @395.47 (fill 396.36) | 13:08:39 @406.08 | 71.4 BOTH | TAKE_PROFIT | **+$106.87** | Clean breakout (broke 394.27, tight **0.30%** entry), ran to +TP. Day's best. |
| 98 | INTC | 13:14:33 @129.74 | 15:56 @131.27 | 84.0 BOTH | EOD_FLATTEN | +$85.79 | Tight breakout (**0.13%** above 129.58), trended up, held to close. |

### What worked / what didn't
- **Worked:** the *directional-with-the-tape* thesis again — on a green/risk-on open (NDX +1.1%, US–Iran de-escalation) the same breakout setups followed through (4/5 winners, +$243 gross). TSLA the clean BOTH→TP winner; GOOG/INTC trended and held to flatten. The two **tight** breakout entries (TSLA 0.30%, INTC 0.13% above level) won. Risk controls held; flatten confirmed flat, 0 overnight.
- **Didn't:** AAPL — lone loser, a gapped-up megacap that false-broke at the open and reversed within an hour. It was also the day's most-*extended* fill (1.62% above level), which *tempts* a "stop chasing / cap extension" read — but the full book refutes that (see candidate 1).
- GOOG ran +1.98% yet TP 354.00 (RR target) was never hit → winners riding to the EOD flatten rather than booking the target; consistent with all-time EOD_FLATTEN PF 1.77.

### Lessons & improvement candidates
1. **(ACTED → IMP-007) Entry extension is NOT a usable false-breakout discriminator.** AAPL's 1.62% extension is today's anecdote, but across all 41 breakout-type trades the **tightest** bucket (≤0.5%) carries the **worst** stop rate (67.9%, −$1,047), and only 2 trades ever exceeded 1.0% extension. An extension cap would overfit one trade and miss the leak (and would also cut tight winners). Recorded as a **refuted candidate** and surfaced as a permanent report metric (`by_entry_extension`) so it can't be silently reopened — same precedent as IMP-004 (confidence) and IMP-006 (volume).
2. **(STANDING #1 lever) Market-regime entry gate** remains the real work. Today corroborates it: AAPL false-broke at the open while the *same* setup class (TSLA/INTC) won on the green tape — the discriminator is **tape direction**, not any per-trade score. Confidence (IMP-004), value/momentum & volume (06-26) and now **entry extension** (IMP-007) have all failed to separate the false breakout. The lever must be a market-level filter (long-only when SPY/QQQ above an intraday MA/VWAP; skip the first N min on a gap-down). Multi-run replay work, not a one-day tweak.
3. **(Note, no action)** For STOP/TP trades the stored `entry_price` is the *signal* price (AAPL 286.37 vs fill 286.51; TSLA 395.47 vs fill 396.36) while `realized_pl` is correctly computed off the real fill — an internal-consistency wrinkle, P&L is right. Already tracked as backlog #5; left there.

### Notes for pre-market research
- **AAPL** — gapped up, false-broke at the open and reversed to stop within the hour: the megacap open-fade pattern persists. Not a quality park (no other read today), but flag the open-fade risk on gap-up megacaps.
- **GOOGL** still **0W3L** and did **not** signal today (only GOOG traded — an MA win +$40.90); park trigger (0W4L) un-matured → **hold**. GOOG caught the Dow-inclusion + risk-on bid.
- **MU** still produced **no live signal** (untested since the 06-24 blowout) — keep and watch.
- SPY/GOOG/INTC all rode the green tape to a positive EOD flatten; TSLA the only target hit. XOM/energy did not signal despite firmer oil. Watchlist healthy, no parks suggested.
- **Equity recovered to $8,000.00 (+1.61%)** — now **$500 above** the −25% ($7,500) review flag (cushion restored from $374). 4-day week (closed Fri 07-03); JOLTS Tue, ADP/ISM Wed, **payrolls Thu 07-02** → expect event-driven, thinner liquidity.

---

## 2026-06-30 — Daily Review

### Stats
- Trades: **6 closed (5W / 1L)**, win rate **83.3%** — the **best day of incubation** by P&L and %.
- Net realized P&L: **+$297.04** (day **+3.713%**). Equity close **$8,297.01** (from $8,000.00 open; Alpaca equity $8,297.01 == DB to the penny, broker move +$297.01 matches). **−17.0% YTD**, **$797 above** the −25% ($7,500) review flag (cushion widened from $500).
- Avg winner **+$59.87** (INTC +90.33, TSM +96.58, TSLA +59.10, MU +20.27, AAPL +33.09); single loser **−$2.33** (AVGO, a scratch). Profit factor (day): 299.37 / 2.33 = **128.5**.
- Exit reasons: **3 TAKE_PROFIT** (INTC/TSM/TSLA — first multi-TP day since the regime turned) + **3 EOD_FLATTEN** (MU/AAPL/AVGO, all green-to-scratch). Circuit breaker NOT tripped (positive day). **0 open positions on Alpaca — no naked overnight** (IMP-002 held a 7th+ session: the 15:55 flatten reported "incomplete" twice (15:55:36, 15:56:39) then confirmed all three flat at 15:57 and stopped retrying — exactly the retry-until-confirmed design). Service active all session (since 06-29 21:36 UTC restart); no in-session errors.
- **One entry was REJECTED, not taken: AMD** (see trade table + Lessons) — a bracket-order 422, the day's only anomaly.

### Trade-by-trade review
*(entry = plan/signal price from the log; exits = real Alpaca bracket fills)*
| # | Sym | Entry (ET) | Exit (ET) | Conf/type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|-----------|------|-----|-----------|
| — | **AMD** | 09:30:22 (attempt) | — | — BOTH | **REJECTED** | **$0 (missed)** | **Bracket 422**: TP (anchored to signal close ~542) fell **below the live base_price 554.29** (AMD gapped >2% at the open, later ran to 578). Entry silently lost; not even persisted to `signals`/`trades`. → IMP-008. |
| 99 | INTC | 09:30:23 @131.69 | 09:37:52 | 83.66 BOTH | **TAKE_PROFIT** | **+$90.33** (+1.13%) | Tight breakout (broke 131.50, +0.14%) on the semis-led risk-on open; ran straight to TP in 7 min. Day's cleanest. |
| 100 | TSM | 09:30:23 @455.12 | 10:04:40 | 72.79 BOTH | **TAKE_PROFIT** | **+$96.58** (+1.92%) | Breakout (broke 453.46, +0.37%), trended to TP in 34 min. Reverses its 06-29 false-break — same name, opposite (green) tape. |
| 101 | MU | 09:30:24 @1145.00 | 15:57:52 | 69.52 BOTH | EOD_FLATTEN | +$20.27 (+1.78%) | First live MU signal since the 06-24 blowout (broke 1141.50). Trended up, never hit TP, held green to flatten. |
| 102 | TSLA | 09:40:03 @411.72 | 14:59:14 | 66.07 BOTH | **TAKE_PROFIT** | **+$59.10** (+2.40%) | Breakout (broke 410.63, +0.27%); the franchise earner hit TP late session. Now **4W0L** (+$375 14d). |
| 103 | AAPL | 10:04:45 @285.46 | 15:57:52 | 60.91 MA | EOD_FLATTEN | +$33.09 (+1.29%) | Low-conf MA; rebounded with the megacap bid (opposite of its 06-29 open-fade), drifted green to flatten. |
| 104 | AVGO | 15:00:24 @378.32 | 15:57:53 | 60.44 MA | EOD_FLATTEN | **−$2.33** (−0.09%) | Low-conf MA entered **late (15:00)**, ~1h before flatten; scratched flat. Lone "loss," pure noise. |

### What worked / what didn't
- **Worked — directional-with-the-tape, the standing thesis, paid in full.** On the risk-on continuation the morning research expected (Dow record, semis/SMH bid, Mag7 rebound), the breakout setups **followed through**: 3 of 5 winners reached TP (INTC/TSM/TSLA — the first multi-TP day since the regime turned), and even the two MA drifters (MU/AAPL) held green to the flatten. This is the green-tape mirror image of the 06-24/06-26 down-tape days where the *same* setups false-broke — reinforcing that **tape direction is the discriminator** (the #1 strategy lever, regime gate). Risk controls held: no halt, flatten confirmed flat (0 overnight), fills tied to broker to the penny.
- **Didn't (≈nothing on realized trades).** The only realized red was AVGO −$2.33, a late low-conf MA scratch — noise, not a strategy failure. There is no losing-trade root cause worth a code change today.
- **The one real defect is a MISSED entry, not a loss: AMD's bracket 422.** AMD was the day's strongest mover (gapped >2% at the open, ran to 578 by post-open) and the bot tried to enter it first (09:30:22) — but the plan's take-profit, anchored to the **stale signal-bar close (~542)**, landed below the **live base_price 554.29**, so Alpaca rejected the entire bracket and the entry was silently lost (no `signals`/`trades` row). This is the highest-impact, capital-relevant, data-justified issue today.

### Lessons & improvement candidates (ranked)
1. **(ACTED → IMP-008) Stale-signal / entry-slippage guard.** The plan's entry/stop/take-profit are all anchored to `ev["close"]` (the signal-bar close), but the order is a **MARKET buy that fills at the live price**. When a symbol gaps/runs up between the signal and submission, two things break: (a) at a gap ≥ ~RR×MIN_STOP (~2.25%) the TP lands below the live price and Alpaca **422s the whole bracket** (AMD today), and (b) at a *smaller* gap (~1–2.25%) the bracket is accepted but the stop now sits that much **further from the real fill — silently inflating per-share risk above the plan**. Note that entering AMD at the +2% gap would NOT have been free money: the stop, anchored to the 542 signal, would have sat ~4% below a 554 fill — far over the intended risk — so the rejection actually *protected* capital by accident. IMP-008 makes that protection **deliberate, logged, and extends it to the silent 1–2.25% band**: a pre-submit guard fetches the live trade price and **skips** any entry whose live price is > `MAX_ENTRY_SLIPPAGE_PCT` (1.0%) above the signal close. Recorded fills all-time are ≤0.5% off the signal, so 1.0% only catches the gap-chase — no false skips on normal opens. Fail-open (a data hiccup never blocks an entry). **A new skip (tightening) — no risk limit widened.**
2. **(STANDING #1 lever) Intraday market-regime entry gate** — unchanged as the real strategy work. Today *corroborates* it (green tape → the same breakout class that false-broke on red tape won) but warrants no one-day action; it remains the deliberate multi-run-replay build at the top of the backlog. Confidence (IMP-004), volume (06-26), entry-extension (IMP-007) have all failed as per-trade discriminators; the lever is market-level (long-only when SPY/QQQ above an intraday MA/VWAP).
3. **(Note, no action)** AMD's rejected attempt produced no `signals` row, so missed entries are invisible to the report/analytics — only the `bot.log` shows them. Acceptable for now (IMP-008 will now log a clean `ENTRY SKIPPED … stale_signal_gap` line); if gap-skips become frequent, consider persisting skipped attempts. Left as a backlog note.

### Notes for pre-market research
- **AMD** — the day's strongest mover (gapped >2% at the open, ran to ~578) but the bot **could not enter** it (bracket 422 on the open gap; now handled by IMP-008 as a deliberate gap-skip). AMD is behaving as a clean momentum leader on the semis-led tape; it remains a high-quality watchlist name — the issue was order mechanics, **not** the name. No park.
- **TSM** flipped from a 06-29 false-break loss to a +1.92% TP win on the green tape — textbook regime-dependence (name behaves with the tape, not a structural defect). **MU** finally produced its first live signal since the 06-24 blowout and won (+1.78% to flatten) — the post-earnings gap has settled; keep. **TSLA** now **4W0L** (+$375 14d), still the franchise earner. **AAPL** rebounded (+1.29%) — the opposite of its 06-29 open-fade, i.e. regime not name.
- **AVGO** was the only red — a *late* (15:00 ET) low-conf MA entry with ~1h to the flatten; nothing to act on, but a reminder that late-session low-conf MA entries have little room to work before 15:55.
- **GOOGL** still **0W3L** and did not signal today (GOOG didn't trade either) — park trigger (0W4L) un-matured, hold. **No watchlist change warranted** by today.
- Macro: **ADP + ISM mfg Wed 07-01, NFP Thu 07-02, market closed Fri 07-03.** Do NOT add names into the data; today's risk-on can whipsaw on a hot/cold print. Equity **$8,297.01 (−17.0%)**, **$797 above** the −25% flag — best cushion since early incubation; protect it into the labor data.

---

## 2026-07-01 — Daily Review

### Stats
- Trades: **6 closed (5W / 1L)**, win rate **83.3%** — **third straight green day** (06-29 +$126, 06-30 +$297, 07-01 +$152), the best 3-day run of incubation.
- Net realized P&L: **+$152.38** (day **+1.837%**). Equity close **$8,449.36** (from $8,297.01 open; Alpaca equity $8,449.36 == DB to the penny, broker move +$152.35 ≈ matches within quote rounding). **−15.5% YTD**, **$949 above** the −25% ($7,500) review flag — best cushion of incubation.
- Avg winner **+$40.04** (SE +60.30, MSFT +58.52, GOOGL +42.41, AAPL +34.40, AMZN +4.59); single loser **−$47.84** (ENPH). Profit factor (day): 200.22 / 47.84 = **4.19**.
- Exit reasons: **2 TAKE_PROFIT** (SE, MSFT), **1 STOP** (ENPH), **3 EOD_FLATTEN** (AAPL/GOOGL/AMZN, all green-to-scratch). Circuit breaker NOT tripped (+1.84% nowhere near −8.0%). **0 open positions on Alpaca — no naked overnight** (IMP-002 held an 8th+ session: the 15:55:51 ET flatten reported "incomplete — 3 still open", retried, and confirmed AAPL/GOOGL/AMZN flat by 15:57:05 — the retry-until-confirmed design working). Service active all session (since 06-30 21:37 UTC restart); no in-session errors.
- **One entry was REJECTED, not taken: NVDA** (bracket 422 at 09:30:26 ET) — the day's only anomaly and the source of today's improvement.

### Trade-by-trade review
*(entry = plan/signal price for STOP/TP rows, real Alpaca fill for EOD_FLATTEN rows per IMP-005)*
| # | Sym | Entry (ET) | Exit (ET) | Conf/type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|-----------|------|-----|-----------|
| — | **NVDA** | 09:30:26 (attempt) | — | — | **REJECTED** | **$0 (missed)** | **Bracket 422** (`stop_loss.stop_price must be <= base_price - 0.01`, base_price **195.02**): NVDA gapped **DOWN** between the signal bar and submission, so the stop (anchored ~1.5% below the higher signal close) landed at/above the live 195.02. Entry silently lost; no `signals`/`trades` row. **Mirror image of AMD's 06-30 up-gap 422.** → IMP-009. |
| 105 | ENPH | 09:32:51 @50.37 | 09:38:26 @48.74 | 73.87 BOTH | **STOP** | **−$47.84** (−1.85%) | **The day's only loss.** BOTH breakout broke 50.2775, filled tight (+0.18%), fully reversed and stopped in ~6 min. Textbook **false breakout** — the STOP bucket (all-time PF 0.01) that IMP-006 proved is the entire leak. Same failure mode as 06-26/06-15 ENPH. |
| 106 | SE | 09:36:08 @96.25 | 09:49:52 @98.46 | 64.81 MA | **TAKE_PROFIT** | **+$60.30** (+2.24%) | Clean MA breakout, hit TP in ~14 min. Day's best. SE redeemed its lone 06-12 loss on the risk-on tape. |
| 107 | MSFT | 09:49:03 @375.81 | 10:42:42 @384.28 | 60.03 MA | **TAKE_PROFIT** | **+$58.52** (+2.22%) | Low-conf MA (60.0) that hit TP — MSFT's first winner of incubation after a long zero/negative history. Reinforces the inverted conf→quality read (IMP-004). |
| 108 | AAPL | 09:55:41 @291.32 | 15:56:53 @295.14 | 60.48 MA | EOD_FLATTEN | +$34.40 (+1.31%) | Low-conf MA; rode the green tape +1.31%, held to flatten (never hit TP). Third straight green AAPL session. |
| 109 | GOOGL | 09:59:56 @358.65 | 15:56:54 @361.48 | 72.83 BOTH | EOD_FLATTEN | +$42.41 (+0.79%) | **GOOGL signaled (BOTH) and WON** — broke 357.28, trended +0.79% to flatten. **The 0W3L park watch is resolved: it signaled + won → trigger does NOT fire, GOOGL stays.** |
| 110 | AMZN | 10:45:03 @241.67 | 15:57:04 @242.09 | 63.32 MA | EOD_FLATTEN | +$4.59 (+0.17%) | Low-conf MA entered mid-morning; near-scratch green drift to flatten. Noise. |

### What worked / what didn't
- **Worked — directional-with-the-tape paid a third straight session.** On the risk-on continuation the breakout/MA setups followed through: 2 clean TPs (SE, MSFT), 3 green EOD flattens, one franchise-adjacent BOTH win (GOOGL). Same green-tape behavior as 06-29/06-30 — reinforces that **tape direction is the discriminator** (the #1 strategy lever), not any per-trade score.
- **Worked — every risk/measurement fix held.** IMP-002 (no-overnight: 0 open on Alpaca, retry-until-confirmed flatten fired exactly as designed), IMP-003/IMP-005 (day gross == broker equity move to the penny), IMP-004/IMP-006 (low-conf MA book carried the day: SE/MSFT/AAPL/AMZN all conf 60–65 and all green — the "raise the MA floor" candidate stays refuted). IMP-008 caused **no false skips** (all 6 real entries filled; fills ≤0.12% off signal).
- **Didn't — one false-breakout STOP (ENPH) was the whole loss**, exactly the STOP/false-breakout bucket (PF 0.01) that is the entire all-time leak. No one-day fix: every *per-trade* discriminator (confidence IMP-004, volume 06-26, extension IMP-007) is refuted; the lever is the market-regime gate (deliberate replay build, not a post-close tweak).
- **The real defect is a MISSED entry, not a loss: NVDA's bracket 422** — the exact down-gap twin of the AMD up-gap 422 that IMP-008 was built for yesterday. IMP-008 only guarded the *up* direction; NVDA gapped *down* so the stop leg went above the live price and Alpaca rejected the whole bracket. Highest-impact, capital-relevant, data-justified issue today → IMP-009.

### Lessons & improvement candidates (ranked)
1. **(ACTED → IMP-009) Symmetric stale-signal / gap guard.** IMP-008 skipped entries where the live price ran > `MAX_ENTRY_SLIPPAGE_PCT` (1.0%) **above** the signal close (up-gap → TP 422). NVDA today is the **mirror**: it gapped **down** ~1.5% between signal and submission, so the stop (anchored ~1.5% below the signal close) landed at/above the live 195.02 → `stop_loss.stop_price must be <= base_price - 0.01` 422 → entry silently lost (no `signals`/`trades` row, invisible to analytics — same as AMD 06-30). Fix: the guard now skips when the live price moves > 1.0% from the signal close in **either** direction (`abs(slip) > MAX_ENTRY_SLIPPAGE_PCT`), with a direction-aware `stale_signal_gap_up/down` reason logged. Also catches the shallower (1.0–1.5%) down-gap that Alpaca *accepts* but that compresses the stop to a hair-trigger while the breakout premise has already failed (price back below the level). Recorded fills are ≤0.5% off the signal both ways, so no false skips. **A NEW skip (tightening) — NO risk limit widened** (paper endpoint, MAX_RISK_PCT 2.0, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all unchanged).
2. **(STANDING #1 lever) Intraday market-regime entry gate** — the real strategy work, unchanged. ENPH's false-break STOP today (the only loss) is the STOP bucket the gate targets; but it needs the deliberate multi-run SPY/QQQ-VWAP replay build, not a one-day change. Every per-trade discriminator remains refuted.
3. **(Note, no action)** Missed/rejected entries still produce no `signals` row, so they're invisible to the report/analytics — only `bot.log` shows them (IMP-009 now logs a clean `ENTRY SKIPPED … stale_signal_gap_down` line for the class it prevents, but a genuine broker-side 422 for another reason would still be log-only). If rejections become frequent, persist skipped attempts. Backlog note, unchanged from 06-30.

### Notes for pre-market research
- **NVDA** — the bot tried to enter it first (09:30:26) but the bracket 422'd on an open **gap-down** (base_price 195.02). Now handled by IMP-009 as a deliberate down-gap skip. Order-mechanics, **not** a name problem — NVDA remains a high-quality watchlist name. No park.
- **GOOGL** — **signaled (BOTH, conf 72.83) and WON (+$42.41)** today, its first live signal in weeks. The long-standing "GOOGL 0W3L → one more loss consolidates to GOOG-only" watch is **RESOLVED in GOOGL's favor** — it signaled + won, so the park trigger did NOT fire. **Drop the GOOGL park watch**; keep both GOOG and GOOGL.
- **ENPH** — genuine BOTH breakout (conf 73.87) that fully round-tripped −1.85% to a stop in ~6 min: another clean false breakout (its recurring failure mode, 06-15/06-26). Name behaves with the regime; no park.
- **SE / MSFT** — both hit TP on low-ish conf (64.8 / 60.0) MA signals; MSFT's first winner of incubation. The low-conf MA book (SE/MSFT/AAPL/AMZN) carried the day — the MA-floor-raise candidate stays refuted. Keep all.
- **NFP Thu 07-02, market closed Fri 07-03** — thin, event-driven back half; do NOT add names into the payrolls print. Equity **$8,449.36 (−15.5%)**, **$949 above** the −25% flag — best cushion of incubation; protect it into the labor data.

---

## 2026-07-02 — Daily Review

### Stats
- Trades: 4 closed (**0W / 3L + 1 scratch**), win rate 0%. Ends the 3-day green run.
- Net P&L: **−$148.24** (day −1.754%). Equity close **$8,301.08** (from $8,449.32 open; −17.0% from $10K, **$801 above** the −25% / $7,500 review flag). DB gross == broker equity move (8449.32→8301.08 = −$148.24) **to the penny** — books tied.
- Avg loser −$49.41 (SE −99.72, GOOGL −35.58, CRM −12.94); BAC scratch $0.00 (real fills 58.67 in / 58.67 out — genuinely flat, **not** an IMP-003/005 fallback). No winners → profit factor 0.
- Circuit breaker NOT tripped (−1.75% << −8.0% halt). Service active all session, no errors. **0 open positions on Alpaca**, no overnight carry (all 3 non-stop names EOD-flattened 15:57 ET; IMP-002 held).
- **NFP-day open-fade** — exactly the whipsaw/open-fade regime the pre-market research flagged into the payrolls print. All 4 entries in the first ~2h (09:30–11:45 ET); nothing followed through.

### Trade-by-trade review
- **GOOGL** #111 — MA, conf 62.2. In 09:30:25 @**360.84** (real fill; DB had recorded the plan price 361.19 — see IMP-010), out 11:44:52 @355.76 (**STOP**), −$35.58 (−1.41%). Opened at the bell, faded straight down to the ~1.5% stop over 2h. MA-only open-fade, no breakout level. Root cause: **regime (open-fade), not stop placement** (stop was the normal ATR/1.5%-floor distance).
- **SE** #112 — BOTH, conf 73.2, broke_level 103.275. In 09:31:46 (submitted) but **filled 09:35:10 @104.73** (a ~3.4-min market-fill lag on the fast open → filled **1.40% above** the broken level), out 15:57:21 @102.88 (**EOD_FLATTEN**), **−$99.72 (−1.76%, 67% of the day's loss)**. Classic **false breakout**: reversed back below 103.275 and bled all session, never hitting the 102.05 stop → carried to the flatten. Root cause: **false breakout + extended/late fill** (chased 1.4% above the level; the >1.0%-extension bucket is the worst all-time, PF 0.09).
- **CRM** #113 — MA, conf 60.9. In 09:41:45 @165.98, out 15:57:21 @165.22 (**EOD_FLATTEN**), −$12.94 (−0.46%). Low-conf MA drift; never trended, small controlled bleed to the flatten. Root cause: **no-follow-through regime**.
- **BAC** #114 — MA, conf 62.9. In 11:44:58 @58.67 (entered the slot GOOGL vacated when it stopped 11:44:52), out 15:57:22 @58.67 (**EOD_FLATTEN**), **$0.00 scratch**. Verified against Alpaca: buy and sell both filled 58.67. Root cause: **dead/no-follow-through regime** (flat all afternoon).

### What worked / what didn't
- **Worked — every risk/measurement invariant held.** No overnight carry (0 on Alpaca), retry-until-confirmed flatten fired at 15:57, circuit breaker correctly dormant at −1.75%, day gross tied to the broker equity move to the penny. Pre-market call was right: it flagged NFP open-fade risk and did NOT add names into the print — the loss was regime, not a bad watchlist.
- **Didn't — the tape faded the open and nothing trended.** 3 of 4 entries were the STOP/false-breakout-and-drift family the all-time books already indict (STOP bucket PF 0.01; EOD_FLATTEN drift on names that never followed through). SE's extended 1.4%-above-level chase was the single worst trade — the >1.0%-extension bucket (PF 0.09) biting again, though a hard extension cap stays **refuted** (IMP-007: the tight ≤0.5% bucket is also net-negative; extension doesn't cleanly discriminate).
- **The real defect found today is a MEASUREMENT bug, not a loss: GOOGL's stored `entry_price` was the stale plan/signal price (361.19), not the real bracket fill (360.84).** Its P&L (−35.58) was already computed off the real fill, so the row *didn't reconcile* (entry×exit×qty ≠ realized_pl) and the by-entry-extension analytic (IMP-007) would mis-measure every slipped STOP/TP breakout. Highest-impact, capital-safe, data-justified issue today → **IMP-010**.

### Lessons & improvement candidates (ranked)
1. **(ACTED → IMP-010) STOP/TP path now corrects `entry_price` to the real bracket fill.** `exits.build_exit_record` already prices P&L off the parent order's `filled_avg_price`, but `logbook.record_exit` forwarded only exit_price/pl/reason to `update_trade_exit` — never the real entry — so the `trades.entry_price` column kept the plan price for STOP/TP exits (GOOGL 361.19 vs fill 360.84). This is the **STOP/TP analog of IMP-005** (which corrected only the EOD_FLATTEN path); it closes the last hole in the fill-accuracy program (IMP-003 exit-flatten, IMP-005 entry-flatten, now IMP-010 entry STOP/TP). Fix: `record_exit` forwards `entry_price=exit_record.get("entry_price")`. Pure measurement-integrity — makes rows reconcile and the extension analytic truthful. **NO entry logic, NO sizing, NO stop, NO risk limit touched** (paper endpoint, MAX_RISK_PCT 2.0, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all unchanged). Also backfilled today's GOOGL row (361.19→360.8429; P&L unchanged, now reconciles).
2. **(STANDING #1 lever) Intraday market-regime entry gate** — unchanged, still the real strategy work. Today (NFP open-fade, 3/4 no-follow-through) is textbook for it: `regime_ok=True` fired on all 4 despite a choppy fade tape, so the current regime flag does NOT filter no-follow-through days. Needs the deliberate multi-run SPY/QQQ-VWAP/breadth replay build, not a one-day tweak. Every *per-trade* discriminator (confidence IMP-004, volume 06-26, extension IMP-007) remains refuted; the lever is market-level.
3. **(Watch, no action) SE's ~3.4-min market-order fill lag** on the fast open pushed the fill 1.40% above the broken level. The IMP-008/009 stale-signal guard checks live-vs-signal-close **at submission**, not fill latency after submission, so it didn't catch this. One occurrence, likely a paper-fill/data artifact — do not act; re-flag only if a pattern of multi-minute market fills recurs (would inflate realized entry-extension vs plan).

### Notes for pre-market research
- **Regime, not names.** Today's −$148 was an NFP-day open-fade with no follow-through — every loser behaved with the tape, none is a name defect. No park triggers matured. All 4 traded names (GOOGL/SE/CRM/BAC) are fine watchlist members.
- **SE** — the day's worst (−$99.72): a genuine BOTH breakout (conf 73) that filled 1.4% above the level (~3.4-min fill lag), reversed below it, and bled to the flatten. Recurring false-breakout-then-drift mode; behaves with the regime, **no park**. Watch whether SE keeps filling late on fast opens.
- **GOOGL** — MA open-fade stop (−$35.58). Park watch already CLOSED (07-01 win); keep both GOOG and GOOGL. No new concern beyond regime.
- **CRM / BAC** — low-conf MA, no follow-through (−$12.94 / scratch). Nothing name-specific; dead-tape drift/flat.
- **Market CLOSED Fri 07-03; next session Mon 07-06.** Review how the NFP print + long-weekend tape resolved: if the fade regime persists, megacap/MA open-fades (today's GOOGL, prior AAPL) stay the risk — the #1 strategy-lever regime gate. If chip/AI leadership resumes, on-list semis are the vehicles. Equity **$8,301.08 (−17.0%)**, **$801 above** the −25% ($7,500) flag — cushion trimmed by one fade day but intact; protect it.

---

## 2026-07-03 — Daily Review

### Stats
- **No trades today — US market CLOSED (Independence Day observed).** July 4 2026 falls on a Saturday, so the NYSE/Nasdaq holiday is observed **Fri 07-03** (this was pre-declared in the 07-02 review: "Market CLOSED Fri 07-03; next session Mon 07-06"). `daily_summary` ends at 07-02; **0 rows in `trades` touch 07-03** (verified: entry_time/exit_time on 2026-07-03 → count 0); journal has **no entries today**; the service has been running since the **07-02 21:33:52 UTC** restart (no pre-market restart today — the market was closed and the `uswisbot-premarket` cron itself no-op'd/failed on an expired Claude OAuth token, unrelated to the trading service).
- Equity **$8,301.08 (−17.0% YTD)**, carried unchanged from the 07-02 close (no trading on a closed market → no P&L, no equity move). **$801 above** the −25% ($7,500) strategy-review flag.
- **Positions: necessarily flat.** The 07-02 15:57 flatten confirmed 0 open on Alpaca (IMP-002 held its 9th+ session), and no order could be placed today → 0 open, **no naked-overnight carry into the 3-day weekend.** ✅ (Live Alpaca re-query could not run this session — the sandboxed-HTTP path was permission-gated in this unattended run — but with zero possible trades the broker state is unchanged from the 07-02 flat book; nothing to reconcile.)
- Circuit breaker not engaged (no trading). Service **active** all day; no in-session errors.

### Trade-by-trade review
None — market closed. Nothing to root-cause at the trade level.

### What worked / what didn't
- **Nothing to fault:** the bot correctly did nothing on a closed market — no spurious entries, no errors, no stranded positions. The book is flat going into the long weekend, exactly as the no-overnight design intends.
- **Root cause of zero trades:** calendar (federal holiday observed), not a strategy/gate/watchlist defect. This is the expected and desired outcome; **no improvement is warranted by today's (non-existent) data.** Manufacturing a code change here would be overfitting with zero supporting evidence — explicitly declined (same call as the 06-19 Juneteenth holiday).
- IMP-009 (symmetric down-gap slippage guard, 07-01) and IMP-010 (STOP/TP entry_price = real fill, 07-02) remain **pending their first post-ship observation** — both need a live session to confirm (IMP-009: a gap-down open logs `ENTRY SKIPPED … stale_signal_gap_down` instead of a 422; IMP-010: a slipped STOP/TP row stores the real buy fill and reconciles). First test is Mon 07-06.

### Lessons & improvement candidates (ranked)
- **No code change this run.** "Reviewed, no change warranted" — today produced no trade evidence, and the capital-protection invariants + recent fixes are all in place. Acting today would be a random/unjustified change.
- Standing candidates carried (NOT acted on today, awaiting live data): (1) **verify IMP-009 & IMP-010 in production Mon 07-06** (first live sessions since they shipped); (2) **the #1 strategy lever remains the intraday market-regime entry gate** (long-only when SPY/QQQ above an intraday MA/VWAP) — the deliberate multi-run `scripts/replay.py` build, unchanged; every per-trade discriminator (confidence IMP-004, volume 06-26, entry-extension IMP-007) is refuted, and the STOP/false-breakout bucket (all-time PF 0.01, −$3,072) is the entire leak the gate targets; (3) the report's own verdict still reads **NEEDS WORK** (expectancy not positive; false-breakout rate 58.3%) — the regime gate is the path to flip it, not a post-close tweak.

### Notes for pre-market research
- **Holiday — no new trade-level observations.** Watchlist state is exactly as the prior pre-market curation left it (last known: 25–26 active; MU re-enabled 06-25; C/JPM/WPM parked; GOOGL park watch CLOSED 07-01 after it signaled + won).
- **Mon 07-06 is the first live session since IMP-009/IMP-010** — on any gap-down open, confirm the guard logs a clean `stale_signal_gap_down` skip (no 422); on any slipped STOP/TP, confirm the stored `entry_price` matches the Alpaca buy fill and the row reconciles.
- **Regime is the watch item.** 07-02 was an NFP open-fade (3/4 no-follow-through); review how the post-NFP + long-weekend tape resolves Monday. If the fade regime persists, megacap/MA open-fades (GOOGL/AAPL) stay the risk; if chip/AI leadership resumes, on-list semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) are the vehicles. TSLA remains the franchise earner (4W0L, +$375 14d).
- **Infra note (not a bot defect):** the `uswisbot-premarket` Claude routine failed this morning on an expired Claude OAuth token (credentials refreshed 07-03 17:24 UTC). It does not affect the trading service (which trades autonomously), but the token expires ~2026-07-04 01:24 UTC — re-login before Monday's pre-market cron so the 07-06 premarket routine runs.
- Equity **$8,301.08 (−17.0%)**, **$801 above** the −25% ($7,500) flag — protect the cushion into the reopen.

---

## 2026-07-06 — Daily Review

### Stats
- Trades: **5 closed (2W / 3L)**, win rate **40%**. First live session since the 07-03 holiday.
- Net P&L: **−$70.51** (day **−0.849%**). Equity close **$8,230.53** (from $8,301.04 open). **Alpaca equity $8,230.53 == DB to the penny**; **0 open positions on Alpaca — no overnight carry**; today's orders 10 filled / 7 canceled (bracket legs), **no rejections/422s**. **−17.7% YTD**, **$730 above** the −25% ($7,500) review flag.
- Avg winner **+$33.55** (GOOGL +44.62, META +22.48); avg loser **−$45.87** (INTC −74.16, SE −55.64, COST −7.81). Profit factor (day): 67.10 / 137.61 = **0.49**.
- Exit reasons: **1 TAKE_PROFIT** (GOOGL), **2 STOP** (SE, INTC), **2 EOD_FLATTEN** (COST −, META +). Circuit breaker NOT tripped (−0.85% vs −8.0% halt). Service active all session (since 07-02 21:33 UTC restart); no in-session errors. IMP-002 flatten held: 15:56 "incomplete — 2 still open (COST/META)", retried, both flat by 15:57.
- **IMP-010 CONFIRMED live (first post-ship STOP rows):** INTC #118 and SE #117 (STOP) store the real Alpaca buy fill and reconcile — INTC entry **126.4923** (plan/log price was 126.91), (123.64−126.4923)·26 = −74.16 == stored; SE (103.05−105.19)·26 = −55.64 == stored. The 07-02 GOOGL forward-path fix works on live STOP exits.
- **IMP-009 NOT triggered (still pending):** no entry gapped past the 1.0% slippage cap today (fills all within band), so the down-gap `stale_signal_gap_down` skip path has not yet fired. No false skip either — all 5 real entries filled.

### Trade-by-trade review
*(entry = real bracket fill per IMP-005/010; "plan" = signal-bar close logged at submit)*
| # | Sym | Entry (ET) | Exit (ET) | Conf/type | Exit | P&L | Root cause |
|---|-----|-----------|-----------|-----------|------|-----|-----------|
| 115 | GOOGL | 09:30:09 @361.44 (plan 359.69) | 15:31:49 @367.81 | 60.1 MA | **TAKE_PROFIT** | **+$44.62** (+1.76%) | Low-conf MA at the bell; rode the tech-led relief bounce to TP in ~6h. Day's best; the low-conf MA book earning again. |
| 116 | COST | 09:41:43 @953.10 | 15:57:03 @949.19 | 62.2 MA | EOD_FLATTEN | −$7.81 (−0.41%) | Low-conf MA drift; never trended, small controlled bleed to the flatten. Noise. |
| 117 | SE | 09:59:35 @105.19 (plan 104.72) | 10:30:11 @103.05 | 63.5 MA | **STOP** | **−$55.64** (−2.03%) | **False breakout / open-fade** — MA-only, faded straight to the ~1.5%-floor stop in ~30 min. SE's recurring mode (06-12, 07-02 −$99.72). STOP bucket (all-time PF 0.01). |
| 118 | INTC | 10:35:54 @126.49 (plan 126.91, broke 126.66) | 13:21:47 @123.64 | 74.3 BOTH | **STOP** | **−$74.16** (−2.25%) | **Day's worst + the biggest loss.** BOTH breakout that **filled 0.13% BELOW its broken level 126.66** (premise already failing at fill), reversed and stopped over ~2.75h. INTC's first loss (was 2W0L +$176). Semis rebound faded intraday. STOP/false-breakout bucket. |
| 119 | META | 13:22:43 @595.03 | 15:57:24 @600.65 | 63.7 MA | EOD_FLATTEN | +$22.48 (+0.94%) | Low-conf MA entered the slot INTC vacated; drifted up +0.94% with the tape to the flatten. |

### What worked / what didn't
- **Worked — every risk/measurement invariant held.** 0 open on Alpaca (no overnight carry), retry-until-confirmed flatten fired 15:56→15:57, circuit breaker correctly dormant at −0.85%, day gross tied to the broker equity move to the penny, no 422/rejection. **IMP-010 confirmed on its first live STOP rows** (INTC/SE reconcile off the real fill). The low-conf MA book paid the winners (GOOGL TP, META drift) — the "raise the MA floor" candidate stays refuted.
- **Didn't — two false-breakout STOPs (SE, INTC) were the entire loss** (−$129.80; the winners + COST drift net +$59.29). Both are the STOP/false-breakout bucket (all-time PF 0.01) — the one leak. INTC filled *below* its broken level; SE was an MA open-fade. `regime_ok=True` fired on all 5, so the existing ADX/long-MA-stack regime flag did NOT filter either loser.
- **No NEW per-trade discriminator today.** INTC filling below its `broke_level` looked promising as a "breakout already failed at fill" skip, but the full book has only **2** such trades ever (MU +20.27 WON, INTC −74.16) → **non-discriminating, refuted** (n=2, mixed). Confidence (IMP-004), volume (06-26), extension (IMP-007) all remain refuted. **The sizing-table refutation was re-checked with fresh data and STANDS:** post-06-15 the ≥66-confidence book is **+$142.63 / PF 1.22** (carried by TSLA/INTC winners) — high-conf does NOT lose at scale on the live regime, so the `CONFIDENCE_RISK_TABLE` must NOT be flattened (would de-size the profitable winners). Do not reopen.

### Lessons & improvement candidates (ranked)
1. **(ACTED → IMP-011, measurement-only) First quantified read of the #1 lever — the market-regime entry gate.** Every per-trade score is refuted, so the only lever is market-level (backlog ★). Today's split is textbook: the winners (GOOGL/META) drifted up with the tech-led relief tape while the breakouts (SE/INTC) false-broke on the intraday chop. Built the FIRST measurement (analytics.by_market_regime + classify_index_regime + standalone scripts/regime_analysis.py; **no engine/sizing/risk change**): tag each closed trade with the SPY intraday regime (SPY close vs EMA9 on 5-min bars) at its entry minute and bucket P&L. **Result — the naive gate's edge is REGIME-DEPENDENT:** *all-time* it has NO edge (bullish PF 0.56 vs bearish PF 0.71 — bearish is even slightly less-bad, because the pre-fix 06-08→06-12 blowups dominate and were regime-agnostic), but on the **post-06-15 live regime it DOES separate: bullish 43 trades +$339.17 / PF 1.45 vs bearish 13 trades −$5.33 / PF 0.98**, and skip-bearish keeps the +$339 winners while removing a net-negative choppy tail. This is the first positive support for the ★ gate — but the bearish sample is small (n=13) and EMA9 is only one proxy (VWAP/QQQ/first-N-minutes untested), so it is **NOT yet a live change**; it graduates to a replay-validated engine IMP once the post-fix bearish sample grows and the proxy is chosen. Measurement-first, exactly like IMP-004/006/007.
2. **(STANDING #1 lever) Intraday market-regime entry gate → now has its measurement.** The deliberate multi-run build continues: (a) grow the post-06-15 sample, (b) compare EMA9 vs VWAP vs QQQ vs "skip first N min on a red open" as the regime proxy in `scripts/regime_analysis.py` / `scripts/replay.py`, (c) only then gate the engine (long-only when bullish) as a *tightening*. SE/INTC today are the exact false-breakout STOPs the gate targets.
3. **(Note, no action)** INTC filled below its broken level (breakout premise failed at submission). Interesting but n=2 and non-discriminating — parked, re-flag only if a pattern of below-level breakout fills separates as losers with a real sample.

### Notes for pre-market research
- **INTC** — the day's worst (−$74.16), its first loss (was 2W0L +$176). A BOTH breakout that filled *below* its broken level and faded with the intraday semis reversal — behaves with the chip tape, **not** a name defect. Still a book anchor; **no park**. Watch whether the semis rebound holds or keeps fading intraday.
- **SE** — −$55.64 MA open-fade, its recurring false-breakout mode (06-12, 07-02 −$99.72). Now **1W3L** on the incubation. Behaves with the regime; small sample, liquid ADR — **no park yet**, but it is the most persistent single-name drag — re-flag if it reaches ~1W4L with the same open-fade signature.
- **GOOGL / META** — both low-conf MA winners riding the tech-led relief bounce (GOOGL TP +$44.62, META +$22.48). Low-conf MA book keeps paying; keep both GOOG/GOOGL and META.
- **COST** — low-conf MA drift, −$7.81 noise; nothing name-specific.
- **Regime read for tomorrow:** today was a mixed relief bounce — MA drifters that went WITH the tech bid won, breakouts that needed follow-through false-broke on the chop. The SPY-EMA9 regime measurement (IMP-011) says post-fix **bullish-tape entries are the profitable ones** — if SPY opens/holds below its short intraday EMA, expect more SE/INTC-style false breakouts. Q2 earnings season is ramping — check the intraday-earnings calendar and park any on-list name reporting during hours. Equity **$8,230.53 (−17.7%)**, **$730 above** the −25% flag — protect the cushion.

---

## 2026-07-07 — Daily Review

### Stats
- Trades: **6 closed (1W / 5L)**, win rate **16.7%**.
- Net realized P&L: **−$8.22** (day **−0.100%**) — essentially a scratch; one TP (META +$85.74) nearly offset all five losers (−$93.96 combined). Equity close **$8,222.28** (from $8,230.53 open; Alpaca last_equity 8230.53 → equity 8222.28 = **−$8.22 broker truth, matches to the penny**). **−17.8% YTD**, **$722 above** the −25% ($7,500) strategy-review flag.
- Avg winner **+$85.74** (META, the only win); avg loser **−$18.79** (AMZN −43.97, TSLA −20.23, AAPL −16.56, AMZN −10.98, GOOGL −2.22). Profit factor (day): 85.74 / 93.96 = **0.91**.
- Exit reasons: **2 STOP (TSLA/AMZN), 1 TAKE_PROFIT (META), 3 EOD_FLATTEN (GOOGL/AAPL/AMZN)**. Circuit breaker NOT tripped (−0.10% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight** (broker `open_position_symbols()` → empty). ✅ IMP-002 held again (the 15:56 flatten reported "3 still open" → retried 15:57/15:58 → all confirmed flat).
- **IMP-008 fired correctly:** COST was **skipped** at 09:30:11 (`live 965.84 = +1.62% vs signal 950.48` → stale-signal gap-up; the bracket TP would have been mispriced). No 422, no missed-fill silent loss. Fill accuracy: entries/exits booked off the real Alpaca fills (IMP-003/005/010) — day gross ties to the broker move to the penny. Service active since the 07-06 21:40 UTC restart; no in-session errors.

### Trade-by-trade review
*(entry = real bracket fill per IMP-005/010; "plan" = signal-bar close logged at submit; regime = SPY/QQQ EMA9 at entry)*
| # | Sym | Entry (ET) | Exit (ET) | Conf/type | Exit | P&L | Regime SPY/QQQ | Root cause |
|---|-----|-----------|-----------|-----------|------|-----|----------------|-----------|
| 120 | TSLA | 09:30:11 @416.82 (plan 419.79) | 09:51:39 @413.45 | 61.5 MA | **STOP** | **−$20.23** (−0.81%) | bear/bear | MA open-fade; broke to the ~0.8% stop in 21 min. STOP/false-breakout bucket. |
| 121 | GOOGL | 09:31:17 @367.86 (broke 367.51) | 15:58:06 @367.70 | 75.0 BOTH | EOD_FLATTEN | −$2.22 (−0.04%) | bear/bear | Tight breakout (0.10% ext), never trended, flat scratch to the flatten. Noise. |
| 122 | META | 09:31:18 @609.73 (broke 601.89) | 14:14:11 @619.26 | 72.5 BOTH | **TAKE_PROFIT** | **+$85.74** (+1.56%) | **bear/bear** | **Day's only win.** BOTH breakout (mom 0.97), ran to TP over ~4.7h — a clean trend **in a BEARISH index regime** (see counterexample below). |
| 123 | AMZN | 09:52:30 @247.68 (plan 247.42) | 11:08:59 @243.68 | 61.3 MA | **STOP** | **−$43.97** (−1.61%) | **bull/bull** | **Day's worst loss** — MA open-fade in a BULLISH index regime; stopped in ~76 min. STOP bucket. |
| 124 | AAPL | 11:11:48 @313.28 | 15:57:04 @311.21 | 60.6 MA | EOD_FLATTEN | −$16.56 (−0.66%) | bear/**bull** | Low-conf MA drift, faded to the flatten. The one trade SPY/QQQ regimes DISAGREE on. |
| 125 | AMZN | 14:22:43 @246.37 (broke 245.87) | 15:58:07 @245.87 | 70.9 BOTH | EOD_FLATTEN | −$10.98 (−0.20%) | bull/bull | **Same-day re-entry** of AMZN after #123 stopped (STOP 11:09 → re-entry 14:22, 3h13m > 30-min cooldown, allowed by design); drifted to a small-loss flatten. |

### What worked / what didn't
- **Worked — every risk/measurement invariant held on a scratch day.** 0 open on Alpaca (no overnight carry), retry-until-confirmed flatten cleared all three stragglers (15:56→15:58), circuit breaker dormant at −0.10%, day gross tied to the broker equity move to the penny, no 422 (IMP-008 skipped the COST gap-up cleanly), STOP rows reconcile off the real fill (IMP-010). The BOTH breakout winner (META TP) again carried the day.
- **Didn't — two false-breakout STOPs (TSLA, AMZN #123) were the whole loss** (−$64.20; the other 3 were flatten drift/scratch −$29.76, offset by META +$85.74). Both were MA-signal open-fades → the STOP/false-breakout bucket (all-time PF 0.01), the one persistent leak. `regime_ok=True` on all 6 (the per-symbol ADX/long-EMA gate never filtered a loser — expected: `regime_ok=False` zeroes confidence, so no such trade ever reaches the book; the flag is a per-SYMBOL trend gate, NOT a market gate).
- **Didn't — the AMZN same-day re-entry (#125) lost again** (−$10.98) after #123's −$43.97 STOP. Combined AMZN −$54.95. The 30-min re-entry cooldown had long expired (3h13m gap), so this was allowed by design; small enough not to be today's story, but re-entering a name that already stopped the same day is worth watching if it recurs at size.
- **No NEW per-trade discriminator.** Confidence (IMP-004), volume (06-26), extension (IMP-007), below-level-fill (07-06) all remain refuted. The lever is still market-level (backlog ★).

### Lessons & improvement candidates (ranked)
1. **(ACTED → IMP-012, measurement-only) Today is a COUNTEREXAMPLE to the naive skip-bearish market-regime gate — and cross-proxy analysis shows its edge is proxy-dependent.** The only winner (META +$85.74 TP) was tagged **BEARISH** under both SPY and QQQ, while the worst loser (AMZN −$43.97 STOP) was tagged **BULLISH**. So on today's tape skip-bearish would have **removed +$46.73 of net-positive P&L and kept −$54.95** — actively harmful. Extended `scripts/regime_analysis.py` to measure the regime under **two proxies (SPY + QQQ, EMA9)** side by side + added a `--since YYYY-MM-DD` window and a pure `analytics.regime_proxy_agreement` helper (**no engine/sizing/risk change**). **Result on the post-06-15 live regime:** under **SPY** bullish PF 1.43 vs bearish PF 0.99 (skip-bearish removes only −$2.57 — barely helps), but under **QQQ** bearish is *profitable* (PF 1.22, +$79.14) so skip-bearish would REMOVE +$79.14 — and the two proxies **disagree on 18% of trades (51/62 agree)**. This **tempers IMP-011's SPY-only optimism** (which read bullish 1.45 vs bearish 0.98): the naive EMA9 gate's edge does NOT survive the proxy swap, so it is **NOT ready to ship**. Measurement-first (IMP-004/006/007 pattern).
2. **(STANDING #1 lever) Intraday market-regime entry gate.** Next steps refined by today: the raw "skip-bearish under SPY-EMA9" gate is refuted as proxy-fragile — a real gate needs (a) a regime definition robust across proxies (test VWAP and "skip first N min on a red open" next, not just EMA), (b) a bigger post-06-15 bearish sample, (c) replay validation, before any engine tightening (long-only when bullish). Re-run `scripts.regime_analysis --since 2026-06-15` each review and watch whether SPY/QQQ converge.
3. **(Note, no action) Same-day re-entry after a stop** (AMZN today): 30-min cooldown allowed it after 3h. Single small instance (−$10.98); park the idea of a longer/loss-aware re-entry cooldown until a real recurring cost appears — do not overfit one AMZN.

### Notes for pre-market research
- **META** — day's only winner (+$85.74 TP), a clean BOTH breakout that trended all afternoon; franchise-quality behavior. Keep top-of-list.
- **AMZN** — worst name today: MA open-fade STOP (−$43.97) then a same-day re-entry that also bled (−$10.98), −$54.95 combined. Both were open/early entries that faded; behaves with the tape, no name defect — **no park**, but note it was the day's drag.
- **TSLA** — MA open-fade STOP (−$20.23) in 21 min; a fast false start, small controlled loss. No park.
- **COST** — **skipped** by the IMP-008 stale-signal guard (gapped +1.62% between signal and fill); not a watchlist issue, the guard did its job. Watch whether COST keeps gapping past the open (recurring gap-and-go that the bot correctly declines).
- **GOOGL/AAPL** — low-conf drifters, scratch/small losses; nothing name-specific.
- **Regime read for tomorrow:** near-scratch mixed tape; the winner trended in a *bearish* index regime while the biggest loser stopped in a *bullish* one → the naive index-EMA regime gate would NOT have helped today (IMP-012). Don't expect a market filter to save false-breakout STOPs yet. Equity **$8,222.28 (−17.8%)**, **$722 above** the −25% flag — cushion intact.

---

## 2026-07-08 — Daily Review

### Stats
- Trades: **8 closed (4W / 4L)**, win rate **50.0%**. Green day — and the **first live session under IMP-013** (break-even@+0.5R / 1R-trail@+1R, shipped last night).
- Net realized P&L: **+$93.02** (day **+1.13%**). Equity close **$8,315.27** (from $8,222.25 open; **+$93.02 broker truth — matches to the penny**, last_equity confirms). **−16.8% YTD**, **$815 above** the −25% ($7,500) strategy-review flag (cushion widened).
- Avg winner **+$34.45** (ENPH +61.76, NVDA +60.84, WMT +14.40, NVDA +0.79); avg loser **−$11.19** (QCOM −37.08, QCOM −7.38, XOM −0.19, AVGO −0.12). **Three of the four "losers" are IMP-013 break-even scratches (−$0.19 / −$0.12 / and NVDA +$0.79)** — the only real loss is QCOM −$37.08.
- Profit factor (day): 137.79 / 44.77 = **3.08**. Exit reasons: **4 STOP** (1 full-1R + 3 IMP-013 break-even), **1 TAKE_PROFIT**, **3 EOD_FLATTEN**.
- Circuit breaker NOT tripped (+1.13% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight** (IMP-002, 10th straight clean session). ✅ Service active all session (since 06:59:15 UTC pre-market restart); journal clean, **0 rejected orders** (no 422 loop), **10 stop-replace orders** (the IMP-013 STOP RAISED chain), 16 filled / 11 canceled.

### Trade-by-trade review
*(entry/exit = real Alpaca fills; orig_stop = plan 1R anchor, kept in trades.stop_price by IMP-013 design; rf = fraction of original 1R retained at a STOP exit)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause / IMP-013 behaviour |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 127 | NVDA | 09:37 @197.36 | 09:50 @197.42 | 61.7 | MA | STOP (rf 1.02) | **+$0.79** | Popped to +0.5R → stop raised to break-even (194.51→197.36); faded back and stopped ~flat. **IMP-013 break-even rescue.** |
| 126 | XOM | 09:36 @141.68 | 12:23 @141.67 | 60.5 | MA | STOP (rf 0.99) | **−$0.19** | Reached +0.5R → stop→entry (139.88→141.68); round-tripped, stopped at break-even. **IMP-013 rescue** (a full 1R would have been ≈−$34). |
| 130 | AVGO | 12:22 @390.04 | 13:46 @390.03 | 79.7 | BOTH | STOP (rf 1.00) | **−$0.12** | BOTH breakout (broke 389.12) that popped +0.5R then fully round-tripped → stop→entry (383.68→390.04). **IMP-013 rescue** — a full 1R here was ≈−$89; the exact false-breakout give-back IMP-013 targets. |
| 129 | QCOM | 10:01 @185.19 | 11:25 @182.10 | 61.0 | MA | STOP (rf 0.00) | **−$37.08** | Faded straight from entry, never reached +0.5R → full original 1R stop (−1.67%). **The one real loss** — classic open-fade false breakout (PF-0.01 bucket); IMP-013 can't help a trade that never gets green (that's the regime gate's job). |
| 131 | NVDA | 12:37 @199.22 | 14:59 @203.90 | 60.6 | MA | TAKE_PROFIT | **+$60.84** | Ran to +1R → trailed 6× (200.01→200.82) then hit TP (+2.35%). **IMP-013 trail rode a clean winner to target.** Day's engine. |
| 128 | WMT | 09:41 @112.46 | 15:57 @113.06 | 64.2 | MA | EOD_FLATTEN | **+$14.40** | Stop raised to break-even (110.68→112.46) but never hit; drifted +0.53% to flatten. Small win. |
| 133 | ENPH | 15:22 @42.55 | 15:57 @42.87 | 83.9 | BOTH | EOD_FLATTEN | **+$61.76** | Late (15:22) high-conf BOTH; small favourable drift (+0.75%), large $ on 193 sh. Flattened green. |
| 132 | QCOM | 14:03 @186.59 | 15:57 @186.34 | 73.6 | BOTH | EOD_FLATTEN | **−$7.38** | Afternoon BOTH breakout (broke 185.88), never reached +0.5R, small drift-down to flatten (−0.14%). |

### What worked / what didn't
- **Worked — IMP-013 VALIDATED cleanly on its first live session.** Broker-confirmed: 10 stop-replace orders fired, **0 rejected** — no 422 "order already replaced" loop (the `resolve_stop_leg` replaced-by chain-following held). Three trades that reached +0.5R and then round-tripped (XOM, NVDA #127, AVGO) were **scratched at break-even** instead of riding to a full 1R stop or the EOD flatten; without IMP-013 those three alone were ≈−$160 of give-back (AVGO's BOTH round-trip ≈−$89 the standout). NVDA #131 trailed +1R→TP for the day's biggest win (+$60.84). The mechanism did exactly what it was built to do; state lived at the broker and survived the pre-market restart.
- **Worked — capital protection + fill accuracy held.** 0 open positions (IMP-002, 10th session); day DB gross (+$93.02) == broker equity move to the penny (IMP-003/005/010); no circuit-breaker, no naked overnight.
- **Didn't — the one real loss (QCOM #129, −$37.08) is the residual leak IMP-013 can't touch.** It faded straight from entry (never green), so break-even never armed → full original 1R stop. This is the PF-0.01 open-fade false-breakout bucket that the **intraday market-regime / breakout-quality entry gate** (standing #1 lever) targets — IMP-013 protects trades that first get to +0.5R; it does nothing for a trade that's red from the first tick.
- **Measurement gap surfaced:** with IMP-013 live, the by_exit_reason "STOP" bucket now blends full-1R losses with break-even rescues — hiding both IMP-013's benefit and the residual real-STOP leak. Fixed as today's IMP-014 (below).

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-014]** De-blend the STOP bucket by stop-protection (fraction of the original 1R retained at exit): **full-1R** (real false-breakout loss) vs **break-even** / **trailed** (IMP-013 rescues). Today: STOP = 1 full-1R (QCOM −$37.08) + 3 break-even (+$0.48). All-time the split is decisive — of 60 STOP exits, **57 are full-1R (−$3,303, PF 0.01)** = the entire leak, and the break-even bucket is the IMP-013 era just beginning. Pure measurement/tooling (the IMP-004/006/007 pattern), no entry/exit/risk logic touched — lets every future review judge IMP-013's real effect and keeps the STOP-PF from being misread as "improving" when it's just blending.
2. **Intraday market-regime / breakout-quality entry gate (standing #1 lever)** — the residual leak (QCOM open-fade) is exactly this. NOT acted on today: it needs the deliberate `scripts/replay.py` multi-run build over post-06-15 history (IMP-011/012 showed the naive EMA9 gate is proxy-fragile SPY-vs-QQQ), not a post-close hack, and today's evidence is IMP-013's validation + measurement, not the gate.
3. **Watch break-even give-back over more sessions:** did any of the 3 break-even scratches (XOM/NVDA/AVGO) recover after the stop? Grow the by_stop_protection sample; if break-even trips too eagerly on names that then run, revisit BREAKEVEN_TRIGGER_R. Single-session — defer, do not tune on n=3.

### Notes for pre-market research
- **IMP-013 works live** — expect fewer full-loss STOPs on trades that get green; watch the daily by_stop_protection split (full-1R vs break-even) as the running scorecard.
- **QCOM** — signaled twice today (MA #129 full-stop −$37; BOTH #132 flatten −$7), both faded from/near entry — the day's weak name; a semi that didn't participate in the Micron-led bid. Not a park (liquid, strategy-fit, open-fade = regime), but note the double open-fade.
- **NVDA** — the day's quality on both sides: a break-even scratch AM (#127) and a clean +1R-trail→TP PM (#131, +$60.84). Semis led (Micron print); NVDA and AVGO both produced tradable breakouts. Keep top-of-list.
- **ENPH** — late (15:22) high-conf BOTH that flattened green (+$61.76); its recurring 0W2 STOP-bucket signature did NOT repeat today. Watch whether it keeps behaving.
- Equity **$8,315.27 (−16.8%)**, **$815 above** the −25% ($7,500) flag — cushion widened, best of incubation. No watchlist change warranted by today.

---

## 2026-07-09 — Daily Review

### Stats
- Trades: **4 closed (3W / 1L)**, win rate **75.0%**. **Best day of incubation** — third green day in four sessions.
- Net realized P&L: **+$217.39** (day **+2.614%**). Equity close **$8,532.59** (from $8,315.20 open; **+$217.39 broker truth — matches to the penny**, daily_summary equity_open/close confirm). **−14.7% YTD**, **$1,033 above** the −25% ($7,500) strategy-review flag (best cushion of incubation).
- Avg winner **+$84.17** (SE +228.54, QQQ +14.87, SPY +9.09); single loser **−$35.11** (TSM). Profit factor (day): 252.50 / 35.11 = **7.19**.
- Exit reasons: **1 TAKE_PROFIT (SE), 3 EOD_FLATTEN (QQQ/TSM/SPY)**. **No STOP exits today** — IMP-013's break-even armed on QQQ/SPY (both drifted up green) and cost nothing; the one loser (TSM) never got green so nothing to protect. Circuit breaker NOT tripped (+2.61% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight** (IMP-002, 11th straight clean session; 15:55 flatten reported "3 still open" → retried → all confirmed flat 15:56). ✅ Service active all session (since 07-08 21:36 UTC restart); journal clean, **0 rejected orders** (no 422), 3 STOP RAISED (SE trail chain), no errors.

### Trade-by-trade review
*(entry/exit = real Alpaca fills; orig_stop = plan 1R anchor kept in trades.stop_price by IMP-013; rf = fraction of original 1R retained at exit; regime = SPY/QQQ EMA9 at entry)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Regime | Root cause / IMP-013 behaviour |
|---|-----|-----------|-----------|------|------|------|-----|--------|-----------|
| 135 | SE | 09:31:25 @105.51 (broke 105.93, ext **−0.40%**) | 09:47:49 @108.44 | **80.13** | **BOTH** | **TAKE_PROFIT** | **+$228.54** (+2.78%) | **bull/bull** | **Day's engine.** BOTH breakout (mom 0.92) that filled *0.40% BELOW* its broken level yet ran to TP in 16 min; stop trailed 3× (rf 3.76). SE — the standing "most persistent single-name drag" (1W3) — **redeemed with the biggest win of incubation.** |
| 134 | QQQ | 09:30:14 @717.91 (plan) | 15:56:34 @722.87 | 63.08 | MA | EOD_FLATTEN | **+$14.87** (+0.69%) | bull/bull | Low-conf MA; stop raised past break-even (700.70→~717.91, rf 1.29), drifted +0.69% and captured at the flatten. Small win. |
| 137 | SPY | 10:07:44 @748.16 (plan) | 15:56:36 @751.19 | 60.81 | MA | EOD_FLATTEN | **+$9.09** (+0.41%) | bull/bull | Low-conf MA; break-even armed (737.22→~748.16, rf 1.28), drifted +0.41% to the flatten. Small win. |
| 136 | TSM | 09:46:47 @442.90 (plan) | 15:56:35 @437.04 | 60.11 | MA | EOD_FLATTEN | **−$35.11** (−1.32%) | bull/bull | **The one loser.** Low-conf MA open-fade; faded from entry, **never reached +0.5R** (rf 0.18) so break-even never armed → IMP-013 can't help. Rode the drift down to the flatten (didn't hit the 435.79 stop). The residual open-fade leak. |

### What worked / what didn't
- **Worked — SE (BOTH breakout) carried the day (+$228.54 TP).** Note SE filled **0.40% below** its broken level (105.51 vs broke 105.93) and still ran straight to TP — a second live data point *reinforcing the 07-06 refutation* that "below-level fill" is non-discriminating (MU won, INTC lost, now SE won big). The trailing stop (IMP-013) rode it (rf 3.76). Without SE the day is +$14.87/QQQ −$35.11/TSM +$9.09/SPY = **−$11.15** — the day's entire edge was one high-conf BOTH breakout TP, the recurring "one BOTH TP carries the book" pattern (TSLA/META/NVDA on prior days).
- **Worked — IMP-013 behaved correctly with zero cost.** QQQ & SPY had stops raised to/past break-even (rf 1.28–1.29) and drifted up to green flattens — the raised stop never tripped, no give-back. No full-1R STOP today at all. State survived the pre-market restart (read off the broker).
- **Worked — every risk/measurement invariant held on the best day.** 0 open on Alpaca (11th clean session), retry-until-confirmed flatten cleared all 3 stragglers 15:55→15:56, circuit breaker dormant, day gross tied to the broker equity move to the penny (IMP-003/005/010), 0 rejected orders.
- **Didn't — TSM was a low-conf (60.1) MA open-fade in a BULLISH index regime.** It faded from entry and drifted −1.32% to the flatten. Crucially it was tagged **bullish under BOTH proxies**, so the naive skip-bearish market-regime gate would NOT have skipped it — today's loser is *another counterexample* to the ★ gate (like 07-07's bullish-tagged AMZN loser). The residual open-fade leak is not cleanly a "bearish-tape" phenomenon.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-015 — measurement/tooling] The ★ skip-bearish market-regime gate is now REFUTED by the grown post-06-15 bearish sample it was explicitly waiting for.** IMP-011 (07-06) gave the gate its "first positive support" at bearish n=13 (−$5.33, PF 0.98); IMP-012 (07-07) tempered it (proxy-fragile). Today the post-06-15 bearish sample has grown to **SPY n=23 / QQQ n=30 and turned NET-POSITIVE under BOTH proxies (SPY bearish PF 1.11 +$37.11; QQQ bearish PF 1.11 +$42.66)** — so skip-bearish would now REMOVE profit under both. Today's own loser (TSM) being bullish-tagged is a fresh in-sample counterexample. Per the IMP-004/007 pattern (surface the metric so a refuted candidate can't be silently reopened): added a **machine `skip_bearish_gate_verdict()`** that rules the gate SUPPORTED only if, under EVERY proxy, the bearish sample is adequate (≥20), skipping it removes a net LOSS, and bearish PF is below bullish — else REFUTED with the reason. `scripts/regime_analysis.py` now prints an explicit **`GATE VERDICT: REFUTED — …`** line (post-06-15: "removes net-positive P&L under SPY/QQQ"; all-time: "bearish not worse than bullish"). Pure tooling — **NO entry/sizing/stop/exit/risk logic touched.**
2. **The ★ market-regime lever needs a fundamentally different regime definition, not a bigger EMA9 sample.** The naive SPY/QQQ-EMA9 skip-bearish gate is now refuted three ways (proxy-fragile 07-07; bearish net-positive 07-09; all-time bearish even less-bad). The next proxy candidates (VWAP, "skip first N min on a red open") remain untested and are the only path forward before any engine gate; the residual leak (TSM/QCOM open-fades) is still real but is NOT captured by index-EMA regime. Needs the deliberate `scripts/replay.py` multi-run build, not a post-close change.
3. **(Note, no action) SE redeemed (biggest win) despite a below-level fill; the "one BOTH TP carries the day" concentration persists.** Nothing to act on — reinforces existing refutations (below-level fill, confidence). Watch whether SE's open-fade signature (1W3 → now 2W3) is truly behind it.

### Notes for pre-market research
- **SE** — the standing "most persistent single-name drag" (was 1W3, watched for a ~1W4L park) **redeemed emphatically**: a conf-80 BOTH breakout that hit TP for **+$228.54, the biggest win of incubation** (now 2W3). The park-candidate watch on SE can be **relaxed** — it just delivered the day. Keep top-of-list; note it filled 0.40% below its broken level and still ran (below-level fill is non-discriminating).
- **TSM** — low-conf (60.1) MA open-fade, the day's only loser (−$35.11, −1.32%); faded from entry in a bullish tape. No name defect (liquid semi, strategy-fit, regime open-fade); it simply didn't participate. No park.
- **QQQ / SPY** — low-conf MA index-ETF drifters that rode the up-tape to small green flattens (+$14.87 / +$9.09); their IMP-013 break-even arms cost nothing. Normal behaviour.
- **Regime read for tomorrow:** today was a clean BULLISH tape under both proxies (all 4 trades bullish-tagged) and the winners rode it — but the one loser was ALSO bullish-tagged, so the naive index-EMA gate would not have helped (now refuted by IMP-015). Don't expect a market-EMA filter to save open-fade STOPs. SK Hynix ADR lists Fri 07-10 — watch whether semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) sustain leadership. Equity **$8,532.59 (−14.7%)**, **$1,033 above** the −25% flag — best cushion of incubation; protect it. Track the by_stop_protection split (IMP-014) to keep scoring IMP-013.

---

## 2026-07-10 — Daily Review

### Stats
- Trades: **5 closed (4W / 1L)**, win rate **80.0%** — but a **net-negative day** because the single loser dwarfs the four winners.
- Net realized P&L: **−$100.62** (day **−1.179%**). Equity close **$8,431.94** (from $8,532.56 open; Alpaca last_equity 8532.56 → equity 8431.94 = **−$100.62 broker truth, matches to the penny** — every entry+exit fill recorded correctly, IMP-003/005/010). **−15.7% YTD**, **$931.94 above** the −25% ($7,500) strategy-review flag (cushion trimmed by one trade, intact).
- Avg winner **+$4.69** (WMT +6.24, SPY +5.59, AAPL +3.77, BAC +3.16); **single loser −$119.38 (TSLA)**. The 4 winners combined = **+$18.76**; TSLA alone = **−$119.38**. Profit factor (day): 18.76 / 119.38 = **0.16**.
- Exit reasons: **2 STOP** (AAPL a *trailed* IMP-013 rescue +$3.77; TSLA a full-1R −$119.38), **3 EOD_FLATTEN** (BAC/SPY/WMT, all small green). **0 TAKE_PROFIT.**
- Circuit breaker NOT tripped (−1.18% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight** (IMP-002, **12th straight clean session**; 15:55 flatten reported "3 still open (BAC/SPY/WMT)" → retried → all confirmed flat 15:56). ✅ Service active all session (since 07-09 21:35:56 UTC restart); journal clean, **0 rejected orders** (no 422), **2 STOP RAISED** (the AAPL IMP-013 chain).
- **IMP-008 fired correctly:** **SE was skipped** at 09:30:22 (`live 111.81 = +2.47% vs signal 109.12` → stale-signal gap-up; the bracket TP/stop would have been mispriced). No 422, no silent missed-fill loss. Yesterday's hero (SE +$228.54 TP) gapped up too far to trade today — the guard declined cleanly.

### Trade-by-trade review
*(entry/exit = real Alpaca fills; orig_stop = plan 1R anchor kept in trades.stop_price by IMP-013; rf = fraction of original 1R retained at a STOP exit)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause / IMP-013 behaviour |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 138 | AAPL | 09:30:22 @313.53 | 10:01:09 @314.00 | 60.68 | MA | STOP (**trailed**) | **+$3.77** (+0.15%) | **First-ever "trailed" STOP win in the books.** Reached +0.5R → stop→break-even (311.42→313.53), then +1R → trailed to 314.01; faded and stopped **GREEN**. IMP-013 turned a would-be round-trip into a small profit. |
| 139 | TSLA | 09:31:40 @411.08 (broke 407.765, ext **0.81%**) | 10:33:22 @405.11 | **81.93** | **BOTH** | **STOP (rf 0.00)** | **−$119.38** (−1.45%) | **THE whole day's loss.** High-conf BOTH breakout that faded straight from entry to the **full original 1R stop** in ~1h — **never reached +0.5R**, so IMP-013 could not arm. Sized large (qty 20) on the high-conf tier. The PF-0.01 full-1R open-fade false-breakout leak, biting once at high confidence. |
| 140 | BAC | 09:31:41 @59.73 (broke 59.33) | 15:56:54 @59.76 | 77.15 | BOTH | EOD_FLATTEN | **+$3.16** (+0.056%) | BOTH breakout, mom 0.98; barely trended, scratch-green drift to the flatten. |
| 141 | SPY | 10:03:13 @753.28 | 15:56:55 @755.14 | 60.03 | MA | EOD_FLATTEN | **+$5.59** (+0.247%) | Low-conf MA index-ETF; drifted up +0.25% with the mildly-bullish tape, captured at flatten. |
| 142 | WMT | 10:34:02 @113.46 | 15:56:56 @113.72 | 60.25 | MA | EOD_FLATTEN | **+$6.24** (+0.229%) | Low-conf MA; small up-drift to the flatten. |

### What worked / what didn't
- **Worked — the entire protective/measurement stack held.** IMP-008 **skipped SE's +2.47% gap-up** (no 422, no mispriced bracket); IMP-013 **rescued AAPL to the first-ever *trailed* STOP win** (+$3.77 instead of a round-trip loss); IMP-002 flatten cleared all 3 stragglers 15:55→15:56 (**0 open on Alpaca, 12th clean session**, no naked overnight); books tied to the broker equity move **to the penny** (IMP-003/005/010); circuit breaker correctly dormant; **0 rejected orders**.
- **Worked — the high-confidence sizing refutation RE-VERIFIED with today included.** TSLA's −$119.38 tempts a "cut the high-conf risk tier" reaction, but the post-06-15 live book says NO: **conf≥66 = 28 trades, +$381.75, PF 1.48** *even with today's TSLA loss*, and **TSLA specifically is 5 trades, +$340.95, PF 3.86.** De-sizing high-conf would strip the +$382 of winners; today is **one bad trade in a winning high-conf book**, not "high-conf loses at scale." The `CONFIDENCE_RISK_TABLE` stays untouched (refuted 06-26, re-checked 07-06, re-verified today).
- **Didn't — TSLA was the whole loss, and it is the one structural leak.** A conf-82 BOTH breakout (broke 407.765, filled 0.81% above) that **faded from entry to its full 1R stop, never going green** → the all-time full-1R STOP bucket (58 trades, −$3,422.61, PF 0.01). IMP-013 can't touch a never-green trade (that's by design — it protects trades that first reach +0.5R). No per-trade discriminator separates it (confidence, volume, extension, momentum all refuted). And it faded in a **mildly-BULLISH SPY tape** (SPY rose 753.28→755.14 during the hold) — a **third bullish-tape open-fade counterexample** (07-07 AMZN, 07-09 TSM, 07-10 TSLA) confirming the naive index-EMA regime gate would NOT have caught it (IMP-015, refuted).
- **No new defect, no new justified lever.** Everything that could protect capital did; the only leak is the known residual one whose sole real fix is the deliberate market-regime / breakout-quality build.

### Lessons & improvement candidates (ranked)
1. **NO code change warranted today — reviewed, no justification.** The day carries no defect (all fills tied to the penny, 0 overnight, 0 rejects, IMP-008/013/002 all fired correctly). The one loss (TSLA) is the known **full-1R open-fade STOP leak at high confidence**, for which every shippable lever is either inapplicable or refuted: (a) sizing is NOT the problem — post-06-15 conf≥66 is **+$381.75/PF 1.48** incl. today, TSLA **+$340.95/PF 3.86**, so the sizing table must not be cut; (b) IMP-013 cannot rescue a trade that never goes green (correct by design); (c) the naive SPY/QQQ-EMA9 regime gate is refuted (IMP-015) and today's TSLA fade in a *bullish* SPY tape is a fresh counterexample; (d) all per-trade discriminators (confidence IMP-004, volume 06-26, extension IMP-007, momentum) are refuted. **Manufacturing a change on one TSLA loss would overfit** — explicitly declined, per the ground rules.
2. **(STANDING #1 lever) Intraday market-regime / breakout-quality entry gate** — unchanged; the only lever that targets the TSLA-class open-fade STOP. Today adds the **third bullish-tape open-fade counterexample** (AMZN 07-07, TSM 07-09, TSLA 07-10): the residual leak is NOT a bearish-tape phenomenon, so an index-EMA gate can't catch it. Next step (backlog ★ step b, still open): build **VWAP** and **"skip first N minutes on a red open"** as alternative regime proxies in `scripts/regime_analysis.py` — the deliberate **multi-run** build with replay validation, NOT a one-day post-close hack (the bot's own methodology, honored again tonight).
3. **(Watch, no action) IMP-013 break-even/trail give-back.** AAPL exited its *trailed* stop at +$3.77 at 10:01:09 — did AAPL run to its TP 323.27 later in the session (i.e. did the trail leave money on the table)? Single instance; grow the by_stop_protection sample before judging BREAKEVEN_TRIGGER_R / TRAIL_DISTANCE_R — do NOT tune on n=1.

### Notes for pre-market research
- **TSLA** — the franchise name, but today a conf-82 BOTH breakout (broke 407.765) that **faded from entry to a full −1.45% stop (−$119.38, the entire day's loss)**. Still strongly net-positive post-06-15 (**+$340.95 / 5 trades / PF 3.86**) — this was **one open-fade, not a name defect; no park.** Keep top-of-list; note it can fade hard from the open even at high confidence (the residual STOP leak).
- **SE** — **skipped by the IMP-008 stale-signal guard** (gapped **+2.47%** between signal 109.12 and live 111.81). Yesterday's hero (+$228.54 TP) was un-tradeable today because it gapped past the cap — the guard did its job (no 422, no chase). Watch whether SE keeps gapping open (a recurring gap-and-go the bot correctly declines).
- **AAPL** — low-conf MA that **IMP-013 rescued to the first-ever *trailed* STOP win** (+$3.77); no concern, behaved well.
- **BAC / SPY / WMT** — small green flatten drifters (BAC +$3.16, SPY +$5.59, WMT +$6.24) on a mildly-bullish tape; nothing name-specific.
- **Regime read for Mon 07-13:** the SPY tape was mildly BULLISH intraday (SPY rose during the session) yet TSLA still open-faded — **do not expect an index-EMA regime filter to save open-fade STOPs** (third such counterexample). Watch whether the SK-Hynix-driven semi/AI leadership sustains or the "crowded-positioning breather" turns into a fade. Bank earnings ramp next week (JPM ~Tue 07-14, already parked) — check the intraday-earnings calendar and park any on-list name reporting during hours. Equity **$8,431.94 (−15.7%)**, **$931.94 above** the −25% ($7,500) flag — cushion trimmed by the one TSLA loss but intact; **protect it.** Track the by_stop_protection split (IMP-014) — today logged the first-ever "trailed" STOP win (AAPL).

---

## 2026-07-13 — Daily Review

### Stats
- Trades: **6 closed (2W / 4L)**, win rate **33.3%** — net-negative; one high-conf open-fade dwarfed the two winners.
- Net realized P&L: **−$85.27** (day **−1.011%**). Equity close **$8,346.63** (from $8,431.90 open; Alpaca last_equity 8431.90 → equity 8346.63 = **−$85.27 broker truth, matches to the penny**, IMP-003/005/010). **−16.5% YTD**, **$846.63 above** the −25% ($7,500) strategy-review flag (cushion trimmed, intact).
- Avg winner **+$43.73** (MSFT +78.39, COST +9.06); avg loser **−$43.18** (NVDA −129.93, SE −41.65, GOOGL −0.78, AMZN −0.36). Profit factor (day): 87.45 / 172.72 = **0.51**.
- Exit reasons: **4 STOP** (2 full-1R: NVDA/SE; **2 IMP-013 break-even rescues**: GOOGL −0.78 / AMZN −0.36, both ~scratch), **2 EOD_FLATTEN** (MSFT/COST). **0 TAKE_PROFIT.** by_stop_protection today = **full-1R 2 / −$171.58**, break-even 2 / −$1.14, trailed 0.
- Circuit breaker NOT tripped (−1.01% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight** (IMP-002, **13th straight clean session**; 15:55 flatten reported "2 still open (COST/MSFT)" → retried → both confirmed flat 15:57). ✅ Service active all session (since 07-09 21:35:56 UTC); one **transient `ConnectionError: RemoteDisconnected` at 09:36:42 self-recovered** on the next tick (no missed entry/exit), **0 rejected orders** (no 422), 3 STOP RAISED (GOOGL/AMZN/MSFT IMP-013 chains). Broker cross-check: 12 fills = 6 trades, 0 mismatch.

### Trade-by-trade review
*(entry/exit = real Alpaca fills; orig_stop = plan 1R anchor in trades.stop_price per IMP-013; rf = fraction of original 1R retained at a STOP; ext = fill vs broken level)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause / IMP-013 behaviour |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 143 | NVDA | 09:30:11 @210.28 (broke 210.596, ext **−0.15%**) | 09:43:38 @207.83 | **94.2** | **BOTH** | **STOP (rf 0.00)** | **−$129.93** (−1.17%) | **THE whole day's loss.** Highest-conf BOTH breakout faded straight from the open to its **full original 1R stop in ~13 min**, **never reached +0.5R** so IMP-013 could not arm. The PF-0.01 full-1R open-fade leak, biting once at top confidence — **same pattern as 07-10 TSLA** (conf-82, 09:31, −$119.38). |
| 144 | GOOGL | 09:30:12 @354.73 | 09:51:14 @354.62 | 61.8 | MA | STOP (**break-even**) | **−$0.78** (−0.03%) | **IMP-013 rescue.** Stop raised to entry (351.81→354.73) at 09:38, then faded and stopped **~scratch** instead of a full round-trip loss. |
| 145 | MSFT | 09:34:34 @387.22 (broke 385.34, ext +0.49%) | 15:57:10 @390.95 | **85.3** | **BOTH** | EOD_FLATTEN | **+$78.39** (+0.96%) | **Day's engine.** High-conf BOTH that trended up; stop raised past break-even (381.05→387.22) at 11:10 and rode to a green flatten. The "one BOTH carries the book" pattern — but today it only half-offset NVDA. |
| 146 | AMZN | 09:47:41 @247.14 | 15:45:42 @247.11 | 60.1 | MA | STOP (**break-even**) | **−$0.36** (−0.01%) | **IMP-013 rescue.** Stop→break-even (243.86→247.14) at 11:02, held ~6h, stopped **~scratch** near the close instead of a loss. |
| 147 | SE | 10:40:35 @114.80 | 11:41:06 @112.35 | 60.4 | MA | **STOP (rf ~0)** | **−$41.65** (−2.13%) | Full-1R low-conf MA fade; **never reached +0.5R** (widest ATR stop, 2.0% of entry) so IMP-013 couldn't arm. Day after being IMP-008 gap-skipped — traded today and faded. |
| 148 | COST | 11:47:40 @923.96 | 15:57:11 @926.98 | 62.3 | MA | EOD_FLATTEN | **+$9.06** (+0.33%) | Small low-conf MA green drift to the flatten. |

### What worked / what didn't
- **Worked — IMP-013 rescued BOTH low-conf faders to ~scratch.** GOOGL (−$0.78) and AMZN (−$0.36) each had stops raised to break-even and stopped near-flat instead of round-tripping to full losses — two more break-even data points (by_stop_protection now 60 full-1R / 7 break-even / 1 trailed all-time). The protective/measurement stack held everywhere: 0 open on Alpaca (13th clean session), retry-until-confirmed flatten cleared COST/MSFT 15:55→15:57, books tied to broker equity **to the penny**, circuit breaker dormant, 0 rejects, one transient ConnectionError self-healed.
- **Worked — high-conf sizing RE-VERIFIED, again.** NVDA −$129.93 tempts a "cut the high-conf tier" reaction, but the post-06-15 book still says NO **with today included: conf≥66 = 30 trades, +$330.21, PF 1.35** (MSFT +78.39 is also conf-85). De-sizing high-conf would strip that +$330. Today is **one bad high-conf trade in a winning high-conf book** — `CONFIDENCE_RISK_TABLE` stays untouched (refuted 06-26, re-checked 07-06/07-10, re-verified today).
- **Didn't — the residual full-1R open-fade STOP leak, again the whole loss.** NVDA (conf-94 BOTH, entered 09:30:11, faded to full 1R, never green) is the **second consecutive session** where the day's entire loss is a high-conf BOTH breakout that faded from the open (07-10 TSLA 09:31 was the first). SE adds a second full-1R (low-conf MA, mid-morning). IMP-013 cannot touch a never-green trade (correct by design).
- **The two-day open-fade pattern invites a "skip the first N minutes" gate — and today's data REFUTES it.** All-time STOP $ by minutes-after-open: 0-5m −1211 / 5-15m −611 / 15-30m −409 / 30-60m −395 / 60m+ −964 — the false-breakout STOP bleed is spread across the WHOLE session, and by win%/PF the 0-5m band is actually the **least-bad** (43.6% / PF 0.76). Critically, the 0-5m band today holds the day's **biggest loser (NVDA) AND biggest winner (MSFT, entered 09:34)** — so an open-skip gate would forgo winners without isolating the leak. Surfaced as a report metric (IMP-016) so this candidate can't be silently reopened.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-016 — measurement/tooling] Added a `by_time_of_day` (minutes-after-open) breakdown to analytics + report.** Two consecutive open-drive full-1R losers (TSLA 07-10, NVDA 07-13) naturally invite a "skip the first N minutes after the open" entry gate — a backlog ★ regime proxy. Rather than manufacture that engine change on a 2-day pattern (overfit), shipped the metric that lets it be judged on evidence: it shows the STOP leak is **not** open-concentrated (0-5m is the least-bad band; the open band also carries the biggest winners), so the open-skip gate is refuted. Pure tooling — **NO entry/sizing/stop/exit/risk logic touched** (paper endpoint, MAX_RISK_PCT 2.0, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all unchanged). The IMP-004/007/015 refuted-candidate-made-visible pattern.
2. **NO engine change warranted — every shippable entry lever is refuted.** (a) sizing must not be cut (post-06-15 conf≥66 = +$330.21/PF 1.35 incl. today); (b) IMP-013 can't rescue a never-green trade (by design); (c) index-EMA skip-bearish gate refuted (IMP-015); (d) entry-time gate refuted today (IMP-016); (e) extension/below-level-fill (NVDA filled −0.15% below level and still lost)/momentum/volume all refuted. Manufacturing a change on NVDA alone would overfit — declined per ground rules.
3. **(STANDING #1 lever) Intraday market-regime / breakout-quality entry gate** — unchanged; still the only lever that targets the NVDA/TSLA-class open-fade STOP, but it needs the deliberate `scripts/replay.py` multi-run build with a NEW regime definition (VWAP; not index-EMA, not time-of-day — both now refuted), not a one-day post-close hack.

### Notes for pre-market research
- **⚠️ BANK EARNINGS TUE 07-14 — BAC is on-list.** Verify BAC's exact report time tomorrow morning and **park it for the day if it reports during market hours** (banks usually report pre-open; JPM/C already parked). Check the full intraday-earnings calendar.
- **NVDA** — conf-94 BOTH breakout that **faded from the open to a full −1.17% stop (−$129.93, the whole day's loss)**. This was **one open-fade, not a name defect** (liquid semi, strategy-fit); **no park.** Keep top-of-list; note it can fade hard from the open even at top confidence (the residual STOP leak). Semis stabilized enough to signal today after last week's risk-off.
- **SE** — traded today (after being IMP-008 gap-skipped 07-10) as a low-conf MA and **faded to a full-1R stop (−$41.65, −2.13%)**; widest ATR stop on the book. Its 07-09 +$228 TP redemption stands, but SE remains streaky — watch, no park.
- **MSFT** — the day's engine (+$78.39, conf-85 BOTH, trended up, IMP-013 rode it); behaved well. **COST** small green drift (+$9.06). **GOOGL / AMZN** — low-conf MA faders that IMP-013 rescued to ~scratch (−$0.78 / −$0.36); nothing name-specific.
- **Regime read for Tue 07-14:** the geopolitical risk-off gap-down open did NOT produce a bloodbath (megacap MSFT even trended); NVDA/SE open-faded regardless of tape — **do not expect a time-of-day OR index-EMA filter to save open-fade STOPs** (both refuted). Watch whether the semi breather resumes or stabilizes. Equity **$8,346.63 (−16.5%)**, **$846.63 above** the −25% ($7,500) flag — cushion trimmed by the one NVDA loss; **protect it** into bank earnings + inflation data. Track by_time_of_day (IMP-016) and by_stop_protection (IMP-014) going forward.

---

## 2026-07-14 — Daily Review

### Stats
- Trades: **6 closed (2W / 4L)**, win rate **33.3%** — net-negative but small; no single trade dominated (biggest loss −$49.78).
- Net realized P&L: **−$41.14** (day **−0.493%**). Equity close **$8,305.46** (from $8,346.60 open; Alpaca last_equity 8346.60 → equity 8305.46 = **−$41.14 broker truth, matches to the penny**, IMP-003/005/010). **−16.9% YTD**, **$805.46 above** the −25% ($7,500) strategy-review flag (cushion trimmed, intact).
- Avg winner **+$34.83** (BAC +51.47, GOOG +18.18); avg loser **−$27.70** (XOM −49.78, UNH −39.33, META −21.28, AMD −0.40). Profit factor (day): 69.65 / 110.79 = **0.63**.
- Exit reasons: **1 TAKE_PROFIT** (BAC), **2 STOP** (UNH full-1R; **AMD IMP-013 break-even rescue −$0.40**), **3 EOD_FLATTEN** (XOM/GOOG/META). by_stop_protection today = full-1R 1 / −$39.33, break-even 1 / −$0.40, trailed 0. **by_flatten_outcome today (new, IMP-017): faded 2 / −$71.06 (XOM/META), drifted-up 1 / +$18.18 (GOOG).**
- Circuit breaker NOT tripped (−0.49% nowhere near −8.0%). **Positions: 0 open on the broker — no naked overnight** (IMP-002, **14th straight clean session**; broker cross-check: 12 fills = 6 trades, 0 mismatch). ✅ Service active all session (since 07-13 21:36:45 UTC restart); app logs to file (journald shows only start/stop). **0 rejected orders** (no 422); IMP-013 STOP-raise fired on AMD (break-even).
- ⚠️ **Process gap (not code): the `uswisbot-premarket` routine did NOT run this morning** — no 2026-07-14 entry in research-log.md (last is 07-13). So yesterday's flag to **park BAC for bank earnings** was never acted on. BAC traded anyway (#149) and **won +$51.47 (TP)** — no harm today, but the missing pre-market run left the watchlist un-curated. Carry to tomorrow's pre-market.

### Trade-by-trade review
*(entry/exit = real Alpaca fills; orig_stop = plan 1R anchor in trades.stop_price per IMP-013; ext = fill vs broken level)*
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | Root cause / IMP-013 behaviour |
|---|-----|-----------|-----------|------|------|------|-----|-----------|
| 149 | BAC | 09:30:12 @59.77 | 10:31:04 @60.89 | 63.4 | MA | **TAKE_PROFIT** | **+$51.47** (+1.87%) | **Day's engine.** Low-conf MA that ran on the bank-earnings pop (BAC reported pre-open) and hit its TP 60.88 in ~1h. Only TP of the day. (Should have been parked for earnings per 07-13 review — the pre-market skip left it on; it won anyway.) |
| 150 | XOM | 09:31:43 @146.09 (broke 145.14, ext **+0.65%**) | 15:56:50 @144.78 | **78.0** | **BOTH** | EOD_FLATTEN | **−$49.78** (−0.90%) | **THE day's biggest loss — and a fade-to-flatten, not a STOP.** High-conf BOTH breakout that faded straight from entry, **never reached +0.5R** (so IMP-013 couldn't arm) but its wide 3×ATR stop (143.32, −1.9%) was **never hit**, so it rode the −0.9% drift to the flatten. The residual open-fade leak escaping into the EOD_FLATTEN bucket (see IMP-017). |
| 151 | UNH | 09:43:35 @430.80 | 10:43:46 @424.24 | 62.6 | MA | **STOP (rf ~0)** | **−$39.33** (−1.52%) | Full-1R low-conf MA open-fade to its original stop; never green so IMP-013 couldn't arm. |
| 152 | AMD | 10:35:51 @553.96 (broke 551.75) | 12:10:57 @553.76 | 64.7 | BOTH | **STOP (break-even)** | **−$0.40** (−0.04%) | **IMP-013 rescue.** BOTH breakout reached +0.5R → stop raised to break-even (538.73→~entry), then faded and stopped **~scratch** instead of a full-1R loss (orig 1R ≈ −$30). |
| 153 | GOOG | 10:47:10 @354.71 | 15:56:51 @357.31 | 60.6 | MA | EOD_FLATTEN | **+$18.18** (+0.73%) | Low-conf MA that drifted up +0.7% with the tape, captured green at the flatten. |
| 154 | META | 12:56:34 @664.81 | 15:56:52 @659.49 | 60.7 | MA | EOD_FLATTEN | **−$21.28** (−0.80%) | Late (12:56) low-conf MA; faded −0.8% and was flattened. A second fade-to-flatten (IMP-017 faded bucket). |

### What worked / what didn't
- **Worked — the protective/measurement stack held everywhere.** 0 open on Alpaca (14th clean session, IMP-002), books tied to the broker equity move **to the penny** (IMP-003/005/010), circuit breaker dormant, **0 rejected orders**, and **IMP-013 rescued AMD to a −$0.40 break-even scratch** (a would-be ~−$30 full-1R loss). Each loss was small and controlled (worst −1.52%); the day was a shallow −0.49% chop, not a risk event.
- **Worked — high-conf sizing NOT the problem, re-verified.** XOM (conf-78) was the biggest loss, but it was a −0.9% flatten, not a blow-up, and the post-06-15 conf≥66 book stays net-positive; **one small high-conf fade in a winning high-conf book.** `CONFIDENCE_RISK_TABLE` untouched (refuted 06-26, re-verified through 07-13).
- **Didn't — the residual open-fade leak, this time escaping into EOD_FLATTEN.** XOM was a conf-78 BOTH breakout that faded from the open but whose **wide 3×ATR stop was never hit**, so it exited as an EOD_FLATTEN (−$49.78), NOT a STOP. That means **IMP-014's by_stop_protection scorecard (STOP-only) is blind to it**, and the by_exit_reason EOD_FLATTEN bucket is net-POSITIVE overall (PF 1.59) — so the fade was masked by the profitable up-drift cohort (GOOG today). META was a second, smaller fade-to-flatten. The open-fade leak is NOT confined to the STOP bucket.
- **Didn't — every shippable per-trade entry lever remains refuted.** XOM filled +0.65% above its level (extension refuted IMP-007), high-conf (confidence refuted IMP-004), entered 09:31 (time-of-day refuted IMP-016), in a mixed tape (index-EMA regime refuted IMP-015). No per-trade discriminator separates it. The only lever is still the deliberate VWAP market-regime/breakout-quality gate — a multi-run `scripts/replay.py` build, not a one-day hack.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-017 — measurement/tooling] Added a `by_flatten_outcome` (faded vs drifted-up) split of the EOD_FLATTEN bucket.** Today's biggest loss (XOM −$49.78) was an open-fade that exited via EOD_FLATTEN (wide stop never hit), invisible to IMP-014's STOP-only by_stop_protection and masked inside the net-positive (PF 1.59) EOD_FLATTEN headline. Splitting the flatten bucket by the sign of realized P&L surfaces the leak: **all-time faded 26 / −$528.10 (PF 0.00) vs drifted-up 35 / +$841.13** — a materially-negative sub-population the old report hid. Pure tooling — **NO entry/sizing/stop/exit/risk logic touched** (paper endpoint, MAX_RISK_PCT 2.0, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT 3, no-overnight all unchanged). The IMP-004/007/014/016 measure-first pattern; it makes the TRUE size of the open-fade leak (STOP full-1R −$3,633 + EOD_FLATTEN-faded −$528) visible to the eventual VWAP regime-gate replay.
2. **NO engine change warranted — every shippable entry lever is refuted.** (a) sizing must not be cut (post-06-15 conf≥66 net-positive); (b) IMP-013 can't rescue a never-green trade (by design — it correctly saved AMD, which DID go green); (c) index-EMA skip-bearish gate refuted (IMP-015); (d) entry-time gate refuted (IMP-016); (e) extension/momentum/volume all refuted. Manufacturing a change on XOM alone would overfit — declined per ground rules.
3. **(STANDING #1 lever) Intraday market-regime / breakout-quality entry gate** — unchanged; still the only lever that targets the XOM/NVDA/TSLA-class open-fade. Next step (backlog ★): build **VWAP** as a regime proxy in `scripts/regime_analysis.py` (index-EMA and time-of-day both now refuted) via the deliberate `scripts/replay.py` multi-run build with validation — NOT a post-close hack.

### Notes for pre-market research
- **⚠️ THE PRE-MARKET ROUTINE DID NOT RUN 07-14** (no research-log entry) — the watchlist went un-curated and BAC (bank earnings) was not parked as flagged. **Confirm the `uswisbot-premarket` cron/routine is healthy tomorrow morning**; if it silently failed, that is a bigger issue than any single trade. BAC won anyway (+$51.47 TP).
- **XOM** — conf-78 BOTH breakout that **faded to a −$49.78 flatten (wide stop never hit)**; one open-fade, not a name defect (liquid energy large-cap, strategy-fit) — **no park.** Note it as the first clear fade-to-flatten instance (IMP-017).
- **BAC** — reported bank earnings pre-open, gapped/ran and hit its TP (+$51.47). Watch the bank-earnings calendar: verify report times each morning and park on-list banks that report **during** market hours (BAC reported pre-open, so it was tradable).
- **UNH** (−$39.33 full-1R STOP) and **META** (−$21.28 late fade-to-flatten) — low-conf MA open/midday faders; nothing name-specific, keep on the list.
- **AMD** — BOTH breakout that IMP-013 rescued to a −$0.40 break-even scratch; behaved well. **GOOG** small green drift (+$18.18).
- **Regime read for Wed 07-15:** a shallow −0.49% chop; some names drifted up (BAC/GOOG/AMD), some faded (XOM/UNH/META) — no clean directional tape. Semis mixed. Equity **$8,305.46 (−16.9%)**, **$805.46 above** the −25% ($7,500) flag — **protect it.** Track by_flatten_outcome (IMP-017), by_stop_protection (IMP-014), by_time_of_day (IMP-016) going forward.

## 2026-07-15 — Daily Review

### Stats
- Trades: **8 closed (2W / 6L), win rate 25%.** **Worst day since 06-10.**
- Net P&L: **−$252.01** (day −3.03%). Equity close **$8,053.42** (from $8,305.46; last_equity −$252.04, DB gross −$252.01 ties to the broker move to the ~penny). −19.5% YTD.
- Avg winner **+$40.26** (META +60.68, NVDA#2 +19.83); avg loser **−$55.42** (QQQ/ABNB/NVDA/NFLX/AVGO/AMZN). Day profit factor 80.51 / 332.52 = **0.24**.
- Exit reasons: **4 STOP** (NVDA, QQQ, AVGO, NFLX), **3 EOD_FLATTEN** (AMZN −1.99, ABNB −91.26, NVDA#2 +19.83), **1 TAKE_PROFIT** (META).
- Circuit breaker NOT tripped (−3.03% << −8.0% halt). Service active all session. **Book flat by close (8 in / 8 out) — no overnight carry.** No 422s, no rejected stop-replaces (IMP-013 clean).

### Trade-by-trade review
| # | Sym | Type/Conf | Entry (ET) | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|-----|-----------|
| NVDA | BOTH 84.1 | 09:41 @211.89 | 10:24 STOP @210.13 | **−$66.87** | High-conf breakout, filled ~0.7% above signal → tight 0.82% eff. stop, **faded from entry, never green** (IMP-013 can't arm). |
| QQQ | BOTH 80.8 | 09:41 @721.37 | 12:05 STOP @712.91 | **−$93.08** | High-conf index breakout, **faded slowly to full-1R stop over 2.5h**, never reached +0.5R. Day's biggest loss. |
| AVGO | MA 61.4 | 09:49 @396.52 | 10:25 STOP @390.30 | −$37.32 | Low-conf MA breakout, full-1R stop in 36 min. |
| META | MA 60.9 | 10:25 @668.36 | 11:10 **TAKE_PROFIT** @683.53 | **+$60.68** | The one clean winner — MA signal ran to TP in 45 min. |
| NFLX | MA 60.1 | 10:36 @74.73 | 15:05 STOP @73.56 | −$42.00 | Low-conf MA, drifted then stopped late-session (full-1R). |
| AMZN | MA 60.1 | 11:17 @255.23 | 15:56 EOD_FLATTEN @255.03 | −$1.99 | Near-flat drift to flatten. Immaterial. |
| ABNB | BOTH 85.7 | 12:06 @150.15 | 15:56 EOD_FLATTEN @148.46 | **−$91.26** | **High-conf BOTH breakout that faded from entry, wide 1.4% stop never hit → escaped into flatten (IMP-017 faded bucket).** 2nd biggest loss. |
| NVDA | BOTH 77.5 | 15:07 @211.70 | 15:56 EOD_FLATTEN @212.49 | +$19.83 | Late (15:07) re-entry, small green drift, flattened. |

### What worked / what didn't
- **Worked:** Risk controls held perfectly — no halt (−3.03% vs −8% cap), book flat by close (8/8, no naked overnight), 0 rejected stop-replaces, all fills ≤~0.7% off signal (no false stale-signal skips). META's TP (+$60.68) and IMP-013's machinery were clean; NVDA#2 flattened green.
- **Didn't — the headline:** the day's **entire** loss is the recurring **high-confidence BOTH open-fade** leak — **NVDA (84) −$66.87 + QQQ (81) −$93.08 + ABNB (86) −$91.26 = −$251.21 ≈ 100% of the −$252.01**. All three broke out, filled at/near their level, then **faded straight from entry, never reaching +0.5R** so IMP-013 could not arm (by design). This is the SAME pattern as 07-10 TSLA, 07-13 NVDA, 07-14 XOM — the residual full-1R STOP + EOD_FLATTEN-faded leak (all-time STOP full-1R −$3,873 / PF 0.01; EOD_FLATTEN-faded −$621 / PF 0.00). No per-trade discriminator (confidence, volume, extension, time-of-day) separates them — all refuted.
- The two MA losers (AVGO −37.32, NFLX −42.00) are the ordinary least-bad MA bucket (all-time PF 0.88); not the concentration.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-018]** The ★ market-regime lever's last-named-but-untested proxy — **SPY session-VWAP** — built as a third regime proxy in `scripts/regime_analysis.py` and fed through IMP-015's machine verdict. **Critically capital-protective:** on today's window the two EMA proxies (SPY-EMA9 & QQQ-EMA9) both flipped bearish-net-negative (today's NVDA/QQQ faders tagged EMA-bearish), so the **EMA-only verdict would have flipped to SUPPORTED** — i.e. a naive read would have green-lit shipping the skip-bearish gate. Adding VWAP keeps it **REFUTED**: under SPY-VWAP the bearish bucket is *profitable* (+$101.86, PF 1.14 > bullish 1.05), and SPY-EMA9 vs SPY-VWAP disagree on **33% of trades** (vs only 18% for SPY-vs-QQQ) — the regime *definition* matters more than the index, so the gate is definition-fragile and must not ship. See below.
2. The residual open-fade leak (full-1R + flatten-faded) remains the core drawdown driver, and **no regime proxy tried (EMA9 index, time-of-day, now VWAP) cleanly isolates it** — today NVDA/QQQ were EMA-*bullish* (an EMA gate wouldn't even skip them) yet VWAP-bearish, and VWAP-bearish is net-profitable. The lever now needs a *fundamentally different* signal (per-symbol breakout-quality / opening-range hold), tested via replay — **not** a post-close hack. Defer; keep measuring.
3. IMP-013 continues to correctly NOT rescue never-green faders (by design). No action; its scope is trades that reach +0.5R.

### Notes for pre-market research
- **NVDA** — TWO trades today: a conf-84 BOTH that open-faded to a full-1R STOP (−$66.87) AND a conf-77 late (15:07) re-entry that flattened green (+$19.83). Net −$47.04. **One open-fade, not a name defect** (liquid mega-cap, strategy-fit) — **no park.** The open-fade is the regime leak, not NVDA-specific.
- **QQQ** — conf-81 index-ETF BOTH breakout that **faded slowly to its stop over 2.5h (−$93.08, day's biggest loss)**. The index itself faded intraday — a broad-tape chop signal, note it.
- **ABNB** — conf-86 BOTH breakout that **faded from entry into the flatten (−$91.26, wide stop never hit)** — the 2nd clean IMP-017 fade-to-flatten instance in two days (XOM 07-14, ABNB 07-15). High confidence did NOT protect. No park (liquid large-cap); it is the regime open-fade leak.
- **META** — the day's only winner (MA conf-61 → TP +$60.68); behaved well, keep.
- **AVGO / NFLX** — low-conf MA full-1R STOPs (−37.32 / −42.00); ordinary MA-bucket losers, no name action. **AMZN** near-flat flatten drift (−1.99), now 0W over recent window — softest small-sample name, watch for a chronic-loser pattern (still a liquid large-cap, no trigger).
- **⚠️ TSM & UNH REPORT TOMORROW (Thu 07-16), both pre-open (BMO)** — verify exact timing and apply the earnings-park rule (park only if a report shifts to *during* market hours; BMO reporters stay tradable but gap/volatile). Re-scan the full intraday-earnings calendar (NFLX Q2 = 07-16 AMC).
- **Regime read for Thu 07-16:** today the SPY intraday tape faded (EMA proxies turned bearish-negative) but **VWAP-bearish stayed profitable** — the index-regime gate is REFUTED under the new 3-proxy test; **do NOT expect any index-regime filter to catch the high-conf open-fades** (NVDA/QQQ were even EMA-*bullish*). The lever is a *different* signal (per-symbol opening-range / breakout-quality via replay), not a watchlist action. Equity **$8,053.42 (−19.5%)**, **$553.42 above** the −25% ($7,500) flag — **cushion cut hard by today's −$252; protect it aggressively into the 07-16 earnings.**

---

## 2026-07-16 — Daily Review

### Stats
- Trades: 4 closed (2W / 2L), win rate 50%.
- Net P&L: **−$2.69** (day −0.033%). Equity close **$8,050.68** (from $8,053.37 open). A flat recovery day after 07-15's −$252.01.
- Avg winner +$18.92 (AAPL +32.32, WMT +5.52); avg loser −$20.27 (AMZN −37.25, GOOG −3.28).
- Profit factor (day): 37.84 / 40.53 = **0.93** (near-scratch).
- Circuit breaker NOT tripped (−0.03% << −8.0% halt). Service active all session, no errors/exceptions. **0 open positions at close — Alpaca fully reconciles (equity $8,050.68, 4 buys GOOG/AAPL/AMZN/WMT all match DB, no overnight leak).**
- Exit reasons: 2 STOP (GOOG, AMZN), 2 EOD_FLATTEN (AAPL, WMT).

### Trade-by-trade review
| # | Sym | Entry (ET) | Exit (ET) | Conf | Exit | P&L | Root cause |
|---|-----|-----------|-----------|------|------|-----|-----------|
| — | GOOG | 09:39:06 @370.997 | 10:55 @370.88 | 92.0 | STOP | **−$3.28** | Genuine breakout (brk=1.0, +0.10% ext), reached +0.5R → **IMP-013 armed break-even**, faded back and stopped at ~entry. A scratch, **not** a full-1R loss (would have been ~−$146). IMP-013 working exactly as designed. |
| — | AAPL | 09:46:39 @329.27 | 15:56 @333.31 | 61.6 | EOD_FLATTEN | **+$32.32** | Non-breakout MA/value entry (brk=0.0, broke_level=None), drifted up steadily, captured green into flatten. Day's best. |
| — | AMZN | 10:26:36 @255.38 | 15:17 @251.66 | 61.5 | STOP | **−$37.25** | Non-breakout MA/value entry (brk=0.0), faded from entry, never reached +0.5R (IMP-013 could not arm), took the full 1R stop (dist 1.45% ≈ ATR floor). Day's only real loss. **AMZN now 0W5** over the recent window. |
| — | WMT | 10:55:58 @114.56 | 15:56 @114.80 | 61.1 | EOD_FLATTEN | +$5.52 | Non-breakout MA/value entry, minor drift-up into flatten. |

### What worked / what didn't
- **Worked:** IMP-013 rescued GOOG — a high-conf (92) breakout that faded reached +0.5R first, armed the break-even stop, and exited at a −$3.28 scratch instead of a ~−$146 full-1R loss. This is the mechanism doing its job. Risk controls all held; 0 overnight; broker/DB reconcile cleanly.
- **Didn't:** AMZN was the whole day's loss — a non-breakout momentum/value entry that faded straight from entry and took the full 1R stop without ever reaching +0.5R (so IMP-013 by design cannot help). Same open-fade signature as the recurring leak, just on a low-conf MA entry rather than a high-conf BOTH.
- 3 of 4 fills were non-breakout (brk=0.0) MA/value entries — 2 small winners + 1 loser; the least-bad bucket (all-time MA PF 0.88), net roughly scratch. Nothing to change there today.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-019]** Finally *measured* the ★ open-fade lever per-trade: the fill's distance from the symbol's **own session VWAP at entry**. Every prior discriminator (confidence, extension, time-of-day, index-EMA/SPY-VWAP *regime*) was REFUTED — this one is **not**. On the 63 recent trades with bars the signal is **cleanly monotonic**: fills at/below session VWAP win 50–57% (exp **+$19 to +$22**), fills stretched ≥+0.25% above VWAP win 31–38% (exp **−$14 to −$20**). The break is right at VWAP (0.00%). Today's AMZN full-1R fade was an above-VWAP fill; the winners AAPL/WMT held near/below. Shipped as a `scripts/replay.py` diagnostic table (+ pure `bot/replay.py` functions + unit tests). This is the first per-trade separator of the open-fade leak — but acting on it (a VWAP entry-quality gate) is an **entry-logic change → proposed in `todo.md` for human approval**, not shipped silently.
2. Residual open-fade leak (full-1R + flatten-faded) remains the core drawdown driver; IMP-019 now gives a candidate gate to test it in replay before touching live entry logic. Defer the gate itself to human sign-off.
3. IMP-013 continues to correctly rescue only trades that reach +0.5R (GOOG today) and correctly does NOT rescue never-green faders (AMZN today). Working as designed; no action.

### Notes for pre-market research
- **AMZN — now 0W5** over the recent window (today −$37.25, a full-1R open-fade stop). This is the softest small-sample name and the pre-market chronic-loser watch flagged 07-15/07-16. **Still a liquid large-cap, strategy-fit; no structural defect — the losses are the above-VWAP open-fade regime, not a name flaw.** No park trigger matured yet, but **if AMZN takes another full-1R fade tomorrow consider a park decision.**
- **GOOG** — conf-92 breakout that faded but was scratched by IMP-013 (+0.5R reached). Behaved fine; the mechanism protected it. Keep.
- **AAPL / WMT** — quiet non-breakout MA/value drift-up winners; no action, both fine.
- **★ Open-fade lever update:** IMP-019 found the **first non-refuted per-trade discriminator** — entry distance from the symbol's own session VWAP. Fills ≥+0.25% above VWAP are net-negative; fills at/below VWAP are net-positive. A **VWAP entry-quality gate** (skip/deprioritize fills stretched above session VWAP) is now proposed in `todo.md` for human approval — do NOT treat as shipped; it is an entry-logic change awaiting sign-off. Run `python -m scripts.replay` for the live band table.
- **NFLX reported AMC today (07-16) → it will gap Fri 07-17** — treat with extra caution (wide post-earnings ranges; no overnight risk for an EOD-flatten bot). Re-scan the intraday-earnings calendar and park any on-list name reporting *during* market hours.
- **TSM/UNH** both printed pre-open today (BMO, not parked); note whether TSM lifts/fades the semi complex. Equity **$8,050.68 (−19.5%)**, **$550.68 above** the −25% ($7,500) flag — cushion essentially flat on the day; protect it.

---

## 2026-07-17 — Daily Review

### Stats
- Trades: 5 closed (**0W / 5L**), win rate **0%**.
- Net P&L: **−$211.48** (day −2.627%). Equity close **$7,839.17** (from $8,050.65 open). Worst day since 07-15 (−$252.01), in a risk-off AI/chip-led selloff tape (Nasdaq-100 futures −1.6%, SOXX −3%, Kospi −7%).
- Avg winner: none. Avg loser −$42.30; the three real losers averaged −$70.33 (CRM −55.65, UNH −40.02, AMD −115.32); MU −0.35 and AAPL −0.14 were near-flat break-even/scratch exits.
- Profit factor (day): 0 / 211.48 = **0.00**.
- Circuit breaker NOT tripped (−2.63% << −8.0% halt). Service active all session, no errors/exceptions. **0 open positions at close — Alpaca fully reconciles** (equity 8050.65→7839.17 = −$211.48 to the penny; all 10 fills CRM/MU/UNH/AMD/AAPL match DB entry & exit exactly; no overnight leak).
- Exit reasons: 4 STOP (CRM, MU, UNH, AMD), 1 EOD_FLATTEN (AAPL).

### Trade-by-trade review
| # | Sym | Entry (ET) | Exit (ET) | Conf | Type | Exit | P&L | VWAP dist | Root cause |
|---|-----|-----------|-----------|------|------|------|-----|-----------|-----------|
| 167 | CRM | 09:37:04 @174.77 | 10:04 @171.06 | 62.6 | MA | STOP | **−$55.65** | **+0.68%** | Non-breakout MA entry filled **above** session VWAP, faded straight down, took the full 1R stop (dist 2.00%, exit −2.12% w/ stop-through). Never reached +0.5R → IMP-013 couldn't arm. Above-VWAP open-fade. |
| 168 | MU | 12:06:10 @884.47 | 13:57 @884.12 | 62.8 | MA | STOP | −$0.35 | +3.66% | qty 1 (884/sh caps size). Reached +0.5R → **IMP-013 armed break-even**, stopped at ~entry for −$0.04%. A scratch, not a loss. Mechanism working. |
| 169 | UNH | 12:21:41 @433.17 | 15:49 @426.50 | 63.8 | MA | STOP | **−$40.02** | **+0.65%** | Non-breakout MA entry above VWAP, ground down all afternoon to the full 1R stop (dist 1.50% = ATR floor). Never green → IMP-013 couldn't arm. Above-VWAP open-fade. |
| 170 | AMD | 12:49:48 @502.00 | 15:14 @492.39 | 81.2 | BOTH | STOP | **−$115.32** | **+3.82%** | Day's worst. High-conf BOTH breakout (ext only +0.08% above broken level) but filled **+3.82% above session VWAP** into a −3% semi selloff; faded to full 1R stop (dist 1.86%). Never reached +0.5R → IMP-013 couldn't arm. The recurring high-conf above-VWAP fade. |
| 171 | AAPL | 15:05:17 @333.98 | 15:57 @333.96 | 60.1 | MA | EOD_FLATTEN | −$0.14 | +0.51% | Late low-conf MA entry, flat into the 15:55 flatten. Scratch. |

### What worked / what didn't
- **Worked:** Every risk control held — no halt, 0 overnight, broker/DB reconcile to the penny. **IMP-013 correctly rescued MU** (reached +0.5R, armed break-even, scratched at −$0.35 instead of a full −1R) and correctly could NOT rescue the three never-green faders (CRM/UNH/AMD) — by design, those are the regime/entry-quality gate's job, not IMP-013's.
- **Didn't:** The entire −$211 is **above-VWAP open-fades.** All 5 fills were above session VWAP; the 3 real losers (CRM +0.68%, UNH +0.65%, AMD +3.82%) each faded from entry to the full 1R stop. AMD is the textbook recurring case: high-conf BOTH, tight extension over the broken *level*, but stretched +3.82% above its own VWAP into an AI-capex/chip selloff — exactly the IMP-019 open-fade signature. This is not a stop-placement, sizing, slippage, data, or bug problem: books reconcile, stops fired correctly, the day just took five entries stretched above fair value on a red-tape day.
- Not open-concentrated: only CRM entered near the open (09:37); MU/UNH/AMD/AAPL were all midday (12:06–15:05). Consistent with IMP-016's refutation of a "skip first N min" gate — the leak is above-VWAP fills, not the clock.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-020]** Today gave 5 more above-VWAP faders (all ≥+0.50% above VWAP), so I advanced the ★★ VWAP-gate's **pre-ship validation step 1** (required by `todo.md` before human sign-off): added a `--vwap-skip PCT` what-if to `scripts/replay.py` (+ pure `vwap_skip_whatif` in `bot/replay.py`, 3 tests on today's real trades). It simulates skipping fills stretched above session VWAP and reports the exact P&L delta vs the replay noise budget. **Result: the delta clears the noise budget by ~12× and the kept book flips positive at +0.25%** — skip >+0.25% keeps 27 trades (**+$78.49**, 44.4% win) and removes 34 above-VWAP trades (−$688.26, 29.4% win); noise budget is only $55.81. Measurement/tooling only — the engine gate itself is still an entry-logic change **awaiting human approval** (todo.md ★★, now escalated with this evidence).
2. **Residual open-fade leak is now fully characterized and has a validated candidate fix** — the VWAP entry-quality gate. The next step is human sign-off on the ★★ proposal (threshold at the +0.25% band edge where the sign flips), then wire it as a *tightening* skip in `engine.consider_entries`. Do NOT ship without approval.
3. IMP-013 continues to do exactly its job (rescued MU, correctly passive on never-green faders). No action.

### Notes for pre-market research
- **AMD — new chronic-loser watch.** Today −$115.32 (the day's worst), a high-conf BOTH breakout that filled +3.82% above its own session VWAP and faded to a full 1R stop in the AI-capex/chip selloff. Liquid mega-cap, strategy-fit — the loss is the **above-VWAP open-fade regime, not a name defect** (same documented cause as AMZN). No park trigger; watch for a repeat.
- **AMZN did NOT trade today** (no signal) — its 0W5 watch is unchanged; still the standing chronic-loser flag but no fresh fade to mature a park.
- **CRM / UNH** — both MA-only entries that faded above VWAP to full stops; regime-driven (risk-off tape), not name defects. Keep. UNH ground down all afternoon — note if it stays heavy.
- **Semis (AMD/NVDA/MU/TSM/AVGO/INTC/QCOM)** — remained the down-driver (global AI-capex/chip de-rate, SOXX −3%). Watch Monday whether the complex stabilizes or the breather deepens; on-list HOLDs (regime, not name-quality). MU capped at qty 1 (884/sh) — negligible risk contribution.
- **★★ VWAP entry-quality gate — now backed by pre-ship validation (IMP-020).** Skipping fills >+0.25% above session VWAP would have flipped the 61-trade replay book from −$610 to **+$78.49**, delta clearing the noise budget ~12×. This is a **strategy/entry-logic lever awaiting human sign-off in `todo.md` — NOT a watchlist action.** Run `python -m scripts.replay` for the band table + skip what-if. Equity **$7,839.17 (−21.6%)**, now **$339.17 above** the −25% ($7,500) review flag — cushion thinned by today's −$211; protect aggressively.

---

## 2026-08-13 — Daily Review

### Stats
- **4 trades (1W/3L), net −$48.06 (−0.64%). Equity $7,512.68 → $7,464.62.** Win rate 25.0% (the one "win" is NVDA **+$1.55**, a rounding-error scratch). Avg win +$1.55, avg loser −$16.54, **PF 0.03**.
- **⚠️ The account is BACK BELOW the $7,500 review line: −25.35% from the $10,000 start.** The 08-13 pre-market run opened $12.68 above it; today's loss put it $35.38 below. The −25% escalation is a **human decision point and it remains open**.
- Broker reconciled and **clean**: Alpaca equity $7,464.62 = cash $7,464.62, `last_equity` $7,512.68 (day −$48.06, matches the DB to the cent), **0 positions, 0 open orders**, `trading_blocked` false. DB `daily_summary` agrees: 4 in / 4 out, close $7,464.62. **No qty drift, no missed fill, nothing carried overnight.**
- All-time: **240 closed, 38.6% win, −$2,239.35, PF 0.61.** Post-VWAP-gate (≥07-25): **51 trades, 41.2% win, −$214.72, PF 0.61, expectancy −$4.21/trade.**
- Service `active`, NRestarts=0, **0 tracebacks in the strategy path**. Four `tick error` entries (Alpaca **504 Gateway Timeout on /v2/account**, 12:59–13:11 ET) — see below; not risk-bearing.
- Market context (WebSearch-corroborated; sonar's tenth weak session — it returned "no company-specific catalyst" for 3 of 4 tickers and quoted an S&P change identical to yesterday's): **July PPI printed cooler than feared at 08:30 ET**, September-hike pricing eased, and the tape closed **risk-on but choppy — S&P +0.3%, Nasdaq +0.5%, AI/semis leading**. My own IEX bars: the day was a grind, not a trend. **This was not a hostile tape** — the loss is not attributable to regime.

### Trade-by-trade review
Every entry today was a **`MA` signal with `breakout_score` = 0.0000** and confidence **60.6–63.1**, i.e. the bottom of the permitted band. **For the second consecutive session not one trade was a breakout.** The VWAP gate did its job loudly: **43 entries vetoed** (TSLA 14, NFLX 14, ABNB 12, TSM 2, QQQ 1).

| # | Sym | Entry | Exit | Conf | 1R (stop dist) | MFE | MAE | Exit | P&L |
|---|-----|-------|------|------|----------------|-----|-----|------|-----|
| 251 | GOOG | 09:37:06 @ 344.397 | 15:57:28 @ 343.457 | 62.5 | 5.98 (1.74%) | **+0.24R** | −0.33R | EOD_FLATTEN | **−$6.58** |
| 252 | NVDA | 09:42:40 @ 225.039 | 15:57:28 @ 225.180 | 62.4 | 3.32 (1.47%) | **+0.43R** | −0.40R | EOD_FLATTEN | **+$1.55** |
| 253 | CRM | 09:51:35 @ 195.020 | 11:50:47 @ 191.710 | 60.6 | 3.30 (1.69%) | **+0.45R** | −0.99R | **STOP** | **−$39.72** |
| 254 | QQQ | 13:13:40 @ 732.780 | 15:57:29 @ 731.677 | 63.1 | 10.88 (1.49%) | **+0.11R** | −0.11R | EOD_FLATTEN | **−$3.31** |

- **GOOG #251 — root cause: the exit machinery was physically inert.** Held **6h20m**, 42/380 green minutes, and travelled a total of **+0.42% / −0.57%** against a **1.74% stop**. GOOG's ENTIRE session range was **0.99% = 0.57× the 1R stop distance**. The stop could not be hit, the target could not be hit, break-even could not arm. The outcome was set by the 15:55 clock and nothing else. Not a signal failure, not a stop failure — **a scale mismatch**.
- **NVDA #252 — same, and it is the day's "win".** 375 minutes, 288 green, MFE **+0.43R** — it spent the whole session profitable and still banked **+$1.55**, because +0.43R never armed break-even (trigger +0.5R) and the range/1R ratio was 1.05×. **This is the clearest single illustration of the structural problem: a trade that was right all day paid 0.4% of the risk taken.**
- **CRM #253 — the entire day's loss, and the one trade where the geometry DID engage.** CRM was the only name whose day was big (**session range 5.89% = 3.48× its 1R**). Entered 09:51 on a conf-60.6 MA signal, peaked **+0.45R** (again just under the +0.5R trigger — so break-even never armed), then went straight through the stop at 11:50 for **−1R exactly, −$39.72**. **Held to the 15:55 flatten it would have made +$75.60** — CRM reversed off the low and closed ~201.3. The 3×ATR stop (1.69%) was calibrated on a quiet-CRM ATR and was ~3.5× too tight for the day CRM actually had. *This is stated as evidence, not as a proposal — see "deliberately not shipped".*
- **QQQ #254 — inert again, and entered into the flattest part of the day.** 164 minutes, MFE **+0.11R**, MAE −0.11R, range/1R 0.91×. The known SPY/QQQ stop-floor mismatch, now confirmed on a third index-ETF trade: **1R sits on the `MIN_STOP_PCT` 1.50% floor while the instrument does not move 1.5% intraday.**
- **The four 504s (12:59–13:11 ET) cost nothing risk-bearing.** `tick()` runs `manage_exits` → `manage_stops` → `consider_entries`, and the failure was in `consider_entries`'s `broker.account_summary()` — so exits and the stop ratchet had already completed on each of those ticks. Four entry-consideration cycles were lost. **Ordering verified in code; no change needed.**

### What worked / what didn't
- **Worked: the VWAP gate (IMP-022).** 43 vetoes, including ABNB 12× at +0.56–0.73% above VWAP and TSLA 14× at up to +0.89%. It is still the one shipped filter that earns its place.
- **Worked: risk containment and the broker reconciliation.** −0.64% on a losing day, nothing stranded, DB = broker to the cent.
- **Didn't work — and this is today's headline: the exit apparatus is inert exactly where the bot makes money and engages exactly where it loses.** Bucketing the 51 post-gate trades by *session range ÷ 1R stop distance* — i.e. "can the geometry physically fire at all?":
  | range / 1R | n | net | win% | PF |
  |---|---|---|---|---|
  | **< 1.0** (1R wider than the whole day's range) | 10 | **+$28.86** | 50.0 | **2.64** |
  | 1.0 – 1.5 | 19 | −$8.33 | 52.6 | 0.92 |
  | 1.5 – 2.5 | 16 | −$146.67 | 31.2 | 0.48 |
  | **> 2.5** (geometry fully engages) | 6 | **−$88.58** | 16.7 | **0.39** |
  **The bot's P&L is positive where its exit logic cannot reach the price and negative where it can.** Today reproduced the pattern exactly: three inert trades netted −$8.34 combined; the one engaged trade lost −$39.72.
- **Didn't work — the same split by exit reason, all-time, is unambiguous:** `EOD_FLATTEN` **n=110, +$423.93, PF 1.47**; `TAKE_PROFIT` **n=25, +$2,033.75**; **`STOP` n=105, −$4,697.03, PF 0.02, 7.6% win.** Post-gate: flattens **+$115.76 (PF 1.93)**, TP +$55.72, **stops −$386.20 (PF 0.08)**. **Every exit path this bot owns is profitable except the stop, and the stop is more than the entire lifetime loss.**
- **Didn't work — the discriminator that separates the loss is `MFE`, and it is not knowable at entry.** Post-gate by peak excursion: **MFE <0.25R → n=20, −$313.05, 10% win, PF 0.02**; MFE 0.25–0.5R → −$127.84; MFE 0.5–1.0R → +$16.43; MFE >1.0R → **+$209.74, 87.5% win**. The loss is entirely in trades that never got going.
- **IMP-031 recorded n=0 decisive cases for a SECOND consecutive session — but it was closer than that sounds.** Its break-even-off-the-printed-high mechanism only bites when peak ≥ +0.5R while live < +0.5R. Today **CRM peaked +0.45R and NVDA +0.43R** — the two nearest misses yet, both *just* under the trigger. Still no harm, still no measured benefit. **Let it run.**

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-033 — capital protection] The EOD flatten has failed its FIRST pass on 10 of the last 10 sessions, and today it left the bot long for 89 seconds past its own deadline.** Alpaca's own order record for today: stop legs cancelled **19:55:23.596Z**, limit legs only **19:55:26.706Z** — **3.1 seconds later**. `flatten_all` fired `close_position()` at 19:55:23.6, all three were rejected `held_for_orders`, and — because the rejection was swallowed by a bare `except: pass` — **pass 1 submitted ZERO liquidation orders** and burned a full 60s poll. Pass 2 at 19:56:25 did submit, but the engine re-checked positions ~1s later while the market sells were still in flight (fills landed 19:56:26.9–19:56:29.2), producing a **second** spurious "incomplete". Log evidence: every session 07-31 → 08-13 failed pass 1, and **6 of 10 needed a second retry**, i.e. the bot was still holding stock at ~15:57 with five minutes of runway to the close. IMP-002's retry is a *survival* net, not a fix. **Fixed by making each phase wait, bounded, for the async broker state it depends on** — shares released before liquidating, flat before returning — plus logging rejections instead of hiding them. Pure execution plumbing: **no entry logic, no signal, no sizing, no stop, no exit geometry, no risk limit touched**, so IMP-031 keeps its clean read.
2. **★ THE STRATEGY VERDICT, stated plainly: this system has no demonstrated edge, and today's work closed the last cheap escape route.** 240 trades, PF 0.61, −22.4% of the account. Post-gate — the *best* version of the bot — 51 trades at **−$4.21 expectancy**. Refuted discriminators now number eight: confidence (IMP-004), volume (06-26), extension (IMP-007), time-of-day (IMP-016), index-EMA regime (IMP-015), opening-range blackout (IMP-030), never-green time-stop (IMP-032), break-even-trigger sweep (IMP-032). **Two more died today** (both measured, both recorded so they are never re-proposed): **(a) stop-distance / `MIN_STOP_PCT`-floor binding is NOT a discriminator** — all-time floor-bound n=167 PF 0.63 vs ATR-driven n=73 PF 0.56; post-gate 0.61 vs 0.60. Flat. **(b) A time-conditioned "scratch if MFE hasn't reached X·R by T minutes" rule is refuted across a 42-cell grid** (X ∈ 0.15–0.5R, T ∈ 15–120min): **every non-degenerate cell is NEGATIVE** (e.g. 0.25R@45min −$36.15, 0.30R@30min −$88.72). The only positive cells are the top-left corner (0.5R@15min **+$176**, 0.4R@15min +$122) — which cut ~45 of 51 trades and "work" purely by removing exposure. **A rule whose optimum is "stop trading" is not an exit rule; it is the no-edge result in disguise.** The honest reading of the geometry buckets above is the same: the bot profits when its logic can't act and loses when it can — which is what a zero-edge entry plus a −1R tail looks like. **The formal strategy review is a human decision and it is now overdue; the account is below the line again.**
3. **[NOT SHIPPED — requires human approval, logged in todo.md] Post-gate stop trades held to the 15:55 flatten instead: −$273.26 vs −$386.20 actual, a +$112.94 delta (CRM alone +$115.32).** Direction of travel is real but it is a **risk-widening** change — it requires eating GOOGL #217 at −$116.77 and ENPH #200 at −$73.08 versus −$31.13/−$43.68 actual, i.e. an unbounded intraday tail in exchange for a bounded one. **Not mine to take: `MAX_RISK_PCT`, the stop, and every loss limit stay exactly where they are.** Proposed in `todo.md` for the human, with the tail cost stated.
4. **[NOT SHIPPED — noise] Any exit-geometry parameter change.** IMP-032's verdict stands and today reinforces it: the post-gate noise budget is **$248** against a book whose whole post-gate P&L is −$215. **51 trades and IEX 1-min bars cannot resolve an exit change**, and today is IMP-031's second live session with n=0 decisive cases. Do not stack.
5. **[NOT SHIPPED — measured, no defect] The four Alpaca 504s.** `consider_entries` fails last in `tick()`, after `manage_exits` and `manage_stops`, so nothing risk-bearing was skipped. Cost: four entry cycles in a 12-minute window during which the VWAP gate was vetoing everything anyway. No change warranted.

### Notes for pre-market research (next session — Fri 08-14)
- **⚠️ Equity closed $7,464.62 (−25.35%) — BELOW the $7,500 line by $35.38.** State it at the top and say below. The escalation is open and the posture is unchanged: **do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols.**
- **July PPI came in cooler than feared and the tape took it risk-on (S&P +0.3%, Nasdaq +0.5%, AI/semis led).** The 08-13 run was blind to it; that gap is now closed. **Fri 08-14 has its own 08:30 blind spot: retail sales + UMich.** FOMC minutes 08-19.
- **AMAT reported after today's close — check its reaction FIRST.** Five on-list names are semis (AMD, INTC, MU, NVDA, QCOM) plus TSM/AVGO adjacent; a sympathy gap is a regime input for the VWAP gate, not a reason to touch a name.
- **CRM had a 5.89% range day and closed near its high (~201.3) after a morning flush to ~191.** Worth a look for a catalyst — sonar claimed none, which given the size of the move is more likely a sonar failure than a fact. **CRM is not a park candidate**: it did exactly what a volatile name does; the bot's stop was the mismatch.
- **GOOG and QQQ both traded a session range SMALLER than their own 1R stop today** (0.99% vs 1.74%; 1.35% vs 1.49%). This is the SPY/QQQ stop-floor finding generalising beyond the index ETFs. **It is an engine stop-geometry question owned by the weekly — do NOT park GOOG or QQQ over it.**
- **TSLA (14), NFLX (14), ABNB (12) were vetoed all day at +0.46% to +0.89% above VWAP** — persistent gap-and-hold names the gate is correctly refusing. **ABNB is now ~7 sessions fill-less; blocked ≠ park (SE precedent).**
- **AAPL, GOOG, QCOM, META, AMD, WMT triggers all carry forward unchanged** — none traded today, so none can have fired. **META's trial opening statements are Tue 08-18** (the 08-17 run owns it); **WMT reports pre-open Thu 08-20** (the 08-19 run owns the one-day event park); **AMD hits its pre-registered 10-session no-fill mark Mon 08-17** and that is a weekly question, not a unilateral park.
- **⚠️ Sonar is 10-for-10 unreliable** — today it gave "no company-specific catalyst" for GOOG/NVDA/CRM (CRM moved 5.89%) and an S&P figure identical to yesterday's. **Demote it below WebSearch or drop it.**
- **Strategy posture untouched by this routine:** `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, `ENTRY_CUTOFF_ET` 15:30, `FLATTEN_ET` 15:55, paper endpoint, no-overnight rules — **all unchanged.** The `watchlist` table was not written to.

---

## 2026-08-14 — Daily Review

### Stats
- **4 trades (1W/3L), net −$71.51 (−0.958%). Equity $7,464.40 → $7,392.89.** Win rate 25.0%; the one "win" is AAPL **+$0.73** (+0.02R), a scratch. Avg win +$0.73, avg loser −$24.08, **PF 0.01**.
- ⚠️ **New equity low: −26.07% from the $10,000 start, $107.11 BELOW the $7,500 review line** (it was $35.38 below yesterday). **Fourth consecutive session under the line; the −25% escalation is a human decision point and remains open and unanswered.**
- Broker reconciled and **clean**: Alpaca equity $7,392.89 = cash $7,392.89, `last_equity` $7,464.40 (day −$71.51, matches the DB to the cent), **0 positions, 0 open orders**, `trading_blocked` false. DB `daily_summary` agrees: 4 in / 4 out, close $7,392.89. **No qty drift, no missed fill, nothing carried overnight.**
- All-time: **244 closed, 38.1% win, −$2,310.86, PF 0.60.** Post-VWAP-gate (≥07-25): **55 trades, 40.0% win, −$286.23, PF 0.54, expectancy −$5.20/trade** (was −$4.21 over 51 — the bleed is not decelerating).
- Service `active`, **NRestarts=0, zero errors and zero tracebacks in the whole session** (the four Alpaca 504s belong to 08-13, not today).
- Market context (WebSearch/sonar-corroborated, own SIP bars authoritative): **July retail sales −0.6% m/m, core −0.3%, and the 10:00 ET preliminary UMich sentiment collapsed to 51 from 55.2** — the in-session binary the pre-market run flagged. The tape faded on it: **SPY 776.08 (−0.23% from 777.88), a mild, choppy risk-off drift, not a rout.** *(Sonar's twelfth session: it produced the macro numbers correctly this time but returned "no company-specific catalyst" for all three single names and gave no index close.)*

### Trade-by-trade review
Every entry today was a **`MA` signal with `breakout_score` = 0.0000**, confidence **60.19–62.57** — the bottom of the permitted band. **For the THIRD consecutive session not one trade was a breakout.** The VWAP gate logged **zero vetoes** today (43 yesterday): nothing was ever stretched enough to refuse.

| # | Sym | Entry | Exit | Conf | 1R (stop dist) | MFE | MAE | green min | rng/1R | Exit | P&L |
|---|-----|-------|------|------|----------------|-----|-----|-----------|--------|------|-----|
| 255 | META | 09:41:40 @ 596.328 | 15:55:29 @ 590.020 | 60.2 | 7.69 (1.29%) | **+0.46R** | −0.86R | 43/374 | 1.64 | EOD_FLATTEN | **−$25.23** |
| 256 | SPY | 09:46:27 @ 778.240 | 15:55:29 @ 776.057 | 62.6 | 11.40 (1.46%) | +0.05R | −0.25R | 23/369 | 0.30 | EOD_FLATTEN | **−$6.55** |
| 257 | QCOM | 09:46:27 @ 166.580 | 11:23:01 @ 163.690 | 60.3 | 2.86 (1.72%) | +0.11R | **−1.05R** | 4/97 | 1.32 | **STOP** | **−$40.46** |
| 258 | AAPL | 11:35:41 @ 305.740 | 15:55:31 @ 305.831 | 60.2 | 4.55 (1.49%) | +0.11R | −0.17R | 90/260 | 0.70 | EOD_FLATTEN | **+$0.73** |

- **QCOM #257 — 57% of the day's loss, and the day's only trade whose exit geometry engaged.** Entered 09:46 on a conf-60.3 MA signal, it was green for **4 of its 97 minutes**, peaked at **+0.11R**, and went to a full **−1.01R** stop at 11:23. **Root cause: signal quality, not stop placement** — a trade that never traded 0.2% in its favour was simply wrong from the first minute. The stop was the *symptom*. Two secondary numbers: entry slippage was **+$0.37/share adverse** (log reference 166.21 vs 166.58 fill = +0.22%, $5.18 of the loss, the only adverse fill of the day), and the stop filled 3c through its 163.72 trigger. **Held to the 15:55 flatten it would have been −$13.16, a +$27.30 delta** — the same direction of travel as the human-gated stop finding in `todo.md`, on a fourth data point.
- **META #255 — the counter-example to "flattens are safe", and a near-miss on break-even.** Held 6h14m, 43/374 green minutes, MFE **+0.46R** in the first hour, then a slow all-day bleed to **−0.86R** MAE; the 15:55 clock caught it at −0.82R, one-sixth of an R from being a full stop. **Root cause: regime.** META never had a company catalyst; it tracked the post-UMich fade. Note the MFE: **+0.46R is the third consecutive session with a peak just under IMP-031's +0.5R break-even trigger** (CRM 0.45R, NVDA 0.43R on 08-13).
- **SPY #256 — structurally inert, exactly as predicted.** Session range **0.43% against a 1.46% stop = rng/1R 0.30**, the most extreme case yet recorded. MFE +0.05R, MAE −0.25R. Neither the stop, the target, the trail nor break-even could be reached by any price SPY traded today; the outcome was set entirely by the 15:55 clock. **Not a signal failure and not a stop failure — a scale mismatch**, the `MIN_STOP_PCT` 1.50% floor sitting on an instrument that moved 0.43%.
- **AAPL #258 — inert and harmless.** 260 minutes, 90 green, MFE +0.11R, MAE −0.17R, rng/1R 0.70. Entered 11:35 (the only afternoon entry), closed +$0.73. Nothing to fix here.
- **⚠️ Concentration: the 3-position cap was filled in 5 minutes and 16 seconds, by three correlated longs — one of which was SPY itself.** META 09:41:40, SPY 09:46:27, QCOM 09:46:27. From 09:46 the book was one directional bet on "US large-cap up" with no capacity left for the rest of the session; the 10:00 UMich miss then hit all three at once. AAPL only got a slot because QCOM stopped out at 11:23. **This is a book-construction observation, not a shipped change — see candidate 3.**

### What worked / what didn't
- **Worked — IMP-033, partially, and the broker record proves which half.** Alpaca's own timestamps: stop legs cancelled **19:55:11.478Z**, limit legs **19:55:16.43Z (5.0s later)**, and **pass 1 created all three liquidations at 19:55:16.71–16.95** — i.e. within 0.3s of the shares being released. **The 10-session run (07-31 → 08-13) of first passes that submitted *nothing* is over, and today's liquidations were created earlier than in any of the 16 sessions sampled** (next-earliest 19:55:25). The book was **flat at 19:55:31.7 vs 19:57:29 yesterday — ~118 seconds less exposure past the deadline.**
- **Didn't work — the other half of IMP-033, and it is today's shipped fix.** Alpaca then took **12.4–15.0s to fill** those sells (with an unprecedented **3.8s of queueing** before `submitted_at`, vs ≤0.12s on every other session sampled) against a **shared 8s** budget. The fill wait expired at ~19:55:25 with the sells still working, so the engine logged **"EOD flatten incomplete — 3 position(s) still open"** at 15:55:26 over a book that was flat five seconds later, and only recorded the exits on the next poll (**DB exit_time 15:56:28 vs the true 15:55:29 fill**). **A false alarm on the one message that signals a genuine naked-overnight risk.** → IMP-034.
- **Didn't work — the structural pattern reproduced for a third straight session.** Bucketing all 55 post-gate trades by *session range ÷ 1R*: today SPY (0.30) and AAPL (0.70) were physically unreachable and netted **−$5.82 combined**; META (1.64) and QCOM (1.32) were reachable and cost **−$65.69**. **The bot still profits where its exit logic cannot act and loses where it can.**
- **Didn't work — the exit-reason split widened again.** All-time **`STOP` n=106, −$4,737.49, PF 0.02, 7.5% win** vs **`EOD_FLATTEN` n=113, +$392.88, PF 1.42** and `TAKE_PROFIT` n=25, +$2,033.75. Post-gate: stops **−$426.66 (PF 0.07)**, flattens **+$84.71 (PF 1.54)**. **Every exit path this bot owns is profitable except the stop, and the stop remains larger than the entire lifetime loss.**
- **IMP-031 recorded n=0 decisive cases for a THIRD consecutive session** — but META's +0.46R is the third near-miss in a row. Its mechanism only bites at peak ≥ +0.5R. **Still no harm, still no measured benefit. Let it run; do not tune the trigger** (IMP-032 already swept it and found only noise).
- **Nothing to fault in execution besides QCOM's fill.** Net entry slippage across the four was **favourable** (META −$1.27/share, SPY −$0.27, AAPL −$0.04 vs the logged reference; QCOM the sole adverse leg).

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-034 — alarm integrity] Give the flatten's fill phase its own budget, sized off the broker record.** 36 EOD liquidations over 16 sessions (07-24 → 08-14): median fill **2.8s**, p90 **8.7s**, max **15.0s** — and what the wait must cover is the *worst fill of the session*, which **exceeded 8s on 3 of those 16** (08-06 8.1s, 08-10 8.7s, 08-14 15.0s). New `FLATTEN_FILL_TIMEOUT_SEC = 25.0` (1.7× the worst on record); the cancel phase keeps its 8s (worst observed 5.0s). **It is a reporting wait, not an exposure wait** — the sells are already working before it starts — and it is **skipped entirely when no close was accepted**, so a rejected pass hands straight back to IMP-002's retry instead of burning the budget. Both phases together are 33s, inside one 60s poll and the 15:55→16:00 runway. **Pure execution plumbing: no entry logic, no signal, no sizing, no stop, no exit geometry, no risk limit touched — so IMP-031 keeps its clean read.**
2. **★ THE STRATEGY VERDICT IS UNCHANGED AND THE EVIDENCE AGAINST THE SYSTEM GREW AGAIN: 244 trades, PF 0.60, −26.07% of the account, post-gate expectancy now −$5.20/trade (was −$4.21 nine sessions ago).** Ten refuted discriminators stand: confidence, volume, extension, time-of-day, index-EMA regime, SPY-VWAP regime, opening-range blackout, never-green time-stop, break-even-trigger sweep, stop-floor binding, and the 42-cell MFE-by-time grid. **Today added a third consecutive session with `breakout_score` = 0.0000 on every fill — the bot has not taken a single breakout in three sessions and its name is a breakout bot.** The honest reading is unchanged: a zero-edge entry plus a −1R tail. **This is a human decision point — fund it, retire it, or halve the size — and it is now four sessions overdue with the account at a new low. I am not going to disguise it with another parameter.**
3. **[NOT SHIPPED — logged in `todo.md` for the human] Correlated book construction: the 3-slot cap filled in 5m16s with three same-direction large-cap longs, one of them SPY.** Today is one clean observation, not a dataset — and every diversification variant I could ship (a per-slot cooldown, an index-vs-single-name exclusion, a correlation cap) is an **entry-side** change on a book whose post-gate noise budget already exceeds its total P&L. **Measure it first: I will need the same statistic over 30+ sessions before it is anything but a story about one afternoon.** Recorded, not actioned.
4. **[NOT SHIPPED — REFUTED, do not re-propose] Anything that keys off QCOM's never-green stop.** QCOM peaked +0.11R and lost −1.01R, which is precisely the population the 08-13 grid tested: **every non-degenerate cell of the 42-cell "scratch if MFE hasn't reached X·R by T minutes" sweep is negative.** Today does not revive it.
5. **[NOT SHIPPED — needs human approval] Holding stopped trades to the flatten.** Today's QCOM adds a fourth data point (−$13.16 vs −$40.46 actual, **+$27.30**), consistent with the +$112.94 post-gate delta already in `todo.md`. **It is still a risk-widening change and still not mine to take.**

### Notes for pre-market research (next session — Mon 08-17)
- **⚠️ Equity closed $7,392.89 (−26.07%) — a NEW LOW, and $107.11 BELOW the $7,500 line.** State it at the top and say below. Fourth consecutive session under the line. Posture unchanged and non-negotiable: **do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols.**
- **★ QCOM'S PRE-REGISTERED TRIGGER FIRED TODAY.** The 08-14 run registered *"one more never-green full-1R stop"*: QCOM #257 was green for **4 of its 97 minutes**, peaked **+0.11R**, and took a full **−1.01R** stop for **−$40.46**. It is now **0W/3, −$120.88**, the worst name on the board by dollars. **The trigger is fired and the park decision is the pre-market routine's to make — this review does not touch the `watchlist` table.**
- **Record what the market did with Friday's data on Monday.** July retail sales **−0.6% m/m** (core −0.3%) and preliminary UMich sentiment **51 vs 55.2** both missed badly and the tape faded into the close (SPY 776.08, −0.23%). **FOMC minutes Wed 08-19** — check whether the September-hike debate moved over the weekend.
- **★ THE THREE QUEUED EVENTS ARE NOW IMMINENT: META's trial opening statements Tue 08-18 (the 08-17 run owns the one-day park — and META traded today, −$25.23), WMT pre-open Thu 08-20 (the 08-19 run), CRM Wed 08-26 (the 08-25 run).** Do not let them collide unnoticed.
- **AMD hits its pre-registered 10-session no-fill mark Monday** (last fill 07-22). **That is a weekly question, not a unilateral park**, and a park still needs a fill. ABNB (fill-less since 07-15) is in the same category.
- **AAPL healed further and its trigger should probably be retired**: it traded today (#258, +$0.73), had the steadiest chart on the board (MFE +0.11R / MAE −0.17R over 4h20m) and gave the bot its only non-negative trade. **Check whether it has reclaimed the 50MA and, if so, retire the trigger rather than carrying it a fourth session.**
- **SPY's stop-floor mismatch hit its most extreme reading yet: a 0.43% session range against a 1.46% stop (rng/1R 0.30).** **This is engine stop geometry owned by the weekly review — do NOT park SPY over it.** The weekly should note that today's SPY trade was structurally incapable of reaching any exit the bot owns.
- **The VWAP gate logged ZERO vetoes today, against 43 yesterday** — TSLA/NFLX/ABNB were not stretched on a soft tape. **Blocked ≠ park still holds, and today there was nothing to block.**
- **Strategy posture untouched by this routine:** `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, `ENTRY_CUTOFF_ET` 15:30, `FLATTEN_ET` 15:55, paper endpoint, no-overnight rules — **all unchanged. The `watchlist` table was not written to.**

---

## 2026-08-17 — Daily Review

### Stats
- Trades: **3 closed (2W / 1L)**, win rate **66.7%**. Net **+$5.46 (+0.074%)**. Winners **TSM +$13.24**, **NVDA +$0.05**; loser **QQQ −$7.83**.
- Avg winner **+$6.65** / avg loser **−$7.83** → **payoff 0.85**, **profit factor 1.70** (gross win $13.29 / gross loss $7.83). A positive day, but see "what worked" — the win rate is flattered by a $0.05 scratch, and the *directional* trade lost.
- **Broker reconciliation EXACT.** Alpaca `equity` **$7,398.13** vs `last_equity` **$7,392.67** → **+$5.46**, matching the DB net to the cent. **`/v2/positions` returns 0 — flat overnight, no drift, no missed fill.** Account ACTIVE, `trading_blocked` false. DB trade count (3) equals the broker's fill record.
- Equity **$7,398.13**, still **−26.02%** from the $10,000 start and **$101.87 BELOW the $7,500 line** — a fifth consecutive close under it. Today's gain does not change the standing escalation.
- Exit mix: **STOP 2 (+$13.29)**, **EOD_FLATTEN 1 (−$7.83)**. **No take-profit for the 5th straight session**; not one trade came within 1.0% of its TP. All-time TP rate now **25/247 (10.1%)**.
- Holding times: QQQ **6h09m**, NVDA **3h18m**, TSM **2h54m**. Entries **09:46 / 09:56 / 10:16 ET** — the 3-slot book was full by 10:17, as on 08-14.
- Intraday equity (broker portfolio-history, 15-min): **peak $7,438.65 (+$45.98) at 12:00 ET**, close $7,398.13 (+$5.46) → **max intraday drawdown $40.52 (−0.54%)** measured off that peak. **Equity never printed below the $7,392.67 open** — the 8% daily-loss halt was never within two orders of magnitude of firing. ⚠️ **The bot gave back 88% of its intraday peak profit.**
- Signals: all three fills were **`MA` type with `breakout_score` = 0.0000** — the **fourth consecutive session** in which the breakout leg, the strategy's namesake, contributed nothing. Confidences **60.26 / 62.48 / 62.65**.
- **VWAP gate: 5 vetoes** (AMD ×3 at +0.68% / +0.45% / +0.32% above session VWAP; XOM ×2 at +0.45% / +0.49%), against zero on 08-14. The gate was live and selective.
- Market context (Perplexity `sonar`, corroborated by own SIP bars): **choppy, mildly risk-off — S&P −0.15%, Nasdaq ~flat**, indices sliding to session lows into the close. ⚠️ **Sonar's 13th consecutive weak session:** it returned "no company-specific catalyst identified" for **every** name queried (QQQ, NVDA, TSM, AMD, XOM). Regime read used; name-level reads discarded.

### Trade-by-trade review

**#261 TSM — WIN +$13.24 (+0.62%), the day's only earned money.** Entry 10:16:57 @ **429.462** (conf 62.65, MA), qty 5, stop 422.98 (**1R = 6.482 = 1.509%**), TP 439.08 (1.48R). The trail worked exactly as designed: stop ratcheted **422.98 → 429.84 → 430.51 → 431.05 → 431.56 → 432.15** across five raises (11:04 → 12:09), exiting **STOP 13:10:32 @ 432.11** for **+0.41R**. Log-derived MFE ≈ **435.39 (+0.91R)**, so it gave back ~0.5R from the peak — that is the trail's designed cost, not a defect. **Root cause of the win: exit machinery, not entry selection.** Slippage on the stop-market exit was **$0.04/share** (432.15 stop → 432.11 fill) — negligible.

**#260 NVDA — SCRATCH +$0.05 (+0.002%), and the most important trade of the day.** Entry 09:56:30 @ **226.201** (conf 62.48, MA), qty 10, stop 222.90 (**1R = 3.301 = 1.459%**), TP 231.38. Exit **STOP 13:14:57 @ 226.206** — a break-even stop-out.
- ★ **This is IMP-031's FIRST DECISIVE CASE in its entire life, and it matched the pre-registration exactly.** IMP-031 (live since 08-12, `n=0` decisive cases through 08-14) made the break-even stage test `max(live, peak_high_since_entry)` instead of the 60s live point-sample, and pre-registered its own narrow bound: *it can only change an outcome when `peak ≥ +0.5R AND live < +0.5R`.* At the **11:55:16** poll the log records `live 227.75, peak 227.87`. The trigger is `226.201 + 0.5 × 3.301 =` **227.8515**. **Live 227.75 was BELOW it; only the bar-high 227.87 cleared it.** Break-even armed, stop moved 222.90 → 226.20.
- **Counterfactual, and it is decisive.** Without IMP-031 the stop stays at **222.90** all day. NVDA's post-11:55 tape never returned to the trigger — session high after that bar was **227.749** and it bled steadily to an afternoon low of **224.86**, i.e. **$1.96 above the original stop, which was never touched.** So the trade survives to the EOD flatten and closes at ≈**225.04** → **10 × (225.04 − 226.201) = −$11.61**. **IMP-031 was worth +$11.66 on this trade.**
- **The trail did not silently do this instead** — had any live sample cleared 227.8515 the trail stage (which reads live by design) would have moved the stop to ≈`227.92 − 1.6505 =` **226.27**. The log records **no second NVDA stop raise all afternoon**. The absence is the evidence: the live tape was never sampled above the trigger, so only the bar-high path could have armed anything.
- **Without IMP-031 today is −$6.20, a losing day. IMP-031 flipped the sign.** ⚠️ **Stated with its caveat: n=1, worth $11.66, inside the standing $248 noise budget. This does not validate the mechanism — it is one pre-registered case resolving in favour. Do not re-tune the exit layer on it.**

**#259 QQQ — LOSS −$7.83 (−0.36%), and structurally unwinnable.** Entry 09:46:56 @ **732.0333** (conf 60.26, MA), qty 3, stop 721.06, TP 748.51. Held **6h09m** to **EOD_FLATTEN 15:56:03 @ 729.4233**.
- **Root cause is NOT signal quality, stop placement, entry timing, slippage or a bug — it is the known range-vs-1R mismatch.** Stop distance **1R = 10.973 = 1.499%**, which is the **`MIN_STOP_PCT` 1.5% floor**, not an ATR-derived level. QQQ's entire session range was **734.58 − 729.27 = 5.31** → **range / 1R = 0.48**. **The whole day's range was less than half the stop distance**; the TP sat **+16.48** away. Neither bracket leg was physically reachable from the first second of the trade. MFE **+0.23R**, MAE **−0.25R** — the trade never had a decision to make.
- This is the **7th consecutive post-gate SPY/QQQ trade to exit EOD_FLATTEN** (now ~−$14.87 net across them). Today's 0.48 is less extreme than SPY's 0.30 on 08-14, but it is the same defect. **It remains engine stop geometry owned by the weekly review, and explicitly NOT a watchlist action** — recorded here for the fourth time rather than acted on unilaterally.

### What worked / what didn't
- ✅ **The exit layer did 100% of the work, and it is now the only part of this bot with demonstrated value.** TSM's trail banked +0.41R; NVDA's break-even converted a −$11.61 EOD bleed into a $0.05 scratch. **Both winners were manufactured by exits. Zero came from entry selection.**
- ✅ **IMP-035 (weekly, shipped 08-15) PASSES its pre-registered condition, which was a NULL result.** All three fills scored **60.26 / 62.48 / 62.65** and every one sized at the **0.5% risk floor** — identical to what the old `(60,0.5) (70,1.0) (80,1.5) (90,2.0)` ladder would have granted, since all three sit in the `[60,70)` band. **Sizing and trade selection were unchanged, which is exactly the pass condition.** The alarm it ships to catch (confidence drifting into the upper bands) did not fire. `scripts.check_sizing_ladder` ALL GREEN. Sizing was risk-driven for QQQ (qty 3) and TSM (qty 5); **NVDA was notional-capped at qty 10 against a risk-implied 11.2** — the cap, not the ladder, bound it.
- ✅ **IMP-034 got its first clean live read.** The EOD flatten ran **one pass, no rejection, no false "incomplete"**: liquidation created 19:55:59.453Z, submitted 19:55:59.487Z, **filled 19:56:02.353Z (2.87s)**, book verifiably flat. Contrast 08-14, which logged the spurious *"EOD flatten incomplete — 3 position(s) still open"*. **Weak evidence (single position, an easy 2.87s fill well inside the 25s budget) but it is the right sign.**
- ✅ **The VWAP gate earned its keep**, refusing 5 stretched entries (AMD three times as it ran +0.68% → +0.32% over VWAP; XOM twice). AMD and XOM were the two names the gate blocked and neither was given away cheaply.
- ❌ **The entry signal still has no demonstrated edge, and today does not challenge that verdict.** The one trade allowed to express a directional view for a full session (QQQ, 6h09m) **lost**. The two "wins" were an exit-manufactured scratch and a trailed 0.41R. **A 66.7% win rate on 3 trades with a 0.85 payoff is noise, not a signal.** All-time remains **247 closed, PF ~0.60, expectancy negative**.
- ❌ **88% of the intraday peak was returned** ($45.98 at 12:00 ET → $5.46 at the close). All three positions were opened in the first 47 minutes and the book then had nothing to do but decay from noon; QQQ alone bled the whole afternoon in a position that could not reach an exit.
- ❌ **Observability defect found while gathering evidence (no trade impact, recorded so the next run does not trip on it).** The unit redirects `StandardOutput`/`StandardError` to `/var/log/ustradewisbot/bot.log`, so **`journalctl -u ustradewisbot.service` returns only 5 systemd lines for the whole session and none of the bot's own output** — the routine's prescribed evidence command is effectively dead. Worse, **logrotate fires at 17:00 UTC = 13:00 ET, mid-session**, so every trading day is split across two files: today's entries and stop-raises are in `bot.log.1` while TSM's exit, NVDA's exit and the flatten are in `bot.log`. A future run reading only `journalctl` could wrongly conclude the bot did nothing. **Read `/var/log/ustradewisbot/bot.log` AND `bot.log.1`.**

### Lessons & improvement candidates
1. **(Shipped today, as housekeeping) Commit IMP-034.** It has been running **unversioned** since the 08-15 restart. See the improvement log — this was explicitly assigned to today by IMP-035's entry, it is the bot's hardest invariant (no overnight holds), and a `git checkout` or redeploy would silently revert it.
2. **★ Let IMP-035 and IMP-031 run. Do NOT ship a strategy change.** Today is IMP-035's **first live session** (Monday rule) and IMP-031's **first decisive case**. Both resolved in favour on `n=1`. Stacking a change now destroys the attribution on two open reads at once.
3. **The range-vs-1R mismatch is now the best-evidenced structural defect the bot has**, at 7 consecutive post-gate SPY/QQQ EOD_FLATTENs and readings of 0.30 and 0.48. **It is a weekly/engine question** (the honest fix is an ATR-relative or instrument-aware stop floor, or declining the entry when `session_ATR / 1R` is below some bound — a genuine entry-side filter, not a `MIN_STOP_PCT` loosening, which would be risk-widening and is NOT authorised).
4. **The breakout leg has now contributed 0.0000 to four consecutive sessions' fills.** IMP-035 deliberately declined to remove it from the scorer (removal risks a confidence-scale shift). That reasoning still holds. **Keep watching, do not tidy.**
5. **Do not read today as a turnaround.** +$5.46 on 3 trades, of which +$11.66 is attributable to one exit mechanism firing once. The strategy verdict from the weekly (grade D, no demonstrated edge) is **unchanged**.

### Notes for pre-market research
- **⚠️ Equity closed $7,398.13 (−26.02%), still $101.87 BELOW the $7,500 line — say "below" at the top.** Fifth consecutive close under it. **The −25% escalation remains an OPEN, UNANSWERED human decision point.** Posture unchanged: **do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols.** A +$5.46 day is not a reason to relax any of that.
- **★ META is parked for TODAY'S (08-18) trial opening statements — this was the point of the park. RE-ENABLE IT AT THE 08-19 RUN**, and re-verify tradable/active on `/v2/assets`. It must not drift into a six-week park.
- **★ QCOM stays parked** on eight trades of evidence. It cannot generate a behaviour change while parked, so any re-enable must be a deliberate argued decision, not housekeeping.
- **TSM was the day's best name (+$13.24, trailed cleanly through five stop raises) and NVDA behaved well mechanically.** Both are working as intended — **no action, just do not park them for a quiet day.**
- **AMD drew 3 of today's 5 VWAP vetoes** (+0.68% / +0.45% / +0.32% over VWAP) after Friday's +6.50%. **It is signalling again after a no-fill run since 07-22 — the 10-session no-fill question is now clearly moot.** Blocked ≠ park; the gate is doing its job.
- **XOM drew the other 2 vetoes** (+0.45% / +0.49%). Also signalling, also correctly refused. No action.
- **QQQ chopped in a 5.31-point range (0.48× its own 1R) and was structurally incapable of reaching either bracket leg.** **Do NOT park QQQ over this** — it is engine stop geometry owned by the weekly, exactly as with SPY on 08-14.
- **Watch the FOMC minutes Wed 08-19 14:00 ET** — the week's event, in-session, and the July decision was reported as the closest Fed call in years. **The 08-19 pre-market run owns whatever posture that deserves.**
- **Sonar is now 13-for-13 unreliable** — today it returned "no specific catalyst" for all five tickers queried. **Lead only, never an action source; verify everything against WebSearch + Alpaca SIP bars.**
- **Evidence-gathering note for future runs: `journalctl` is EMPTY for this service.** Bot output goes to `/var/log/ustradewisbot/bot.log`, and logrotate splits each session at 17:00 UTC (13:00 ET) — **read both `bot.log` and `bot.log.1`** or you will miss every afternoon exit.
- **Strategy posture untouched by this routine:** `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, `ENTRY_CUTOFF_ET` 15:30, `FLATTEN_ET` 15:55, paper endpoint, no-overnight rules — **all unchanged. The `watchlist` table was not written to.**
