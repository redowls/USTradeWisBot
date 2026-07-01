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
