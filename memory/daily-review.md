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
