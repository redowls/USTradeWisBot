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
