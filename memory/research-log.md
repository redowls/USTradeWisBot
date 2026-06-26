# Research Log

Pre-market watchlist research journal for USTradeWisBot. **One dated entry per day**,
written by the `uswisbot-premarket` routine (11:45 UTC, Mon–Fri) after reviewing
news + technical charts for every watchlist symbol and applying changes to the
`watchlist` table in the WisBot database.

Hard rules the routine must never break:
- NEVER park/remove a symbol that has an open position in the Alpaca account.
- Max **30 active** symbols.
- Every added symbol must be verified tradable & active on Alpaca (`/v2/assets/{SYM}`).
- Park with `is_active = 0` (keep the row, set a dated `notes`) instead of DELETE.

Entry template:

## YYYY-MM-DD — Pre-market Research

### Market context
(futures, key news, earnings today, sector momentum)

### Carried from daily review
(watchlist observations from memory/daily-review.md acted on today)

### Watchlist review
(symbols reviewed: news + technical verdict; keep / park / add candidates)

### Changes applied to watchlist
(exact adds/parks/re-enables with one-line reasons; "no changes" is a valid outcome)

### Final watchlist
(N active symbols, listed; service restarted: yes/no)

---

## 2026-06-15 — Pre-market Research

### Market context
S&P 500 futures ~7,490–7,530 (supportive); FOMC two-day meeting begins today, rate decision Wed Jun 17 at 2PM ET (Warsh's first as chair — 98–99% hold at 3.50–3.75% priced in, but ~70% odds of at least one hike by year-end). May CPI 4.2% YoY (Iran oil shock); May Industrial Production report due today. Sector rotation from mega-cap tech toward industrials/energy/staples; Russell 2000 at ATH; Nasdaq lagging (still ~2.6% below late-Oct 2025 peak). Market in cautious wait-and-see mode ahead of Warsh press conference — low-conviction breakout day expected.

### Carried from daily review
No prior daily-review entries (first run of this routine). Acted on trade-performance data queried directly from DB: past 15 trading days per-symbol P&L and win rates reviewed.

### Watchlist review

**Trade performance summary (last 15 days, closed trades):**
- TSLA: +$257.17, 3W 0L — only consistently profitable symbol
- XOM: +$12.38 · TSM: +$9.61 — small gains
- AAPL: −$9 · WMT: −$35 · NFLX: −$38 · UNH: −$46 · GOOG: −$51 · NVDA: −$75 · ABNB: −$95 · BAC: −$88 — losses but limited trades
- INTC: −$102 (1W 3L) · META: −$122 (0W 1L) · SE: −$142 (0W 1L) · MU: −$147 (0W 4L) · AMD: −$240 (0W 4L) · JPM: −$231 (0W 4L) · C: −$292 (0W 4L) · GOOGL: −$357 (0W 3L) — concerning
- AVGO, CRM, ENPH, QCOM, QQQ, SPY, WPM: zero signals generated in 15 days
- Account equity: $8,205 vs $10,000 start (−18%)

**Symbol-by-symbol verdict:**

BIRD: $3.80/share, $32M market cap, rebranded as "NewBird AI" after selling shoe business — sub-$5 speculative name, clear violation of liquid large-cap rule. → PARK

BABA: Pentagon "Chinese military company" designation Jun 8 2026, Q4 earnings miss, ADR delisting risk, BABA dropped 3.8% on the designation. Geopolitical proxy — can gap on US-China headlines at any time, not appropriate for intraday breakout strategy. → PARK

GOOG + GOOGL: Both on watchlist. PHASE-002 equivalence guard now prevents simultaneous holds; keeping both gives the bot two opportunities to catch the same underlying's move, which is the intended behavior. GOOG −$51 (1W 3L), GOOGL −$357 (0W 3L). Both underperforming but GOOGL's 0/3 warrants watching; not parking either today — insufficient evidence to drop GOOGL given small sample and guard now in place.

UNH: DOJ antitrust probe + FTC insulin case + Medicare Advantage scrutiny — multi-layered binary risk. Trade P&L: −$46 (2W 1L), acceptable. Jun 15 is UNH record date for $2.32 dividend (ex-date Jun 14) — may see small downward gap adjustment at open. Keep, but monitor for DOJ escalation.

INTC: Rebounded from ~$18 to ~$117; BofA upgraded to Buy, $135 target; Foxconn AI deal catalyst. Headline-sensitive but active trend — keep.

TSM: Record May revenue +30% YoY; 52-week high area; earnings Jul 16. Strong AI chip demand. Keep.

WPM: Gold/silver streaming, down 14–21% recently on commodity sell-off. Doesn't fit breakout strategy well (moves on commodity prices not market momentum); zero signals in 15 days. Watch for further deterioration — park candidate if still signaling nothing in one week.

MU, AMD, JPM, C: All 0% win rate over 4 trades each. Could be market environment (most of the list is losing). Not parking yet — too early to distinguish bad names from bad conditions. Revisit if losses persist.

INTC, ABNB, GOOGL: Concerning streaks but small trade samples. Watch.

No new additions: pre-FOMC caution, account down 18%, no high-conviction large-cap breakout setups identified that aren't already on the list.

### Changes applied to watchlist
- BIRD: parked 2026-06-15 — sub-$5 ($3.80) speculative AI pivot (NewBird), $32M cap — violates liquid large-cap rule
- BABA: parked 2026-06-15 — Pentagon Chinese-military-company designation 2026-06-08, ADR delisting risk, earnings miss — not suitable for intraday breakout

### Final watchlist
29 active symbols (reduced from 31 to 29 via two parks — within 30-symbol cap):
AAPL ABNB AMD AMZN AVGO BAC C COST CRM ENPH GOOG GOOGL INTC JPM META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT WPM XOM

Service restarted: yes — active, clean startup confirmed (06:50:11 UTC Jun 15).

### 11:45 UTC scheduled-run confirmation
Second pass of the day (the 06:50 entry above was an early test run; 11:45 UTC is the production cron slot). Re-verified state — no new information warrants additional changes:
- Positions: zero open (nothing locked). Equity unchanged at $8,205.65 (last_equity flat — no trades since Fri 06-12; Mon 06-15 has not traded yet).
- Market context refreshed: S&P futures firmer ~7,574 (Strong-Buy technical signal, up from the cautious open earlier) on US-Iran de-escalation hopes; chip sector recovering (AVGO ~$385). FOMC two-day meeting underway → decision Wed Jun 17 2PM ET; inflation >4% (Iran oil shock) keeps tape headline-driven. No watchlist large-cap reports earnings intraday today.
- Loser cluster (GOOGL 0W3L, C/AMD/JPM 0W4L, MU 0W4L): held per earlier reasoning — losses are broad across the list (regime, not name-specific) and the park threshold ("next week") has not arrived. Will reassess after this week. GOOGL still 0W3L (not yet the 0W4+L park trigger).
- Decision: **no further watchlist changes.** 29 active retained. Service NOT restarted (no changes since the 06:50 restart). Pre-FOMC caution → no adds.

### Notes for pre-market research (next session)
- Watch MU, AMD, JPM, C closely — four consecutive losses each with 0% win rate; if these persist into next week, park them and reduce symbol count further.
- WPM: if still generating zero signals by Jun 20, park it (precious metals proxy, doesn't fit strategy).
- GOOGL: watch for at least 1 win in next 5 trades; if trend continues (0W 4+L) consider parking and consolidating to GOOG only.
- FOMC decision Jun 17 2PM ET — expect choppy tape Wed afternoon; do not add new symbols until after Warsh press conference digested.
- Account equity at $8,205 (−18% from $10K start) — if drawdown reaches −25% ($7,500), flag for strategy review.

---

## 2026-06-16 — Pre-market Research

### Market context
Risk-on tape into FOMC. Mon 06-15 was a big rally — S&P +1.7%, Nasdaq +3.1% (best day since Mar 31), Dow record close — on a US–Iran preliminary de-escalation (Strait of Hormuz reopening, oil lower, inflation fears easing). Index futures climbing again pre-open ahead of the **FOMC decision Wed 06-17 2:00PM ET** (Warsh's first as chair; hold at 3.50–3.75% near-certain, dot-plot/guidance is the binary). First theoretical 100%-odds hike now pushed out to Mar-2027. VIX calm. **Note: market closed all day Fri 06-19 (Juneteenth)** — the post-FOMC signal lands Thu 06-18. Today's earnings (JBL, KEP, KTAND, ~10 small caps) include **no watchlist name** — no intraday earnings risk on the list.

### Carried from daily review (2026-06-15)
- TSLA = franchise name (only winner again, conf 97; 4W0L / +$348 over 14d). Keep top-of-list. ✅ retained.
- ENPH chopped/false-breakout at open; the double-entry was the IMP-001 bot bug (now fixed), not an ENPH problem. No park.
- C, MU, AMD, JPM (0W4-5L cluster) + GOOGL (0W3L): daily review explicitly judged this **broad-regime weakness, "not yet name-specific park triggers — reassess later this week."** Instruction was *watch*, not park. Honored: no parks today.
- WPM: park only if still zero signals by Jun 20 — not yet (today is 06-16).

### Watchlist review
- Positions: **zero open — nothing locked.** Equity $7,965.90 (flat vs last_equity; no trades since 06-15 close).
- Per-symbol P&L last 14d (66 closed, net **−$1,845**): only TSLA +$348, XOM +$12.4, TSM +$9.6 positive. Worst: GOOGL −$357 (0W3), C −$308 (0W5), AMD −$240 (0W4), JPM −$231 (0W4), MU −$147 (0W4). The list bled even on a +3.1% Nasdaq day → confirms **broad-regime / strategy underperformance, not symbol-quality** (all names are liquid large-caps that fit the strategy's liquidity bar; strategy fixes belong to the daily-review routine, not pre-market curation).
- No watchlist name has a disqualifying catalyst today (no intraday earnings, no halt/binary event). C is the single most matured park candidate (0W5L, breached its stated 0W4L watch line, weak conf-61 MA-only signals) — but the latest daily-review deliberately deferred it to "later this week," so held under watch one more session.
- Adds: none — pre-FOMC caution (prior guidance: no new symbols until Warsh presser digested). No high-conviction large-cap breakout setup not already on the list.

### Changes applied to watchlist
**No changes.** 29 active retained. Park triggers (MU/AMD/JPM/C "next week"; GOOGL 0W4+L; WPM zero-signal by 06-20) have not matured as of today; deferral honored to avoid churn.

### Final watchlist
29 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC C COST CRM ENPH GOOG GOOGL INTC JPM META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT WPM XOM
Service restarted: no (no changes).

### Notes for pre-market research (next session)
- **Post-FOMC (Thu 06-18) is the decision point for the loser cluster.** If C (0W5L), MU/AMD/JPM (0W4L) keep losing through Wed, park the persistent ones Thu to consolidate around the few earners (TSLA, XOM, TSM). C is first in line — it has already breached its 0W4L watch line.
- GOOGL still 0W3L — one more loss (0W4L) triggers the "consolidate to GOOG only" park.
- WPM: park if still zero signals by Fri 06-20 (precious-metals proxy, doesn't fit breakout strategy).
- FOMC Wed 06-17 2PM ET + Juneteenth Fri 06-19 closed → thin, headline-driven Wed PM and a 4-day week. Expect choppy, low-conviction breakouts; do not add names until the Warsh guidance is digested.
- Strategy concern for daily-review: the book lost on a +3.1% Nasdaq day — entries are not capturing broad up-moves. Flag if drawdown reaches −25% ($7,500); currently $7,966 (−20.3%).

---

## 2026-06-17 — Pre-market Research

### Market context
**FOMC decision day.** Futures mixed-to-higher into the meeting: Nasdaq-100 +0.6% (rebound after chips led equities lower Tue), Dow lower, S&P slightly up. Rate hold at 3.50–3.75% ~97% priced (Warsh's debut as chair) — the binary is the **dot plot / whether the Fed drops its easing bias** (May CPI 4.2%, a 3-yr high). Schedule ET: pending home sales + business inventories ~10:00, **rate decision 2:00PM, Warsh press conference 2:30PM**. CME FedWatch now prices ~40% odds of a hike by Dec vs ~0% cut. 10y 4.44%, oil ~$76, VIX calm. Today's earnings (JBL, KMX, ~8 names) include **no watchlist symbol** — no intraday earnings risk on the list. Reminder: **market closed Fri 06-19 (Juneteenth)** → 4-day week, post-FOMC signal lands Thu 06-18.

### Carried from daily/research review (06-15, 06-16)
- Loser-cluster park decision was explicitly **deferred to Thu 06-18 post-FOMC** ("if C/MU/AMD/JPM keep losing through Wed, park the persistent ones Thu"). Today is the FOMC chop day → honored, no parks.
- GOOGL park trigger = 0W**4**L → consolidate to GOOG only. Still 0W**3**L (no new GOOGL trade since 06-12) → not matured, hold.
- WPM park trigger = zero signals by Fri 06-20 → not yet (today 06-17), hold.
- "Do not add new symbols until the Warsh guidance is digested" → honored, no adds.

### Watchlist review
- **Positions: 3 OPEN — AMZN (10sh, −$9.4), BAC (46sh, +$12.0), C (18sh, +$15.9). All LOCKED** (cannot park). Equity $7,948.87 (last_equity $7,939.19), buying power $22,605, account ACTIVE.
- ⚠️ **Naked overnight holds:** all three were entered 06-16 (AMZN/C 09:41, BAC 10:24) and remain open pre-market 06-17 — the 15:55 ET EOD flatten did not close them despite the service being active since 06-15 21:29 UTC. No-overnight design violated; **flag for the daily-review/code routine** (this routine may not touch source code).
- Per-symbol P&L (last 14d, closed): only TSLA +$348 (4W0L), TSM +$9.6, XOM +$12.4 positive. Worst still GOOGL −$357 (0W3), C −$308 (0W5, now locked), AMD −$240 (0W4), JPM −$231 (0W4), **MU now −$182 (0W5)** — MU lost again 06-16 (10:23), advancing 0W4→0W5.
- C was the most-matured park candidate (0W5L) but is now **locked by an open position** → cannot park; revisit after it closes.
- MU is now a genuinely matured candidate (0W5L) but the prior two reviews judged the cluster **broad-regime weakness, not name-specific** (book lost even on a +3.1% Nasdaq day), and the park decision is scheduled for Thu 06-18. On FOMC chop day, no churn → hold MU one more session.
- No watchlist name has a disqualifying catalyst today (no intraday earnings, no halt/binary). No high-conviction large-cap breakout setup not already listed.

### Changes applied to watchlist
**No changes.** 29 active retained. All park triggers either un-matured (GOOGL 0W3L, WPM not yet 06-20), deferred to Thu 06-18 (MU/AMD/JPM loser cluster), or blocked by an open position (C). No adds — pre-FOMC caution.

### Final watchlist
29 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC C COST CRM ENPH GOOG GOOGL INTC JPM META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT WPM XOM
Service restarted: no (no watchlist changes).

### Notes for pre-market research (next session)
- **⚠️ Carry to daily-review TODAY:** 3 positions (AMZN/BAC/C) held overnight from 06-16 — EOD flatten failure / naked-overnight risk despite active service. Needs a code-side fix in the daily-review routine.
- **Thu 06-18 is the loser-cluster park day** (post-FOMC). Park the persistent 0W names — **MU (0W5L)** is now first in line (C is parked-by-default once its position closes; AMD/JPM 0W4L but no new trades since 06-09/06-10). Consolidate around earners (TSLA, TSM, XOM).
- GOOGL still 0W3L — one more loss (0W4L) triggers consolidate-to-GOOG-only.
- WPM: park if still zero signals by Fri 06-20.
- Warsh dot-plot/guidance digestion is the gate for any new adds; reassess Thu with a clearer regime read. Equity $7,949 (−20.5% from $10K) — flag for strategy review at −25% ($7,500).

---

## 2026-06-18 — Pre-market Research

### Market context
**Post-FOMC relief bounce.** Wed 06-17 was a hawkish-FOMC shock: Fed held 3.50–3.75% but the dot plot lifted the year-end median to 3.8% (9/18 participants now pencil a 2026 hike, one quarter-point hike fully priced by year-end), and the S&P fell −1.21% — its worst first-Fed-day under a new chair (Warsh) since 1994; all 11 GICS sectors closed lower. Today futures rebound: S&P +0.9%, Nasdaq-100 +1.6%, Dow +0.6%. **Dominant catalyst: INTC +9% pre-market on a reported Apple deal to design/build chips in the US — the whole semi complex is bid (SOXX +3.9%, MU +4.7%, NVDA +1.2%).** US–Iran interim peace deal sent oil lower (WTI ~$75). No watchlist name reports earnings intraday today. **Reminder: market closed Fri 06-19 (Juneteenth)** → today is the last session of a 4-day week. Bounce is a relief move on a divided-Fed backdrop, not a confirmed trend.

### Carried from daily/research review (06-15→06-17)
- **Today (Thu 06-18) was the explicitly-scheduled loser-cluster park day** ("park the persistent 0W names; consolidate around earners TSLA/TSM/XOM").
- MU "first in line" (0W5L) and AMD (0W4L) — **but both are semiconductors and today is a powerful semi-rally day on the INTC/Apple catalyst.** The losing streaks were repeatedly judged broad-regime weakness, not name quality; the sector tailwind they always lacked is finally present. Holding both one more session is a reasoned, evidence-based deferral (new material catalyst), not passive churn-avoidance. Neither added a fresh loss on Wed (MU last 06-16, AMD last 06-09).
- C (0W5L) — **locked by an open position**, cannot park.
- JPM (0W4L) — bank, no catalyst today, stale since 06-10: the one cluster member with no offsetting reason to wait → parked (executes the consolidation intent where it is cleanest).
- GOOGL 0W3L — trigger is 0W**4**L; no trade since 06-12, not matured → hold.
- WPM — park trigger is zero-signal by Fri 06-20; not yet → hold.

### Watchlist review
- **Positions: 2 OPEN — BAC (46sh, +$11.1), C (18sh, +$39.8). Both LOCKED** (cannot park). AMZN (overnight 06-16/17) has since closed. Equity $7,886.11 (last_equity $7,854.87, ACTIVE), cash $2,666, buying power $25,281, daytrade_count 0.
- ⚠️ **BAC and C have now been held multiple nights** (open since ~06-16, through 06-17 and into 06-18 pre-market) — the 15:55 ET EOD flatten is still not closing positions despite the service being active. Repeated naked-overnight risk; **carry to daily-review/code routine** (this routine may not touch source code).
- Per-symbol P&L (14d closed): only TSLA +$348 (4W0L), XOM +$12.4, TSM +$9.6 positive. Worst: GOOGL −$357 (0W3), C −$308 (0W5, locked), AMD −$240 (0W4), JPM −$231 (0W4, parked today), MU −$182 (0W5).
- Watchlist is well-positioned for today's catalyst (INTC, AAPL, NVDA, AVGO, QCOM, MU, AMD, TSM all in the bid semi/tech complex). INTC +9% on the Apple deal is on-list — best-positioned name today.
- Adds: **none.** Divided-Fed hawkish backdrop, relief bounce (not trend confirmation), account −21% from $10K. No high-conviction large-cap breakout not already listed; today's strongest names (INTC/semis) are already on the watchlist.

### Changes applied to watchlist
- **JPM: parked 2026-06-18** — 0W4L (−$231 over 4 closed trades), chronic loser, bank with no catalyst in today's semi-led tape, stale since 06-10. Executes the long-deferred loser-cluster consolidation on the cleanest member.
- MU/AMD held (semi catalyst today); GOOGL held (0W3L, trigger not matured); WPM held (zero-signal park date is 06-20). No adds.

### Final watchlist
28 active (reduced from 29 via one park; within 30 cap):
AAPL ABNB AMD AMZN AVGO BAC C COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT WPM XOM
Service restarted: yes — active, clean restart 11:49:04 UTC Jun 18.

### Notes for pre-market research (next session — Mon 06-22, market closed Fri 06-19 Juneteenth)
- **MU & AMD reassessment:** held today on the semi catalyst. If they signal today (06-18) and lose again (MU→0W6L, AMD→0W5L) with no win, park them Mon 06-22 — the catalyst rationale will have been tested and failed. If they win, the regime-weakness thesis is confirmed and they stay.
- **C (0W5L) is parked-by-default once its open position closes** — revisit the moment it is flat.
- GOOGL still 0W3L — one more loss (0W4L) triggers consolidate-to-GOOG-only.
- WPM: park if still zero signals by Fri 06-20 (note: 06-20 is a non-trading Saturday and 06-19 is closed → effectively decide Mon 06-22).
- **⚠️ Carry to daily-review TODAY:** BAC + C held multiple nights — EOD-flatten failure / naked-overnight risk persists. Needs the code-side fix.
- Hawkish, divided Fed + 4-day week + relief bounce → treat today's strength with caution; do not chase. Equity $7,886 (−21.1% from $10K) — flag for strategy review at −25% ($7,500).

---

## 2026-06-19 — Pre-market Research

### Market context
**US market CLOSED today — Juneteenth holiday.** Alpaca clock confirms `is_open=false`, next open **Mon 2026-06-22 09:30 ET**. No trading occurs today; this is a curation-only pass to set the watchlist for Monday's reopen. (Context for Monday: Wed 06-17 hawkish FOMC dot-plot shock, Thu 06-18 relief bounce led by INTC +9% on the reported Apple US-chip deal / broad semi bid; divided-Fed backdrop, one 2026 hike now priced. Treat Monday's tape on its own data — Thursday's bounce was relief, not a confirmed trend.)

### Carried from daily review (2026-06-18)
- **C (0W5L) is now FLAT** — 06-18 daily review confirms C and BAC closed at the 15:55 EOD flatten; C's open-position lock released → "the long-deferred C park can be executed." Live Alpaca check: **zero open positions** — confirmed.
- MU/AMD: held 06-18 on the semi catalyst; neither generated a qualifying entry, so the "park if they lose again" test did not trigger → reassessment carried to Mon 06-22 (no new evidence on a holiday).
- INTC/semis were the day's strength but produced no qualifying breakout — flagged to daily-review (gate may be slow on gap-and-go opens), not a watchlist issue.
- IMP-002 (verified, retried EOD flatten, commit 427ab21) shipped 06-18 — should end the naked-overnight breach that ran 06-16→06-18.

### Watchlist review
- **Positions: zero open — nothing locked.** Account ACTIVE, equity **$7,838.56** (last_equity flat — no trades since 06-18 close, as expected on a holiday), cash $7,838.56, buying power $31,354, daytrade_count 0. −21.6% from $10K start.
- **C** — chronic loser 0W5L (−$308 over 5 closed trades), breached its stated 0W4L watch line several sessions ago; the only reason it survived was the open-position lock, now released. This is the queued, well-documented park, not churn → PARK.
- **MU (0W5L) / AMD (0W4L)** — held on the standing semi-catalyst deferral; reassess Mon 06-22 once they actually signal+lose. No new trades → hold.
- **GOOGL (0W3L)** — park trigger is 0W4L (consolidate to GOOG only); no trade since 06-12 → not matured, hold.
- **WPM** — park trigger is zero-signal by Fri 06-20; effectively decide Mon 06-22 → hold.
- No disqualifying catalyst applies on a closed market. **Adds: none** — −21.6% drawdown, hawkish divided-Fed backdrop, relief-bounce (not trend), no high-conviction large-cap breakout not already listed.

### Changes applied to watchlist
- **C: parked 2026-06-19** — chronic loser 0W5L (−$308), breached 0W4L watch line; executes the long-deferred park now that its open position has closed (position lock released at the 06-18 flatten).

### Final watchlist
27 active (reduced from 28 via one park; within 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT WPM XOM
Service restarted: yes — active, clean restart 11:47:38 UTC Jun 19 (safe: market closed for Juneteenth).

### Notes for pre-market research (next session — Mon 06-22)
- **MU & AMD reassessment is due Mon 06-22** — held twice on the semi catalyst without a fresh test. If either signals Monday and loses again (MU→0W6L, AMD→0W5L), park it; if it wins, the regime-weakness thesis is confirmed and it stays. Consolidate around earners (TSLA, TSM, XOM).
- **WPM decision is due Mon 06-22** — park if still generating zero signals (precious-metals proxy, doesn't fit breakout strategy).
- **GOOGL** still 0W3L — one more loss (0W4L) triggers consolidate-to-GOOG-only.
- **Watch IMP-002 in action Mon:** first live trading session since the EOD-flatten fix — verify any position opened Monday is confirmed flat by 15:55 ET (no overnight carry into Tue 06-23).
- TSLA remains the franchise name (only consistent earner). Equity $7,838.56 (−21.6%) — flag for strategy review at −25% ($7,500).

---

## 2026-06-22 — Pre-market Research

### Market context
Week opens cautious. Index futures slightly lower pre-open: S&P 500 −0.2%, Nasdaq-100 ~flat, Dow −0.1%. Dominant macro: US–Iran talks show "encouraging progress" (Qatar/Pakistan report a roadmap to a final deal within 60 days) → oil eases (WTI ~$75.30, Brent ~$79). Backdrop is last week's hawkish-Warsh FOMC dot-plot shock (9/18 officials now pencil ≥1 2026 hike; S&P's worst Fed-day under a new chair since 1994) followed by a Thu relief bounce — a divided-Fed, one-hike-priced tape, not a confirmed uptrend. **This week's key event: PCE inflation (Fed's preferred gauge), watched closely given the hawkish posture.** Alan Greenspan died at 100 (not market-moving). First live trading session since IMP-002 (verified/retried EOD flatten) — daily-review will validate it.

### Carried from daily/research review (06-18→06-19)
- **MU (0W5L) / AMD (0W4L) semi-catalyst reassessment due today** — but the standing plan gates the park on Monday's *actual* trade outcome ("if either signals today and loses again, park it; if it wins, the thesis holds"), which only the post-close daily-review can evaluate. Both are liquid large-cap semis that fit the strategy's liquidity/breakout profile; the losses have been judged broad-regime, not name-specific. → held this morning; daily-review parks tonight if they signal+lose. **Note: MU reports fiscal Q3 earnings Wed 06-24 AFTER the close** — no intraday-hold risk for an EOD-flatten bot, but expect a volatile gap Thu 06-25.
- **WPM decision due today** — see below; executed.
- **GOOGL 0W3L** — trigger is 0W4L (consolidate to GOOG only); no new trade since 06-12 → not matured, hold.
- C (parked 06-19) and JPM (parked 06-18) remain parked.

### Watchlist review
- **Positions: zero open — nothing locked.** Account ACTIVE, equity **$7,838.56** (flat vs 06-18/06-19 close — no trades over the holiday weekend), cash $7,838.56, buying power $31,354. −21.6% from $10K. Clock `is_open=false`, next open Mon 06-22 09:30 ET (this run is pre-open).
- **WPM** — confirmed **0 signals all-time** in the `signals` table (and 0 closed trades). Park trigger (decide Mon 06-22) is matured. WPM is a gold/silver streaming name that moves on commodity prices, not the market-momentum the breakout strategy needs → PARK.
- Per-symbol P&L (21d closed) unchanged from Thu: only TSLA +$348 (4W0L), XOM +$12.4, TSM +$9.6 positive; worst GOOGL −$357 (0W3), C −$288 (parked), AMD −$240 (0W4), JPM −$231 (parked), MU −$182 (0W5).
- Other rarely-signalling names (AVGO, CRM, QCOM, QQQ, SPY) are liquid large-caps/ETFs that fit the strategy and signal-droughts here reflect the regime, not name-quality — not park candidates (only WPM is a structural strategy mismatch).
- **Adds: none** — −21.6% drawdown, hawkish divided-Fed backdrop, soft futures, PCE data looming this week; no high-conviction large-cap breakout not already on the list.

### Changes applied to watchlist
- **WPM: parked 2026-06-22** — zero signals all-time, precious-metals streaming proxy (moves on commodity prices, not market momentum) — does not fit the intraday breakout strategy. Executes the long-standing 06-20/06-22 zero-signal park trigger.

### Final watchlist
26 active (reduced from 27 via one park; within 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: yes — active, clean restart 11:48:39 UTC Jun 22.

### Notes for pre-market research (next session — Tue 06-23)
- **MU/AMD:** today (06-22) is the live reassessment — if either signaled and lost again, the daily-review should park it tonight; check the outcome before tomorrow. **MU earnings Wed 06-24 after close** → MU will gap Thu 06-25; treat MU's intraday action Thu with extra caution (no overnight risk, but wide ranges).
- **GOOGL** still 0W3L — one more loss (0W4L) triggers consolidate-to-GOOG-only.
- **Validate IMP-002:** 06-22 is the first live session under the fixed EOD flatten — confirm any position opened today is broker-confirmed flat by 15:55 ET (no carry into Tue 06-23).
- **PCE inflation data this week** — given the hawkish Warsh posture, a hot print could whipsaw the tape; do not add names into the event.
- TSLA remains the only consistent earner. Equity $7,838.56 (−21.6%) — strategy-review flag at −25% ($7,500), $338 of headroom.

---

## 2026-06-23 — Pre-market Research

### Market context
Directionless, two-sided tape. Monday 06-22 closed lower as megacaps slid — **Alphabet (GOOGL) led the megacap losses, Nasdaq Composite −1%** — overshadowing de-escalation optimism; chip shares were the lone tailwind. Futures had pointed lower on a rocky US–Iran talks restart (Trump's Strait-of-Hormuz "tolls" threat). The Hormuz MoU reopened the strait for a 60-day negotiating window, but Iran threatened to re-close it amid the Lebanon/Hezbollah flare-up → headline-driven, but **oil eased** (WTI ~$76.6 flat, Brent −1.45% to ~$79.4). Backdrop is the hawkish Warsh FOMC: short yields climbing, futures now price **~70% odds of a hike by September**, curve flattening. **Today's calendar is light on macro/earnings**; it ramps later — **FedEx reports late TODAY (after close, not on watchlist)**, **Micron (MU, on watchlist) late Wed 06-24**, **PCE Thu 06-25**. **No watchlist name reports during market hours today** → no intraday earnings risk on the list.

### Carried from daily review (2026-06-22)
- **IMP-002 VALIDATED in production 06-22** (first same-day open-and-flatten under the rewritten flatten: SPY/QQQ/TSM market-sold at 15:56:50 ET, Alpaca confirmed 0 open, no carry into 06-23). Live check this morning confirms **0 open positions** — the no-overnight contract held. ✅
- **IMP-003** (EOD-flatten P&L accuracy) only went live on the 06-23 00:57 UTC restart (the 06-22 "restart" didn't take — process ran pre-fix code through the close); next EOD flatten should record real fills — verify in tonight's daily-review.
- **MU/AMD:** NEITHER signaled 06-22, so the "park if it signals and loses again" test did NOT trigger — MU stays 0W5L, AMD 0W4L → reassessment carried forward (unchanged).
- **GOOGL** did not signal 06-22 — still 0W3L, park trigger (0W4L) not matured → hold.
- **Low-conf MA-only (conf 60–63) drag** flagged again (5 of 06-22's losers) — a strategy-side candidate (#2, replay validation first), not a watchlist removal; SPY/QQQ/TSM/META/AVGO are liquid and fit the strategy.

### Watchlist review
- **Positions: zero open — nothing locked.** Account ACTIVE, equity **$8,015.20** (flat vs 06-22 close $8,015.23 — no overnight change), cash $8,015.20, buying power $32,061, daytrade_count 0. **−19.8% from $10K** (above the −20% line; $515 to the −25%/$7,500 strategy-review flag). Clock `is_open=false`, next open 06-23 09:30 ET (this run is pre-open).
- Per-symbol P&L (14d closed): positive only TSLA **+$294.36** (2W0L), XOM +$61.60, BAC +$52.20, INTC +$49.00, AAPL +$12.33, TSM +$11.75, NFLX +$7.04. Worst: C −$240.07 (parked), GOOGL −$237.50 (0W3 all-time), SE −$142.35, META −$134.00, ENPH −$63.85, MU −$59.93 (0W5 all-time), JPM −$53.60 (parked), GOOG −$50.81.
- **GOOGL** led the megacap slide Monday — but that is a broad-market megacap drag, not a name-specific binary catalyst, and it did not signal 06-22. Still 0W3L all-time; trigger is 0W4L → hold (one more loss consolidates to GOOG only).
- **MU (0W5L) / AMD (0W4L):** matured loss records but the standing plan gates the park on a *fresh* signal+loss, which hasn't occurred (no MU/AMD trade since the streaks were set). Both liquid large-cap semis fitting the strategy; losses judged broad-regime → hold per plan. (Reminder: **MU earnings Wed 06-24 after close → MU gaps Thu 06-25** — trade MU's intraday action Thu with extra caution; no overnight risk for an EOD-flatten bot, but wide ranges.)
- **Zero-signal all-time: CRM, MSFT, QCOM** — all liquid large-caps that fit the strategy; the signal drought reflects the regime (most of the book under-signals), not name-quality. Only a *structural* strategy mismatch (WPM, already parked) warrants a curation park → hold all three.
- No watchlist name has a disqualifying catalyst today (no intraday earnings, no halt/binary). 
- **Adds: none** — directionless tape, hawkish-Fed (70% Sept-hike) backdrop, −19.8% drawdown, and FedEx (tonight)/Micron (Wed)/PCE (Thu) event risk later this week. No high-conviction large-cap breakout not already on the list; today's only relative strength (chips) is already covered (NVDA/AVGO/AMD/MU/INTC/TSM/QCOM).

### Changes applied to watchlist
**No changes.** 26 active retained. Every park trigger is either un-matured (GOOGL 0W3L < 0W4L; CRM/MSFT/QCOM are regime-droughts, not structural mismatches) or gated on a fresh signal+loss that hasn't occurred (MU/AMD). No adds into an event-heavy, directionless week. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: no (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Wed 06-24)
- **MU earnings Wed 06-24 AFTER the close** → MU gaps Thu 06-25. No overnight-hold risk for the EOD-flatten bot, but expect wide ranges Thu; treat MU intraday with extra caution. (FedEx reports tonight 06-23, not on watchlist — no direct list effect, but a soft FedEx print can pressure the broad tape Wed.)
- **GOOGL** still 0W3L — one more loss (0W4L) triggers consolidate-to-GOOG-only. It led the megacap slide Monday; watch if weakness persists.
- **MU/AMD** (0W5L/0W4L) — still gated on a fresh signal+loss; park if either signals and loses again.
- **PCE inflation Thu 06-25** — given the hawkish Warsh posture and 70% Sept-hike pricing, a hot print could whipsaw the tape; do not add names into the event.
- **Verify IMP-003 tonight:** the fix only went live on the 06-23 00:57 UTC restart — confirm any EOD_FLATTEN exit today records the real Alpaca fill (not exit==entry $0.00).
- TSLA remains the only consistent earner (+$294 14d, 2W0L). Equity $8,015.20 (−19.8%) — $515 of headroom to the −25% ($7,500) strategy-review flag.

---

## 2026-06-24 — Pre-market Research

### Market context
Wed futures **mixed** — Dow lower, Nasdaq 100 / S&P 500 modestly higher, a fragile rebound attempt after **Tuesday's >2% Nasdaq drop on a semiconductor plunge** (Micron, SanDisk hit hardest; Greed Index in 'Fear'). AI-trade concerns and chip weakness still the dominant theme. Macro: easing Iran tensions vs. a still-live Fed hike risk (≈70% Sept-hike pricing). **Earnings: MU reports fiscal Q3 today AFTER the close (~4:30 PM ET), options pricing a ~14% move.** **PCE inflation Thu 06-25** — event-heavy back half of week.

### Carried from daily review (06-23)
- "MA-only conf 60–62 names are NOT low quality" (IMP-004 refuted the floor-raise) — **kept** XOM/BAC/CRM/WMT and the whole MA-only book; no parks on the conf-60–62 thesis.
- **MU/AMD** (0W5L / 0W4L) — reassessment gated on a *fresh signal+loss*; **GOOGL** 0W3L, park trigger un-matured (0W4L). Honored below.
- 06-22 reminder: "MU earnings Wed 06-24 after close → gaps Thu 06-25, trade with caution" — acted on (park, see below).

### Watchlist review
- Account: equity **$8,104.34**, ACTIVE, **0 open positions → nothing locked.** 14-day book net **+$17.05** across 21 names.
- **MU** — 0W5L all-time (−$182.3; all losses STOP), last signal 06-16 (−$35.5). **Earnings tonight after close (~14% implied move)** and already in the eye of Tuesday's semi plunge → erratic, news-driven, low-quality breakout tape today. Chronic loser + binary event TODAY = the one clear park. **→ PARK** (re-enable after 06-25 gap settles).
- **AMD** — 0W4L all-time (−$239.8, worst net), but all 4 losses are 06-09 (the flagged overtrading day) and it has NOT signaled in 15 days. No fresh signal+loss → trigger un-matured. **→ HOLD** per standing discipline.
- **GOOGL** — 0W3L (−$356.7), no signal since 06-12. Park trigger (0W4L) not reached; GOOG (sister, 1W3L, has a TP winner) still carried as the better vehicle. **→ HOLD** (one more loss consolidates to GOOG-only).
- **SE** — 1 trade, −$142.3 (06-12); single sample, reasonably liquid ADR → insufficient evidence. **→ HOLD.**
- Semis broadly (NVDA/AVGO/TSM/QCOM/INTC) weak on the sector down-day, but liquid and strategy-fit — a one-day sector dip is not a park trigger; the gate self-throttles. **→ HOLD all.**
- Recent winners (TSLA +$294, GOOG +$120, CRM +$58, INTC +$49, XOM, AAPL, TSM, BAC) all retained.

### Changes applied to watchlist
- **PARK MU** — "parked 2026-06-24: 0W5L chronic loser (−$182 all-time) + earnings AFTER close tonight (~14% implied move) amid Tue semi plunge; re-enable after 06-25 gap settles".
- No adds (event-heavy, directionless rebound tape — adds stay conservative per 06-23 note). No re-enables.

### Final watchlist
**25 active** (was 26): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM. (Parked: MU.)
Service **restarted: yes** — 11:48:32 UTC, active, clean startup ("USTradeWisBot starting", sleeping until 09:30 ET open), no errors. 0 positions locked.

### Notes for pre-market research (next session — Thu 06-25)
- **Re-enable MU** once Thursday's post-earnings gap settles (likely Thu/Fri) — it's a structurally fine liquid large-cap, parked only for the binary event.
- **PCE inflation Thu 06-25** — hot print could whipsaw the tape; do not add names into the event; watch for a hawkish repricing.
- **MU gaps Thu 06-25** on tonight's report (~14% implied) — note direction for whether to re-enable immediately or wait a session.
- **GOOGL** still 0W3L / **AMD** 0W4L — both gated on a fresh signal+loss; park if either signals and loses again.
- TSLA remains the franchise earner (+$294 14d, 2W0L). Equity $8,104.34 (−19.0%), $604 to the −25% ($7,500) flag.

---

## 2026-06-25 — Pre-market Research

### Market context
**Micron-led AI/chip rally into PCE.** MU reported fiscal Q3 Wed 06-24 after close — a blowout: revenue $41.46B (vs ~$36B est, >4x YoY), EPS $25.11 (vs $20.20), gross margin 84.9%, and a **~$50B current-quarter revenue guide** (vs $43.6B est) on locked-in AI/data-center memory demand (16 multi-year customer agreements). Stock **+15% AH / +17% pre-market**; whole semi complex bid in sympathy — **QCOM +11.7%** (raised FY29 non-handset guide; on-list), SanDisk/WDC/LRCX/KLA/AMAT all up, SMH +3% AH. Futures: **Nasdaq-100 +2.1%, S&P 500 +0.7%, Dow +0.2%.** **Main event: May PCE (Fed's preferred gauge) at 8:30 ET** — consensus hotter (headline +0.5% m/m, ~4.1% y/y; **core +0.3% m/m, 3.4% y/y**, both above April) on a hawkish-Warsh backdrop (~half the FOMC pencils a 2026 hike, markets price ~+0.5% over 12m). Also Q1 GDP final, May durable orders; DRI earnings. A hot PCE print can whipsaw the tape, so treat the open with caution.

### Carried from daily review (2026-06-24)
- **Re-enable MU once Thursday's gap settles** (standing plan from 06-24 park: "parked only for the binary earnings event; re-enable Thu/Fri once the 06-25 gap settles, note direction"). Direction is **strongly bullish** (+15–17% on a fundamental beat + blowout guide), MU is the day's market driver and a >$1T liquid AI-memory leader → re-enabled today (see below). The park reason (binary event) is resolved.
- **MA-only conf 60–62 names are NOT low quality** (IMP-004/06-23 disproof; 06-24 review re-affirmed) — XOM/BAC/CRM/WMT kept; no conf-floor parks.
- **GOOGL 0W3L / AMD 0W4L** — both gated on a *fresh* signal+loss; neither signaled 06-24 → triggers un-matured, **hold both**.
- **PCE Thu 06-25 → do not add NEW names into the event** — honored (MU is an event-park restore, not a new momentum chase).

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,017.23** (flat vs 06-24 close $8,017.26 — no overnight change), cash $8,017.23, buying power $32,069, daytrade_count 0. **−19.8% from $10K**, $517 to the −25% ($7,500) strategy-review flag. Clock `is_open=false`, next open 06-25 09:30 ET (pre-open run).
- Per-symbol P&L (12d closed): positive TSLA **+$294.36 (2W0L)**, XOM +$19.57, CRM +$16.21, NFLX +$7.04, C +$4.32. Worst small: ENPH −$63.85 (1W3), MU −$35.50 (1 trade), WMT −$25.43, QQQ/TSM/BAC/SPY/META/AVGO each <−$23. 12d net **+$120.35** (carried by TSLA). All names liquid large-caps/ETFs that fit the strategy; no chronic-loser park matured.
- **MU** — verified on Alpaca `/v2/assets/MU` → **tradable:true, status:active**. Earnings binary resolved bullishly; liquid, now in a powerful uptrend with massive volume and a fresh sector tailwind — exactly the trending/liquid profile the breakout strategy wants. Gap-day + PCE volatility is bounded by ATR-based sizing (large post-gap ATR → small qty → small $ risk) and the no-overnight EOD flatten. **→ RE-ENABLE.**
- **GOOGL** (0W3L) / **AMD** (0W4L) — no fresh signal+loss; **hold** (GOOGL one more loss → consolidate-to-GOOG-only). **SE** (1 trade −$142) single-sample → hold. Zero-signal liquid names (MSFT/QCOM/CRM history) reflect regime, not name-quality → hold.
- **Adds: none** — hot-PCE risk + hawkish Fed + −19.8% drawdown; do not chase new names into the 8:30 ET print. Today's strength (semis) is already fully covered on-list (MU/NVDA/AVGO/AMD/TSM/INTC/QCOM).

### Changes applied to watchlist
- **MU: re-enabled 2026-06-25** — earnings event (parked 06-24) resolved bullish (+15% beat, ~$50B Q4 guide); liquid AI-memory large-cap, today's market driver. (Restore of an event-park, not a new add — consistent with the "no new names into PCE" guidance.)

### Final watchlist
**26 active** (was 25, +1 re-enable; within 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service **restarted: yes** — active (running), Main PID 3628083, clean startup 11:49:25 UTC Jun 25, no errors. 0 positions locked.

### Notes for pre-market research (next session — Fri 06-26)
- **Watch MU's first live session back:** today is its +15% earnings-gap day — confirm any MU trade taken is ATR-sized small and flattened by 15:55 ET; review whether gap-day breakouts on MU are clean or choppy. If MU signals and loses badly on the gap, note it (it was re-enabled on conviction, not yet trade-proven post-earnings).
- **PCE digestion:** if the 8:30 ET print ran hot and the tape whipsawed, factor the regime read into Friday's adds (still none unless a high-conviction trending large-cap emerges).
- **GOOGL** still 0W3L / **AMD** 0W4L — both gated on a fresh signal+loss; park the one that signals and loses again. GOOGL one more loss → consolidate-to-GOOG-only.
- **QCOM** (+11.7% on raised guidance) — already on-list; watch whether it produces a clean breakout today (fresh fundamental catalyst, unlike its long signal-drought).
- TSLA remains the franchise earner (+$294 12d, 2W0L). Equity $8,017.23 (−19.8%), $517 to the −25% ($7,500) flag.

---

## 2026-06-26 — Pre-market Research

### Market context
**Cautious, tech-vs-chips split tape after an in-line PCE.** Thu 06-25 May PCE printed roughly in line (headline +0.4% m/m / 4.1% y/y — highest since Apr-2023; core +0.3% m/m / 3.4% y/y — highest since Oct-2023); markets took relief that it wasn't hotter (10y eased to ~4.40%), but the Fed stays hawkish (Goolsbee: core "too high, trending the wrong way"; a majority of FOMC favors a 2026 hike). Friday futures slightly lower (S&P/Nasdaq red) as the relief is offset by a continued **rotation OUT of megacap tech**: Thu close had AAPL −6.1% (announced MacBook/iPad/iPhone price hikes; led the Nasdaq's first 4-day losing streak since Feb), NVDA −1.6%, MSFT −3.5%, AMZN −3.1%, META −2.7% — all on-list. Offsetting bid in **memory/chips**: MU +15.7% (blowout, on-list), AMAT +13.4%, SanDisk/WDC up. **Oil +2% back above $70** on a Strait-of-Hormuz vessel attack (Iran IRGC) → XOM tailwind, geopolitical headline risk live. Structural note: **GOOGL replaces Verizon in the Dow before the 06-29 open** (mild positive for GOOG/GOOGL, both on-list). Today's only macro item is the final UMich June consumer sentiment; **no watchlist name reports earnings during market hours** → no intraday earnings risk on the list.

### Carried from daily review (2026-06-25)
- **AMD signaled (first since 06-09) and WON (+$19.61)** → the "park AMD if it signals and loses again" trigger did NOT fire; AMD stays, broad-regime (not name-quality) thesis supported. **AMD park watch dropped** — honored, no action.
- **MU re-enabled 06-25 did NOT signal** on its +15% gap day — gap-day-breakout question still untested; keep MU and watch (it's bid again today, +15.7% sympathy). Honored.
- **MA-only conf 60–62 names are NOT low quality** (IMP-004 refutation, re-affirmed) — XOM/BAC/CRM/WMT kept; no conf-floor parks.
- **GOOGL** did not signal 06-25 → still 0W3L, park trigger (0W4L) un-matured → hold. **PCE digestion → adds stay none** unless a high-conviction trending large-cap emerges (06-25 note). Honored.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,013.52** (flat vs 06-25 close $8,013.54 — no overnight change), cash $8,013.52, buying power $32,054, daytrade_count 0. **−19.9% from $10K**, $514 above the −25% ($7,500) strategy-review flag.
- Per-symbol P&L (closed, since 06-12): positive **TSLA +$294.36 (2W0L)**, GOOG +$119.97, INTC +$49.00, AMD +$19.61, XOM +$19.57, CRM +$16.21, QCOM +$9.62, NFLX +$7.04, BAC +$6.44, C +$4.32. Worst: SE −$142.35 (1t), META −$134.00 (0W2), GOOGL −$128.79 (0W1 in-window / 0W3 all-time), ENPH −$63.85. All liquid large-caps/ETFs that fit the strategy; **no chronic-loser park trigger matured today.**
- **GOOGL** (0W3L all-time, −$356.67) — park trigger is 0W**4**L (consolidate to GOOG-only); it has not signaled since 06-12, so the 4th loss hasn't occurred → **HOLD**. (Mild offsetting positive: Dow inclusion 06-29.)
- **AAPL** (−6.1% Thu on price-hike news, soft into today) — a one-day megacap rotation move, not a binary intraday event (no earnings/halt); liquid mega-cap that fits the strategy and is ~flat all-time (−$9.21/3t). A down day is not a park trigger — the gate self-throttles. **HOLD.** Same logic for NVDA/MSFT/AMZN/META (one-day rotation, all liquid mega-caps). META 0W2L is too small a sample (2 trades) for a name-specific park.
- **SE** (1 trade −$142.35) single-sample, reasonably liquid ADR → insufficient evidence → **HOLD.** Zero-signal liquid names (MSFT/QCOM-history/CRM-history) reflect the regime, not name-quality → **HOLD.**
- **Adds: none** — −19.9% drawdown, hawkish-Fed backdrop, two-sided megacap-tech-rotation tape, live Hormuz/oil geopolitical risk, and a Friday. Today's only real momentum (memory chips) is already covered on-list (MU/NVDA/AVGO/AMD/TSM/INTC/QCOM); MU is the cleanest expression and already active. No high-conviction trending large-cap absent from the list. (06-25 standing note: "still none unless a high-conviction trending large-cap emerges" — none did.)

### Changes applied to watchlist
**No changes.** 26 active retained. Every park trigger is un-matured (GOOGL 0W3L < 0W4L and hasn't signaled; AMD watch dropped after its 06-25 win; SE/META small-sample; the rest are regime-droughts or one-day rotation, not structural mismatches). No adds into a hawkish, rotation-driven, geopolitically-charged Friday. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Mon 06-29)
- **GOOGL joins the Dow before the 06-29 open** (replaces VZ) — watch for an index-inclusion bid/volume bump on GOOG/GOOGL Monday; GOOGL still 0W3L (one more loss → consolidate-to-GOOG-only), so a clean GOOGL win Monday would also help resolve that watch.
- **MU** still has not produced a live signal since its 06-24 blowout — its gap/post-earnings breakout behavior remains untested; keep watching whether it signals cleanly now that the gap has settled.
- **Megacap-tech rotation:** AAPL (−6.1% on price hikes) led a 4-day Nasdaq slide; if the megacaps (AAPL/NVDA/MSFT/AMZN/META) keep bleeding into next week, watch whether any becomes a genuine name-specific park candidate vs a regime move (currently regime — all held).
- **Oil/Hormuz geopolitical risk is live** (IRGC vessel attack, oil >$70) — XOM has a tailwind but headline-driven gaps are possible; do not chase energy on a single oil spike.
- **Hawkish Fed holds** (majority pencils a 2026 hike) — keep adds conservative; no new names without a high-conviction trending large-cap. TSLA remains the franchise earner (+$294, 2W0L). Equity $8,013.52 (−19.9%), $514 to the −25% ($7,500) flag.

---
