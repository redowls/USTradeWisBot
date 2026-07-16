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
