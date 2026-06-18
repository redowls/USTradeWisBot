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
