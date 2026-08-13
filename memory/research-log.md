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

## 2026-06-29 — Pre-market Research

### Market context
**Risk-on relief open after a brutal June.** Futures higher to start a holiday-shortened week: Dow +0.4%, S&P 500 +0.8%, **Nasdaq-100 +1.1%** — tech rebounding on a **US–Iran "stand down" de-escalation** (both sides traded fire near the Strait of Hormuz over the weekend testing the 60-day truce, but officials say talks remain "on track" ahead of a Tuesday Doha summit; Polymarket put ~86% odds on an up-open). The bounce follows a rough month — as of Fri's close **S&P −3% / Nasdaq −6% for June**, Dow +1%. **Market CLOSED Fri Jul 3 (Independence Day)** → 4-day week. **No economic data today;** the week is back-loaded and labor-heavy: Case-Shiller / Conf. Board confidence / **JOLTS Tue**, **ADP + ISM manufacturing Wed**, **nonfarm payrolls Thu 07-02**. Oil firmer (WTI ~$69.82 +0.85%, Brent ~$72.39) on the Hormuz fire-exchange; gold/silver pulled back. Deutsche Bank cautions geopolitical tail-risk stays hard to price — treat the bounce as relief, not a confirmed trend.

### Carried from daily review (2026-06-26)
- **GOOGL joins the Dow today (06-29, replaces VZ)** — mild index-inclusion positive for GOOG/GOOGL; GOOGL still **0W3L**, park trigger is 0W**4**L (consolidate-to-GOOG-only). It has not signaled since 06-12 → trigger un-matured, **hold**; a clean GOOGL win today would help resolve the watch.
- **MU** still has not produced a live signal since its 06-24 blowout (re-enabled 06-25) — gap/post-earnings breakout behavior remains untested → keep and watch.
- **Megacap-tech rotation** (AAPL/NVDA/MSFT/AMZN/META bled into a 4-day Nasdaq slide last week) — judged regime, not name-quality; all rebounding on today's risk-on tape → **hold all**, no name-specific park.
- **Oil/Hormuz risk live** — XOM tailwind but headline-gap prone; don't chase energy on a single oil spike. **Hawkish-Fed backdrop → adds stay conservative.** Honored below.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$7,873.51** (flat vs 06-26 close $7,873.54 — no overnight change), cash $7,873.51, buying power $31,494, daytrade_count 0. **−21.3% from $10K**, **$374 above the −25% ($7,500) strategy-review flag** (cushion thinned — watch). Clock `is_open=false`, next open 06-29 09:30 ET (pre-open run).
- Per-symbol P&L (14d closed): positive only **TSLA +$300.01 (3W0L)**, AMD +$19.61, XOM +$19.57, CRM +$16.21, QCOM +$9.62, NFLX +$7.04, C +$4.32. Worst small: ENPH −$78.70, TSM −$55.56, MU −$35.50, WMT −$25.43, QQQ −$22.68, META −$17.83, BAC −$16.81. All liquid large-caps/ETFs that fit the strategy; **no chronic-loser park trigger matured.**
- **No watchlist name reports earnings during market hours today** (week's earnings — NKE/STZ Tue, GIS Wed — are off-list). No halt/binary catalyst on any name. Today's premarket headliners (Comcast +25% spin-off, SpaceX Nasdaq-100 add, Viridian +11%) are event-driven one-offs, **not** clean trending large-caps that fit an intraday breakout strategy → not add candidates.
- Today's relative strength is chips (Intel +1.1% premkt, Arm/Marvell bid) — **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM). Samsung/SK Hynix down on $1T+ capex plans is mild memory-supply noise, not a list catalyst.
- **Adds: none** — relief-bounce (not trend) after a −6% Nasdaq month, −21.3% drawdown with the cushion thinned to $374, and a labor-data-heavy 4-day week culminating in **NFP Thu**. No high-conviction trending large-cap absent from the list; conservative-adds guidance honored.

### Changes applied to watchlist
**No changes.** 26 active retained. Every park trigger is un-matured (GOOGL 0W3L < 0W4L and hasn't signaled; AMD watch dropped after its 06-25 win; SE/META small-sample; the rest are regime-droughts or last-week's one-day rotation, not structural mismatches) and 0 positions are open (nothing locked). No adds into a relief-bounce, geopolitically-charged, labor-data-heavy holiday week. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Tue 06-30)
- **Labor-data week is the macro driver:** JOLTS + Conf. Board confidence Tue 06-30, ADP + ISM mfg Wed 07-01, **NFP Thu 07-02** — hot/cold prints can whipsaw the hawkish-Fed tape; **do not add names into the data**, especially ahead of Thursday's payrolls. Market closed Fri 07-03 (Independence Day).
- **GOOGL** joined the Dow 06-29 — watch for an inclusion bid/volume bump and whether it finally signals; still 0W3L (one more loss → consolidate-to-GOOG-only).
- **MU** gap/post-earnings breakout behavior still untested (no live signal since 06-24) — keep watching whether it signals cleanly now the gap has settled.
- **Megacaps** rebounded on Monday's risk-on tape — if the relief fails and they roll back over into the data, re-check whether any (AAPL/NVDA/MSFT/AMZN/META) becomes name-specific vs regime (currently regime, all held).
- **Oil/Hormuz** geopolitical tail-risk stays live (DB: "expect more policy volatility, not less") — XOM tailwind but don't chase energy on a headline spike.
- TSLA remains the franchise earner (**+$300 14d, 3W0L**). Equity $7,873.51 (−21.3%), **$374 to the −25% ($7,500) flag** — cushion thin; flag for strategy review if breached.

---

## 2026-06-30 — Pre-market Research

### Market context
**Risk-on continuation into the labor-data block.** Monday 06-29 snapped a 5-day losing streak: **Dow closed at a record 52,182.74 (+0.59%), S&P 500 +1.18% (7,440.43), Nasdaq Composite +2.07% (25,820.14)** on US–Iran de-escalation (Strait of Hormuz reopened to commercial vessels) + a broad Magnificent-Seven rebound — **GOOG rose ~5% in its first session as a Dow member** (on-list), the single biggest Dow contributor. Tue futures edge higher again; semis bid (SMH +0.8% pre-mkt), MAGS +0.25%. **Today 10:00 ET: JOLTS (May job openings, prior 7.6M) + Conference Board Consumer Confidence (prior 93.1)** — first of a labor-heavy, holiday-shortened week: **ADP + ISM mfg Wed 07-01, nonfarm payrolls Thu 07-02, market/bond-close Fri 07-03 (Independence Day)**. 10y ~4.38%. **Earnings: NKE reports AFTER the close today (the only Dow name reporting this week) — off-list and post-close → no intraday earnings risk on the watchlist.** Treat the bounce as momentum-into-data, not a confirmed trend; hot/cold prints can whipsaw the still-hawkish-Fed tape.

### Carried from daily review (2026-06-29)
- **AAPL** false-broke at the open 06-29 and reversed to its stop (−$116.55, lone loser) — judged the megacap open-fade/regime pattern, not a quality park; AAPL is rebounding on today's risk-on tape → **hold** (flag the gap-up-megacap open-fade risk, but no name action). Same logic holds the rest of the megacaps (NVDA/MSFT/AMZN/META) — all bid today.
- **GOOGL** still **0W3L** and did **not** signal 06-29 (only GOOG traded, an MA win +$40.90); park trigger is 0W**4**L (consolidate-to-GOOG-only) → un-matured, **hold**. GOOG caught the Dow-inclusion + risk-on bid (+~5% Mon).
- **MU** still produced **no live signal** (untested since the 06-24 blowout, re-enabled 06-25) → keep and watch.
- Watchlist judged healthy with no parks suggested; **adds stay conservative into the labor data** (06-29 note: no new names into JOLTS/ADP/NFP). Honored below.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$7,999.97** (flat vs 06-29 close $8,000.00 — no overnight change), cash $7,999.97, buying power $31,999.88, daytrade_count 0. **−20.0% from $10K**, **$500 above the −25% ($7,500) strategy-review flag** (cushion restored from $374 by Monday's +$126 day). Clock `is_open=false`, next open 06-30 09:30 ET (pre-open run).
- Per-symbol P&L (14d closed, 29 trades, net **+$174.28**): positive **TSLA +$316.01 (3W0L)**, INTC +$85.79, GOOG +$40.90, C +$20.25, AMD +$19.61, XOM +$19.57, CRM +$16.21, QCOM +$9.62. Worst: AAPL −$116.55 (06-29 false breakout), ENPH −$78.70, TSM −$55.56, WMT −$25.43, QQQ −$22.68, META −$17.83, BAC −$16.81. All liquid large-caps/ETFs that fit the strategy; **no chronic-loser park trigger matured** (the book is net green over 14d, carried by TSLA + Monday's INTC/GOOG/TSLA winners).
- **No watchlist name reports earnings during market hours today** (NKE is after the close, off-list; no other on-list name reports). No halt/binary catalyst on any name. Today's premarket headliner (SpaceX fast-tracked into the Nasdaq-100 for ~Jul 7) is an index-mechanics one-off, not a tradable on-list catalyst.
- Today's relative strength is again semis (SMH bid) + Mag7 — **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM + AAPL/MSFT/AMZN/META/GOOG/GOOGL/TSLA). No high-conviction trending large-cap absent from the list.
- **Adds: none** — momentum-into-data (JOLTS/confidence at 10:00 today, ADP Wed, **NFP Thu**), still-hawkish Fed, −20.0% drawdown, and a 4-day holiday week. Conservative-adds guidance (06-29) honored; no chasing into the print.

### Changes applied to watchlist
**No changes.** 26 active retained. Every park trigger is un-matured (GOOGL 0W3L < 0W4L and hasn't signaled; AMD watch dropped after its 06-25 win; AAPL/megacaps are regime open-fade not name-quality; SE/META small-sample; the rest are regime droughts, not structural mismatches), and 0 positions are open (nothing locked). No adds into a labor-data-heavy holiday week. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Wed 07-01)
- **Labor data is the macro driver all week:** JOLTS + Conf. Board confidence today 06-30, **ADP + ISM mfg Wed 07-01, NFP Thu 07-02**; **market/bond closed Fri 07-03**. Do NOT add names into the data, especially ahead of Thursday's payrolls; a hot/cold print can whipsaw the hawkish-Fed tape.
- **NKE reports after the close today** (only Dow name this week, off-list) — will gap Wed 07-01 but has no direct watchlist effect; a sharp NKE move can color consumer-discretionary sentiment.
- **GOOGL** still 0W3L — one more loss (0W4L) triggers consolidate-to-GOOG-only; GOOG remains the stronger vehicle (Dow-inclusion bid, +$40.90 Mon). Watch whether GOOGL finally signals.
- **MU** gap/post-earnings breakout behavior still untested (no live signal since 06-24) — keep watching whether it signals cleanly now the gap has settled.
- **AAPL/megacap open-fade:** AAPL false-broke and stopped 06-29 on a gap-up; if gap-up megacaps keep fading at the open into the data, that's the recurring regime case (the #1 strategy lever, regime gate) — not a watchlist park.
- TSLA remains the franchise earner (**+$316 14d, 3W0L**). Equity $7,999.97 (−20.0%), **$500 to the −25% ($7,500) flag** — cushion restored; flag for strategy review if breached.

---

## 2026-07-01 — Pre-market Research

### Market context
**Breather to open H2 after a blockbuster first half.** Futures slip: Dow −0.4% (−202), S&P 500 −0.4%, Nasdaq 100 −0.6% pre-open — a pause, not a reversal, after H1 gains (Dow +8.9%, S&P +9.6%, Nasdaq +12.8%; Q2 S&P +14.9%, best since Q2-2020). The rally was chip/AI-led — a record chip run added ~$2T of combined cap to MU/INTC/AMD in Q2 (all on-list). **Labor-data block dominates:** ADP private payrolls 8:15 ET (cons. 122k vs 117k prior), **ISM Manufacturing 10:00 ET (high importance, ~53.8–54.0)**, and Fed Chair **Warsh speaks 9:30 ET** at the ECB Sintra forum — then **June NFP Thu 07-02; market/bond closed Fri 07-03**. 10y ~4.38%, still-hawkish Fed. Retail sentiment: SPY bearish / QQQ bullish. **No watchlist name reports today** — today's earnings (GIS, FDS, MSM, UNF, GBX) are all off-list; NKE reported yesterday (−4% pre-mkt on China weakness, off-list).

### Carried from daily review (2026-06-30)
- **Best incubation day by P&L: 5W/1L, +$297.04**, equity close **$8,297.01 (−17.0%)** — cushion widened to **$797** above the −25% ($7,500) flag. 0 open positions, no overnight carry. Directional-with-the-tape thesis paid in full (3 TAKE_PROFIT: INTC/TSM/TSLA).
- **AMD** — day's strongest mover but bot could not enter (bracket 422 on the >2% open gap); now handled by **IMP-008** gap-skip guard. Order mechanics, **not** the name — high-quality momentum leader, **hold, no park**.
- **TSM** flipped 06-29 false-break → +1.92% TP win (regime-dependence); **MU** produced its first live signal since the 06-24 blowout and won (+1.78%) — post-earnings gap settled, keep. **TSLA now 4W0L (+$375 14d)**, franchise earner. **AAPL** rebounded +1.29% (opposite of its 06-29 open-fade → regime, not name).
- **GOOGL** still **0W3L**, did not signal — park trigger (0W4L) un-matured → hold. Adds stay conservative into the labor data. Honored below.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,296.98** (flat vs 06-30 close $8,297.01 — no overnight change), cash $8,296.98, buying power $33,187.92, daytrade_count 0. **−17.0% from $10K**, **$797 above** the −25% ($7,500) strategy-review flag (best cushion since early incubation — protect it into the labor data).
- Per-symbol P&L (14d closed): positive **TSLA +$375.11 (4W0L)**, INTC +$176.12 (2W0L), TSM +$41.02, GOOG +$40.90, MU +$20.27, AMD +$19.61, XOM +$19.57, CRM +$16.21, QCOM +$9.62. Worst small: AAPL −$83.46 (1W1L), ENPH −$78.70 (1W1L), WMT −$25.43, QQQ −$22.68 (0W1L), META −$17.83 (0W2L), AVGO −$9.37 (incl. the 06-30 −$2.33 scratch), COST −$7.50, SPY −$5.58, BAC −$1.63. All liquid large-caps/ETFs that fit the strategy; **no chronic-loser park trigger matured** — AAPL/ENPH are 1W1L small samples, AAPL explicitly regime open-fade (held), and the book is strongly net-green over 14d (TSLA + INTC).
- **No watchlist name reports during market hours today** (GIS/FDS/MSM/UNF/GBX off-list; NKE reported yesterday). No halt/binary catalyst on any on-list name. Pre-market movers (LUNR +8%, ASTS +20%, NIO −4%, defense AVAV/KTOS on initiations, NKE −4%) are event/small-cap one-offs — **not** clean trending liquid large-caps that fit an intraday breakout strategy → **not add candidates**.
- Today's relative strength story is again chips/AI — **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM). No high-conviction trending large-cap absent from the list.
- **Adds: none** — futures lower into a labor-data-heavy, holiday-shortened week (ADP + ISM + Warsh today, **NFP Thu**, closed Fri), still-hawkish Fed, and a −17% drawdown to protect. Conservative-adds guidance (06-30) honored; no chasing into the print.

### Changes applied to watchlist
**No changes.** 26 active retained. Every park trigger is un-matured (GOOGL 0W3L < 0W4L and hasn't signaled; AAPL/megacaps are regime open-fade not name-quality; ENPH/META/AVGO small-sample noise; AMD's 06-30 miss was order mechanics fixed by IMP-008, not the name; the rest are regime droughts, not structural mismatches), and 0 positions are open (nothing locked). No adds into the labor data on a lower-futures breather. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Thu 07-02)
- **NFP DAY (June payrolls, 8:30 ET) is the single biggest macro event of the week** — do NOT add names into the print; a hot/cold number can whipsaw the hawkish-Fed tape. **Market/bond closed Fri 07-03 (Independence Day)** → Thu is the last full session of the week; expect thinner post-lunch liquidity ahead of the long weekend and flatten cleanly.
- Watch how today's ADP/ISM + Warsh set the tone: if the H2-open breather deepens into a down tape, the megacap open-fade (AAPL-style) risk returns (the #1 strategy lever, regime gate); if the chip/AI leadership resumes, the on-list semis (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM) are the vehicles.
- **GOOGL** still 0W3L and untested — one more loss (0W4L) triggers consolidate-to-GOOG-only; GOOG remains the stronger vehicle. Watch whether GOOGL finally signals.
- **TSLA 4W0L (+$375 14d)** and **INTC 2W0L (+$176)** are carrying the book — the franchise earners; no action, just the anchors of the current green-tape edge.
- Equity **$8,296.98 (−17.0%)**, **$797 above** the −25% ($7,500) flag — best cushion of incubation; protect it through NFP.

---

## 2026-07-02 — Pre-market Research

### Market context
**NFP DAY — the week's single biggest macro event.** June nonfarm payrolls print **8:30 ET (before the open)**, pulled forward to Thursday because **market/bond closed Fri 07-03 (Independence Day observed)** → today is the last full session of the week. Consensus ~110–115k jobs (slowdown from May's 172k), unemployment ~4.3%. Wednesday's tells were mixed: **ADP soft at 98k** private (below consensus), JOLTS upbeat. The tension is good-news-is-bad-news: a hot print reinforces the still-hawkish Warsh Fed (core PCE 3.4%, highest since Oct-2023; some desks positioning for hikes) and can whipsaw the tape. Futures softening into the release; S&P at record highs but growth slowing + U.Mich sentiment at an all-time low + U.S.–Iran tensions underneath. 10y ~4.38%. **No watchlist name reports during market hours today** — early July is pre-Q2-earnings-season (banks kick it off ~mid-July); no on-list earnings/halt/binary catalyst.

### Carried from daily review (2026-07-01)
- **Third straight green day: 5W/1L, +$152.38 (+1.84%)**, equity close **$8,449.36 (−15.5%)** — best 3-day run and **best cushion of incubation ($949 above the −25% flag)**. 0 open positions, no overnight carry (IMP-002 retry-until-confirmed flatten held again). Directional-with-the-tape thesis paid a third session (2 TP: SE/MSFT).
- **NVDA** — bot tried it first (09:30:26) but the bracket 422'd on an open **gap-down** (base 195.02); now handled by **IMP-009** (symmetric down-gap skip). Order mechanics, **not** the name → **hold, no park**.
- **GOOGL park watch RESOLVED in its favor** — signaled (BOTH, conf 72.83) and **won +$42.41**, its first live signal in weeks. The 0W3L→consolidate-to-GOOG watch does NOT fire → **drop the park watch; keep both GOOG and GOOGL**.
- **ENPH** — genuine BOTH breakout that round-tripped −1.85% to a stop in ~6 min: recurring false-breakout mode (06-15/06-26), behaves with the regime → **no park** (the leak is the regime-wide STOP bucket PF 0.01, the #1 strategy-lever gate — not name-specific). **SE/MSFT** hit TP on low-conf MA (MSFT's first winner) → MA-floor-raise candidate stays refuted; keep all.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,449.32** (flat vs 07-01 close $8,449.36 — no overnight change), cash $8,449.32, buying power $33,797.28, daytrade_count 0. **−15.5% from $10K**, **$949 above** the −25% ($7,500) strategy-review flag — **best cushion of incubation; protect it into the payrolls print.**
- Per-symbol P&L (14d closed, net **+$623.70**): positive **TSLA +$375.11 (4W0L)**, INTC +$176.12 (2W2L→2W0L), SE +$60.30, MSFT +$58.52, GOOGL +$42.41, TSM +$41.02, GOOG +$40.90, MU +$20.27, C +$20.25, AMD +$19.61, XOM +$19.57, CRM +$16.21, QCOM +$9.62, AMZN +$4.59. Worst: **ENPH −$126.54 (3t,1W)**, AAPL −$49.06 (3t,2W), WMT −$25.43, QQQ −$22.68, META −$17.83 (0W2L), BAC −$16.81, AVGO −$9.37, COST −$7.50, SPY −$5.58. All liquid large-caps/ETFs that fit the strategy; **no chronic-loser park trigger matured** — ENPH is the biggest loser but explicitly the regime-wide false-breakout leak, NOT a name defect (07-01 note: no park); AAPL 2W/3t is regime open-fade; book is strongly net-green (+$624) over 14d.
- Pre-market movers into NFP are event/macro one-offs, not clean trending liquid large-caps that fit an intraday breakout strategy → **not add candidates**. Today's leadership (chips/AI + megacaps) is **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM + AAPL/MSFT/AMZN/META/GOOG/GOOGL/TSLA). No high-conviction trending large-cap absent from the list.
- **Adds: none** — NFP-day whipsaw risk on a hot/cold print, hawkish Fed, holiday-shortened week (closed Fri), and a −15.5% drawdown with the best cushion of incubation to protect. Standing "do NOT add into the payrolls print" guidance (07-01) honored; no chasing into the print.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (ENPH/regime-wide STOP-bucket leak = strategy-gate work not a name park; AAPL/megacaps regime open-fade; META/AVGO small-sample noise; NVDA's 07-01 miss was order mechanics fixed by IMP-009; GOOGL park watch resolved in its favor and dropped; the rest are regime droughts, not structural mismatches). 0 positions open (nothing locked). No adds into the labor data. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Mon 07-06)
- **Market closed Fri 07-03; next session Mon 07-06.** Review how the NFP print + the long-weekend tape resolved: a hot number that whipsaws into a down tape brings back the megacap open-fade (AAPL-style) risk (the #1 strategy-lever regime gate); if chip/AI leadership resumes, on-list semis (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM) are the vehicles.
- **GOOGL park watch is CLOSED** (signaled + won 07-01) — keep both GOOG and GOOGL; no lingering 0W3L trigger.
- **ENPH remains the single biggest 14d loser (−$126.54)** and the recurring false-breakout name — but it is the regime-wide STOP-bucket leak (PF 0.01), addressed by the deliberate intraday-regime entry gate (post-close work), NOT a pre-market name park. Re-flag only if a name-specific pattern separates from the regime.
- **TSLA 4W0L (+$375 14d)** and **INTC 2W0L (+$176)** remain the book's anchors; **SE/MSFT** joined the winners' column 07-01 (low-conf MA). No action — just the current green-tape earners.
- Equity **$8,449.32 (−15.5%)**, **$949 above** the −25% ($7,500) flag — best cushion of incubation; protect it.

---

## 2026-07-06 — Pre-market Research

### Market context
**Holiday-return rebound; tech/semis bid after a two-day chip plunge.** First full session after the long weekend (market closed Fri 07-03, Independence Day observed). Pre-market: **S&P 500 +0.49%, Nasdaq-100 +1.12%, Dow +0.10%, Russell +0.14%** — tech leading the bounce. Backdrop is a **soft June NFP** (released Thu 07-02): +57k jobs vs +113k expected, unemployment 4.2% — a cooler labor market that breaks a three-month hot streak and supports Fed patience (risk-on read). Thu 07-02 closed split: **Dow at a record 52,900**, but **Nasdaq −0.8% as semis fell a 2nd day** (SMH −4.5%, MU −5.5%, NVDA −1.4%, Teradyne −13.6%, KLA −11.5%; Korea's Kospi −7.9% on chip weakness). Today's rebound is that chip rotation trying to stabilize. **Meta +1.4% pre-mkt** (Bloomberg: entering cloud/AI-compute business). Today's macro: **ISM June Services PMI**. **Q2 earnings season is kicking off** (Samsung prelim Q2 today, off-list; US banks start ~mid-July) — **no watchlist name reports during market hours today** → no intraday earnings risk on the list. Other overhangs: USMCA not renewed (annual reviews instead), US–Iran talks "positive" (oil lower). Treat the bounce as a relief/rotation-stabilization move, not a confirmed trend.

### Carried from daily review (2026-07-03)
- **07-03 was a holiday — no trade-level observations.** Watchlist state is exactly as prior curation left it (26 active; MU re-enabled 06-25; C/JPM/WPM/BABA/BIRD parked; **GOOGL park watch CLOSED 07-01** after it signaled + won). Live check confirms 26 active, 0 open, nothing to reconcile.
- **Mon 07-06 is the first live session since IMP-009 (symmetric down-gap skip) & IMP-010 (STOP/TP real-fill entry_price)** — pre-market curation cannot verify these (they trigger intraday); flagged to the daily-review routine to confirm a clean `stale_signal_gap_down` skip on any gap-down open and a reconciling STOP/TP row. Relevant to today given the chip-gap volatility.
- **Regime is the watch item** (07-02 was an NFP open-fade, 3/4 no follow-through). If the fade regime persists, megacap/MA open-fades (AAPL/GOOGL) stay the risk; if chip/AI leadership resumes, on-list semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) are the vehicles. This is a strategy-gate item (post-close #1 lever), not a watchlist action.
- **Infra note resolved:** the 07-03 premarket cron failed on an expired Claude OAuth token (refreshed 07-03 17:24 UTC); this 07-06 run executed, confirming the token is live.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,301.04** (flat vs 07-02/07-03 close $8,301.08 — no trading over the holiday), cash $8,301.04, buying power $33,204, daytrade_count 0. **−17.0% from $10K**, **$801 above** the −25% ($7,500) strategy-review flag. Clock `is_open=false`, next open 07-06 09:30 ET (pre-open run).
- Per-symbol P&L (14d closed, 39 trades, net **+$232.34**): positive **INTC +$176.12 (2W0L)**, **TSLA +$171.62 (3W0L)**, MSFT +$58.52, TSM +$41.02, GOOG +$40.90, MU +$20.27, AMD +$19.61, XOM +$19.57, QCOM +$9.62, GOOGL +$6.83, AMZN +$4.59, CRM +$3.27. Worst: **ENPH −$180.28 (0W2)**, AAPL −$49.06 (2W3), SE −$39.42 (1W2), WMT −$25.43, QQQ −$22.68, COST −$7.50, META −$5.69, SPY −$5.58, AVGO −$2.33, BAC −$1.63. All liquid large-caps/ETFs that fit the strategy; **no chronic-loser park trigger matured** — the book is net-green over 14d, carried by INTC + TSLA.
- **ENPH** — the single biggest 14d loser (−$180, 0W2, both STOP) — but it is the recurring **regime-wide false-breakout leak** (all-time STOP bucket PF 0.01), the target of the deliberate intraday-regime entry gate (post-close #1 lever), **NOT** a name-specific defect. Consistent standing judgment (06-15/06-26/07-01/07-02): no park; re-flag only if a name-specific pattern separates from the regime. **HOLD.**
- **AAPL** (2W3L, −$49) — regime open-fade small sample, liquid mega-cap → **HOLD.** **SE** (1W2L, −$39) single-name small sample, reasonably liquid ADR → **HOLD.**
- **Semis broadly** (NVDA/AVGO/TSM/QCOM/INTC/AMD/MU) — hit by the two-day chip plunge, but liquid and strategy-fit; a two-day sector dip is a regime move, not a name park trigger (the gate self-throttles). They are today's rebound vehicles if leadership resumes. **HOLD all.**
- Zero/low-signal liquid names (CRM/MSFT/QCOM-history) reflect the regime, not name-quality — only a *structural* strategy mismatch (WPM, already parked) warrants a curation park. **HOLD.**
- **No watchlist name reports during market hours today**; no on-list halt/binary catalyst. Pre-market movers (VERA +6% ahead of a 07-07 PDUFA; Samsung prelim) are event/off-list one-offs — **not** clean trending liquid large-caps that fit an intraday breakout strategy → not add candidates.
- **Adds: none** — first session back from a holiday into **elevated two-day chip volatility** + the **start of Q2 earnings season** (event risk ramping), still-hawkish-but-patient Fed, and a −17% drawdown with an $801 cushion to protect. Today's leadership (tech/semis rebound + Meta cloud news) is **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM + AAPL/MSFT/AMZN/META/GOOG/GOOGL/TSLA). No high-conviction trending large-cap absent from the list.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (ENPH = regime-wide STOP-bucket leak → strategy-gate work, not a name park; AAPL/SE small-sample; semis are a two-day sector dip, not name-quality; the rest are regime droughts, not structural mismatches; GOOGL park watch already CLOSED 07-01). 0 positions open (nothing locked). No adds into holiday-return chip volatility + the Q2-earnings-season start. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Tue 07-07)
- **Confirm IMP-009 & IMP-010 fired cleanly on their first live session (07-06)** — carry to today's daily-review: on any gap-down open a clean `stale_signal_gap_down` skip (no 422); on any slipped STOP/TP a stored `entry_price` matching the Alpaca buy fill that reconciles. The chip-gap tape makes 07-06 a likely test.
- **Chip rotation is the tape's swing factor:** semis plunged two days into 07-02 then bounced 07-06 — watch whether the on-list semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) resume leadership or fade again; INTC (2W0L, +$176) and TSLA (3W0L) remain the book's anchors.
- **Q2 earnings season is starting** — no on-list name reported during hours 07-06, but reports ramp; **check the intraday-earnings calendar each morning** and park any on-list name reporting during market hours on its report day (event risk). Banks (~mid-July) are mostly parked already (C/JPM).
- **ENPH** stays the biggest 14d loser (−$180, 0W2) but remains the regime-wide false-breakout leak (STOP bucket PF 0.01), addressed by the post-close intraday-regime gate (#1 lever) — re-flag as a name park only if a name-specific pattern separates from the regime.
- **VERA PDUFA 07-07** (off-list) — no direct watchlist effect. Equity **$8,301.04 (−17.0%)**, **$801 above** the −25% ($7,500) flag — protect the cushion.

---

## 2026-07-07 — Pre-market Research

### Market context
**Risk-off open on renewed memory-chip weakness; broad market pulls back from records.** Monday 07-06 closed at fresh records — **S&P 500 +0.72% (7,537.43), Nasdaq Composite +1.12% (26,121.16), Dow +0.29% to a first-ever close above 53,000 (53,055.91)**. Tue futures turn **lower**: **S&P 500 −0.2%, Nasdaq-100 −1.0%**, the pressure concentrated in semis/memory: **Samsung fell 8.8% in Seoul** (Q2 profit surged 19× but the report underwhelmed), dragging **MU and SanDisk down >5% in US pre-market** in sympathy — the third chip-down move in a week (SMH −4.5% on 07-02, bounce 07-06, back down today). **SpaceX joins the Nasdaq-100 today** (index-mechanics one-off). Fed: CME FedWatch now ~**56% odds of a Sept hike** (down from 61% a week ago) after last week's soft June NFP (+57k). Macro today is light. **Earnings: a light day — no noteworthy pre-bell reports; today's names (PENG after close, ~5 total) are all off-list; PEP reports Thu 07-09 pre-open (off-list).** Q2 earnings season ramps mid-week/Thursday; banks begin ~mid-July. **No watchlist name reports during market hours today → no intraday earnings risk on the list.** Treat the open as a risk-off chip-led pullback from records, not a trend break.

### Carried from daily review (2026-07-06)
- **IMP-010 CONFIRMED live 07-06** (INTC/SE STOP rows stored the real Alpaca buy fill and reconcile); **IMP-009 still PENDING** (no down-gap past the 1.0% cap fired yet). Both are daily-review/code items — no watchlist action.
- **Q2 earnings season starting → check the intraday-earnings calendar each morning and park any on-list name reporting during market hours.** Acted on: verified today's calendar — **no on-list name reports during hours 07-07** → no earnings park.
- **Chip rotation is the tape's swing factor** — semis are today's down-driver again (Samsung). Standing judgment: a multi-day sector dip is a **regime** move, not a name-park trigger; the gate self-throttles. Honored (hold all semis).
- **ENPH** remains the biggest 14d loser but is the **regime-wide false-breakout STOP-bucket leak** (all-time PF 0.01), addressed by the post-close intraday-regime gate (#1 lever), **not** a name park. Held per consistent standing judgment (06-15/06-26/07-01/07-02/07-06).

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,230.53** (flat vs 07-06 close $8,230.53; last_equity $8,301.04), cash $8,230.53, buying power $32,922, daytrade_count 0. **−17.7% from $10K**, **$730 above** the −25% ($7,500) strategy-review flag. Clock `is_open=false`, next open 07-07 09:30 ET (pre-open run).
- **MU / semis (NVDA/AVGO/TSM/QCOM/INTC/AMD)** — MU down >5% pre-market on Samsung memory weakness (sector sympathy, not a name catalyst); all are liquid large-cap semis that fit the strategy. A Samsung-driven memory dip is a regime move → **HOLD all** (the ATR-based sizing + no-overnight flatten bound the risk; the entry gate self-throttles). If chip leadership resumes they are the rebound vehicles.
- **ENPH** (biggest 14d loser, regime STOP-bucket leak) → **HOLD** (strategy-gate work, not a name park). **AAPL / SE** (small-sample regime open-fades, liquid) → **HOLD**. Zero/low-signal liquid names (CRM/MSFT/QCOM-history) reflect the regime drought, not name-quality — only a structural mismatch (WPM, already parked) warrants a curation park → **HOLD**.
- **No on-list name reports during market hours today**; no halt/binary catalyst on any name. Pre-market movers (Samsung prelim, SpaceX index add, VERA 07-07 PDUFA) are event/off-list one-offs — **not** clean trending liquid large-caps that fit an intraday breakout strategy → not add candidates.
- **Adds: none** — lower futures into renewed chip volatility (Samsung), a pullback from record highs, the start of Q2 earnings season (event risk ramping), still-hawkish-but-patient Fed (~56% Sept hike), and a −17.7% drawdown with a $730 cushion to protect. Today's leadership is already fully covered on-list (semis + megacaps). No high-conviction trending large-cap absent from the list.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (no on-list intraday earnings today; MU/semis = a Samsung-driven sector dip, not name-quality; ENPH = regime STOP-bucket leak → strategy-gate work; AAPL/SE small-sample; the rest are regime droughts, not structural mismatches; GOOGL park watch already CLOSED 07-01). 0 positions open (nothing locked). No adds into a risk-off, chip-led pullback at the start of earnings season. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Wed 07-08)
- **Chip weakness is the live watch item:** memory (MU/SanDisk/Samsung) led a 3rd down-move today — watch whether the on-list semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) stabilize or keep fading; INTC (2W0L→first loss 07-06) and TSLA remain the book's earners. A multi-day chip dip stays a regime move (no name park) unless a single name separates structurally.
- **Q2 earnings season ramps Wed/Thu** (7 reports Wed 07-08, 13 Thu 07-09; **PEP pre-open Thu 07-09**, off-list) — **check the intraday-earnings calendar each morning and park any on-list name reporting during market hours on its report day.** Banks (~mid-July) are mostly parked already (C/JPM).
- **ENPH** stays the biggest 14d loser but remains the regime-wide false-breakout STOP-bucket leak (PF 0.01) — post-close intraday-regime gate (#1 lever), not a pre-market name park.
- **Verify IMP-009 (down-gap skip) if a gap-down open occurs** — still pending its first live trigger; today's chip-gap tape is a likely test. Equity **$8,230.53 (−17.7%)**, **$730 above** the −25% ($7,500) flag — protect the cushion.

---

## 2026-07-08 — Pre-market Research

### Market context
**Risk-on, chip-led rebound after strong Micron results.** Dow futures ~53,627 (Strong-Buy technicals, up from 53,380 open); APAC ripped overnight — **KOSPI +5.9%, Nasdaq (NQ) +1.9% after Micron (MU) reported its best quarter ever (+18%)** on surging AI-memory demand, rising memory prices and long-term supply agreements (though recent intraday chip volatility wiped ~$137B across memory names, and Michael Burry disclosed a MU short on 07-02). The AI trade is the swing factor — Nasdaq-100 hunting its next catalyst with **Magnificent-Seven Q2 earnings about to begin (late July)**. Other flow: AMZN seeking a ≥$25B USD bond sale (Bloomberg); GOOGL joined a €411M Proxima Fusion round; US–Iran Doha talks reported "positive progress" on the Strait-of-Hormuz 60-day MoU (oil contained). **Earnings today are light — 7 reports, all off-list (LEVI, IMMR, HELE + 4 small-caps); no watchlist name reports during market hours → no intraday earnings risk on the list.** Note: code side, **IMP-013 (break-even@+0.5R / 1R-trail@+1R via broker-side bracket-leg replace) went LIVE today** (post-close routine) — first live session under the new exit management.

### Carried from daily review (2026-07-07)
- **Near-scratch day (−$8.22, 1W/5L):** META TP +$85.74 nearly offset five small losers; two false-breakout STOPs (TSLA −$20.23, AMZN #123 −$43.97) were the whole loss — the standing STOP/false-breakout bucket (all-time PF 0.01), a strategy-gate item, **not** a name defect. **No park triggers matured.**
- **META** — day's only winner, clean BOTH breakout that trended all afternoon → keep top-of-list. ✅
- **AMZN** — worst name (MA open-fade STOP + same-day re-entry that also bled, −$54.95 combined) but behaves with the tape → **no park**; noted as the day's drag. Honored (hold).
- **TSLA** MA open-fade STOP (−$20.23, 21 min), small controlled loss → **no park**. **COST** correctly **skipped** by the IMP-008 stale-signal guard (+1.62% gap) — not a watchlist issue. GOOGL/AAPL low-conf drifters → nothing name-specific.
- **Regime read:** the naive index-EMA gate would NOT have helped 07-07 (winner tagged bearish, biggest loser tagged bullish — IMP-012 proxy-fragility). Don't expect a market filter to save false-breakout STOPs yet → strategy-gate work (post-close #1 lever), **not** a pre-market name action.
- **Q2 earnings season instruction:** "check the intraday-earnings calendar each morning and park any on-list name reporting during hours." Acted on — verified today's 7 reports are all off-list → no earnings park.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,222.25** (flat vs 07-07 close $8,222.28; last_equity carried), cash $8,222.25, buying power $32,889, daytrade_count 0. **−17.8% from $10K**, **$722 above** the −25% ($7,500) strategy-review flag. Clock pre-open (next open 07-08 09:30 ET).
- Per-symbol P&L (14d closed, 42 trades, net **+$118.19**): positive **TSLA +$151.39 (3W4)**, **META +$102.53 (2W3)**, **INTC +$101.96 (2W3)**, TSM +$63.66, MSFT +$58.52, GOOGL +$49.23 (2W4), GOOG +$40.90, MU +$20.27, AMD +$19.61, QCOM +$9.62, SPY +$9.48. Worst: **ENPH −$180.28 (0W2)**, SE −$95.06 (1W3), AAPL −$65.62 (2W4), CRM −$54.42 (0W2), AMZN −$50.36 (1W3), WMT −$27.41, BAC −$18.19, COST −$15.31, AVGO −$2.33. All liquid large-caps/ETFs that fit the strategy; book strongly net-green over 14d, carried by TSLA/META/INTC. **No chronic-loser park trigger matured** — ENPH is the recurring regime-wide false-breakout STOP-bucket leak (PF 0.01, post-close #1-lever target, not a name defect — consistent standing judgment 06-15/06-26/07-01/07-02/07-06/07-07); SE (1W3, open-fade) is watched for ~1W4L with the same signature but not there yet; AAPL/CRM/AMZN are regime open-fades / small-sample.
- **Semis (MU/NVDA/AVGO/TSM/QCOM/INTC/AMD)** — today's leadership on the strong Micron print; all liquid large-cap and strategy-fit → **HOLD all** (the rebound vehicles). MU beat + guided up → the 06-24 earnings park stays correctly resolved (re-enabled 06-25). No halt/binary catalyst on any on-list name.
- **Adds: none** — today's relative strength (chips/AI + megacaps) is **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM + AAPL/MSFT/AMZN/META/GOOG/GOOGL/TSLA). Pre-market movers (Plug Power +1.5% on a 50MW deal, Eos Energy +6.7%, IBM) are event/off-list one-offs — not clean trending liquid large-caps for an intraday breakout strategy. Backdrop still a −17.8% drawdown with a $722 cushion to protect and Mag-7 Q2 earnings about to begin (event risk ramping); no chasing.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (no on-list intraday earnings today; ENPH = regime STOP-bucket leak → strategy-gate work; SE/AAPL/CRM/AMZN = regime open-fades / small-sample; semis are today's leaders not park candidates; the rest are regime droughts, not structural mismatches; GOOGL park watch already CLOSED 07-01). 0 positions open (nothing locked). No adds into a chip-led rebound with everything already covered. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Thu 07-09)
- **IMP-013 went live today (07-08)** — first live session under broker-side break-even@+0.5R + 1R-trail@+1R. Carry to the daily-review: confirm any position that reaches +0.5R has its stop moved to break-even (fewer round-trip STOP losses) and that the bracket-leg replace fires cleanly (no 422/"order already replaced" loops). This directly targets the STOP-bucket leak — watch whether it trims the false-breakout give-back.
- **Chip/AI is the tape's swing factor** — Micron's blockbuster print lifted the whole memory/semi complex; watch whether on-list semis (MU/NVDA/TSM/AVGO/AMD/INTC/QCOM) sustain leadership or fade intraday (the 07-02→07-07 pattern was plunge→bounce→fade). TSLA (3W4, +$151) / META (+$102) / INTC (+$102) remain the book anchors.
- **Q2 / Mag-7 earnings begin late July** — 13 reports Thu 07-09 (PEP pre-open, off-list); banks ~mid-July (JPM ~07-14, C/JPM already parked). **Check the intraday-earnings calendar each morning and park any on-list name reporting during market hours on its report day.**
- **SE** (1W3 incubation, recurring open-fade) — the most persistent single-name drag; re-flag as a park candidate if it reaches ~1W4L with the same false-breakout signature. **ENPH** stays the biggest 14d loser (−$180, 0W2) but remains the regime-wide STOP-bucket leak (post-close gate, not a name park).
- Equity **$8,222.25 (−17.8%)**, **$722 above** the −25% ($7,500) flag — protect the cushion into the start of earnings season.

---

## 2026-07-09 — Pre-market Research

### Market context
**AI-trade rebound day 2 vs a fresh US–Iran flare-up — mixed/higher tape.** Nasdaq-100 futures **+0.5%**, S&P 500 **+0.1%**, Dow ~flat-to-slightly-lower; VIX ~17. The bid is the AI/memory complex ahead of **SK Hynix's US ADR debut** (offering ~7× oversubscribed, prices Thu, lists Fri) — chips rallied across Asia/Europe/US for a 2nd day. Offsetting it: the US launched **new airstrikes on Iran overnight** and Tehran targeted Gulf states; Trump warned of "much worse," revoked the Iran oil-sanction waiver → crude popped Wed then eased (Brent −0.5% to ~$77.60; gold +0.8% to ~$4,115). **Earnings today are all off-list** — PEP (reported a Q2 beat, backed guide), PGR + ~25 small/mid names; **no watchlist name reports during market hours → no intraday earnings risk on the list.** On-list catalyst: **CRM downgraded to Sector Weight from Overweight at KeyBanc** (Agentforce upside doubt) — a rating change, not a binary event.

### Carried from daily review (2026-07-08)
- **Green day (+$93.02, 4W/4L, PF 3.08)** and **IMP-013's first live session — VALIDATED**: 10 broker stop-replaces, 0 rejected (no 422 loop); 3 trades reached +0.5R, round-tripped, and were scratched at break-even (XOM/NVDA #127/AVGO — AVGO's full-1R was ≈−$89), NVDA #131 trailed +1R→TP (+$60.84). The one real loss (QCOM #129 −$37.08) faded from entry so break-even never armed — the residual open-fade leak is the regime-gate's job, not IMP-013's. → watch the daily by_stop_protection split (full-1R vs break-even) as the running scorecard. No watchlist change warranted by 07-08.
- **QCOM** — signaled twice, both faded from/near entry (MA full-stop −$37, BOTH flatten −$7); the day's weak name but liquid + strategy-fit open-fade → **no park**, note the double open-fade. Honored (hold).
- **NVDA** — quality on both sides (AM break-even scratch + PM +1R-trail→TP); semis led on the Micron print → keep top-of-list. **ENPH** — late high-conf BOTH flattened green (+$61.76), its 0W2 STOP signature did NOT repeat → watch, no park. Honored.
- **Instruction acted on:** "check the intraday-earnings calendar each morning and park any on-list name reporting during hours." Verified today's ~13–27 reports (PEP/PGR + small caps) are **all off-list → no earnings park.**

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,315.20** (flat vs 07-08 close $8,315.27; last_equity carried — market closed), cash $8,315.20, buying power $33,260. **−16.8% from $10K**, **$815 above** the −25% ($7,500) strategy-review flag (best-of-incubation cushion). Clock pre-open (next open 07-09 09:30 ET).
- Per-symbol P&L (14d closed, 44 trades): positive **TSLA +$151.39 (3W4)**, **META +$102.53 (2W3)**, **INTC +$101.96 (2W3)**, TSM +$63.66, NVDA +$61.63, MSFT +$58.52, GOOGL +$49.23, GOOG +$40.90, MU +$20.27, AMD +$19.61, WMT +$14.40, SPY +$9.48. Worst: **ENPH −$118.52 (1W3)**, **SE −$95.06 (1W3)**, AAPL −$65.62 (2W4), AMZN −$50.36 (1W3), QCOM −$34.84 (1W3), COST −$15.31, CRM −$12.94. All liquid large-caps/ETFs that fit the strategy; book net-green over 14d, carried by TSLA/META/INTC/TSM/NVDA. **No chronic-loser park trigger matured** — ENPH is the recurring regime-wide false-breakout STOP-bucket leak (PF 0.01, post-close #1-lever target, not a name defect — standing judgment 06-15→07-08); SE (1W3, open-fade) is watched for ~1W4L with the same signature but not there yet; AAPL/AMZN/QCOM are regime open-fades / small-sample.
- **Semis / AI (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM)** — today's leadership on the SK-Hynix-led memory bid; all liquid large-cap and strategy-fit → **HOLD all**. **CRM** — KeyBanc downgrade is a rating change (not a halt/binary event); CRM stays a liquid large-cap that fits the strategy → **HOLD**, just note it may open heavy/not break out cleanly (the bot simply won't signal if it's weak). No halt/binary catalyst on any on-list name. **UNH/XOM** — oil whipsaw on the Iran headlines is a macro move, not a name defect → HOLD.
- **Adds: none** — today's relative strength (chips/AI + megacaps) is **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM + AAPL/MSFT/AMZN/META/GOOG/GOOGL/TSLA). **SK Hynix** (the day's headline) is an illiquid IPO/ADR debut, not a clean trending liquid US large-cap for an intraday breakout strategy. Pre-market one-offs (SpaceX +0.8%, MNST 2-for-1 split) are event/off-list. Backdrop is a geopolitically charged (US–Iran) mixed tape at a −16.8% drawdown with an $815 cushion to protect — no chasing.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (no on-list intraday earnings today; CRM downgrade = rating change not binary event; ENPH = regime STOP-bucket leak → strategy-gate work; SE/AAPL/AMZN/QCOM = regime open-fades / small-sample; semis are today's leaders not park candidates; the rest are regime droughts, not structural mismatches). 0 positions open (nothing locked). No adds into a geopolitically charged mixed tape with leadership already fully covered. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Fri 07-10)
- **AI/memory is the tape's swing factor** — SK Hynix lists Fri 07-10 (its ADR debut day); watch whether the on-list semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) sustain the SK-Hynix/Micron-led leadership or fade intraday (the plunge→bounce→fade pattern has recurred). TSLA (3W4, +$151) / META (+$102) / INTC (+$102) / NVDA (+$62) remain the book anchors.
- **US–Iran is a live macro risk** — overnight airstrikes + Gulf retaliation + revoked oil-sanction waiver → oil/energy (XOM) and defensive rotation can whipsaw the tape intraday; a geopolitical gap open is a live test of IMP-009 (down-gap skip) / IMP-008 (up-gap skip). Not a name action.
- **Earnings ramp:** DAL pre-open Fri 07-10 (off-list); banks ~mid-July (JPM ~07-14, C/JPM already parked); Mag-7 Q2 late July. **Check the intraday-earnings calendar each morning and park any on-list name reporting during market hours on its report day.**
- **CRM** carries a fresh KeyBanc downgrade (07-09) — watch whether it turns into a persistent laggard vs a one-day fade. **SE** (1W3, recurring open-fade) — re-flag as a park candidate at ~1W4L with the same false-breakout signature. **ENPH** stays the biggest 14d loser (−$118, 1W3) but remains the regime-wide STOP-bucket leak (post-close gate, not a name park).
- Equity **$8,315.20 (−16.8%)**, **$815 above** the −25% ($7,500) flag — protect the cushion. Track the daily by_stop_protection split (IMP-014) to keep scoring IMP-013.

---

## 2026-07-10 — Pre-market Research

### Market context
**Cautious-lower open after Thursday's strong risk-on rally, on SK Hynix's Nasdaq debut day.** Thu 07-09 closed strong (S&P 500 +0.81% to 7,543.64, Nasdaq Composite +1.30% to 26,206.89, Dow +0.27%) on renewed chip strength + cooling oil after Trump said Iran called to make a deal (Qatar/Pakistan brokering a return to talks — a **de-escalation reversal** of Wednesday's flare-up). Fri futures **mixed-to-slightly-lower**: Nasdaq-100 −0.2%, S&P 500 ~flat (−0.2%), Dow +0.2% (+111); one Polymarket gauge implies just **~20% odds of a higher open** — a breather after the rally. VIX ~17. **Dominant event: SK Hynix ADR (SKHY) lists on Nasdaq today** — a record ~$26–29B offering (7× oversubscribed, priced ~$149, indicated ~$158 pre-open); the memory/AI complex is bid into it (SMH +2.5%, MU +4.5%, SanDisk +7.6%), though analysts flag a crowded-positioning "breather." **Earnings today are all off-list** — DAL (beat but −3% pre-open), WD-40 (+15%), Circle Internet (+13% on OCC bank approval); **The Whisper Number shows no material AMC reports Friday. No watchlist name reports during market hours today → no intraday earnings risk on the list.**

### Carried from daily review (2026-07-09)
- **Best day of incubation (+$217.39, 3W/1L, PF 7.19)**, carried by **SE** — the standing "most persistent single-name drag" (was 1W3) **redeemed emphatically** with a conf-80 BOTH breakout → TP **+$228.54**, the biggest win of incubation (now 2W3). Daily review: **relax the SE park-candidate watch** — honored (SE is now +$133.48 / 2W4 over 14d; no park).
- **TSM** — the day's only loser (−$35.11), a low-conf (60.1) MA open-fade in a bullish tape; no name defect (liquid semi, strategy-fit), the residual open-fade leak → **no park**. Honored.
- **IMP-015 (07-09):** the ★ skip-bearish market-regime gate is now **REFUTED** by the grown post-06-15 bearish sample (net-positive under both SPY/QQQ proxies); the regime lever needs a different definition (VWAP / skip-first-N-min), not a watchlist action. Noted (strategy-side, not curation).
- **Instruction acted on:** "check the intraday-earnings calendar each morning and park any on-list name reporting during market hours." Verified today's reporters (DAL/WD-40/Circle pre-open; no AMC Friday) are **all off-list → no earnings park.** Banks start ~07-14 (JPM already parked); Mag-7 Q2 late July.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,532.56** (flat vs 07-09 close $8,532.59; last_equity carried — market closed), cash $8,532.56. **−14.7% from $10K**, **$1,033 above** the −25% ($7,500) strategy-review flag — **best cushion of incubation.** Clock pre-open (next open 07-10 09:30 ET).
- Per-symbol P&L (14d closed): positive **TSLA +$151.39 (3W4)**, **SE +$133.48 (2W4)**, **META +$102.53 (2W3)**, **INTC +$101.96 (2W3)**, NVDA +$61.63, TSM +$61.47, MSFT +$58.52, GOOGL +$49.23, GOOG +$40.90, MU +$20.27, SPY +$18.57, QQQ +$14.87, WMT +$14.40, ENPH +$13.92. Worst: **AAPL −$65.62 (2W4)**, **AMZN −$50.36 (1W3)**, **QCOM −$44.46 (0W2)**, COST −$15.31 (0W2), CRM −$12.94, AVGO −$2.45, XOM −$0.19. Book net-green over 14d, carried by TSLA/SE/META/INTC. **No chronic-loser park trigger matured** — AAPL/AMZN/QCOM/COST are regime open-fades / small-sample (all liquid large-caps that fit the strategy), not name defects; ENPH (the standing regime-wide false-breakout STOP-bucket leak, post-close #1 gate lever) is now actually +$13.92 over 14d; SE's park watch is relaxed after its redemption.
- **Semis / AI (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM)** — today's leadership into the SK Hynix debut; all liquid large-cap and strategy-fit → **HOLD all** (a one-day "breather" in a crowded chip trade is not a park trigger; the gate self-throttles). **CRM** — carries the 07-09 KeyBanc downgrade (rating change, not a binary/halt event) → **HOLD**, may open heavy / not break out cleanly (the bot simply won't signal if weak). **UNH/XOM** — oil whipsaw on the Iran headlines is a macro move, not a name defect → HOLD. No halt/binary catalyst on any on-list name today.
- **Adds: none** — today's relative strength (chips/AI + megacaps) is **already fully covered on-list** (NVDA/AVGO/AMD/MU/TSM/INTC/QCOM + AAPL/MSFT/AMZN/META/GOOG/GOOGL/TSLA). **SK Hynix (SKHY)** — the day's headline — is a **first-day ADR/IPO debut**: no price history, no established intraday S/R levels, and extreme first-session volatility → the antithesis of the clean, liquid, trending large-cap the breakout strategy needs. Explicitly not added. Backdrop is a cautious (~20% higher-open odds), post-rally tape at a −14.7% drawdown with the best-of-incubation $1,033 cushion to protect — no chasing.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (no on-list intraday earnings today; CRM downgrade = rating change not a binary event; SE redeemed → park watch relaxed; ENPH/AAPL/AMZN/QCOM/COST = regime open-fades / STOP-bucket leak / small-sample, not structural mismatches; semis are today's leaders, not park candidates; the rest are regime droughts). 0 positions open (nothing locked). No adds into a cautious post-rally tape with leadership already fully covered; SK Hynix is an illiquid first-day debut, not a strategy fit. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Mon 07-13)
- **SK Hynix's first-day trade sets the AI-memory tone** — watch whether the on-list semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) sustain leadership Mon or the "crowded-positioning breather" turns into a fade (the plunge→bounce→fade pattern has recurred). TSLA (3W4, +$151) / SE (2W4, +$133 after its +$228 TP) / META (+$102) / INTC (+$102) remain the book anchors.
- **Bank earnings ramp next week** — JPM ~Tue 07-14 (already parked), other financials mid-July; **check the intraday-earnings calendar each morning and park any on-list name reporting during market hours on its report day.** Mag-7 Q2 late July.
- **US–Iran flipped to de-escalation** (Trump: "Iran called to make a deal") — oil eased and helped Thursday's rally, but it's headline-driven and can whipsaw XOM/energy either way; not a name action.
- **CRM** — watch whether the 07-09 KeyBanc downgrade turns into a persistent laggard vs a one-day fade. **AAPL/AMZN/QCOM** — the current 14d soft names (regime open-fades / small-sample), no park trigger; watch for a chronic-loser pattern. **ENPH** stays the regime-wide STOP-bucket leak (post-close gate work, not a name park).
- Equity **$8,532.56 (−14.7%)**, **$1,033 above** the −25% ($7,500) flag — **best cushion of incubation; protect it.** Track the daily by_stop_protection split (IMP-014) to keep scoring IMP-013.

---

## 2026-07-13 — Pre-market Research

### Market context
**Risk-off, chip-led gap-down open on a fresh US–Iran military flare-up.** Futures point lower: **S&P 500 −0.3% to −0.5%, Nasdaq-100 −0.9% to −1.2%, Dow ~flat-to-−0.4%.** Dominant catalyst: **the US and Iran exchanged fresh missile strikes over the weekend**, shattering the fragile interim Strait-of-Hormuz peace deal — a geopolitical risk-off reversal of last Thursday's "Iran called to make a deal" optimism. **Oil spiked** (Brent +7% on the week to >$77, WTI +6% to >$72), amplifying inflation concerns. **Semis are leading the declines**: US-listed **SK Hynix −8%** (giving back part of Friday's +13% Nasdaq-debut pop), **MU −4%, SanDisk −4%, Seagate −3%, AMD −2%, INTC −2%** — the crowded-chip "breather" the 07-10 note flagged, now amplified by the Middle East + chip-trade-exhaustion worries ahead of ASML/TSM later this week. Backdrop: last week the S&P +1.2% / Nasdaq +1.7% (4th advance in 5 weeks) but the Dow broke a 4-week win streak; Friday closed green (S&P +0.4%). **Big-bank earnings kick off TUESDAY 07-14** (Citi, Goldman, Wells Fargo, JPMorgan, **BofA**); key **US inflation data** this week. Treat today as a geopolitically-driven risk-off chip-led pullback, not a trend break.

### Carried from daily review (2026-07-10)
- **TSLA** — 07-10's whole loss (−$119.38, conf-82 BOTH full-1R open-fade) was **one open-fade, not a name defect** (still +$340.95 / PF 3.86 post-06-15). **No park**, keep top-of-list. Honored.
- **SE** — skipped 07-10 by the IMP-008 stale-signal guard (+2.47% gap-up); watch whether it keeps gapping open. Note today's per-symbol has SE the book's top 14d earner (+$133.48, 2W4). No action.
- **AAPL** — IMP-013 rescued it to the first-ever *trailed* STOP win (+$3.77); behaved well. BAC/SPY/WMT small green flatten drifters — nothing name-specific.
- **Regime read for Mon 07-13:** the naive index-EMA regime filter is refuted (three bullish-tape open-fade counterexamples) — a geopolitical gap-down open is a **live test of IMP-009 (down-gap skip)**; carry to today's daily-review. Strategy-side, not a watchlist action.
- **Standing instruction acted on:** "check the intraday-earnings calendar each morning and park any on-list name reporting during market hours." Verified — see below: **no on-list name reports during market hours today.**

### Watchlist review
- **Positions: 0 open — nothing locked.** Account ACTIVE, equity **$8,431.90** (flat vs 07-10 close $8,431.94 — no trading over the weekend; last_equity $8,431.90), cash $8,431.90, buying power $33,727. **−15.7% from $10K**, **$931.90 above** the −25% ($7,500) strategy-review flag. Clock `is_open=false`, next open 07-13 09:30 ET (pre-open run).
- **Intraday-earnings check (standing rule):** today's headline reporter is **NFLX — but its Q2 report is Thu 07-16 after the close** (confirmed IR release ~1:01pm PT / after-market), NOT today and after-close anyway → no intraday risk for an EOD-flatten bot. The bank cohort (BAC on-list) reports **Tue 07-14**, not today. **No watchlist name reports during market hours today → no earnings park.**
- Per-symbol P&L (last ~10 sessions closed): positive **SE +$133.48 (2W4)**, **META +$108.22 (2W2)**, **INTC +$101.96 (2W3)**, NVDA +$61.63, TSM +$61.47, MSFT +$58.52, GOOGL +$49.23, GOOG +$40.90, TSLA +$26.36 (2W4), SPY +$24.16 (3W3), WMT +$20.64, MU +$20.27, QQQ +$14.87, ENPH +$13.92. Worst: **AAPL −$61.85 (3W5)**, **AMZN −$50.36 (1W3)**, **QCOM −$44.46 (0W2)**, CRM −$12.94, COST −$7.81, AVGO −$2.45, XOM −$0.19. Book net-green over the window, carried by SE/META/INTC/NVDA/TSM. **No chronic-loser park trigger matured** — AAPL/AMZN/QCOM are regime open-fades / small-sample (all liquid large-caps that fit the strategy), not name defects; ENPH (the standing regime-wide false-breakout STOP-bucket leak, post-close #1 gate lever) is now +$13.92; SE's park watch stays relaxed after its 07-09 redemption.
- **Semis / AI (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — today's down-driver (SK Hynix −8%, MU −4%, AMD/INTC −2%) on the Middle East risk-off + crowded-chip breather. All liquid large-cap and strategy-fit → **HOLD all**: a geopolitical + one-week-old sector move is a **regime** phenomenon, not name-quality; the entry gate self-throttles and ATR sizing + no-overnight flatten + IMP-013 break-even bound the risk. **CRM** — 07-09 KeyBanc downgrade is a rating change (not a binary/halt event) → **HOLD**, may open heavy / not break out cleanly (the bot won't signal if weak). **XOM / UNH** — oil spiking +6–7% on the Iran strikes is a macro move (XOM could even benefit); not a name action → **HOLD**. No halt/binary catalyst on any on-list name today.
- **Adds: none** — a geopolitical risk-off gap-down open (US–Iran strikes), chip-led weakness, bank-earnings (Tue 07-14) + inflation event risk this week, and a −15.7% drawdown with a $932 cushion to protect. Today's movers are off-list/illiquid (SK Hynix ADR) or macro (oil); everything relevant is already covered on-list (semis + megacaps). No high-conviction trending large-cap absent from the list — no chasing into a risk-off tape.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (no on-list intraday earnings today — NFLX is 07-16 AMC, banks Tue 07-14; semis = a geopolitical/sector regime move, not name-quality; ENPH now net-green; AAPL/AMZN/QCOM = regime open-fades / small-sample; CRM downgrade = rating change; the rest are regime droughts, not structural mismatches; SE watch relaxed). 0 positions open (nothing locked). No adds into a risk-off geopolitical gap-down with leadership already covered. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Tue 07-14)
- **⚠️ BANK EARNINGS TUE 07-14 — BAC is on-list.** Citi/Goldman/Wells/JPMorgan/**BofA** report Tuesday. Banks typically report **pre-open (BMO)**, so BAC may not report "during market hours" (the park rule's trigger) — but it will gap and trade volatile; **verify BAC's exact report time tomorrow morning and park it for the day if it reports during market hours** (JPM/C already parked). Check the full intraday-earnings calendar as always.
- **Chip trade is the tape's swing factor** — semis led today's risk-off drop (SK Hynix −8%, MU −4%); watch whether the on-list semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM) stabilize or the breather deepens into a fade. **ASML + TSM report this week** — TSM is on-list (confirm its exact date/time and treat as an earnings-park candidate on its report day). SE (2W4, +$133) / META (+$108) / INTC (+$102) / NVDA (+$62) remain the book anchors.
- **US–Iran flipped back to escalation** (fresh weekend missile strikes) — oil spiked +6–7%, energy/XOM can whipsaw either way and a geopolitical gap open is a live test of IMP-009 (down-gap skip) / IMP-008 (up-gap skip); not a name action. **Inflation data this week** given the oil pop — do not add names into the prints.
- **AAPL/AMZN/QCOM** — the current soft names (regime open-fades / small-sample), no park trigger; watch for a chronic-loser pattern. **CRM** — watch whether the KeyBanc downgrade turns into a persistent laggard. **ENPH** now +$13.92 over the window (its STOP-bucket signature quiet); remains the post-close gate's target, not a name park.
- Equity **$8,431.90 (−15.7%)**, **$931.90 above** the −25% ($7,500) flag — protect the cushion into bank earnings + the geopolitical risk-off. Track the daily by_stop_protection split (IMP-014) to keep scoring IMP-013.

---

## 2026-07-15 — Pre-market Research

### Market context
**Risk-on, tech-led tape on a cooler-than-expected inflation print.** Futures higher: **Dow/S&P +0.2%, Nasdaq-100 +0.5%**, building on Tuesday's gains. Dominant catalyst: **June CPI fell 0.4% m/m (annual 3.5% vs 3.8% expected) — the largest single-month decline since April 2020** — which slashed July-hike odds to **17% (from 42%)** on CME FedWatch. **PPI due 8:30 ET today** (the second inflation read of the week). **Chips leading:** US-listed **ASML +3.8%** after raising its 2026 forecast (reassuring on AI-driven demand) — a tailwind for the on-list semis. **PayPal +18.5%** on a Stripe/Advent $60.50/sh buyout offer (an M&A gap, not a breakout name). Today's reporters — **Morgan Stanley, BlackRock, J&J, United Airlines** — are **all off-list**. Oil stays elevated on the ongoing US–Iran flare-up (Iran threatening export corridors), a lingering macro tail, not a name action.

### Carried from daily review (2026-07-14)
- **⚠️ Pre-market routine did NOT run 07-14** (no research entry; BAC traded un-parked into bank earnings and won +$51.47). **VERIFIED the `uswisbot-premarket` cron is healthy** — cron.log shows today's run started 11:45:01 UTC (this session); the 07-14 skip was a one-off, cron is firing normally now.
- **XOM** (−$49.78 fade-to-flatten, wide 3×ATR stop never hit → the first clear IMP-017 EOD_FLATTEN-faded instance), **UNH** (−$39.33 full-1R STOP), **META** (−$21.28 late fade-to-flatten) — all low-conf MA/BOTH open/midday faders; **no name defect, no park** (liquid large-caps, strategy-fit; residual open-fade leak is the ★ VWAP-gate lever, not a curation action). **AMD** IMP-013 break-even rescue (−$0.40) and **GOOG** +$18.18 drift behaved well.
- **BAC** — reported bank earnings pre-open 07-14, gapped/ran to its TP (+$51.47). Bank-earnings park rule = park on-list banks reporting **during** market hours (BAC reported pre-open → tradable). No banks on-list report today.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$8,305.43** (flat vs 07-14 close $8,305.46; last_equity carried — market closed, next open 07-15 09:30 ET), cash $8,305.43. **−16.9% from $10K**, **$805.43 above** the −25% ($7,500) strategy-review flag — cushion trimmed by the 07-14 chop, intact.
- **Intraday-earnings check (standing rule):** today's headline reporters (**MS / BLK / JNJ / UAL**) are **all off-list**. Two on-list names report **TOMORROW (Thu 07-16), both pre-open — NOT today, NOT during market hours:** **TSM** (Q2 conf 2:00 ET / ~2 AM ET pre-dawn, quiet period through 07-15) and **UNH** (results pre-open, 8:00 ET call). Because WisBot **flattens every position by 15:55 ET today**, a name reporting tomorrow morning carries **zero overnight/earnings risk to today's trades** → **no earnings park today.** (The sister EMA-ribbon ustradebot parked TSM & UNH at 11:30 UTC — a more conservative pre-earnings posture for a different, ribbon strategy; not applicable to an EOD-flatten intraday bot.) **⚠️ Both TSM and UNH become earnings-park candidates for TOMORROW's (07-16) pre-market run** — verify report timing and treat per the during-market-hours rule.
- Per-symbol P&L (14d closed, SE's +$228 07-09 TP now aged out of window): green **META +$86.94 (2W3)**, **MSFT +$78.39 (1W1)**, **ENPH +$61.76 (1W1)**, **BAC +$54.63 (2W3)**, **SE +$31.53 (1W4)**, WMT +$20.64, GOOG +$18.18, QQQ +$14.87, SPY +$14.68, GOOGL +$6.04, COST +$1.25. Red **TSLA −$139.61 (0W2)**, **INTC −$74.16 (0W1)**, **NVDA −$68.30 (2W3)**, **AMZN −$55.31 (0W3)**, XOM −$49.97 (0W2), QCOM −$44.46 (0W2), UNH −$39.33 (0W1), TSM −$35.11 (0W1), CRM −$12.94, AAPL −$12.79 (1W2), AMD −$0.40. Book net-red over the window (the concentration flagged weekly: profit had been carried by SE's single TP, now aged out). **No chronic-loser park trigger matured** — TSLA/INTC/NVDA/AMZN/XOM/QCOM are the standing full-1R/EOD-fade open-fade leak (regime, PF-0.01 STOP + IMP-017 EOD_FLATTEN-faded buckets — the ★ VWAP-gate target), **not name defects**: all liquid large-caps that fit the breakout strategy. AMZN (0W3) and QCOM (0W2) are the softest but remain small-sample regime open-fades, not structural mismatches.
- **Semis / AI (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — ASML's guide-up + cooler CPI is a **tailwind** into today's risk-on tape; all liquid large-cap and strategy-fit → **HOLD all.** **CRM** — 07-09 KeyBanc downgrade still a rating change, not a binary/halt → **HOLD** (bot won't signal if weak). **XOM / UNH** — oil macro / UNH pre-earnings-eve drift are not name defects → **HOLD** (UNH flattened by close, well before its 07-16 pre-open report). No halt/binary catalyst on any on-list name **today**.
- **Adds: none** — today's movers are off-list or unfit: **PayPal +18.5%** is an M&A buyout gap (event-driven spike, not a clean liquid breakout — the antithesis of the strategy), **ASML** exposure is already covered via the on-list semis, and today's reporters (MS/BLK/JNJ/UAL) carry binary event risk. Leadership (semis + megacaps) is **already fully covered on-list**. No high-conviction trending large-cap absent from the list → no chasing into an event-heavy (PPI) risk-on tape at a −16.9% drawdown with an $805 cushion to protect.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured (no on-list intraday-earnings reporter today — TSM & UNH are 07-16 pre-open, off today's EOD-flatten trades; softs = regime open-fades / small-sample, the ★ VWAP-gate lever, not name defects; CRM downgrade = rating change; semis are a tailwind today, not park candidates; the rest are regime droughts). 0 positions open (nothing locked). No adds (PayPal = M&A spike; leadership already covered; event-heavy PPI day). Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Thu 07-16)
- **⚠️ TSM & UNH REPORT TOMORROW (Thu 07-16), both pre-open — verify exact timing and apply the earnings-park rule.** TSM: Q2 conf ~2 AM ET pre-dawn (Taipei 14:00); UNH: results pre-open + 8:00 ET call. Both report **before** the open (BMO) like BAC did — so under the during-market-hours trigger they'd stay tradable but gap/volatile; confirm each and park any that shifts to a during-hours release. Also re-scan the full intraday-earnings calendar (Netflix Q2 = Thu 07-16 AMC per prior note; Mag-7 late July).
- **Inflation-data swing:** cooler CPI (−0.4% m/m) flipped the tape risk-on and cut July-hike odds to 17%; **watch today's PPI reaction** and whether the chip strength (ASML guide-up) sustains the semis or fades. META (+$87) / MSFT (+$78) / ENPH (+$62) / BAC (+$55) are the current 14d book anchors; SE's +$228 TP has aged out (book now net-red — the single-trade concentration weekly flagged).
- **Open-fade leak unchanged as the core drawdown driver** — TSLA (−$140) / INTC (−$74) / NVDA (−$68) / AMZN (−$55, 0W3) / XOM (IMP-017 EOD_FLATTEN-faded) are the full-1R + flatten-faded buckets; the only lever is the ★ VWAP market-regime replay (index-EMA & time-of-day both refuted), a `scripts/replay.py` build — NOT a watchlist action and NOT a post-close hack. **AMZN/QCOM** the softest small-sample names — watch for a chronic-loser pattern.
- Equity **$8,305.43 (−16.9%)**, **$805.43 above** the −25% ($7,500) flag — protect the cushion into the 07-16 TSM/UNH earnings + the PPI/oil macro tail. Track by_flatten_outcome (IMP-017), by_stop_protection (IMP-014), by_time_of_day (IMP-016).

---

## 2026-07-16 — Pre-market Research

### Market context
**Modestly lower futures after a two-day rally; heavy earnings + data day.** S&P 500 −0.1% to −0.17%, Nasdaq-100 −0.54%, Dow +0.23%, Russell 2000 −0.36%. Backdrop is two straight cooler inflation prints (Tue CPI −0.4% m/m; **Wed PPI −0.3%**, though annual PPI still 5.5%) — firming near-term Fed-hold expectations while markets still price a meaningful later-year hike. **Oil topped $80/bbl** (+16% off the recent low) after fresh overnight US–Iran attacks and the US reinstating its Iranian-oil blockade — a live inflation/transport tail. **Fed Chair Warsh testifies to Congress today.** Data: **June retail sales + weekly jobless claims** pre-open. Earnings slate is heavy: **TSM (BMO, before open), UNH (BMO, before bell), GE Aerospace (BMO, off-list)** all report pre-open; **NFLX reports AMC (after close).** Notable off-list moves: SpaceX (SPCX) at a new all-time low (below IPO price), BlackRock/Morgan Stanley beat Q2 (Wed), PayPal's Wed M&A gap.

### Carried from daily review (2026-07-15)
- **07-15 was the worst day since 06-10: −$252.01 (−3.03%, 2W/6L).** The entire loss = the recurring **high-confidence BOTH open-fade** leak: NVDA (84) −$66.87 + QQQ (81) −$93.08 + ABNB (86) −$91.26 = −$251.21 ≈ 100% of the day. All broke out, filled near their level, then **faded from entry, never reaching +0.5R** so IMP-013 could not arm (by design). No per-trade discriminator (confidence, volume, extension, time-of-day) separates these — all refuted. **This is the ★ VWAP/opening-range strategy lever (replay build), NOT a watchlist action** — every named symbol is a liquid large-cap, strategy-fit, **no park.**
- **⚠️ Standing instruction acted on: TSM & UNH report today (07-16) — verify timing + apply the earnings-park rule.** Confirmed via calendar: **both are BMO (before open)** — TSM Q2 pre-dawn / conf ~2 AM ET, UNH results pre-open + 8:00 ET call. Under the during-market-hours trigger, BMO reporters stay tradable (exactly like BAC on 07-14, which reported pre-open and ran to TP +$51.47). **NFLX reports AMC** (after close). Since WisBot flattens every position by 15:55 ET, none of the three carries overnight/earnings risk to today's trades → **no earnings park.** (Sister EMA-ribbon ustradebot parks TSM/UNH pre-earnings — a more conservative posture for a different, overnight-holding strategy; not applicable to an EOD-flatten intraday bot.)
- IMP-018 (SPY-VWAP as a 3rd regime proxy) shipped 07-15 and kept the skip-bearish gate **REFUTED** (VWAP-bearish bucket is net-profitable; proxies disagree on 33% of trades → definition-fragile). The regime gate remains unshipped-by-design; the leak's real fix is a per-symbol opening-range/breakout-quality replay, not a curation action.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$8,053.37** (flat vs 07-15 close $8,053.42; last_equity carried — market closed, next open 07-16 09:30 ET), cash $8,053.37, buying power $32,213. **−19.5% from $10K**, **$553.37 above** the −25% ($7,500) strategy-review flag — cushion cut hard by yesterday's −$252; protect aggressively. Clock `is_open=false` (pre-open run).
- **Intraday-earnings check (standing rule):** on-list reporters today = **TSM (BMO), UNH (BMO), NFLX (AMC)**; off-list = GE Aerospace (BMO), plus MS/BLK reported Wed. **None report DURING market hours** → **no earnings park.** All three stay tradable (BMO reports are digested pre-open; NFLX prints after the 15:55 flatten). Expect TSM/UNH to gap/trade volatile at the open — the stale-signal guard (IMP-008) self-throttles chased gap-ups.
- **Per-symbol P&L (14d closed, 51 trades, net −$360.02):** green **META +$147.62 (3W4)**, **MSFT +$78.39 (1W1)**, **ENPH +$61.76 (1W1)**, **BAC +$54.63 (2W3)**, **GOOGL +$41.62 (1W3)**, **SE +$31.53 (1W4)**, WMT +$20.64, GOOG +$18.18, SPY +$14.68, COST +$1.25. Red **TSLA −$139.61 (0W2)**, **NVDA −$115.34 (3W5)**, **ABNB −$91.26 (0W1)**, **QQQ −$78.21 (1W2)**, **INTC −$74.16 (0W1)**, **AMZN −$57.30 (0W4)**, XOM −$49.97 (0W2), QCOM −$44.46 (0W2), NFLX −$42.00 (0W1), UNH −$39.33 (0W1), AVGO −$37.44 (0W2), TSM −$35.11 (0W1), CRM −$12.94, AAPL −$12.79 (1W2), AMD −$0.40. Book net-red — the concentration weekly-flagged (SE's +$228 TP aged out; the open-fade leak dominates). **No chronic-loser park trigger matured** — TSLA/NVDA/ABNB/QQQ/INTC/AMZN/XOM are the standing full-1R + IMP-017 EOD_FLATTEN-faded open-fade leak (regime, the ★ VWAP-gate target), **not name defects**; all liquid large-caps that fit the breakout strategy. **AMZN (now 0W4) and QCOM (0W2)** the softest, but still small-sample regime open-fades, not structural mismatches — watch for a chronic-loser pattern, no trigger yet.
- **Semis / AI (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — TSM prints pre-open (a swing factor for the whole complex); all liquid large-cap and strategy-fit → **HOLD all** (a report/sector move is regime, not name-quality; the entry gate self-throttles, ATR sizing + no-overnight flatten + IMP-013 bound the risk). **CRM** — 07-09 KeyBanc downgrade is a rating change (not binary/halt) → **HOLD.** **XOM / UNH** — oil >$80 macro / UNH BMO-earnings gap are not name defects → **HOLD** (UNH's report is out before the open; any trade flattens by close). No halt/binary catalyst on any on-list name **during market hours** today.
- **Adds: none** — softer futures after a 2-day rally, a heavy event day (TSM/UNH/NFLX earnings + retail sales + jobless claims + Warsh Congressional testimony + oil >$80 on the Iran flare-up), and a **−19.5% drawdown with the cushion cut to $553** by yesterday's −$252. Today's notable movers are off-list/unfit: **SpaceX** new low (not a long breakout), the bank beats (MS/BLK) are already-reported event names, PayPal was a Wed M&A spike. Leadership (semis + megacaps) is **already fully covered on-list.** No high-conviction trending large-cap absent from the list → no chasing into an event-heavy tape at a trimmed cushion.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: **no on-list name reports DURING market hours** (TSM/UNH BMO, NFLX AMC — all off today's EOD-flatten trades, like BAC 07-14); the soft names (AMZN 0W4 / QCOM 0W2 / XOM 0W2) are small-sample regime open-fades — the ★ VWAP-gate strategy lever, **not** name defects or structural mismatches; CRM's downgrade is a rating change; semis are a TSM-earnings/regime swing, not park candidates; the rest are regime droughts. 0 positions open (nothing locked). No adds into an event-heavy day at a −19.5% drawdown with leadership already covered. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Fri 07-17)
- **⚠️ NFLX reported AMC today (07-16) → it will gap Fri 07-17** — treat NFLX intraday with extra caution (wide ranges post-earnings; no overnight risk for an EOD-flatten bot). Re-scan the full intraday-earnings calendar (Mag-7 late July begins ramping); park any on-list name that reports **during** market hours.
- **TSM/UNH earnings reaction** — both printed pre-open today; note whether TSM's report (June revenue +68% YoY momentum) lifts or fades the semi complex, and whether UNH gapped. Neither was parked (BMO). META (+$148) / MSFT (+$78) / ENPH (+$62) / BAC (+$55) are the 14d book anchors; book net-red (open-fade leak dominant).
- **Open-fade leak = still the core drawdown driver** — 07-15's NVDA/QQQ/ABNB high-conf BOTH open-fades (−$251) are the same full-1R + IMP-017 flatten-faded buckets; the only lever is the ★ VWAP/opening-range market-regime replay (index-EMA, time-of-day, and now VWAP-as-conceived all refuted), a `scripts/replay.py` build — **NOT a watchlist action and NOT a post-close hack.** **AMZN (0W4) / QCOM (0W2)** the softest small-sample names — watch for a chronic-loser pattern.
- **Macro tail:** oil >$80 on the US–Iran flare-up + reinstated blockade, Warsh Congressional testimony, retail sales/jobless claims today — an inflation/geopolitics-driven tape; do not add names into the events. Equity **$8,053.37 (−19.5%)**, **$553.37 above** the −25% ($7,500) flag — cushion trimmed by 07-15's −$252; protect it aggressively.

---

## 2026-07-17 — Pre-market Research

### Market context
**Risk-off, AI/chip-led selloff deepening — futures sharply lower.** Nasdaq-100 futures **−1.6%**, S&P 500 **−0.8%**, Dow **−0.5% (−266 pts)**. Dominant catalyst: a **global semiconductor selloff on AI-capex sustainability fears** — SOXX −3%, SMH −2%; AMAT −4%, LAM −3%, INTC/KLA/Arm −3%, NVDA −2%, MU −1%. Trigger: South Korea's Kospi −7% (SK Hynix/Samsung plunge) + carryover from Wed's Meta "sell compute" excess-capacity worry; BBH/BIS flag AI capex "boom-bust" risk. **NFLX −8% to a 52-wk low** after weak Q3 guidance (reported AMC 07-16 — event now RESOLVED). Gold +0.6% (safe-haven bid). Major averages headed for a **losing week** (SMH −6.9% wk). Today's earnings slate is a **light Friday — RF, TFC (regional banks), USAU — all off-list**; **no on-list name reports during market hours.**

### Carried from daily review (2026-07-16)
- **AMZN now 0W5** (07-16 −$37.25 full-1R open-fade STOP) — the standing chronic-loser watch, flagged as the softest small-sample name. Daily-review verdict is firm: the losses are the **above-VWAP open-fade regime (IMP-019), not a name defect** — AMZN is a top-liquidity mega-cap, strategy-fit. Note said "if AMZN takes another full-1R fade *consider* a park." A fresh fade hasn't happened yet (pre-open); parking one megacap won't fix a strategy-wide leak whose real fix is the **VWAP entry-quality gate proposed in todo.md (awaiting human approval)**. → **HOLD, keep as #1 watch** (no trigger matured).
- **GOOG** — 07-16 conf-92 breakout faded but IMP-013 scratched it (−$3.28 vs ~−$146 full-1R); mechanism working. **AAPL/WMT** quiet MA drift-up winners. All fine, no action.
- **★ Open-fade lever:** IMP-019 found the first non-refuted per-trade discriminator (entry distance from own session VWAP; ≥+0.25% above = net-negative). This is a **strategy/entry-logic lever awaiting human sign-off in todo.md — NOT a watchlist action.**

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$8,050.65** (flat vs last_equity $8,050.65 — market closed, next open 07-17 09:30 ET), cash $8,050.65, buying power $32,202. **−19.5% from $10K**, **$550.65 above** the −25% ($7,500) strategy-review flag — thin cushion; protect aggressively.
- **Intraday-earnings check (standing rule):** today's reporters (**RF, TFC, USAU**) are **all off-list**; no on-list name reports **during market hours** → **no earnings park.** **NFLX** reported AMC 07-16 (event resolved) and will gap/trade wide today — treat with extra caution intraday, but a −8% post-earnings gapper is still a liquid large-cap and WisBot flattens by 15:55 ET (**zero overnight risk**) → **HOLD, no park.**
- **Semis / AI (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — today's down-driver is a **global AI-capex/chip regime selloff** (Kospi −7%, SOXX −3%), not name-quality; all liquid large-cap and strategy-fit → **HOLD all.** The entry gate self-throttles chased gaps (IMP-008), ATR sizing + no-overnight flatten + IMP-013 break-even bound the risk. **CRM** — the 07-09 KeyBanc downgrade remains a rating change (not binary/halt) → **HOLD.** **XOM/UNH** — oil >$80 macro / post-earnings drift are not name defects → **HOLD.** No halt/binary catalyst on any on-list name during market hours today.
- **Adds: none** — a risk-off AI-chip selloff, a losing week, and a **−19.5% drawdown with the cushion cut to $550** argue against chasing. Today's movers are off-list/unfit (regional banks; chip names are *down*, not clean breakouts); NFLX is a resolved earnings gapper. Leadership (semis + megacaps) is **already fully covered on-list.** No high-conviction trending large-cap absent from the list → no chasing into a risk-off tape at a thin cushion.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: no on-list name reports during market hours (RF/TFC/USAU off-list; NFLX AMC-resolved, off today's EOD-flatten trades); AMZN (0W5) is the above-VWAP open-fade regime — the ★ VWAP-gate strategy lever (todo.md, human sign-off), **not** a name defect; semis are a global AI-capex regime selloff, not name-quality; CRM downgrade = rating change; the rest are regime droughts. 0 positions open (nothing locked). No adds into a risk-off chip-selloff losing week at a −19.5% drawdown with leadership already covered. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Mon 07-20)
- **AI-capex / chip-selloff is the tape's swing factor** — 07-17 opened risk-off on global AI-buildout skepticism (Kospi −7%, SOXX −3%, NVDA/MU/AMD/INTC weak). Watch whether the semis stabilize or the breather deepens into a multi-day de-rate; on-list semis are HOLDs (regime, not name defects) but note if any prints a chronic-loser pattern. Mag-7 earnings ramp begins late July — re-scan the intraday-earnings calendar Monday and park any on-list name reporting **during** market hours.
- **AMZN — still the #1 chronic-loser watch (0W5 into 07-17).** If it takes *another* full-1R open-fade this week, the park decision matures — but the documented cause is the above-VWAP open-fade regime, not a name flaw. The real lever is the **VWAP entry-quality gate in todo.md (human approval)**, not a curation action.
- **NFLX** post-earnings (07-16 AMC, −8% to a 52-wk low) — expect wide intraday ranges for a few sessions; no overnight risk (EOD-flatten). Keep unless it shows a chronic-loser pattern.
- **Open-fade leak = still the core drawdown driver** (full-1R + IMP-017 flatten-faded buckets); every index-regime proxy (EMA9, time-of-day, SPY-VWAP) refuted, only IMP-019's per-symbol entry-vs-own-VWAP separates it — a `scripts/replay.py`/entry-logic lever awaiting human sign-off, **NOT a watchlist action.** Equity **$8,050.65 (−19.5%)**, **$550.65 above** the −25% ($7,500) flag — cushion thin; protect it aggressively into the chip selloff.

---

## 2026-07-20 — Pre-market Research

### Market context
**Risk-on bounce to start the week — chips rebound after a brutal week; futures higher.** S&P 500 futures **+0.3%**, Nasdaq-100 **+0.6%**, Dow **+131 (+0.3%)**. **Semis lead the recovery**: SMH +1%, **MU +3% (leader)**, NXP/Teradyne/**AMD +2%** each — a relief bounce after last week's AI-capex/chip de-rate (SOXX −11% over the month, **−20% off its late-June peak**; SMH −6.9% on the wk, 3rd weekly drop in 4). Selloff driver was AI-hyperscaler capex-sustainability fears + Chinese AI competition (Moonshot's Kimi release). Sector rotation last week ran from chips → **financials/industrials/energy** (BAC/XOM on-list cover these). Oil/Iran remains the macro swing: US completed a 9th straight day of strikes overnight, but sentiment improved on renewed diplomacy hopes (Iran signaled openness to talks) → oil fluctuating. **Monday is quiet — no major earnings or US data today.** This week's Mag-7 slate: **GOOGL + TSLA both Wed 07-22 AMC (after close), INTC Thu — all after-hours / off-list, none during market hours** (GOOGL is the first hyperscaler AI-capex read-through). No on-list name reports during market hours today or this week.

### Carried from daily review (2026-07-17)
- **AMD — new chronic-loser watch** (07-17 −$115.32, the day's worst; conf-BOTH breakout filled +3.82% above session VWAP → full-1R fade in the chip selloff). Documented cause = the **above-VWAP open-fade regime, not a name defect** (same as AMZN). No park trigger. Ironically AMD is a **+2% pre-market leader today** on the semi bounce → clearly liquid/strategy-fit → **HOLD.**
- **AMZN — still #1 chronic-loser watch (0W5).** Did NOT trade 07-17 (no signal) → no fresh full-1R fade matured the park decision. Cause remains the above-VWAP open-fade regime, whose real fix is the **VWAP entry-quality gate (todo.md, human sign-off)**, not a curation action → **HOLD, keep as #1 watch.**
- **CRM / UNH** — MA-only entries that faded above VWAP to full stops in the risk-off tape; regime-driven, not name defects → **HOLD.** UNH ground down all afternoon — note if it stays heavy.
- **Semis (NVDA/MU/TSM/AVGO/INTC/QCOM)** — last week's down-driver was a global AI-capex/chip de-rate (regime, not name-quality); today they lead the bounce → **HOLD all.** MU stays qty-capped (~$884/sh, negligible risk).
- **★★ VWAP entry-quality gate (IMP-020)** — pre-ship validation shows skipping fills >+0.25% above session VWAP flips the 61-trade replay book −$610 → **+$78.49** (~12× the noise budget). This is a **strategy/entry-logic lever awaiting human sign-off in todo.md — NOT a watchlist action.**

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$7,839.15** (flat vs last_equity — market closed, next open 09:30 ET), cash $7,839.15, buying power $31,356. **−21.6% from $10K**, **$339.15 above** the −25% ($7,500) strategy-review flag — cushion thinned by 07-17's −$211; protect aggressively.
- **Intraday-earnings check (standing rule):** Monday is a quiet no-earnings day; this week's on-list reporters **GOOGL + TSLA are Wed 07-22 AMC (after close), INTC Thu after-hours** → **no on-list name reports during market hours today or this week** → **no earnings park.** (WisBot flattens by 15:55 ET → zero overnight risk on any AMC gapper.)
- **Semis / AI (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — the de-rate was a global regime move, not name-quality; today they lead the relief bounce (MU +3%, AMD +2%) → all liquid large-cap, strategy-fit → **HOLD all.** Whether this is a durable bottom or a bounce inside a de-rate resolves at GOOGL's Wed capex read-through.
- **Financials/industrials/energy rotation** — **BAC** and **XOM** already carry that exposure on-list; no gap to fill.
- **AMZN (0W5) / AMD** chronic watches — regime (above-VWAP open-fade) not name defects, no trigger matured → **HOLD.** **NFLX** (07-16 AMC, −8% to 52-wk low) — post-earnings wide ranges fading; still a liquid large-cap, EOD-flatten → **HOLD.** **CRM/UNH/rest** — regime droughts, no halt/binary catalyst during market hours today → **HOLD all.**
- **Adds: none.** Today's leaders are the on-list semis (already covered); the rotation sectors are covered (BAC/XOM). Chasing a Day-1 relief bounce into an unresolved AI-capex de-rate — with a **−21.6% drawdown and only $339 of cushion** and the first hyperscaler capex print (GOOGL) still two days out — is exactly the wrong risk to add. No high-conviction trending large-cap is absent from the list.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: no on-list name reports during market hours today or this week (GOOGL/TSLA Wed AMC, INTC Thu after-hours); AMZN (0W5) and AMD are the above-VWAP open-fade regime — the ★ VWAP-gate strategy lever (todo.md, human sign-off), **not** name defects; semis are a global AI-capex regime move (leading today's bounce), not name-quality. 0 positions open (nothing locked). No adds — leaders/rotation already covered, and a thin $339 cushion argues against chasing a Day-1 bounce before GOOGL's Wed capex read-through. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Tue 07-21)
- **Chip bounce durability is Tue's swing factor** — 07-20 opened risk-on with semis leading (MU +3%, AMD +2%) after a −20%-off-peak de-rate. Watch whether the bounce holds or fades back into the AI-capex skepticism; the real test is **GOOGL's Wed 07-22 AMC print (first hyperscaler capex read-through)** — on-list semis are HOLDs (regime, not name defects). Re-scan the intraday-earnings calendar: **GOOGL + TSLA Wed AMC, INTC Thu** — all after-hours so far, but park any on-list name that shifts to *during* market hours.
- **AMD + AMZN — dual chronic-loser watch.** AMD (07-17 −$115, worst of day) and AMZN (0W5, didn't trade 07-17). Both are the **above-VWAP open-fade regime, not name flaws** — a fresh full-1R open-fade on either matures a park *discussion*, but the real lever is the **VWAP entry-quality gate (IMP-020, todo.md, human sign-off)**, not curation.
- **Open-fade leak = still the core drawdown driver**; IMP-020 validated that skipping fills >+0.25% above session VWAP flips the replay book −$610 → +$78.49 — an entry-logic lever awaiting human sign-off, **NOT a watchlist action.** Equity **$7,839.15 (−21.6%)**, **$339.15 above** the −25% ($7,500) flag — cushion thin; protect it aggressively into the Mag-7 earnings week.

---

## 2026-07-21 — Pre-market Research

### Market context
**Risk-on again — semis rebound Day 2; futures higher.** Nasdaq-100 futures **+1.4%**, S&P 500 **+0.6%**, Dow **+166 (+0.3%)**. Chips extend Monday's relief bounce (oversold NDX/SOX mean-reversion) on **US–Iran ceasefire-talk hopes** (mediators floating a 10-day truce); oil steadied ~**$83.90 WTI** (Red Sea shipping still a swing). **Earnings season strong** — 87% of the ~54 S&P names reported have beaten EPS; premarket beats **3M +7%, GM +2%**. Fed pause priced at 88% (CME FedWatch). Today's BMO reporters (**GM, MMM, NOC, NVS, SCHW, DHR, HAL, DHI, MSCI, EFX, SYF, GPC, HAS, KEY, ALLY** …) are **all off-list**; **no on-list name reports during market hours today.** This week's on-list slate: **GOOGL + TSLA Wed 07-22 AMC, INTC Thu — all after-hours** (GOOGL = first hyperscaler AI-capex read-through, the week's real test).

### Carried from daily review (last written 2026-07-17; 07-20 review not yet posted)
- **Mon 07-20 booked −$87.86** across 4 trades (QCOM −40.32 STOP @09:36, MU −25.18 STOP, INTC −22.12 EOD_FLATTEN, AVGO −0.24 STOP) — equity $7,839.15 → **$7,751.27**. Same **above-VWAP open-fade signature** (QCOM opened straight into a full-1R stop); not name defects.
- **QCOM now 0W3 (−$84.78 / 14d)**, **AMZN 0W4 (−$50.58)**, **AMD 0W2 (−$115.72)**, **UNH 0W2 (−$79.35)**, **TSLA 1×−$119.38** — the standing chronic-loser watches. Documented cause across every daily review = the **above-VWAP open-fade regime, not name flaws** (all top-liquidity large-caps, strategy-fit). The real lever is the **VWAP entry-quality gate (IMP-020, todo.md, human sign-off)**, not curation → **HOLD all.**
- **14d winners anchor the book:** SE +186.89, MSFT +78.39, ENPH +61.76, BAC +54.63, META +39.40, AAPL +35.95, WMT +26.16 — the list's quality names are producing; the leak is entry-quality, uniform across names.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$7,751.27**, cash $7,751.27, buying power $31,005. **−22.5% from $10K**, **$251.27 above** the −25% ($7,500) strategy-review flag — cushion cut to a hair by Monday's −$88; protect aggressively.
- **Intraday-earnings check (standing rule):** today's reporters are all off-list; on-list GOOGL/TSLA are Wed AMC, INTC Thu after-hours → **no on-list name reports during market hours today or this week** → **no earnings park.** (WisBot flattens by 15:55 ET → zero overnight risk on any AMC gapper.)
- **Semis / AI (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — extend the relief bounce (Day 2, oversold mean-reversion); the de-rate was a global AI-capex regime move, not name-quality → all liquid large-cap, strategy-fit → **HOLD all.** Durability resolves at GOOGL's Wed capex print.
- **Chronic watches (QCOM 0W3 / AMZN 0W4 / AMD / UNH / TSLA)** — every loss is the above-VWAP open-fade regime, no name-specific defect (all top-liquidity large-caps, none sub-$5/illiquid/halt-prone) → **HOLD.** Parking liquid large-caps won't fix a strategy-wide entry-quality leak; that's churn. **NFLX** (07-16 AMC gapper) post-earnings ranges normalizing, EOD-flatten → **HOLD.** **CRM/rest** — regime droughts, no halt/binary during market hours today → **HOLD all.**
- **Adds: none.** Today's premarket movers are earnings gappers (3M +7%, GM +2%) — off-list and not clean-breakout adds; the semi/megacap leadership is already fully on-list; rotation sectors (financials/energy) covered by BAC/XOM. Chasing a Day-2 relief bounce into an unresolved AI-capex de-rate — with a **−22.5% drawdown and only $251 of cushion** and GOOGL's capex read-through still a day out — is exactly the wrong risk to add.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: no on-list name reports during market hours today or this week (GOOGL/TSLA Wed AMC, INTC Thu after-hours); QCOM 0W3 / AMZN 0W4 / AMD / UNH / TSLA are the above-VWAP open-fade regime — the ★★ VWAP-gate strategy lever (IMP-020, todo.md, human sign-off), **not** name defects; semis are a global AI-capex regime move (bouncing today), not name-quality. 0 positions open (nothing locked). No adds — leaders/rotation already covered, thin $251 cushion argues against chasing a Day-2 bounce before GOOGL's Wed capex print. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Wed 07-22)
- **★★ THE REAL FIX IS BLOCKED ON HUMAN SIGN-OFF, NOT CURATION.** The book has bled to −22.5% ($7,751, only **$251 above** the −25% flag) almost entirely on above-VWAP open-fades. IMP-020 is validated: skipping fills >+0.25% above session VWAP flips the 61-trade replay book −$610 → **+$78.49** (~12× noise budget). This is a `bot/engine.py` entry-logic change awaiting approval in `todo.md` — **re-escalate it; watchlist churn cannot fix a strategy-wide leak.**
- **GOOGL Wed 07-22 AMC = the week's pivot** (first hyperscaler AI-capex read-through) — decides whether the 2-day semi bounce is a bottom or a bounce inside the de-rate. On-list semis stay HOLDs (regime, not name defects). **TSLA also Wed AMC, INTC Thu** — all after-hours; park any on-list name that shifts to *during* market hours.
- **QCOM now 0W3 / AMZN 0W4 / AMD 0W2 / UNH 0W2** chronic watches — all the above-VWAP open-fade regime, all top-liquidity large-caps, no name-specific defect. A fresh full-1R fade matures a park *discussion* only; the real lever remains the VWAP gate, not a park. Cushion is at a hair ($251) — protect it aggressively into the Mag-7 print week.

---

## 2026-07-22 — Pre-market Research

### Market context
**Risk-off into the first Mag-7 prints; chips cool, oil spikes.** Futures lower: **S&P 500 −0.2%, Nasdaq-100 −0.6% (leading the retreat), Dow −0.1%** (steeper at 4 AM ET: NDX −0.9%). SPY $746.85 −0.19%, QQQ $704.86 −0.58% pre-market. Dominant catalysts: (1) **the US–Iran conflict entered its 12th day → WTI crude surged above $85/bbl**, dampening risk appetite; (2) **Tuesday's chip rally cooled** — NVDA −1.0%, MU −2.8%, AVGO, AMD −2.0%, INTC −3.2% all lower pre-market (Perplexity + WebSearch corroborated). **GOOGL + TSLA both report Q2 AMC (after close) today — the first two Magnificent-7 megacaps** (GOOGL = first hyperscaler AI-capex read-through, the week's real test); IBM/TXN/ServiceNow also AMC (off-list); **INTC reports Thu.** Off-list movers: **SMCI +16%** pre-market on a record backlog (AI server maker); SK Hynix denied an Intel-Ohio-campus buyout. AAPL firm (~$327; China approved Apple Intelligence, PT raises). Retail sentiment SPY "extremely bearish"; Polymarket prices a lower open. **No on-list name reports DURING market hours today** → no intraday earnings risk on the list.

### Carried from daily review (2026-07-21)
- **07-21 booked +$78.41 (3W/0L)** — first green day after three reds — all MA-only conf 60-62 drifted-up EOD_FLATTENs (AVGO +13.38, QQQ +16.00, **INTC +49.03 / +3.70%, day's engine**). Notes flagged **INTC** as the best name (chip recovery, keep top-of-list), AVGO/QQQ benign; tape had flipped green, watch for the return of high-conf BOTH breakouts (none fired). Equity $7,829.68, books reconcile to the penny, 0 open, no naked overnight.
- **★★ THE REAL FIX IS BLOCKED ON HUMAN SIGN-OFF, NOT CURATION** (07-21 note, re-escalated): the drawdown is almost entirely above-VWAP open-fades; IMP-020 validated skipping fills >+0.25% above session VWAP flips the 61-trade replay book −$610 → +$78.49 (~12× noise budget). This is a `bot/engine.py` entry-logic change awaiting approval in `todo.md` — watchlist churn cannot fix a strategy-wide leak.
- **QCOM 0W3 / AMZN 0W4 / AMD 0W2 / UNH 0W2** chronic watches — all the above-VWAP open-fade regime, all top-liquidity large-caps, no name-specific defect → HOLD.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$7,829.66** (flat vs 07-21 close $7,829.68; last_equity $7,829.66 — market closed, next open 07-22 09:30 ET), cash $7,829.66, buying power $31,318. **−21.7% from $10K**, **$329.66 above** the −25% ($7,500) strategy-review flag — thin cushion; protect aggressively. Clock `is_open=false` (pre-open run).
- **Intraday-earnings check (standing rule):** today's on-list reporters **GOOGL + TSLA are AMC (after close)**; off-list AMC = IBM/TXN/ServiceNow/Southwest; **INTC is Thu**. **No on-list name reports DURING market hours today** → **no earnings park** (WisBot flattens by 15:55 ET → zero overnight risk on any AMC gapper). Expect GOOGL/TSLA to gap Thu 07-23.
- Per-symbol P&L (12d closed): green **MSFT +$78.39 (1W1)**, **BAC +$54.63 (2W2)**, **META +$39.40 (1W2)**, **AAPL +$32.18 (1W2)**, **INTC +$26.91 (1W2)**, GOOG +$14.90, WMT +$11.76 (2W2), COST +$9.06, SPY +$5.59. Red **NVDA −$176.97 (1W3)**, **AMD −$115.72 (0W2)**, **ABNB −$91.26 (0W1)**, **UNH −$79.35 (0W2)**, **QQQ −$77.08 (1W2)**, CRM −$55.65, XOM −$49.78, NFLX −$42.00, SE −$41.65, QCOM −$40.32, **AMZN −$39.60 (0W3)**, MU −$25.53, AVGO −$24.18. Book net-red over the window — the open-fade leak dominates. **No chronic-loser park trigger matured:** NVDA/AMD/ABNB/UNH/QCOM/AMZN are the standing full-1R + IMP-017 EOD_FLATTEN-faded open-fade leak (regime, the ★★ VWAP-gate target), **not name defects** — all liquid large-caps that fit the breakout strategy; none sub-$5/illiquid/halt-prone.
- **Semis / AI (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — cooling pre-market after Tuesday's bounce; the swing factor is GOOGL's AMC capex read-through, a regime move, not name-quality → all liquid large-cap, strategy-fit → **HOLD all.** **CRM** — the 07-09 KeyBanc downgrade remains a rating change (not binary/halt) → **HOLD.** **XOM** — oil >$85 macro is not a name defect → **HOLD** (may whipsaw either way). **NFLX** (07-16 AMC gapper) post-earnings ranges normalized, EOD-flatten → **HOLD.** No halt/binary catalyst on any on-list name during market hours today.
- **Adds: none** — a risk-off tape (chips cooling, oil >$85 on the Iran flare-up, extremely-bearish SPY sentiment) into the first Mag-7 prints, at a **−21.7% drawdown with only $330 of cushion** and GOOGL's capex read-through still after today's close. Today's notable mover **SMCI +16%** is off-list and an earnings-gap spike (the antithesis of a clean liquid breakout), not an add. Semi/megacap leadership is already fully covered on-list; rotation sectors (financials/energy) covered by BAC/XOM. No high-conviction trending large-cap absent from the list → no chasing into an event-heavy, oil-shocked tape at a thin cushion.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: no on-list name reports during market hours today (GOOGL/TSLA AMC, INTC Thu); NVDA/AMD/ABNB/UNH/QCOM/AMZN are the above-VWAP open-fade regime — the ★★ VWAP-gate strategy lever (IMP-020, todo.md, human sign-off), **not** name defects; semis are a global AI-capex regime move (cooling into GOOGL's read-through), not name-quality; CRM's downgrade is a rating change; the rest are regime droughts. 0 positions open (nothing locked). No adds — leaders/rotation already covered, SMCI is an off-list earnings spike, and a thin $330 cushion argues against chasing a risk-off tape before GOOGL's capex print. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Thu 07-23)
- **⚠️ GOOGL + TSLA reported AMC today (07-22) → both gap Thu 07-23** — treat intraday with extra caution (wide post-earnings ranges; no overnight risk for an EOD-flatten bot). GOOGL is the first hyperscaler AI-capex read-through — its reaction decides whether the semi complex re-rates up or resumes the de-rate. **INTC reports Thu 07-23** (after-hours per current calendar — verify timing and park it if it shifts to *during* market hours). Re-scan the full intraday-earnings calendar (Mag-7 ramp: MSFT/META/AAPL/AMZN late July).
- **Chronic watches unchanged (QCOM 0W3 / AMZN 0W4 / AMD 0W2 / UNH 0W2 / NVDA)** — all above-VWAP open-fade regime, all top-liquidity large-caps, no name-specific defect. A fresh full-1R fade matures a park *discussion* only; the real lever is the ★★ VWAP entry-quality gate (IMP-020, human sign-off), NOT curation. INTC was the 07-21 standout (+3.70%) — keep top-of-list.
- **★★ The real fix is still blocked on human sign-off** — re-escalate IMP-020 (skip fills >+0.25% above session VWAP; validated −$610 → +$78.49 in replay). Watchlist churn cannot fix a strategy-wide entry-quality leak.
- **Macro:** oil >$85 on the US–Iran flare-up (day 12), chips cooling, extremely-bearish sentiment — an inflation/geopolitics-driven risk-off tape; do not add names into the Mag-7 prints. Equity **$7,829.66 (−21.7%)**, **$329.66 above** the −25% ($7,500) flag — cushion thin; protect it aggressively.

---

## 2026-07-23 — Pre-market Research

### Market context
**Risk-off after the first two Mag-7 prints; megacap tech leads futures lower.** Futures: **S&P 500 −0.3%, Dow −0.3%, Nasdaq-100 −0.4%** (WebSearch corroborated; Perplexity `sonar` returned no fresh search evidence this morning → fell back to WebSearch). **GOOGL** reported Q2 AMC 07-22: revenue/ads beat (ads +10% YoY, "strongest revenue-growth quarter in five years") but a **+$10B 2026 capex hike** spooked the tape — dipped after-hours, now **+~3% pre-market (~$197.43)**. **TSLA** Q2 AMC 07-22 was weak: **revenue −12% YoY (biggest drop in a decade)**, opex +47%, operating margin 1.4% (from 4.1%), Musk flagged 2026 a "massive capex year" (Optimus/robotaxi/data centers) → **−~6% pre-market (~$313.44)**. **INTC reports Q2 today AFTER the close** (verified — TMUS/LMT also today; jobless claims 8:30 ET). Oil touched **~$90** on the US–Iran conflict; the dominant theme is **AI-capex ROI scrutiny.** **No on-list name reports DURING market hours today** → no intraday earnings risk (WisBot flattens by 15:55 ET → GOOGL/TSLA gaps carry zero overnight risk; INTC gaps Fri 07-24).

### Carried from daily review (latest posted 2026-07-17; 07-20→07-22 context tracked in this research-log)
- **07-22 booked ≈ −$165.52** (equity $7,829.66 → **$7,664.14**): **ENPH −124.80 STOP (−1.59%, day's worst)**, UNH −59.88 EOD_FLATTEN, QCOM −20.15 EOD_FLATTEN vs BAC +18.52, AMD +20.79 (IMP-013 breakeven-rescued STOP). Same **above-VWAP open-fade signature** — not name defects.
- **★★ THE REAL FIX IS BLOCKED ON HUMAN SIGN-OFF, NOT CURATION** (standing, re-escalated): the drawdown is almost entirely above-VWAP open-fades; IMP-020 validated that skipping fills >+0.25% above session VWAP flips the 61-trade replay book −$610 → **+$78.49** (~12× noise budget). A `bot/engine.py` entry-logic change awaiting approval in `todo.md` — watchlist churn cannot fix a strategy-wide leak.
- **Chronic watches (NVDA/UNH/ENPH/AMD/QCOM/AMZN)** — all the above-VWAP open-fade regime, all top-liquidity large-caps, no name-specific defect → HOLD.

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$7,664.14**, cash $7,664.14, buying power $7,664.14 (last_equity API field read 0 — known quirk; prior close $7,829.66 is the reference). **−23.4% from $10K**, only **~$164 above** the −25% ($7,500) strategy-review flag — **cushion at its thinnest yet**; protect aggressively. Clock `is_open=false`, next open 07-23 09:30 ET (pre-open run).
- **Intraday-earnings check (standing rule):** GOOGL + TSLA reported AMC yesterday (gap today, no overnight risk); **INTC is AMC today**; off-list TMUS/LMT today. **No on-list name reports DURING market hours today** → **no earnings park.**
- Per-symbol P&L (14d closed): red **NVDA −$176.97 (1W3)**, **UNH −$139.23 (0W3)**, **ENPH −$124.80 (0W1)**, **TSLA −$119.38 (0W1)**, **AMD −$94.93 (1W3)**, ABNB −$91.26 (0W1), QQQ −$62.21, QCOM −$60.47 (0W2), CRM −$55.65, XOM −$49.78, NFLX −$42.00, SE −$41.65, **AMZN −$39.60 (0W3)**, TSM −$35.11, MU −$25.53, AVGO −$24.18, GOOGL −$0.78. Green **MSFT +$78.39**, **BAC +$73.15 (3W3)**, **META +$39.40**, AAPL +$35.95, INTC +$26.91, GOOG +$14.90, SPY +$14.68, WMT +$11.76, COST +$9.06 — the quality names still produce; the leak is uniform above-VWAP entry-quality, not name-specific. **No chronic-loser park trigger matured:** every red name is the standing above-VWAP open-fade regime (the ★★ VWAP-gate target), all liquid large-caps that fit the breakout strategy; none sub-$5/illiquid/halt-prone.
- **GOOGL (+3%) & TSLA (−6%)** — post-earnings wide intraday ranges expected today; both liquid mega-caps, EOD-flatten → **HOLD** (extra intraday caution, no overnight risk). **ENPH** (07-22 −$124.80 full-1R STOP) — solar large-cap, single above-VWAP fade, no name defect → **HOLD**, watch for a repeat. **Semis (NVDA/MU/TSM/AVGO/AMD/INTC/QCOM)** — AI-capex regime move, not name-quality → **HOLD all.** No halt/binary on any on-list name during market hours today.
- **Adds: none** — a risk-off tape (megacap tech leading futures lower on AI-capex ROI fears, oil ~$90 on the Iran flare-up) into GOOGL/TSLA gap reactions, at a **−23.4% drawdown with only ~$164 of cushion.** Semi/megacap leadership already fully on-list; financials/energy rotation covered by BAC/XOM. No high-conviction trending large-cap is absent → chasing into an event-heavy, oil-shocked tape at the thinnest cushion yet is exactly the wrong risk.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: no on-list name reports during market hours today (GOOGL/TSLA AMC yesterday, INTC AMC today); NVDA/UNH/ENPH/AMD/QCOM/AMZN are the above-VWAP open-fade regime — the ★★ VWAP-gate strategy lever (IMP-020, todo.md, human sign-off), **not** name defects; semis are a global AI-capex regime move, not name-quality. 0 positions open (nothing locked). No adds — leaders/rotation already covered, and a ~$164 cushion argues against chasing a risk-off tape into GOOGL/TSLA gap reactions. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked).

### Notes for pre-market research (next session — Fri 07-24)
- **⚠️ INTC reported AMC today (07-23) → gaps Fri 07-24** — treat intraday with extra caution (wide post-earnings ranges; no overnight risk for an EOD-flatten bot); INTC has been the recent standout (07-21 +3.70%). GOOGL/TSLA gap reactions (07-22 AMC) largely digest today. Re-scan the intraday-earnings calendar (Mag-7 ramp: MSFT/META/AAPL/AMZN late July) and park any on-list name that shifts to *during* market hours.
- **Chronic watches (NVDA 1W3 / UNH 0W3 / AMZN 0W3 / AMD 1W3 / QCOM 0W2 / ENPH)** — all above-VWAP open-fade regime, all top-liquidity large-caps, no name-specific defect. A fresh full-1R fade matures a park *discussion* only; the real lever is the ★★ VWAP entry-quality gate (IMP-020, human sign-off), NOT curation.
- **★★ The real fix is still blocked on human sign-off** — re-escalate IMP-020 (skip fills >+0.25% above session VWAP; validated −$610 → +$78.49 in replay). Watchlist churn cannot fix a strategy-wide entry-quality leak.
- **⚠️ Cushion is at its thinnest yet: equity $7,664.14 (−23.4%), only ~$164 above the −25% ($7,500) strategy-review flag.** One more −$165 day breaches it. Protect aggressively; do not add names into the ongoing AI-capex-scrutiny / oil-~$90 risk-off tape.

---

## 2026-07-24 — Pre-market Research

### Market context
**Modest stabilization bounce after Thursday's Big-Tech rout.** Thu 07-23 was an AI-capex bloodbath: **S&P 500 −1.21% (7,408.30), Nasdaq Composite −2.15% (25,137.69), Dow −0.97%** — the Mag-7 shed ~$800B, **GOOGL −7% / TSLA −14%** on their earnings (both posted **negative Q2 free cash flow** amid ballooning AI spend). Fri 07-24 futures point **modestly higher: S&P +0.11%** (Polymarket implied ~66% odds of an up-open) — a stabilization attempt, not a trend. Overhangs: **new Trump Section 301 tariffs (10–12.5%) took effect overnight**; **10Y yield briefly >4.7%** → rising rate-hike odds (hawkish); **Brent eased −2% to <$99** after briefly topping $100 on Red Sea tanker attacks. Today's data: **S&P Global flash PMIs (services/mfg) + new home sales**. Earnings BMO: **AXP, VZ, NEE, CHTR, SLB, HCA, THC** — **all off-list; NO on-list name reports DURING market hours today** → no intraday earnings park. INTC (07-23 AMC) gaps today, already digesting by the open.

### Carried from daily review (2026-07-23)
- **07-23 booked −$70.18 (0W/5L)** → equity close **$7,593.96** (−24.06% YTD). All 5 faded from entry (2 STOP, 3 EOD_FLATTEN); **4 of 5 fills were >+0.25% above session VWAP** — the ★★ VWAP entry-quality gate (IMP-019/020) would have skipped all four faders and avoided −$69.85 of the −$70.18 day. **Strongest single-day evidence yet, but the gate is an entry-logic change AWAITING HUMAN SIGN-OFF — not shippable here, not fixable by curation.**
- **Per-name reads all "not a name defect":** XOM (biggest loss, chased breakout +0.60% above VWAP; energy strength real), MU (traded twice, re-entries into a fading tape, ~$1000/sh so tiny qty), NFLX (regime), BAC (late 15:27 entry — entry-timing backlog). All liquid, all HOLD.
- **⚠️ Cushion at its thinnest yet — $93.96 above the −25% ($7,500) flag.** Protect aggressively; do not add.
- **Traceability flag (not acted on):** IMP-021/022 offline tooling (analytics.py, replay.py, scripts/replay.py, tests/test_replay.py) sit uncommitted in the tree — left untouched per ground rules (code changes belong to the daily-review routine).

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **ACTIVE**, equity **$7,593.87** (last_equity $7,593.87 = flat, no trades since 07-23 close), cash $7,593.87, buying power $30,375. **−24.06% from $10K, only $93.87 above the −25% ($7,500) strategy-review flag — thinnest cushion yet.** Clock `is_open=false`, next open 07-24 09:30 ET (pre-open run).
- **Intraday-earnings check (standing rule):** GOOGL/TSLA earnings ALREADY resolved (dropped Thu 07-23); INTC (07-23 AMC) gaps today. Today's BMO reporters (AXP/VZ/NEE/CHTR/SLB/HCA/THC) are **all off-list**. **No on-list name reports during market hours today → no earnings park.** No halt/binary on any on-list name.
- Per-symbol P&L (14d closed): red **NVDA −$176.97 (1W3)**, **UNH −$139.23 (0W3)**, **ENPH −$124.80 (0W1)**, **AMD −$94.93 (1W3)**, **ABNB −$91.26 (0W1)**, XOM −$80.02 (0W2), QQQ −$77.08 (1W2), QCOM −$60.47 (0W2), NFLX −$57.48 (0W2), CRM −$55.65 (0W1), **MU −$44.66 (0W4)**, SE −$41.65, **AMZN −$39.60 (0W3)**, AVGO −$24.18, GOOGL −$0.78. Green **MSFT +$78.39**, **BAC +$67.82 (3W4)**, **META +$39.40**, AAPL +$32.18, INTC +$26.91, GOOG +$14.90, WMT +$11.76, COST +$9.06, SPY +$5.59. **The quality names still produce; the red is uniform above-VWAP open-fade regime, not name-specific.** Zero-signal check: **no on-list name has never signaled** (empty) — no structural-mismatch park candidate (WPM already parked for that reason).
- **No chronic-loser park trigger matured.** Every red name (NVDA/UNH/ENPH/AMD/ABNB/MU/AMZN) is the standing above-VWAP open-fade regime — the ★★ VWAP-gate target (IMP-020, human sign-off), all liquid large-caps that fit the breakout strategy; none sub-$5/illiquid/halt-prone. MU 0W4 (14d) is the same regime + re-entry-into-fade pattern the 07-23 review documented (~$1000/sh → tiny $ risk), not a name defect; held per the deliberate 06-25 re-enable (AI-memory day-driver).
- **GOOGL/TSLA post-earnings day-2** — wide intraday ranges likely persist; both liquid mega-caps, EOD-flatten (no overnight risk) → **HOLD** (extra intraday caution: favor at/below-VWAP drift-ups, avoid chasing breakouts stretched above VWAP into the heavy tape, per 07-23 review).
- **Adds: none** — a stabilization bounce (not a confirmed trend) into fresh tariffs + rising yields (10Y >4.7%) + AI-capex ROI scrutiny, at a **−24.06% drawdown with only $93.87 of cushion.** Leaders/rotation already fully on-list (semis, megacaps, financials via BAC, energy via XOM). Chasing into a fragile bounce at the thinnest cushion yet is exactly the wrong risk.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: no on-list name reports during market hours today; every red name is the above-VWAP open-fade regime (the ★★ VWAP-gate strategy lever, IMP-020 / todo.md / human sign-off), **not** a name defect; no structural mismatch (no zero-signal names). 0 positions open (nothing locked). No adds — thinnest-ever cushion argues against chasing a fragile bounce into tariffs/rate-hike overhang. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked; service already active since the 07:00 UTC nightly cycle).

### Notes for pre-market research (next session — Mon 07-27)
- **Mag-7 earnings ramp late July** — MSFT/META/AAPL/AMZN report over the coming sessions. Re-scan the intraday-earnings calendar each morning and park any on-list name that shifts to reporting *during* market hours (WisBot flattens by 15:55 ET, so AMC/BMO gaps carry no overnight risk — only *during-hours* reports warrant a park).
- **Chronic watches (NVDA 1W3 / UNH 0W3 / ENPH 0W1 / AMD 1W3 / ABNB 0W1 / MU 0W4 / AMZN 0W3)** — all above-VWAP open-fade regime, all top-liquidity large-caps, no name-specific defect. A fresh full-1R fade matures a park *discussion* only; the real lever is the ★★ VWAP entry-quality gate (IMP-020, human sign-off), NOT curation.
- **★★ The real fix is still blocked on human sign-off** — re-escalate IMP-020 (skip fills >+0.25% above session VWAP; 07-23 was its strongest single-day evidence yet — would have turned −$70.18 into −$0.33). Watchlist churn cannot fix a strategy-wide entry-quality leak.
- **⚠️ Cushion at its thinnest ever: equity $7,593.87 (−24.06%), only $93.87 above the −25% ($7,500) strategy-review flag.** One more ~$100 day breaches it → strategy review triggers. Protect aggressively; do NOT add names into the tariff/rate-hike/AI-capex-scrutiny tape.

---

## 2026-07-27 — Pre-market Research

### Market context
**Risk-on bounce extends into the busiest week of the quarter.** Weekend US–Iran ceasefire/peace-talk hopes sank oil ~7% (Brent <$88, WTI ~$85), and futures rallied hard: **S&P 500 +0.79%, Nasdaq-100 +1.34%, Dow +0.67%, Russell 2000 +1.16%**, tech-led, VIX lower. Fri 07-24 had closed mixed/stabilizing (S&P 7,411.98 +0.05%, Nasdaq Comp −0.64%) after Thu's AI-capex rout (GOOGL −7% / TSLA −14%). **This is the continuation of the Fri firming bounce, not a confirmed trend** — the AI-capex ROI scrutiny that sank Alphabet/Tesla still overhangs the hyperscalers reporting this week. **Big week: 4 Mag-7 report + FOMC + Core PCE.** Today's data: **June durable-goods orders**; today's earnings (NUE et al.) are **off-list**. 10Y still elevated; consensus is a Fed **hold Wed** with the first hike priced to September.
- **★ Intraday-earnings scan (the 07-24 carried action item):** MSFT + META **Wed 07-29 AMC**, AAPL + AMZN **Thu 07-30 AMC**, QCOM **Wed AMC**, XOM **Fri (BMO)**. **Every on-list reporter this week reports AMC/BMO — NONE during market hours.** WisBot flattens by 15:55 ET, so AMC/BMO gaps carry **no overnight risk** → **no earnings park is warranted.** No on-list name reports *during* market hours today or any day this week.

### Carried from daily review (2026-07-24)
- **07-24 booked +$87.13 (3W/0L)** → equity close **$7,681.00** (−23.19% YTD, recovered $87 off the low; now **$181 above the −25% ($7,500) flag**, up from the thinnest-ever $93.96). BAC/COST/NFLX all drifted up and captured green at the flatten on the firming tape — the mirror image of 07-23's faded-flatten losses (**same names/signals, opposite tape → regime, not name quality**).
- **Action item honored:** re-scan the Mag-7 intraday-earnings calendar and park any name that shifts to *during-hours* reporting — done above; all AMC/BMO → no park.
- **★★ VWAP gate (IMP-019/020) remains the real lever, still AWAITING HUMAN SIGN-OFF** — and 07-24 was a clean out-of-sample *counterexample* (2 of 3 winners were fills >+0.25% above VWAP the gate would have skipped, costing +$65.35). The gate is **tape-dependent** (helps heavy-tape faders, saws off green bounce-day winners), not an unconditional cure — one more reason curation cannot fix it.
- **Traceability flag (not acted on):** IMP-021/022 offline tooling (analytics.py, replay.py, scripts/replay.py, tests/test_replay.py) + backtest_result.json sit uncommitted in the tree — **left untouched/unstaged per ground rules** (code changes belong to the daily-review routine).

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **PA3ESJUO8RU0 ACTIVE**, equity **$7,680.97** (last_equity $7,680.97 = flat, no trades since 07-24 close), buying power $30,723.88, trading_blocked false. Clock `is_open=false` (pre-open run). **−23.19% from $10K, $181 above the −25% ($7,500) strategy-review flag.**
- **Intraday-earnings check (standing rule):** all 4 Mag-7 reporters (MSFT/META Wed AMC, AAPL/AMZN Thu AMC) + QCOM (Wed AMC) + XOM (Fri BMO) report AMC/BMO — **none during market hours** → **no earnings park.** No halt/binary on any on-list name today.
- Per-symbol P&L (14d closed, 44 trades, net **−$656.28**): red **UNH −$139.23 (0W3)**, **ENPH −$124.80 (0W1)**, **AMD −$94.93 (1W3)**, **ABNB −$91.26 (0W1)**, XOM −$80.02 (0W2), QQQ −$77.08 (1W2), QCOM −$60.47 (0W2), CRM −$55.65 (0W1), **NVDA −$47.04 (1W2)**, **MU −$44.66 (0W4)**, AMZN −$39.24 (0W2), NFLX −$25.08 (1W3), AVGO −$24.18 (1W3). Green **BAC +$86.44 (3W4)**, COST +$42.01 (2W2), META +$39.40, AAPL +$32.18, INTC +$26.91, GOOG +$14.90, WMT +$5.52. **The quality names still produce; the red is uniform above-VWAP open-fade regime, not name-specific** (BAC/COST/NFLX all *won* 07-24 on the firming tape after losing 07-23 — cleanest possible regime-vs-name proof). No on-list name has never signaled → no structural-mismatch park candidate.
- **No chronic-loser park trigger matured.** Every red name (UNH/ENPH/AMD/ABNB/QCOM/MU/AMZN/NVDA) is the standing above-VWAP open-fade regime — all liquid large-caps that fit the breakout strategy, none sub-$5/illiquid/halt-prone. MU 0W4 (14d) is the same regime + re-entry-into-fade pattern, ~$1000/sh → tiny $ risk; held per the deliberate 06-25 re-enable (AI-memory day-driver).
- **Adds: none** — a risk-on bounce (not a confirmed trend) into a Mag-7 earnings gauntlet + FOMC Wed + Core PCE, with AI-capex ROI scrutiny still overhanging, at a **−23.19% drawdown with $181 of cushion.** Leaders/rotation already fully on-list (semis, megacaps, financials via BAC, energy via XOM). Chasing into a fragile bounce ahead of binary macro is exactly the wrong risk.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: every on-list reporter this week is AMC/BMO (no during-hours earnings risk → no park); every red name is the above-VWAP open-fade regime (the ★★ VWAP-gate strategy lever, IMP-020 / todo.md / human sign-off), **not** a name defect; no structural mismatch (no zero-signal names). 0 positions open (nothing locked). No adds — thin cushion + FOMC/Mag-7 binary week argues against chasing a fragile bounce. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked; service already active since the 07-25 15:15 UTC restart).

### Notes for pre-market research (next session — Tue 07-28)
- **★ Re-scan the intraday-earnings calendar Wed/Thu:** MSFT + META report **Wed 07-29 AMC** (gap Thu), AAPL + AMZN **Thu 07-30 AMC** (gap Fri), QCOM **Wed AMC**, XOM **Fri BMO**. All AMC/BMO = **no overnight risk** for an EOD-flatten bot → **no park** — but expect wide post-earnings intraday ranges on those names the morning after. Only a *during-hours* report warrants a park.
- **FOMC decision Wed 07-29 + Core PCE this week** — consensus hold Wed (first hike priced to Sept); a hawkish surprise or hot PCE could whipsaw the tape. Do NOT add names into these binaries.
- **Chronic watches (UNH 0W3 / ENPH 0W1 / AMD 1W3 / ABNB 0W1 / QCOM 0W2 / MU 0W4 / AMZN 0W2)** — all above-VWAP open-fade regime, all top-liquidity large-caps, no name-specific defect. The real lever is the ★★ VWAP entry-quality gate (IMP-020, human sign-off), NOT curation.
- **Equity $7,680.97 (−23.19%), $181 above the −25% ($7,500) flag** — cushion improved off the low but still thin. Protect; the bounce is risk-on but unconfirmed into a Mag-7 + Fed + PCE week.

---

## 2026-07-28 — Pre-market Research

### Market context
**The risk-on bounce reversed overnight — a semiconductor/AI sell-off deepened.** Futures split hard: **Nasdaq-100 −1.2%, S&P 500 −0.2%, Dow +0.6%** (+310pts on KO/SHW earnings). A **~10% crash in Korea's Kospi** (SK Hynix −14%, Samsung −13%) on AI circular-financing fears — reports of **NVDA exploring a $250B funding backstop for OpenAI** — dragged chips worldwide: premarket **NVDA −5%, AMD −5.2%, MU −2.3%**, SanDisk −11%. Oil retreated (WTI ~$85, still +~20% for July → hot headline inflation), 10Y eased to **4.61%**. Mon 07-27 closed mixed (S&P 7,413.18 +0.02%, Nasdaq Comp 24,932.08 −0.18%, Dow +0.51%). **The AI-capex ROI scrutiny that sank GOOGL/TSLA last week is now the dominant tape driver into the mega-cap prints.**
- **★ FOMC two-day meeting BEGINS today (Tue 07-28); decision Wed 07-29 2pm ET** — hold priced ~68.5% (FedWatch); the Fed sees no July inflation data before deciding. Today's data: **June durable-goods orders**.
- **★ Intraday-earnings scan (standing rule):** today's notable reporters — KO, UPS, BA, RCL, ECL, HLT (BMO), PYPL (AMC) — are **all off-list**. On-list reporters this week: MSFT + META **Wed 07-29 AMC**, QCOM **Wed AMC**, AAPL + AMZN **Thu 07-30 AMC** (HSBC upgraded AAPL to Buy, $366 PT), XOM **Fri BMO**. **NONE report during market hours today or any day this week** → WisBot flattens by 15:55 ET, AMC/BMO gaps carry **no overnight risk** → **no earnings park warranted.**

### Carried from daily review (2026-07-27)
- **07-27 booked −$72.52 (2W/3L)** → equity close **$7,608.45** (−23.92% YTD; cushion thinned to **$108 above the −25% ($7,500) flag**, from $181). First live session under IMP-021 (breakout veto) + IMP-022 (VWAP gate): **both gates fired exactly as designed** — 0 breakout entries to veto, all 5 fills at/below VWAP (nothing to skip), books reconcile to the penny, ~28th straight no-overnight session.
- The loss was **2 residual at/below-VWAP MA-faders** (QCOM −$39.66, META −$37.92) on the choppy tech-off tape — the leak *neither* new gate targets; **regime, not name.** Every per-trade discriminator (confidence, momentum, extension, time-of-day, VWAP-distance, index-regime) stays refuted. Daily review's explicit instruction: **do NOT layer a third entry change; accrue post-IMP-021/022 sessions.** Curation cannot fix this.
- Named notes: QCOM/META (Wed AMC, wide Thu range) — keep, name defect refuted; AAPL (Thu AMC), NFLX, COST — keep. **"Do NOT chase into the binaries this week."**
- **Traceability flag (not acted on):** IMP-021/022 offline tooling (analytics.py, replay.py, scripts/replay.py, tests/test_replay.py) + backtest/gate-monitor JSON sit uncommitted in the tree — **left untouched/unstaged per ground rules** (code changes belong to the daily-review routine).

### Watchlist review
- **Positions: 0 open — nothing locked.** Account **PA3ESJUO8RU0 ACTIVE**, equity **$7,608.42** (last_equity $7,608.42 = flat, no trades since 07-27 close; ≈ DB close $7,608.45), trading not blocked. **−23.92% from $10K, only $108 above the −25% ($7,500) strategy-review flag.**
- **Intraday-earnings check:** no on-list name reports during market hours today (all Mag-7 + QCOM AMC Wed/Thu, XOM Fri BMO); no halt/binary on any on-list name today → **no park.**
- Per-symbol P&L (14d closed, 42 trades, net ≈ **−$685**): red **ENPH −$124.80 (0W1)**, **QCOM −$100.13 (0W3)**, **UNH −$99.90 (0W2)**, **AMD −$94.53 (1W2)**, ABNB −$91.26 (0W1), QQQ −$77.08 (1W2), CRM −$55.65 (0W1), NVDA −$47.04 (1W2), **MU −$44.66 (0W4)**, AMZN −$39.24 (0W2), XOM −$30.24 (0W1), AVGO −$24.18 (1W3), NFLX −$21.05 (2W4). Green **BAC +$34.97 (2W3)**, COST +$34.17 (2W2), AAPL +$31.99 (1W3), INTC +$26.91 (1W2), WMT +$5.52 (1W1), META +$1.48 (1W3). **Quality names still produce; the red is uniform above/at-VWAP open-fade regime, not name-specific** — the 07-24 vs 07-23 same-name flip (BAC/COST/NFLX won on the firming tape, lost on the heavy one) is the cleanest regime-vs-name proof. No zero-signal / structural-mismatch name → no such park candidate.
- **No chronic-loser park trigger matured.** Every red name (ENPH/QCOM/UNH/AMD/ABNB/MU/AMZN/NVDA) is the standing above/at-VWAP open-fade regime — all liquid large-caps that fit the breakout strategy, none sub-$5/illiquid/halt-prone. The chip cluster (NVDA/AMD/MU/AVGO/TSM/QCOM/INTC) is down hard premarket, but that is a **one-session AI-financing sell-off = regime**, not a name defect; IMP-021/022 + the EOD flatten + no-overnight invariant are exactly the guards for a heavy tape. Parking liquid chip leaders on a single red-tape day would be churn and violates the park-only-on-disqualifying-catalyst rule. MU 0W4 = same regime + tiny $ risk (~$1000/sh, qty≈1); held per the deliberate 06-25 re-enable.
- **Adds: none** — into a deepening chip/AI sell-off + FOMC (decision Wed) + 4 Mag-7 prints + Core PCE, at a **−23.92% drawdown with only $108 of cushion.** All leaders/rotation already on-list (semis, megacaps, financials via BAC, energy via XOM, staples via COST/WMT). Chasing a name into a risk-off binary week is the wrong risk — matches every prior review's discipline.

### Changes applied to watchlist
**No changes.** 26 active retained. No park trigger matured: no on-list name reports during market hours today (all AMC/BMO → no overnight risk → no park); every red name is the above/at-VWAP open-fade regime (the ★★ VWAP-gate + residual-MA-fader strategy questions, todo.md), **not** a name defect; no structural mismatch (no zero-signal names); the chip weakness is a one-day regime sell-off, not a name park trigger. 0 positions open (nothing locked). No adds — thin cushion + chip sell-off + FOMC/Mag-7 binary week argues decisively against chasing. Conservative hold is the correct call — no churn.

### Final watchlist
26 active (unchanged): AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, JPM, WPM.)
Service restarted: **no** (no watchlist changes; 0 open positions — nothing locked; service already active since the 07-25 15:15 UTC restart).

### Notes for pre-market research (next session — Wed 07-29)
- **★ FOMC decision today Wed 07-29 2pm ET** (hold priced ~68.5%) + **MSFT + META + QCOM report AMC** → all three gap Thu with wide post-earnings ranges (no overnight risk for an EOD-flatten bot; only a *during-hours* report warrants a park — none this week). A hawkish Fed surprise or the ongoing AI-capex/chip sell-off could whipsaw the tape. **Do NOT add names into these binaries.**
- **Chip/AI-financing sell-off is the live regime risk** (NVDA/AMD/MU/AVGO/TSM/QCOM/INTC all down 2–5% premarket Tue on the SK Hynix/Samsung −13/14% Kospi crash + NVDA-OpenAI $250B backstop reports). Expect heavy-tape MA-faders; IMP-021/022 gates + EOD flatten are the designed guards — curation is not the lever.
- **Chronic watches (ENPH/QCOM/UNH/AMD/ABNB/MU/AMZN/NVDA)** — all above/at-VWAP open-fade regime, top-liquidity large-caps, no name-specific defect. The open strategy questions (VWAP gate; the residual at/below-VWAP MA-fader) belong to the daily-review routine, NOT curation.
- **Equity $7,608.42 (−23.92%), only $108 above the −25% ($7,500) flag** — cushion thinned again; one ~$110 day trips the formal strategy review. Protect aggressively into FOMC + PCE + Mag-7.

---

## 2026-07-29 — Pre-market Research

### Market context
**FOMC decision day (2:00pm ET)** — ~70% odds of a hold at 3.50–3.75% (CME FedWatch), but a first-hike-in-3-years risk is live under Warsh. Futures steady/slightly higher pre-open: **S&P +0.2%, Nasdaq-100 +0.3%, Dow −0.2%** (P&G drag). **Chip complex weak** — SK Hynix Q2 profit +557% YoY but below Street, Samsung/Hynix dumped, KOSPI −6% on AI-slowdown fears — a headwind for the on-list semis. **Oil +3%** on renewed Iran/Mideast hostilities (missile attack on US forces) → XOM tailwind + risk-off overhang. Mag-7 gauntlet AMC: **MSFT** (est $4.24/$87.63B), **META** (est $7.18), plus **QCOM + ARM** after the bell. Movers Ford +4%, Bloom +11% (not on list).

### Carried from daily review (07-28)
- 07-28 was +$31.64 (2W/1L) under the IMP-021/022 gates; no defect, no code change. Its notes flagged MSFT/QCOM/META (Wed 07-29 AMC), AAPL (Thu 07-30 AMC) and a choppy/risk-off-for-tech tape into FOMC. Acted on the earnings calendar below.
- SE flagged for watch (session memory): all-time **2W/4L, −$50.52, dormant since 07-13** — modest, has wins, not a chronic 0W structural mismatch → held under watch, **not parked**.

### Watchlist review
- Positions: **0 open — nothing locked.** Account PA3ESJUO8RU0 ACTIVE, equity **$7,640.04** (−23.6% YTD, ~$140 above the −25%/$7,500 review flag). Clock is_open=false, pre-open.
- 14d closed P&L broadly red (worst ENPH −124.80, QCOM −100.13, UNH −99.90, AMD −94.53, ABNB −91.26; best AAPL +38.21, BAC +34.97, COST +34.17). This is the documented **regime** leak (choppy/tech-off tape), not name-quality — every per-name/per-trade discriminator refuted across prior reviews. Not park triggers; parking regime-losers would be churn.
- **Earnings binaries today (verified — Perplexity + WebSearch):** MSFT, META, QCOM all report **AMC today**. QCOM options imply a 9.34% move; Cantor cut PT to $200 (Hold). AAPL/AMZN report Thu 07-30 (no park today).
- No add candidate clears the bar into a FOMC + triple-earnings binary day with chip-sector weakness; nothing high-conviction that isn't already listed.

### Changes applied to watchlist
- **MSFT, META, QCOM: parked 2026-07-29** — each reports earnings AMC today, on FOMC decision day. One-day event parks to remove single-name whipsaw risk on their own event day and the naked-overnight-through-earnings-gap tail risk. Precedent-consistent (MU 06-24→06-25, NFLX 07-17). **Re-enable 07-30** after the binaries resolve.
- SE held under watch (2W/4L, dormant); no other parks; no adds (FOMC + earnings binary day, thin cushion).

### Final watchlist
23 active (reduced from 26 via three one-day event parks; within 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC MU NFLX NVDA QQQ SE SPY TSLA TSM UNH WMT XOM
Service restarted: **yes** — active & healthy (11:50:10 UTC, MainPID alive, 0 errors in journal).

### Notes for pre-market research (next session — Thu 07-30)
- **Re-enable MSFT, META, QCOM** first thing 07-30 once their AMC prints have landed (binaries resolved) — liquid mega-caps parked only for the event day.
- **AAPL + AMZN report Thu 07-30 AMC** → consider the same one-day event park for them tomorrow (both liquid, re-enable Fri) if the pattern holds; verify the calendar first.
- FOMC outcome (hold vs first hike) sets Thu's regime — a hawkish surprise re-heavies the tape; don't chase breakouts into it.
- Chip weakness (SK Hynix / AI-slowdown) + the oil spike (Iran) are the swing factors for the on-list semis (AVGO/NVDA/MU/TSM/INTC/AMD) and XOM.
- Equity $7,640.04 (−23.6% YTD), ~$140 above the −25% ($7,500) review flag — protect; thin cushion into the binaries.

---

## 2026-07-30 — Pre-market Research

### Market context
**Post-FOMC, Mag-7 gauntlet continues.** Yesterday (07-29) the Fed **held at 3.50–3.75% with 3 hawkish dissents** (preferred a 25bp hike) and the tape **closed sharply lower** on the AI/chip selloff. Overnight AMC prints drove the pre-open: **MSFT +8.3%** (Azure topped $100B revenue, beat top & bottom line — the standout), **META −9%** (rev beat / EPS miss, weak Q3 outlook, 91% FCF collapse), **QCOM −5%** and **ARM −7%** (Q3 beat but handset revenue slid, broad chip-sector weakness). AI-capex ROI scrutiny remains the dominant driver. **AAPL + AMZN both report AMC today** (AAPL Q3 est ~$1.89 EPS; AMZN Q2 est ~$1.82 EPS / ~$196B rev) → wide post-close ranges into Fri, but **no overnight risk for an EOD-flatten bot.**

### Carried from daily review (07-28) + last research note (07-29)
- 07-29's note instructed: **re-enable MSFT/META/QCOM** first thing today once their AMC prints landed (binaries now resolved ✓ verified via WebSearch), and **consider a one-day event park for AAPL/AMZN** (both confirmed reporting AMC today). Acted on both below.
- SE flagged for watch (all-time 2W/4L, −$50.52, dormant): modest, has wins, not a chronic 0W structural mismatch → **held under watch, not parked.**

### Watchlist review
- Positions: **0 open — nothing locked.** Account PA3ESJUO8RU0 **ACTIVE**, equity **$7,578.78** (last_equity flat = no trades yet today; 07-29 closed ~−$61 red). **−24.2% YTD, only ~$79 above the −25% ($7,500) strategy-review flag — thinnest cushion yet.** 0 open orders; broker reconciles flat.
- Per-symbol P&L (14d closed, **36 trades, net −$471.62**): red **ENPH −168.48 (0W2)**, **QCOM −100.13 (0W3)**, **UNH −99.90 (0W2)**, **AMD −94.53 (1W2)**, CRM −55.65 (0W1), **MU −44.66 (0W4)**, META −37.92 (0W1), XOM −30.24 (0W1), AAPL −24.17 (1W4). Green **BAC +34.97 (2W3)**, **COST +34.17 (2W2)**, **INTC +26.91 (1W2)**, **GOOG +25.90 (1W1)**, **NFLX +20.95 (2W3)**, QQQ +16.0, AVGO +13.14, GOOGL +12.5. **Quality names still produce; the red is the documented above/at-VWAP open-fade regime, not name-specific** — no zero-signal / structural-mismatch name, no chronic-loser park trigger matured.
- **Intraday-earnings check:** no on-list name reports *during* market hours today; AAPL/AMZN are AMC (handled via event park). No halt/binary on any on-list name intraday → no other park.
- **Adds: none** — into continued chip/AI weakness + two more Mag-7 AMC prints, at a −24.2% drawdown with only ~$79 of cushion. All leaders/rotation already listed; chasing a name into the binary tail is the wrong risk.

### Changes applied to watchlist
- **MSFT, META, QCOM: re-enabled 2026-07-30** — their 07-29 AMC earnings resolved (verified: MSFT beat/+8% premkt, META miss/−9%, QCOM beat/−5%); one-day event park from 07-29 lifted. All three re-verified **tradable & active on Alpaca** (`/v2/assets`).
- **AAPL, AMZN: parked 2026-07-30** — both report earnings AMC today; one-day event park to remove single-name pre-earnings whipsaw on their event day (precedent-consistent: MSFT/META/QCOM 07-29, NFLX 07-17, MU 06-24). **Re-enable 07-31** once the prints land.
- SE held under watch; no other parks; no adds.

### Final watchlist
**24 active** (net +1 vs 23: +3 re-enabled MSFT/META/QCOM, −2 parked AAPL/AMZN; within 30 cap):
ABNB AMD AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: AAPL, AMZN, BABA, BIRD, C, JPM, WPM.)
Service restarted: **yes** — active & healthy (11:49:16 UTC, MainPID alive, 0 errors in journal).

### Notes for pre-market research (next session — Fri 07-31)
- **Re-enable AAPL + AMZN** first thing once their 07-30 AMC prints have landed (event resolved) — both liquid mega-caps parked only for the event day.
- **Watch META (−9%) and QCOM (−5%) post-earnings behavior** — re-enabled today after gapping down hard on their prints; a gap-down that stabilizes can still produce clean intraday breakouts, but flag if they chop into repeated fades.
- Chip/AI-capex scrutiny + META's weak outlook keep the tech tape heavy; the post-FOMC hawkish-hold + AAPL/AMZN reactions set Friday's regime. Don't chase breakouts into a re-heavying tape.
- Equity **$7,578.78 (−24.2% YTD), only ~$79 above the −25% ($7,500) flag** — thinnest cushion yet; one ~$80 red day trips the formal strategy review. Protect aggressively.

---

## 2026-07-31 — Pre-market Research

### Market context
**Constructive, risk-on pre-open on cooler inflation.** June PCE landed benign — headline −0.1% m/m (3.7% YoY), core +0.1% m/m (3.3% YoY) — and Q2 GDP softened to 1.5% annualized (from 2.1%), reinforcing that inflation pressure is easing after the FOMC's 07-29 hawkish hold (3 dissents for a hike). Futures higher: **S&P +0.3%, Nasdaq-100 +0.5%**; in pre-market ETFs **SPY +0.56% ($745.85), QQQ +1.26% ($692.16)**. 10Y 4.65% / 2Y 4.24%. Mega-cap earnings drive the tape: **AMZN +9% AH** (Q2 net sales +20% to $200.6B, EPS $5.75, AWS +37% — fastest in 18 quarters), **AAPL −4% AH** (revenue beat / iPhone +22% but Cook flagged a demand-forecast shortfall). **XOM reports Q2 today BMO** (press release 5:30am CT, call 8:30am CT ≈ 9:30am ET; est ~$3.68–3.87 EPS) with oil elevated on Mideast/Suez risk. Month-end Friday.

### Carried from daily review (07-28) + last research note (07-30)
- 07-30's note instructed: **re-enable AAPL + AMZN** first thing today once their 07-30 AMC prints landed (both now resolved ✓ verified via Perplexity + WebSearch), and **watch META/QCOM** post-earnings behavior. Acted on both below.
- SE flagged for watch (all-time 2W/4L, dormant since 07-13): modest, has wins, not a chronic 0W structural mismatch → **held under watch, not parked.**

### Watchlist review
- Positions: **0 open — nothing locked.** Account PA3ESJUO8RU0 **ACTIVE**, equity **$7,641.60** (last_equity flat = no trades yet today; recovered ~+$63 vs 07-30's $7,578.78). **−24.0% YTD, ~$142 above the −25% ($7,500) review flag** — cushion slightly restored. 0 open orders; broker reconciles flat. Clock closed (pre-open).
- Per-symbol P&L (14d closed, **18 symbols, net −$353.13**, window-shifted improvement from −$471.62): red **ENPH −168.48 (0W2)**, **QCOM −100.13 (0W3)**, **UNH −99.90 (0W2)**, **AMD −94.53 (1W2)**, MU −44.66 (0W4), META −37.92 (0W1), XOM −30.24 (0W1), AAPL −24.17 (1W4). Green **INTC +82.63 (2W3)** (turned green on a good 07-30), **BAC +34.97 (2W3)**, **COST +34.17 (2W2)**, GOOG +25.90, NFLX +20.95, QQQ +16.0, AVGO +13.14, GOOGL +12.5, SPY +7.12. Quality names still produce; the red is the documented above/at-VWAP open-fade **regime**, not name-specific — no zero-signal / structural-mismatch name matured into a chronic-loser park trigger.
- **Intraday-earnings / event check (verified):** **XOM reports Q2 today BMO** — press release ~6:30am ET, conference call 8:30am CT = **9:30am ET, straddling the open** → elevated single-name whipsaw on its report day; also a red 14d name (0W1). No other on-list name reports intraday/AMC today; no halts/binaries on the rest.
- **Adds: none** — leaders/rotation already listed; at −24% drawdown with a still-thin cushion, chasing a new name on a month-end earnings-heavy day is the wrong risk. Constructive tape doesn't change curation.

### Changes applied to watchlist
- **AAPL, AMZN: re-enabled 2026-07-31** — their 07-30 AMC earnings resolved (AAPL −4% AH demand-forecast miss, AMZN +9% AH on AWS +37%); one-day event park from 07-30 lifted. Both re-verified **tradable & active on Alpaca** (`/v2/assets`).
- **XOM: parked 2026-07-31** — reports Q2 earnings today (BMO, call at ~the open); one-day event park to remove single-name earnings whipsaw on its report day, consistent with the protect-aggressively posture and its red 14d record. Re-enable **08-03** (Mon) once the print is digested.
- SE held under watch; no other parks; no adds.

### Final watchlist
**25 active** (net +1 vs 24: +2 re-enabled AAPL/AMZN, −1 parked XOM; within 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM ENPH GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT
(Parked: XOM, BABA, BIRD, C, JPM, WPM.)
Service restarted: **yes** — active & healthy (11:49:30 UTC, MainPID 3812438 alive, 0 restarts, exit status 0, 0 errors in journal).

### Notes for pre-market research (next session — Mon 08-03)
- **Re-enable XOM** first thing Monday once its 07-31 earnings are digested (liquid oil major parked only for its report day; oil catalyst still live on Mideast/Suez risk).
- **Watch META (−9%) and QCOM (−5%) post-earnings drift** — still re-enabled after gapping down; flag if they chop into repeated fades rather than producing clean breakouts. Also watch AMZN (+9% gap-up) and AAPL (−4% gap-down) reaction quality on their first post-print session.
- Cooler PCE + softer GDP eased the tape into month-end, but the FOMC hawkish-hold backdrop persists — a constructive open can still fade; the above/at-VWAP open-fade regime remains the documented leak (a curation-immune, code-side question for daily-review).
- Equity **$7,641.60 (−24.0% YTD), ~$142 above the −25% ($7,500) flag** — cushion slightly restored but still thin; protect. SE still dormant (last trade 07-13) — keep on watch.

---

## 2026-08-04 — Pre-market Research

### Market context
**Risk-on, earnings-led melt-up continues.** Futures higher pre-open: Nasdaq-100 **+1%**, Dow **+454pts (+0.8%)**, S&P 500 **+0.2%**, on blowout prints from **PLTR (+15% pre-mkt)** and **CAT (+9%)**; semis firm (MU +3%, MRVL +7%). This follows Monday 08-03's strong one-way trend-up session (SPY +1.10% → 757.72, QQQ +1.72% → 700.10, Dow closed at a record, **AMZN crossed $3T market cap**). Oil is two-way: WTI settled −5% Monday at $80.34 on Trump's Iran de-escalation signal, then rebounded **+2.3% to ~$82** today on supply-disruption worry (Brent $86.13). 10Y **4.69%**. Economic calendar during market hours: **June factory orders + international trade data (10:00 ET)** — second-tier, not a regime event. **August jobs report is Friday 08-07, 8:30 ET** (still the week's binary).
⚠️ **Perplexity `sonar` was wrong again** — its pre-market screen claimed META −3.40%, MSFT −2.28%, GOOGL −2.33% and a +10% AMAT/LRCX semis melt-up; no source corroborates and it is the *opposite* of Monday's actual tape (META +6.03%, MSFT +4.92%, GOOGL +4.90%). Second consecutive session sonar returned stale/mismatched data (cf. 08-03 daily review). Market read here is taken from **Alpaca bars + WebSearch (CNBC/Benzinga)**, not sonar. Alpaca's IEX feed carried **no pre-market prints** at 07:50 ET, so intraday gaps are unverified — treat the futures read as directional.

### Carried from daily review
Acted on the **2026-08-03** daily review's "Notes for pre-market research" (the 08-03 *pre-market* routine itself never ran — there is no 08-03 research-log entry, which is the third silent no-run flagged in the record):
- **"Do not park any of the 17 blocked names"** (AAPL AMD AVGO BAC GOOG GOOGL INTC META MSFT MU NVDA QCOM QQQ SE SPY TSLA TSM) — **honored.** Neither of today's parks comes from that set on blocked-day evidence: AMD is parked for a *confirmed earnings event today*, and ENPH was **not** in the blocked set at all.
- **"SE: watch, do not park yet"** — honored; SE held (+4.18% Monday, above both MAs).
- **"AMZN fine — timing not selection"** — held, no action.
- **"Expect the VWAP gate to veto most candidates again if the trend regime persists; that is expected behaviour, not a fault — do not react by widening risk"** — honored; no risk parameter touched, no add made to manufacture activity.
- **Overdue action from the 07-31 entry: "Re-enable XOM first thing Monday 08-03."** The 08-03 run never fired, so XOM sat parked an extra session. **Done today** — one day late, recorded rather than glossed.

### Watchlist review
**Account state:** equity **$7,707.63**, cash $7,707.63, **0 open positions, 0 open orders** → **no locked symbols**; every name was eligible for review. **$207.63 above** the −25% ($7,500) strategy-review flag. Post-gate scorecard (`gate_monitor --since 2026-07-27`, 6 sessions): **17 trades, 10W/7L (58.8%), net +$26.80, PF 1.17**; IMP-021 ✅ held; IMP-022 620 skipped attempts. Still 17 of the 40–60 trades the weekly set as the decidability bar.

- **Trade performance (14d closed, 33 trades, 18W/15L, net −$43.36):** red **ENPH −168.48 (0W2)**, UNH −59.88 (0W1), QCOM −59.81 (0W2), META −37.92, XOM −30.24, AAPL −24.03, MU −19.13, AMZN −5.09, MSFT −0.48. Green **INTC +104.75 (2W0)**, BAC +44.40 (3W1), NVDA +44.87, COST +34.17 (2W0), GOOG +25.90, SPY +23.99 (2W0), NFLX +20.95, AMD +20.79, QQQ +16.00, AVGO +13.38, GOOGL +12.50. **ENPH alone is ~4× the whole book's net loss.**
- **Dormancy check — no dead names.** The `signals` table only records *executed* signals, so it cannot distinguish "no candidate" from "gate-blocked". Scanning the bot's own rotated logs instead: **all 25 active symbols produced VWAP-blocked candidates in the post-gate era** (fewest: AMZN/COST/CRM/UNH/WMT at 1 session each). **No symbol qualifies for a zero-signal park** — this retires the standing dormancy suspicions on SE (2 blocked sessions), TSLA (3), TSM (2) and ABNB (3).
- **Intraday-earnings / event check (verified two sources):** **AMD reports Q2 TODAY after the close (08-04 AMC, call 5:00pm ET — company-confirmed 07-08, Wall Street Horizon "confirmed")**. No on-list name reports *during* market hours. **ABNB reports Thu 08-06 AMC** (company IR confirmed; one aggregator wrongly says 08-05 — trust 08-06) → park it on 08-06, not today. No halts, M&A, FDA or legal binaries on the rest.
- **Technicals (daily bars, through 08-03 close):** broken/below-both-MA names — **QCOM (−11.6% vs 20MA, −23.2% vs 50MA, 5d −10.8%)**, **ENPH (−20.9% vs 50MA)**, INTC (−18.9% vs 50MA but +$104.75 and the best recent earner), MU (−14.2% vs 50MA, ATR 10.7%, but $829/sh caps size at qty 1), TSLA (−17.2% vs 50MA yet the best all-time name, +$583.54 8W2L), AAPL (5d −9.95% post-print), META, TSM, WMT. Extended post-earnings gap-ups: **MSFT +21.3% vs 20MA (5d +25.3%)**, **AMZN +15.6% vs 20MA (5d +22.8%)** — these will draw VWAP vetoes, correctly.
- **Adds: none.** The tape's momentum is in semis (AMAT/LRCX/MRVL) — chasing a +7–10% pre-market semis move on the day AMD prints after the close is precisely the wrong risk with $207 of cushion. Coverage is already complete across mega-cap tech, semis, financials, staples, healthcare, index ETFs and (with XOM back) energy; there is no sector gap to fill. The weekly's standing order is analysis-only accrual — churning the sample composition mid-measurement would corrupt the 17→40 trade read.

### Changes applied to watchlist
- **XOM: re-enabled 2026-08-04** — its 07-31 Q2 print is digested; the park was always one-day and is **one session overdue** because the 08-03 routine did not run. Re-verified **tradable & active on Alpaca** (`/v2/assets`: tradable true, status active, NYSE). Technically the healthiest re-entry available: above both MAs (+3.8% / +5.9%), ATR 2.30%, $78.8M/day, and a live two-way oil catalyst.
- **AMD: parked 2026-08-04** — **reports Q2 today AMC (5:00pm ET call)**. One-day pre-print event park, consistent with the house rule applied to MSFT/META (07-29), AAPL/AMZN (07-30) and QCOM. The bot flattens at 15:55 so there is no overnight gap exposure, but AMD carries the **highest ATR on the list (8.51%)** and pre-print positioning whipsaw is a poor fit for a long-only intraday book with a thin cushion. **RE-ENABLE 2026-08-05.**
- **ENPH: parked 2026-08-04 (structural, not one-day)** — the clearest park trigger on the list. **Worst symbol all-time (2W6L, −$350.85)** *and* **worst of the last 14 days (0W2, −$168.48 — ~4× the entire book's net loss)**. It is also the one genuine **liquidity outlier**: **$7.2M average daily dollar volume, 3× thinner than the next-thinnest name** (ABNB $21.4M) and ~150× thinner than SPY, against a strategy that explicitly requires liquid large caps. Chart is broken (−20.9% below its 50MA at $39.35, ATR 6.09%) and it carries solar policy/tariff headline risk. Not one of the 08-03 blocked names, so this decision is independent of that day's evidence. Revisit only if liquidity **and** trend both repair.
- QCOM held **under explicit watch** — its chart is now the most broken on the list (−23.2% vs 50MA, 5d −10.8%, 0W2 for −$59.81, all-time 1W5L −$134.97). It was *not* parked today because the 08-03 review named it among the **best** blocked candidates (+0.63%) and instructed against parking that set on one day's evidence. It is the **#1 park candidate** if it produces another full-1R fade.
- ABNB held (0W4L all-time −$186.30, 2nd-thinnest at $21.4M/day) — stale record, still generating candidates, chart above both MAs. **Park it 08-06 for its AMC print.**

### Final watchlist
**24 active** (net −1 vs 25: +1 XOM re-enabled, −2 parked AMD/ENPH; within the 30 cap):
AAPL ABNB AMZN AVGO BAC COST CRM GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: AMD, ENPH, BABA, BIRD, C, JPM, WPM.)
Service restarted: **yes** — active & healthy (11:52:56 UTC, MainPID 87451, NRestarts=0, clean `USTradeWisBot starting (dry_run=False)`, **0 errors/tracebacks** since boot, correctly sleeping until the 09:30 ET open).

### Notes for pre-market research (next session — Wed 08-05)
- **RE-ENABLE AMD** once tonight's Q2 print is digested — it is a one-day event park only, and AMD is a liquid mega-cap semi that was net **+$20.79** over the last 14d. Check the after-hours reaction first; if it gaps hard, it still re-enters (gap-downs that stabilise are fine for this strategy) but note the direction.
- **PARK ABNB on Thu 08-06** — confirmed Q2 AMC that day (company IR; ignore the aggregator's 08-05). Set the reminder now so it is not missed the way XOM's 08-03 re-enable was.
- **QCOM is the standing #1 park candidate** — −23.2% below its 50MA and −10.8% over 5 sessions. Park on the next full-1R fade; do not park pre-emptively on a gate-blocked day.
- **ENPH is now parked on structural grounds** (liquidity + chronic loss), not on an event — do **not** re-enable it on a single green solar day. It needs both a liquidity repair and a trend repair.
- **The pre-market routine did not run on 08-03** — third silent no-run in the record (after 07-14 pre-market and 07-29 daily review). Consequence was real but small: XOM traded a day short. Worth a reliability check on the cron/routine wiring; a routine that fails silently is the same class of defect IMP-024 fixed for `gate_monitor`.
- **Sonar is now 2-for-2 unreliable** (08-03 stale close, 08-04 inverted pre-market movers). Keep leading with it for speed, but **verify every trade-critical claim against Alpaca bars + WebSearch before acting** — no park or add should ever rest on it alone.
- **Regime expectation:** another trend-up open would again put most names above VWAP and draw heavy IMP-022 vetoes (172 attempts / 17 symbols on 08-03, where the replay showed the gate **COST** money). That is a *code-side, regime-aware-gate* question for the daily review, **not** a watchlist action — do not react by widening risk or adding names to force activity. Equity **$7,707.63 (−22.9% YTD), $207.63 above** the −25% ($7,500) flag; thinnest-ever remains $78.78 (07-29). **Protect it.**
- Watch **Friday 08-07's August jobs report (8:30 ET)** — the week's one binary; verify the time each morning.

---

## 2026-08-06 — Pre-market Research

### Market context
**Mixed open with tech on the back foot.** S&P 500 futures **7,764.50 (+0.19%)**, Dow futures **+135 (+0.25%)**, but **Nasdaq-100 futures −116 (−0.39%)** and Russell +0.12%; VIX **15.94 (+0.82%)**, SPY +0.22% / QQQ −0.3% pre-market, XLK −0.5%. The divergence is a **global AI/semi selloff overnight** — KOSPI −4% with Samsung and SK Hynix down ~8% — running against continued Iran/Hormuz de-escalation optimism (Bessent: "we are in talks with the Iranians"); crude ~$75.83 (+0.81%), i.e. **oil has given back the 08-04 spike**. This follows Monday 08-03's record closes (S&P above 7,700, Dow +907) and Wednesday 08-05's clean trend-down session (SPY −0.79%, QQQ −1.27%, both closing on their lows).
**Economic calendar:** Challenger job cuts, Q2 preliminary nonfarm productivity (exp +0.7%), **initial jobless claims 8:30 ET (cons. 203K vs prev 197K)**, continuing claims, June final wholesale inventories — all **pre-open or second-tier, none is a regime event**. **Friday 08-07's July jobs report (8:30 ET) is verified and remains the week's one binary** (ADP already showed July private hiring below forecast, which makes today's claims a live pre-check).
**Earnings:** heavy day, but **no watchlist name reports during market hours**. Before the open: MAR, TSN, CNH, L. After the close: EBAY, ETSY, EXPE, DASH, MELI, MET, HUBS, AXON, APP, OXY, MSI, WDC, XYZ, ZG — plus **ABNB** (see below).
⚠️ **Perplexity `sonar` unreliable for a third consecutive session.** It returned "no sourced overnight catalyst" for 23 of 25 tickers, could not produce futures direction, could not confirm the ABNB earnings date, and could not identify the GOOGL catalyst — all four of which WebSearch resolved in one pass. Its only substantive claims (NVDA up on SpaceX AI-chip spend; AAPL pre-market strength) are unverified and nothing here rests on them. Running record: 08-03 stale, 08-04 inverted movers, **08-06 empty**. Market read below is from **Alpaca bars + WebSearch (CNBC/Benzinga/company IR)**.

### Carried from daily review
Acted on the **2026-08-05** daily review's "Notes for pre-market research". Note first that **the 08-05 pre-market routine itself did not run** — there is no 08-05 research-log entry, which is the **fourth silent no-run** in the record (07-14 pre-market, 07-29 daily review, 08-03 pre-market, 08-04 daily review rc=127, and now 08-05 pre-market). The consequence was again real but small: AMD sat parked one session longer than planned, exactly the way XOM did on 08-03.
- **"RE-ENABLE AMD once tonight's Q2 print is digested"** (from the 08-04 entry, due 08-05) — **done today, one day late.** Reaction checked first as instructed: AMD **beat** (revenue $11.5B **+50% YoY**, record; data center $6.7B +107%; non-GAAP EPS $1.66 vs $1.61; Q3 guide ~$13B, **2.9% above** consensus) yet **fell ~7–9%** to $481.41 on valuation compression (53× forward vs NVDA ~20×), not on results. Per the standing rule a gap-down that stabilises still re-enters, and the direction is recorded here.
- **"PARK ABNB on Thu 08-06"** — **done.** Reminder set on 08-04 was honoured, and the date was **re-verified against company IR** (announced 07-09: Q2 results after the close **08-06**, call 2:00pm PT / **5:00pm ET**), which also settles the aggregator conflict flagged on 08-04. This is the first event park in the record that was scheduled two sessions ahead and executed on time.
- **"GOOGL — establish whether 08-05's −5.39% was news-driven before GOOGL is traded again"** — **done, and it was.** Catalyst identified: a **sweeping Google/DeepMind AI leadership exodus** announced 08-05 — **Jeff Dean departing** to found Discovery Loop (with Oriol Vinyals, Quoc Le and Sanjay Ghemawat reportedly joining as co-founders), and **Demis Hassabis stepping back** from day-to-day management to become DeepMind chairman. Shares fell >5% intraday, recovering to close −3.53% (GOOG −3.59%). Explicitly **not** earnings-driven — Q2 revenue was $119.8B (+24.2%), Cloud +82%, EPS $9.11 vs $3.04 consensus, an 11th straight beat. See the verdict below.
- **"SE is now a genuine park candidate"** — **NOT actioned; the premise is factually wrong** (see below). This is a correction to the record, not a deferral.
- **"INTC — worth asking whether it is a structural mismatch"** — noted, **no watchlist action**. INTC is a *code-side* question about `VWAP_MAX_DIST_PCT` on gap-and-go names, and it is the **best earner on the list** (+$104.75 over 14d, 2W0L). Parking the top performer over a gate-interaction question would be backwards.
- **"NFLX — watch"** and **"WMT behaved as designed"** — both held, no action.

### Watchlist review
**Account state:** equity **$7,640.90**, cash $7,640.90, **0 open positions, 0 open orders** → **no locked symbols**; every name was eligible for review. Cushion is **$140.90 above** the −25% ($7,500) strategy-review flag — **thinnest since the 07-29 low of $78.78**, after 08-05's −$95.95. Equity is down $66.73 from the 08-04 reading of $7,707.63.

- **Trade performance (closed since 07-21, 41 trades, 21W/20L, net −$109.83):** red **ENPH −168.48** *(already parked 08-04)*, META −78.99 (0W2), UNH −59.88 (0W1), QCOM −59.81 (0W2), XOM −30.24, AAPL −24.03, MU −19.13, GOOGL −18.63, QQQ −7.35, AMZN −5.09, SE −4.56, MSFT −0.48, WMT −0.40. Green **INTC +104.75 (2W0)**, BAC +57.93 (5t, 4W), NVDA +55.58, COST +34.17, NFLX +30.75 (4t, 3W), GOOG +25.90, SPY +23.99, AMD +20.79, AVGO +13.38.
- **✅ Correction to the 08-05 daily review — SE is not a dormant name and is not parked.** That entry stated SE "has been flagged blocked-only since 07-31 and has **still never produced a filled trade**", concluding it "consumes gate cycles and has contributed nothing". The `trades` table refutes both halves: SE **filled on 08-04** (09:38 → 10:21, STOP, −$4.56) and has **7 closed trades all-time**, including **two TAKE_PROFITs — +$228.54 (07-09) and +$60.30 (07-01)**. The +$228.54 is the **largest single winning trade in the recent book**. SE's all-time −$55.08 over 7 trades is *better* than eleven active names. Its chart is also among the strongest on the list (**+6.9% vs 20MA, +17.0% vs 50MA**, ATR 3.42%). The only genuine mark against it is liquidity ($25.0M/day, second-thinnest) — real, but not disqualifying on its own and not what the park was proposed on. **SE held.** Standing note: the blocked-attempt counter measures *gate cycles*, not dormancy — always confirm a dormancy claim against `trades` before parking on it.
- **Intraday-earnings / event check (verified against company IR):** **ABNB reports Q2 TODAY after the close** (5:00pm ET call) — the only on-list event. **No on-list name reports during market hours.** No halts, M&A, FDA or legal binaries elsewhere on the list.
- **Technicals (daily bars through 08-05 close):** broken/below-both-MA names — **QCOM (−6.8% vs 20MA, −19.2% vs 50MA)**, **TSLA (−8.6% / −16.5%)**, **META (−4.8% / −2.0%)**, **AMD (−5.6% / −6.5%, post-print)**; INTC (−9.3% vs 50MA but **+23.4% over 5d** and the top earner), MU (−8.1% vs 50MA, ATR 9.47%, $893/sh caps size at qty 1), AAPL (−3.9% vs 20MA, 5d −8.07%), NFLX/TSM/WMT/COST marginally below their 50MAs. Extended gap-ups still drawing correct VWAP vetoes: **MSFT +18.2% vs 20MA (5d +24.7%)**, AMZN +9.5% (5d +20.2%), CRM +10.8%. Liquidity is healthy across the board now that ENPH is gone — thinnest actives are **ABNB $22.3M** *(parked today)* and **SE $25.0M**; everything else is ≥$64M/day.
- **QCOM held under explicit watch, second session running.** It remains the most broken chart on the list (−19.2% vs 50MA, all-time 1W5L −$134.97) and the standing **#1 park candidate**, but the 08-04 trigger was *"park on the next full-1R fade"* and **QCOM has not traded since 07-27** — there is no new fade to act on, and its 50MA gap actually **narrowed from −23.2% to −19.2%**. Parking it today would be parking on an old datapoint. The trigger stands.
- **GOOGL held, with the catalyst now on the record.** The 08-05 drop was a **structural sentiment event, not a one-off**: talent exodus stacked on a negative-$5.86B Q2 free cash flow, long-term debt $46.5B → $98.2B, a suspended buyback, $180–190B FY26 capex, and the DOJ search-remedy overhang. But the overhang is *directional*, and this bot is flat every night; GOOGL is still **above both MAs (+3.9% / +1.3%)**, is the **third-most liquid name on the list ($377M/day)**, and its 14d record (−$18.63, 1W2) is unremarkable. Its all-time −$326.85 sits almost entirely in the pre-gate era against **GOOG's +$30.89 on the same underlying** — that spread is noise, not a name property, and parking one twin on it would be data-mining. Both held; the PHASE-002 equivalence guard already prevents simultaneous holds. **Watch GOOGL's 50MA at ~$358.43** (it closed $362.38, ~1.1% above).
- **Adds: none.** The weekly 2026-08-01's standing order is **analysis-only accrual until the post-gate book reaches 40–60 trades** (now **25**), and changing the sample composition mid-measurement would corrupt exactly the read the whole incubation is waiting on. On top of that: the cushion is $140.90, the thinnest since 07-29; today's tape is a **semi/AI selloff**, so the momentum on offer is precisely the wrong momentum to chase; and sector coverage is already complete (mega-cap tech, semis, financials, staples, healthcare, energy, index ETFs). There is no gap to fill and no conviction that clears the bar.

### Changes applied to watchlist
- **AMD: re-enabled 2026-08-06** — its 08-04 AMC Q2 print is digested and the park was always one-day (**one session overdue** because the 08-05 routine did not run). Re-verified **tradable & active on Alpaca** (`/v2/assets`: `tradable: true`, `status: active`, NASDAQ). Beat on revenue, EPS and guidance; the −7% is valuation compression, not deterioration. Liquid at $352M/day. **Caveat recorded: AMD now carries the highest ATR on the list (8.66%)** and re-enters into an overnight semi selloff — a fine breakout name, but the one most likely to produce a full-1R fade if the AI de-rate continues.
- **ABNB: parked 2026-08-06** — **reports Q2 today AMC** (5:00pm ET call, company IR). One-day pre-print event park, consistent with the house rule applied to MSFT/META (07-29), AAPL/AMZN (07-30), QCOM and AMD (08-04). The bot flattens at 15:55 so there is no overnight gap exposure, but pre-print positioning whipsaw is a poor fit for a long-only intraday book with a $141 cushion. Independently supported: ABNB is **0W4L all-time (−$186.30)** and the **thinnest active name at $22.3M/day**. **RE-ENABLE 2026-08-07.**
- Everything else held. **No adds.**

### Final watchlist
**24 active** (net 0 vs 24: +1 AMD re-enabled, −1 ABNB parked; within the 30 cap):
AAPL AMD AMZN AVGO BAC COST CRM GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: ABNB, AMD→re-enabled, BABA, BIRD, C, ENPH, JPM, WPM — 7 rows inactive.)
Service restarted: **yes** — `active`, MainPID 234382, NRestarts=0, ActiveEnterTimestamp 11:50:44 UTC; clean `USTradeWisBot starting (dry_run=False)` at 07:50:46 EDT, **0 errors/tracebacks since boot**, correctly sleeping until the 09:30 ET open, and the bot's own `get_active_watchlist()` reads back all 24 symbols. (One cosmetic `[notify] Telegram send failed … Connection reset by peer` fired on the *shutdown* alert during the restart — transient, outside the trading path, no retry needed.)
⚠️ Operational note: writing the AMD/ABNB notes initially failed with **"String or binary data would be truncated"** — `watchlist.notes` is **nvarchar(255)**. Future runs must keep note text ≤255 characters; the first attempt was rejected by SQL Server and re-applied at 200/181 chars, so no partial write occurred.

### Notes for pre-market research (next session — Fri 08-07)
- **RE-ENABLE ABNB** once tonight's Q2 print is digested — one-day event park only. Check the after-hours reaction first and record the direction; a gap-down that stabilises still re-enters. **But note its independent weaknesses** (0W4L all-time, $22.3M/day, thinnest on the list): if it gaps down hard *and* liquidity thins further, converting the event park into a structural one is defensible — say so explicitly rather than re-enabling by reflex.
- **⚠️ FRIDAY 08-07 IS THE JULY JOBS REPORT, 8:30 ET — verified twice this week.** It lands before the open, so it is a *gap* risk rather than an intraday-halt risk, but it is the week's one genuine binary and ADP already printed below forecast. Read the number before deciding whether anything needs a one-day park.
- **AMD is the name to watch today and tomorrow.** Highest ATR on the list (8.66%), just re-enabled into an overnight AI/semi selloff, below both MAs. If it produces a full-1R fade, that is *regime*, not a park trigger — but record it, because AMD is already the third-worst all-time name (−$315.09, 8 trades, 2W).
- **QCOM remains the standing #1 park candidate** — −19.2% vs 50MA, 1W5L all-time. It has not traded since 07-27, so there is still no new fade. **Park on the next full-1R fade**; do not park pre-emptively on a gate-blocked day, and do not forget it because it is quiet.
- **SE's park proposal is retired on evidence** (2 take-profits, +$228.54 and +$60.30; filled 08-04). Do not re-raise it on blocked-attempt counts alone. **General rule established today: a dormancy claim must be checked against the `trades` table before it becomes a park.**
- **GOOGL: watch the 50MA at ~$358.43** (closed $362.38). The AI-leadership exodus is a multi-week sentiment overhang, not a one-day event; if GOOGL loses the 50MA on volume, re-open the park question — and at that point the GOOG/GOOGL double-listing becomes a real decision rather than a theoretical one.
- **The 08-05 pre-market routine did not run — fourth silent no-run in ~4 weeks** (07-14, 07-29, 08-03, 08-04 rc=127, 08-05). The 08-05 daily review already traced the 08-04 failure to `timeout: failed to run command 'claude': No such file or directory` (a PATH/binary issue in the cron wrapper, **outside this repo**). Two consecutive weeks of one-day-late re-enables (XOM, now AMD) is a small but compounding cost. This needs a human or an infra-scoped run; it cannot be fixed from the pre-market routine.
- **Sonar is now 3-for-3 unreliable** (08-03 stale close, 08-04 inverted movers, 08-06 empty on 23/25 tickers). Keep leading with it for speed — it costs seconds — but **budget for WebSearch to do the actual work**, and never let a park or add rest on it.
- **Regime expectation:** a lower Nasdaq open with semis leading down is the mirror of 08-05. Expect fewer above-VWAP vetoes and more genuine candidates — which historically has *not* been good news (08-05 took 4 and lost on all 4, MFE ≤ +0.48%). The IMP-022 replay series now reads **PAID / COST / COST**; keep accruing it per IMP-025, but **this is a code-side question for the daily review, not a watchlist action.** Do not widen risk, do not add names to manufacture activity. Equity **$7,640.90 (−23.6% YTD), $140.90 above** the −25% ($7,500) flag — second-thinnest cushion of the incubation. **Protect it.**

---

## 2026-08-07 — Pre-market Research

### Market context
**Flat futures into the week's one genuine binary.** S&P 500 futures **~7,740 (+0.07%)**, **Nasdaq-100 futures +0.29% (~29,570)**, Dow futures **−0.04% (~53,990)** — a coiled, directionless tape ahead of the data. **July nonfarm payrolls, unemployment and average hourly earnings all print at 8:30 ET**, consensus **+83K** (FactSet +97.5K) with unemployment steady at **4.2%**, against June's +57K. June consumer credit follows at 15:00 ET (second-tier).
⚠️ **This routine runs at 07:46 ET — the jobs number had NOT printed when these decisions were made.** The 08-06 daily review asked to "read the number before deciding any one-day park"; that was **not possible at this hour** and is recorded as a limitation rather than skipped. It does not change the decisions: the release lands **pre-open**, so it is **gap** risk, the bot's first entry is after 09:30 once the number is digested, and it holds nothing overnight. No watchlist action is contingent on it.
**Rate backdrop is the live risk, and it is a *hike* risk:** markets price **~54% odds of a 25bp HIKE as soon as September**; 10-year **4.67%**, 2-year **4.24%**. BofA: an in-line print would give the Fed room for **three hikes** over the rest of 2026. A hot payroll number is therefore a **risk-off** trigger for a long-only book, not the usual "good news is good news."
**Thursday's close:** Dow **−0.85%**, S&P **−0.18%**, Nasdaq **−0.06%**; 8 of 11 sectors red (industrials, real estate, materials worst) as a crude rebound revived hike fears. WTI **~$77.60 (+0.40%)**, gold **$4,305.90 (+1.54%)**, DXY 99.94. **Strait of Hormuz optimism has faded** — no Iran deal announced, talks continue via Oman. Overseas mixed: Nikkei −0.12%, Kospi −0.60%, Hang Seng +0.44%, CSI 300 +0.93% on strong China July exports.
**Earnings:** ~110 reporters, headlined by **VST** and **TTWO** — **no watchlist name reports today** (all 25 have already reported Q2). Pre-market movers are off-list: **TEAM +30%**, **NET +16%**, **ABNB +8%**, **DKNG −3%**.

⚠️ **Perplexity `sonar` failed for a FOURTH consecutive session, and this time it fabricated.** Asked for ABNB's Q2 reaction it returned **Apple's** results under ABNB's ticker — "revenue $109.42B", "record June-quarter demand for iPhone, Mac and Services", a "$0.27/share dividend", and an after-hours **drop of −6.65% from $333.43 to $311.25**. Every one of those is wrong for Airbnb, and the *direction was inverted*: ABNB actually **rose 8–10.8%**. It also returned "no overnight catalyst found" for 24 of 25 tickers and could not produce futures, movers or the jobs-report timing. **Had this been trusted, ABNB would have been structurally parked on a fabricated earnings miss.** Running record: 08-03 stale, 08-04 inverted movers, 08-06 empty, **08-07 fabricated + inverted**. Everything below comes from **WebSearch (CNBC/Benzinga/StockStory/company IR) + Alpaca bars**; the ABNB close of **$151.64** in Alpaca's own daily bar independently corroborates the WebSearch account and refutes sonar's $333.43.

### Carried from daily review
Acted on the **2026-08-06** daily review's "Notes for pre-market research". Both routines ran last session — **no silent no-run to report this time**, the first clean handoff since 08-04.
- **"RE-ENABLE ABNB — check the after-hours reaction first and say explicitly which"** — **done, and the answer is unambiguous: re-enable.** ABNB **beat and raised**: revenue **$3.61B vs $3.58B** est (+16.5% YoY), GAAP EPS **$1.37 vs $1.25** (+9.5%), adj. EBITDA **$1.26B vs $1.23B** (35% margin), GBV **$27.2B (+16%)**. Q3 revenue guided **$4.69–4.77B** above consensus and **full-year revenue guidance raised** to mid-teens growth (from low-to-mid teens), FY adj. EBITDA margin **35.0% → 35.5%**. Stock closed the regular session **$151.64 (−0.56%)**, traded **~$163.72 (+7%)** on the release and built to **~$168 (+10.8%)** through the call, clearing its 52-week high of $156.50; **+8% pre-market** this morning. The review's structural-park test was **"gapped down hard AND liquidity thinned"** — **neither leg is met; both are inverted** (gap **up**, and post-print volume will run far above its normal turnover). Per the pre-registered rule it re-enters. **Its independent weaknesses are recorded and stand: 0W4L all-time (−$186.30) and the thinnest name on the list.** This is an event park that expired, not a verdict on the name.
- **"Read the July jobs number before deciding any one-day park"** — **not possible at 07:46 ET** (prints 08:30 ET). See the limitation logged above. No park decision today depended on it.
- **"QCOM — park on the next full-1R fade; do not park on blocked-attempt counts alone"** — **held, third session running, correctly.** QCOM **still has not traded since 07-27**, so there is again no new fade to act on. Its chart even improved: **−16.9% vs 50MA** today vs −19.2% on 08-06 and −23.2% on 08-04, with **5d +5.8%**. Parking it now would be parking on a 7-session-old datapoint and would violate its own trigger. The trigger stands.
- **"AMD — watch; it has not yet had its first post-re-enable session"** — **still true, and still no action.** AMD did not trade again on 08-06 (1 blocked attempt). It remains the **highest-ATR name on the list (8.22%)**, below both MAs (−3.5% / −4.9%), third-worst all-time (−$315.09). Watching, not parking: a re-enabled name that has produced zero fills cannot yet have produced the fade that would justify a park.
- **"WMT and AMZN — if either repeats a fade, they join the fader watch"** — noted, **no action on one session** each. Both are covered below.
- **"SE's park proposal is retired on evidence — do not re-raise on blocked-attempt counts"** — **honoured, not re-raised.**
- **"GOOGL: watch the 50MA at ~$358.43"** — **checked. GOOGL closed $357.75, +0.2% vs its 50MA** — it is sitting *on* the line, not through it. See below.

### Watchlist review
**Account state:** equity **$7,548.34**, cash $7,548.34, **0 open positions, 0 open orders** → **no locked symbols**; every name was eligible for review. ACTIVE, not blocked. **Cushion is $48.34 above the −25% ($7,500) strategy-review flag — the thinnest of the entire incubation** (prior low $78.78 on 07-29), **−24.5% YTD**. This is the dominant constraint on today's decisions.

- **Trade performance (33 closed since 07-24, net −$44.81):** red **META −78.86 (1W2L)**, ENPH −43.68 *(parked)*, QCOM −39.66 (0W1), WMT −37.36 (0W2), AAPL −24.46 (1W3), AMZN −23.87 (0W2), QQQ −23.35 (0W1), GOOGL −18.63 (1W1), SE −4.56, MSFT −0.48. Green **INTC +55.72**, NFLX +46.23 (3W0), BAC +44.74 (3W0), COST +34.17 (2W0), GOOG +25.90, SPY +23.99 (2W0), NVDA +19.35 (2W1).
- **Technicals (daily bars through the 08-06 close).** Broken/below both MAs: **QCOM (−4.2% / −16.9%)**, **TSLA (−8.0% / −16.5%)**, **AMD (−3.5% / −4.9%)**, **META (−4.3% / −1.8%)**, **UNH (−4.1% / −2.0%, 5d −4.2%)**, **MU (−1.3% / −9.3%)**, WMT (−0.0% / −2.3%), AAPL (−3.4% / +0.9%, 5d −6.3%), NFLX (+2.5% / −3.0%), INTC (+2.5% / −10.1% but 5d +9.5%). Stretched and correctly drawing VWAP vetoes: **MSFT +19.6% / +23.3% (5d +10.8%)** — by far the most extended name on the list — plus **AMZN +8.8% / +10.0% (5d +15.6%)**, AVGO +7.7% / +6.5%, CRM +6.6% / +8.7%, NVDA +6.2% / +6.4% (5d +12.3%).
- **Volatility/size outliers:** **MU ATR 9.56% at $881/share** (still caps sizing at qty 1 — a structural inefficiency, not a park trigger) and **AMD ATR 8.22%**, **INTC 7.74%**. Everything else sits in a workable 1.2–4.9%.
- **Liquidity is healthy across the list.** Thinnest by median 20-day dollar volume are **ABNB (~$472M)** and **SE (~$478M)**; every other name is ≥$1.8B/day. *(Note on methodology: these are consolidated-tape figures and run ~20× the IEX-only numbers quoted in earlier entries — e.g. ABNB "$22.3M". The **ranking is unchanged** — ABNB and SE remain the two thinnest — but the absolute levels in prior entries should not be compared against these. Neither name is anywhere near an illiquidity threshold on consolidated volume.)*
- **No negative catalysts on any active name:** no earnings during market hours, no halts, no M&A, no FDA or legal binaries. The only on-list event is ABNB's print, which is resolved and positive.
- **GOOGL held, on the line rather than through it.** It closed **$357.75, +0.2% above its 50MA** — the level the 08-06 entry flagged at ~$358.43. That is a *touch*, not the "loses the 50MA on volume" break that was pre-registered as the trigger to re-open the park question, and it is up **+7.2% over 5 days**. The AI-leadership-exodus overhang remains directional and multi-week, but this bot is flat every night and GOOGL is the third-most-liquid name on the list. **Held — but this is now the closest thing to a live park trigger on the board; if it closes below the 50MA on elevated volume, the GOOG/GOOGL double-listing becomes a real decision.**
- **META, WMT, AMZN, UNH — all held, all on one-session evidence.** META is the worst post-gate name (−$78.86) and below both MAs, but 08-06's META trade was an **IMP-013 break-even rescue working exactly as designed**, not a fade. WMT and AMZN each faded once on 08-06 with no catalyst — the daily review explicitly said one session is not a trigger. UNH is quietly weak (−4.1% / −2.0%, 5d −4.2%, all-time 2W4L −$185.47) and goes **on watch**, not parked.
- **MSFT is the most extended name on the list (+19.6% / +23.3%)** and generated 21 VWAP vetoes on 08-06. **Not a park candidate — the gate is doing precisely its job.** Same reading for TSM (33 vetoes), QCOM (20) and XOM (18): blocked-attempt counts measure gate cycles, not dormancy.
- **Adds: none.** Four independent reasons, any one of which is sufficient. (1) The **2026-08-01 weekly's standing order is analysis-only accrual until the post-gate book reaches 40–60 trades** — it is at **30 post-veto (33 since 07-24)**, and changing the sample composition mid-measurement corrupts the exact read the incubation is waiting on. (2) The **cushion is $48.34** — the thinnest ever; the 08-06 review's instruction was explicit: *"Do NOT widen risk, do NOT add names to manufacture activity."* (3) **The one binary of the week has not printed yet**, and with a September hike ~54% priced, a hot number is a risk-off trigger for a long-only book — adding exposure hours before it would be backwards. (4) Today's real momentum (**TEAM +30%, NET +16%**) is **post-earnings day-one gap momentum**, the single worst fit for a strategy whose VWAP gate exists to refuse stretched gap-chases. Sector coverage is already complete. **No gap to fill, no conviction that clears the bar.**

### Changes applied to watchlist
- **ABNB: re-enabled 2026-08-07** — the one-day pre-print event park expired and **the event resolved bullishly** (beat on revenue, EPS and EBITDA; **full-year guidance raised**; +8–10.8% after hours from $151.64, above its 52-week high). Re-verified on Alpaca before the write: **`/v2/assets/ABNB` → `tradable: true`, `status: active`**, NASDAQ, shortable. The structural-park condition from the 08-06 review (**gap down hard AND liquidity thinned**) is **not met on either leg** — stated explicitly as instructed. **Caveats recorded and unchanged: 0W4L all-time (−$186.30), thinnest name on the list, and today it is a day-one post-earnings gap-up — the exact profile the IMP-022 VWAP gate is built to veto, so the realistic expectation is that it is blocked rather than traded.**
- **Everything else held. No parks. No adds.**
- *Operational note:* the 08-06 entry's **255-char `watchlist.notes` limit** was respected — the note was length-asserted **before** the write (first draft 288 chars was rejected in-script, final 252), so no truncation error and no partial write.

### Final watchlist
**25 active** (+1 vs 24: ABNB re-enabled; no parks; within the 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SE SPY TSLA TSM UNH WMT XOM
(Parked: BABA, BIRD, C, ENPH, JPM, WPM — 6 rows inactive.)
Service restarted: **yes** — `systemctl is-active` → **active**, MainPID 317464, **NRestarts=0**, ActiveEnterTimestamp 11:51:05 UTC. `bot.log` shows a clean **`USTradeWisBot starting (dry_run=False)` at 07:51:06 EDT**, then `market closed — sleeping ~5932s until next open` — correct behaviour for 09:30 ET. **0 errors, 0 tracebacks, 0 loop errors since boot.** The bot's own `get_active_watchlist()` reads back all **25** symbols. *(journald holds only systemd lifecycle lines — the unit redirects stdout to `bot.log`, per IMP-024; startup was verified there, not in journalctl.)*

### Notes for pre-market research (next session — Mon 08-10)
- **⚠️ CUSHION IS $48.34 — the thinnest of the incubation.** One average red day (−$92 to −$96 this week) **trips the −25% / $7,500 formal strategy review.** Read Friday's close first and state the cushion at the top of Monday's entry. **Do not widen risk, do not add names, do not manufacture activity.** If the review flag trips, that is a human decision point, not something the pre-market routine resolves.
- **Read Friday's jobs reaction before anything else.** Today's routine could not see the number (ran 07:46 ET, print 08:30 ET). Monday's entry should record **what the payroll print was, how the tape took it, and whether the September-hike odds moved** off ~54% — that is now the dominant macro variable for a long-only intraday book, and a hike repricing is a *risk-off* input, not a neutral one.
- **ABNB is the name to watch Monday.** Re-enabled today into a **+8–10.8% day-one post-earnings gap**. Expect the VWAP gate to veto it rather than trade it — **if it does trade and fades a full 1R, that is a park trigger given 0W4L all-time**; if it is merely blocked all day, that is the gate working and **not** a park trigger (the SE precedent: never park on blocked-attempt counts).
- **GOOGL is the closest live park trigger on the board** — it closed **$357.75, only +0.2% above its 50MA**. The pre-registered trigger is a **close below the 50MA on elevated volume**; check it explicitly Monday. If it breaks, the GOOG/GOOGL double-listing becomes a real decision rather than a theoretical one.
- **QCOM: the trigger is unchanged and still un-fired.** No trade since **07-27**, so there is still no full-1R fade to act on, and its 50MA gap has now narrowed three sessions running (−23.2% → −19.2% → −16.9%). **Do not park it on quietness**, and equally **do not forget it** — it has been the standing #1 park candidate for four sessions.
- **AMD still has not had its first post-re-enable fill** (re-enabled 08-06). Highest ATR on the list (8.22%), below both MAs, third-worst all-time. Keep watching; a park needs a fill, not a blocked attempt.
- **UNH added to the fader watch** — below both MAs (−4.1% / −2.0%), 5d −4.2%, all-time 2W4L −$185.47. Not actioned on chart weakness alone; if it produces a full-1R fade it is a legitimate park candidate ahead of QCOM.
- **⚠️ Sonar is now 4-for-4 unreliable and has escalated from empty to FABRICATING** — it returned Apple's earnings under ABNB's ticker with an **inverted direction**, which, if trusted, would have structurally parked a name that had just beaten and raised. **Treat sonar output as an unverified lead only. Never let a park or an add rest on it, and always corroborate an earnings claim against Alpaca's own bars plus a primary source.** Consider whether the pre-market routine should stop leading with it altogether — it has not added value in four sessions and has now actively introduced a false premise.
- **Liquidity methodology changed today** — figures are now **consolidated-tape** median 20-day dollar volume, ~20× the IEX-only numbers in entries before 08-07. **Do not compare the two.** Rankings are unaffected (ABNB and SE remain thinnest).
- **Strategy posture is unchanged and is not the pre-market routine's to alter:** analysis-only accrual toward the 40–60 post-gate-trade bar (**at 30**), everything on exit geometry, nothing on per-trade filters. `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, paper endpoint and the no-overnight rules all untouched.

---

## 2026-08-11 — Pre-market Research

### Market context
⚠️ **CUSHION FIRST, as the 08-07 entry instructed: equity $7,535.12, cash $7,535.12, 0 positions — $35.12 above the −25% / $7,500 formal-strategy-review flag, the thinnest of the incubation** (−24.65% YTD). One average red day of last week (−$92 to −$96) trips it. Every decision below is taken under that constraint.
**Futures firm, tape indecisive.** S&P 500 futures **~7,772.75** (opened 7,787.25, range 7,767–7,798); Nasdaq-100 futures **~29,764** (opened 29,881, range 29,719–29,984) — modestly positive but off the overnight highs. **Monday 08-10 closed flat-to-lower: S&P 500 −0.06% to 7,753.11, Nasdaq Composite −0.32% to 26,605.36, Dow −0.11% to 53,975.98.** *(Note: the 08-10 daily review recorded "S&P +0.62% to 7,757.64, a record close" from sonar — that is the 08-07 print, not Monday's. Monday was flat and slightly red. Corrected here.)*
**Today's dominant fact is what happens TOMORROW: July CPI, Wed 08-12 at 08:30 ET.** Consensus 3.4% headline (from 3.5% June, 4.2% May), core ~2.51% from 2.59%. **Nothing of consequence is scheduled during today's US market hours** — no tier-1 release, so today is a low-information pre-CPI session. Rest of week: PPI Thu 08-13, retail sales + UMich Fri 08-14.
**Rate risk is still a HIKE risk, but it eased.** Friday's July payrolls printed **+23K vs ~83K consensus**; September-hike odds fell to **~52% from ~67%** a week earlier. A cool CPI tomorrow bolsters the case to refrain at the Sept 16 FOMC. For a long-only intraday book a hike repricing is risk-off, so the asymmetry sits on tomorrow, not today.
**Oil is the live macro:** WTI settled **+5.1% at $82.13**, Brent +5.0% at $87.72 Monday as the Iran/Hormuz deal talk soured — Bessent had signalled an imminent deal, then Trump said the US is "only semi-negotiating" and wants economic pressure to build. Constructive for **XOM** (+4.5%/+8.9% vs its MAs), a background risk for everything else.
**Earnings:** ~150–207 reporters. **Exactly one watchlist name reports today — SE — and it reported pre-open** (see below). No other active symbol has an in-session print, a halt, an M&A, an FDA or a legal binary. Pre-market movers are off-list day-one gappers: SMCI, ONON, CAVA, NBIS, RKLB, ASTS, TME, CAH.

⚠️ **Sonar: fifth consecutive unreliable session, though this one failed honestly rather than by fabricating.** It returned "no overnight/pre-market catalyst identified" for **24 of 25 tickers** — including **SE, which was reporting Q2 earnings that same morning** — and explicitly could not produce futures direction, the pre-market movers, or today's in-session calendar ("not explicitly provided in the search results"). Its one substantive lead, the **AAPL** Jefferies downgrade, was real and **verified independently** (see below); credit where due. But a briefing tool that misses an earnings print on the one watchlist name reporting that day is not a briefing tool. **Running record: 08-03 stale, 08-04 inverted, 08-06 empty, 08-07 fabricated+inverted, 08-11 empty and missed the day's only on-list event.** Everything below is WebSearch (CNBC/Benzinga/Investing.com/AppleInsider/StockTitan/EarningsWhispers) + Alpaca bars. **Recommendation to the weekly: sonar has now failed five straight sessions and the one time it mattered most; either drop it from this routine or demote it below WebSearch.**

### Carried from daily review
Acted on the **2026-08-10** daily review's "Notes for pre-market research". ⚠️ **The 08-10 pre-market routine did not fire** (no 08-10 entry in this log; last is 08-07), so this entry closes a **two-session gap** and also carries the un-acted 08-07 notes forward. The daily reviews themselves have run every session.
- **"MSFT — keep, high priority"** — **kept, and confirmed on the tape.** MSFT was Monday's only winner (+$17.54) and the first *profitable STOP* in the bot's history — the IMP-029 trail ratcheting seven times. Post-gate 1W/2 **+$17.06**; all-time 3W/4 **+$153.97**, the best per-trade name on the list. It is also the **most extended name on the board (+17.8% vs 20MA, +23.9% vs 50MA)** and will keep drawing VWAP vetoes — that is the gate working, not a reason to touch it.
- **"QQQ / SPY — flag for gap handling, do NOT park"** — **honoured; both held, neither parked.** Both were bought inside 90 seconds of Monday's bell, both were dead money for 6.4 hours (MFE +0.23R / +0.20R), and both are one index bet held twice. Charts are fine (QQQ +2.9%/+0.9%, SPY +2.9%/+3.4%, SPY the most liquid name on the list). **This is an entry-timing and correlation-cap problem, i.e. engine work owned by the daily review — not a watchlist problem.** Recorded, not actioned here.
- **"SE — recommend parking unless pre-market shows a specific catalyst"** — **PARKED. The pre-market check found a catalyst, and it argues for parking, not keeping** (detail below).
- **"AMZN remains the standing park candidate"** — **held on watch, deliberately not parked.** Post-gate 0W/2 = **−$5.09 and −$18.78, both EOD_FLATTEN clock-outs**, not full-1R fades; the routine's own pre-registered park trigger for a fader is a **full-1R fade**, and it has not fired. AMZN is also the **second-most-liquid name on the list** and is currently stretched (+9.8%/+12.3%), so its recent absence is **gate-vetoing, not dormancy** — the SE precedent forbids parking on blocked-attempt counts. **Trigger pre-registered: the next full-1R STOP fade parks it.** All-time 1W/9, −$113.83, so this is the last extension it gets.
- **"Chopped above VWAP, never entered — ABNB, CRM, AMZN, WMT, XOM"** — checked, **none actioned, all correct as vetoes.** ABNB is now **+22.2%/+27.7% vs its MAs and +22.5% over 5 days** after the 08-07 beat-and-raise; it is the single most extended name on the board and the gate will almost certainly refuse it all day again. **Blocked ≠ park** (SE precedent). CRM +10.9%/+14.4%, XOM +4.5%/+8.9% on the oil move, WMT +0.7%/−1.6% flat.
- Carried from **08-07** and re-checked: **GOOGL's park trigger moved further away, not closer** — the pre-registered trigger was *a close below the 50MA on elevated volume*; it closed **$357.55, +2.4% above the 50MA** (vs +0.2% on 08-06). **Trigger un-fired; GOOG/GOOGL double-listing stays a theoretical question.** **QCOM's trigger is also still un-fired** — no trade since **07-27**, and its 50MA gap has now narrowed four sessions running (−23.2% → −19.2% → −16.9% → **−14.7%**, 5d **+7.0%**). Parking it would be parking on a 10-session-old datapoint and would violate its own rule. **AMD still has not had a single fill since its 08-06 re-enable** — a park needs a fill, not a blocked attempt.

### Watchlist review
**Account state: equity $7,535.12, ACTIVE, not blocked, `/v2/positions` returns 0 → NO LOCKED SYMBOLS.** Every name was eligible for review; nothing was constrained by an open position.

- **Trade performance, post-gate era (42 closed trades since 07-24, net −$52.14).** Red: **META −78.94 (1W4)**, ENPH −43.68 *(parked)*, QCOM −39.66, WMT −37.36 (0W2), QQQ −27.24 (0W2), AMZN −23.87 (0W2), TSM −23.30, GOOGL −18.63 (1W2), AAPL −16.97 (2W5), **SE −13.80 (0W2)**, TSLA −6.47. Green: **INTC +55.72**, NFLX +46.23 (3W0), BAC +44.74 (3W0), COST +34.17 (2W0), GOOG +25.90, NVDA +25.26 (3W5), SPY +23.34 (2W3), MSFT +17.06.
- **Technicals (daily bars through the 08-10 close; dollar volume is IEX-only median 20-day — multiply by ~20 for consolidated, and do NOT compare against the 08-07 entry's consolidated figures).**
  - Below both MAs: **AMD (−6.1% / −8.5%, 5d −3.0%)**, **TSLA (−2.7% / −12.5%)**, **MU (−2.5% / −11.1%)**, **META (−2.3% / −0.6%)**, **UNH (−2.5% / −1.1%, 5d −1.6%)**, **QCOM (−1.8% / −14.7% but 5d +7.0%)**, **AAPL (−4.6% / −0.5%)**, WMT (+0.7% / −1.6%), INTC (+0.9% / −11.4% but 5d +7.2%), TSM (+2.3% / −1.7%).
  - Most extended (and correctly drawing vetoes): **ABNB +22.2% / +27.7%**, **MSFT +17.8% / +23.9%**, **CRM +10.9% / +14.4%**, **AMZN +9.8% / +12.3%**, AVGO +7.3% / +7.0%, XOM +4.5% / +8.9%, NFLX +5.9% / +1.1%, NVDA +4.8% / +5.5%.
  - **Volatility outliers unchanged and still not park triggers: MU ATR 9.09% at $862/share** (sizing still pinned at qty 1 — a structural inefficiency the engine owns, not the watchlist), **AMD 8.06%**, **INTC 7.56%**. Everything else 1.14%–4.65%; SPY the tightest at 1.14%.
  - **Liquidity healthy across the whole active list.** After parking SE the thinnest name is **ABNB (~$22.7M IEX ≈ ~$450M consolidated)**; every other active name is ≥$62M IEX. Deepest: SPY $1,126M, MU $951M, NVDA $922M.
- **AAPL — the one real overnight catalyst, verified, and NOT a park.** Jefferies (Edison Lee) cut AAPL **Hold → Underperform, PT $285.56 → $263.66** (~16% downside, among the Street's lowest) after supply-chain checks showed Apple **cancelled the 20th-anniversary all-glass iPhone** on poor production yield; ASP-growth estimate for FY26–31 cut to 6.8% from 9%. DZ Bank separately cut to **Hold, PT $310**. **This is already in the tape — AAPL fell ~2% on Monday and closed $308.17**, and there are now 3 underperform ratings against 30 buy/strong-buy with a $319.48 consensus. **A digested analyst downgrade is not a today-binary**; AAPL is a top-3 liquidity name ($577M IEX) and post-gate 2W/5. **Kept.** Its chart is the thing to watch, not the rating: −4.6% vs the 20MA and now only **−0.5% vs its 50MA**, i.e. sitting on the line. **Pre-registered: if AAPL closes below its 50MA on elevated volume it joins the fader watch** — the same test GOOGL is under.
- **META, UNH, WMT, TSLA, MU, TSM — all held, all on unchanged evidence.** META is the worst post-gate name (−$78.94) and below both MAs, but 3 of its 4 post-gate trades were IMP-013/029 break-even scratches, not fades. UNH stays on the fader watch (below both MAs, 5d −1.6%, 2W/6 −$185.47 all-time, no trade since 07-22). Nothing here has produced a new full-1R fade to act on.
- **Adds: none.** Five independent reasons, any one sufficient. (1) **The cushion is $35.12** — the thinnest of the incubation; the standing instruction from both the weekly and the last two daily reviews is *do not widen risk, do not add names to manufacture activity*. (2) **CPI prints tomorrow at 08:30 ET with a September hike ~52% priced** — adding exposure the session before a binary that could reprice the whole rate path is backwards for a long-only book. (3) **IMP-029 has exactly one armed live trade (MSFT, 08-10).** Changing watchlist composition now corrupts the attribution the weekly explicitly ordered be measured before anything else ships. (4) **Today's actual momentum is day-one post-earnings gap momentum** — SMCI, ONON, CAVA, NBIS, RKLB, ASTS — the single worst fit for a strategy whose VWAP gate exists to refuse stretched gap-chases; ABNB's own +22% post-print extension is the live demonstration. (5) **Sector coverage is complete at 24 names** with a 3-position concurrency cap: mega-cap tech, semis, banks, staples, retail, healthcare, energy, streaming, software and two index ETFs. There is no gap to fill and no conviction that clears the bar.

### Changes applied to watchlist
- **SE: PARKED 2026-08-11** (`is_active = 0`, row kept, dated note written; note length asserted at **223 chars** before the write, inside the 255 limit). Verified **0 open positions** on Alpaca first — SE was **not locked**. Three independent legs, and today's news moves the third from "watch" to "act":
  1. **The 08-10 daily review pre-registered the recommendation** — *"chronic-loser watch escalates… Recommend parking SE unless pre-market shows a specific catalyst."*
  2. **The record.** Post-gate **0W/2 (−$13.80)**; last 30 days **0W/3 (−$55.45)**; all-time **2W/8 (−$64.32)**, and both wins are from early July while every trade since is red. Monday it entered at the **confidence floor (60.00)** with the **weakest momentum of the day (0.67)**, at 14:32 with 83 minutes of runway, and **never traded above entry** — a textbook member of the never-green cohort.
  3. **The catalyst the review asked for exists, and it argues for parking.** **Sea Limited reported Q2 2026 before the open this morning** (release ~07:00 ET, call 07:30 ET) — the **only watchlist name reporting today**. Revenue **$7.80B vs ~$7.27B** est (+~$530M), EPS **$0.86 vs $0.79** on one benchmark — **but a ~14% MISS against the Zacks $1.00 consensus**, and Sea has missed Zacks in **all four trailing quarters** (avg −15.5%). **Options priced a 19.1% move**, one of the largest of the season. So: an ambiguous print on the thinnest ADR on the list, on a day-one gap with a ~19% implied range, in a name that is 0-for-its-last-5. **That is the exact profile that makes intraday longs dangerous**, and it is the opposite of the "specific catalyst" that would have justified a reprieve.
  *This is a park on evidence, not on blocked-attempt counts — the SE precedent from 08-06 (which correctly retired an earlier park proposal built on veto counts) is honoured, not contradicted. The row is retained and can be re-enabled by a future run.*
- **No adds. No re-enables. Everything else held.** Parked rows now: BABA, BIRD, C, ENPH, JPM, **SE**, WPM (7 inactive).

### Final watchlist
**24 active** (−1 vs 25: SE parked; no adds; within the 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM GOOG GOOGL INTC META MSFT MU NFLX NVDA QCOM QQQ SPY TSLA TSM UNH WMT XOM
Service restarted: **yes** — `systemctl is-active` → **active**, MainPID 638179, **NRestarts=0**, ActiveEnterTimestamp **11:51:58 UTC**. `/var/log/ustradewisbot/bot.log` shows a clean **`USTradeWisBot starting (dry_run=False)` at 07:52:01 EDT** followed by `market closed — sleeping ~5877s until next open` — correct for a 09:30 ET open. **0 errors, 0 tracebacks since boot.** The bot's own `get_active_watchlist()` reads back all **24** symbols and no longer contains SE. *(journald holds only systemd lifecycle lines; startup is verified in `bot.log` per IMP-024.)*

### Notes for pre-market research (next session — Wed 08-12)
- **⚠️ CUSHION $35.12. Read Tuesday's close first and state it at the top.** One average red day trips the −25% / $7,500 formal strategy review. That is a human decision point, not something this routine resolves. **Do not widen risk, do not add names, do not manufacture activity.**
- **⚠️ JULY CPI PRINTS WED 08-12 AT 08:30 ET — before this routine's own decisions are final and before the open.** Consensus 3.4% headline / ~2.51% core. **This routine runs ~07:46 ET, so it will NOT have seen the number** — exactly the 08-07 payrolls limitation, so record it explicitly again rather than skipping it. The release is **pre-open, therefore gap risk**, the bot's first entry is after 09:30 once it is digested, and it holds nothing overnight. A hot print revives the September hike (~52% priced) and is **risk-off for a long-only book**; a cool print is the relief case. No park decision should be made contingent on a number this routine cannot see.
- **AMZN's park trigger is now live and pre-registered: the next full-1R STOP fade parks it.** It is 1W/9 all-time (−$113.83) and 0W/2 post-gate on two clock-outs. Do not park it on another EOD_FLATTEN drift or on veto counts — but do not let a genuine 1R fade pass unactioned either.
- **AAPL joins the watch list with a concrete test.** Post-Jefferies-downgrade it sits **−0.5% vs its 50MA**. **The trigger is a close below the 50MA on elevated volume** — identical to GOOGL's. Check both explicitly; GOOGL is currently +2.4% above and receding from its trigger.
- **QCOM: fifth session with the trigger un-fired.** Still no trade since 07-27; the 50MA gap has narrowed four sessions running (now −14.7%, 5d +7.0%). **Do not park on quietness, do not forget it.** Same for **AMD** — re-enabled 08-06 and still zero fills; a park needs a fill.
- **ABNB is the most extended name on the board (+22.2% / +27.7%, 5d +22.5%)** and now the thinnest active name (~$22.7M IEX). Expect it to be vetoed all day. **If it trades and fades a full 1R, that is a park trigger** given 0W/4 all-time (−$186.30); if it is merely blocked, that is the gate working.
- **SE is parked, not deleted.** If a future run wants it back, re-enable the existing row (`upsert_watchlist_symbol`) — do not re-insert. The bar for re-entry should be a *demonstrated* change in behaviour, not merely the earnings event being over: it was parked on a 0-for-5 record as much as on the print.
- **QQQ/SPY remain one bet held twice** and consumed 2 of 3 concurrent slots for all of Monday. This is engine work (gap-aware ETF entry, one-index-ETF-at-a-time cap) owned by the daily review — **do not park either name to work around it.**
- **⚠️ Sonar is now 5-for-5 unreliable and missed SE's earnings on the morning SE reported.** Treat it as an unverified lead only; never let a park or an add rest on it. **Escalating to the weekly: drop it from this routine or demote it below WebSearch.**
- **Strategy posture unchanged and not this routine's to alter:** `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, paper endpoint, no-overnight rules — all untouched. The post-gate book is at **42 closed trades**, past the 40–60 bar; the exit-geometry decision belongs to the daily/weekly review, not here.

---

## 2026-08-12 — Pre-market Research

### Market context
⚠️⚠️ **THE FLAG HAS TRIPPED, AS THE 08-11 REVIEW INSTRUCTED BE STATED FIRST: broker equity is $7,482.47, cash $7,482.47, 0 positions — $17.53 BELOW the −25% / $7,500 formal-strategy-review line** (−25.18% vs the $10,000 start). `last_equity` equals `equity`, so nothing has moved overnight. *(The 08-11 daily review recorded the close as $7,482.65; the broker now reports $7,482.47 — an $0.18 settlement difference, immaterial, but the broker figure is used here.)* **This is a human decision point and this routine does not resolve it.** Every decision below is taken under the standing conservative posture: do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols to get back to flat.
**Futures modestly higher into the one number that matters.** S&P 500 futures **+0.2%**, Nasdaq-100 futures **+0.6%**, Dow flat; SPY +0.23% at ~$772.33 and QQQ +0.58% at ~$722.62 in pre-market. Tuesday 08-11 closed red: **S&P 500 −0.32% to 7,728.20, Nasdaq Composite −0.60% to 26,445.45, Dow −0.34% to 53,791.85**, on fading US/Iran deal hopes and higher oil.
⚠️ **JULY CPI PRINTS TODAY AT 08:30 ET AND THIS ROUTINE RAN AT 07:46–07:51 ET — I DID NOT SEE THE NUMBER.** Recording the limitation explicitly, exactly as the 08-07 payrolls and 08-11 entries required. Consensus **3.4% headline** (from 3.5%), **+0.1% m/m**, **core +0.2% m/m / ~2.5% y/y**. The asymmetry is unusual and unchanged: **the live debate is a HIKE, not a cut** — multiple FOMC members have signalled a possible September hike, ~52% priced, so a hot print is **risk-off for a long-only intraday book**. It is a **pre-open** release, therefore gap risk; the bot's first entry is after 09:30 once it is digested, and it holds nothing overnight. **No decision below is contingent on a number I could not see.**
**Earnings: NOT ONE ACTIVE WATCHLIST NAME REPORTS TODAY.** ~189 reporters; the headline is **CSCO after the close** (not on the list), with CRWV, NBIS and CBRS also off-list. Verified the nearest on-list print: **WMT reports Q2 FY27 on Thu 2026-08-20 pre-open** (confirmed on Walmart IR) — **eight days out, not today**. No active name has an in-session print, halt, M&A, FDA or legal binary today. Other calendar item: July Treasury monthly balance, 14:00 ET (immaterial).
**Pre-market movers are off-list and semi-friendly.** **SMCI +9.5%** (EPS beat, Q1 guide $14.5–15.5B vs $11.8B est, >$60B of new fiscal-2026 orders) and **CRWV +18%** are dragging the whole semi complex up: **MU +3%, NVDA +2%, INTC +2%, AMD +1%** pre-market. That is a *sympathy* bid on four on-list names, not a name-specific catalyst on any of them.
⚠️ **Sonar: SEVENTH consecutive unreliable session — this one failed by recycling AND by staleness.** It returned "no overnight/pre-market catalyst identified" for **23 of the 24** tickers; its only substantive output was **AAPL**, and that was **yesterday's Jefferies downgrade re-served as new**, padded with genuinely stale items (WWDC 2026 as a "key catalyst", "Q3 FY2026 earnings are the most immediate catalyst" — Apple has already reported). It gave **no futures direction** beyond "mixed", listed "most active premarket options names" instead of pre-market movers, and **missed the July CPI print entirely** — the single dominant scheduled event of the day. **Running record: 08-03 stale, 08-04 inverted, 08-06 empty, 08-07 fabricated+inverted, 08-11am empty, 08-11pm recycled, 08-12 recycled+stale+missed CPI.** Everything above and below is WebSearch (TheStreet/Yahoo/Benzinga/CNBC/TipRanks/Walmart IR) + Alpaca bars. **Third escalation to the weekly in two days: drop sonar from this routine or demote it below WebSearch — it has now cost more verification time than it has saved for seven straight sessions.**

### Carried from daily review
Acted on the **2026-08-11** daily review's "Notes for pre-market research". Every named item was checked and its pre-registered trigger tested explicitly.
- **"⚠️⚠️ The −25% flag has tripped — state it at the top"** — **done, above.** Posture honoured to the letter: **no adds, no re-enables, nothing widened.**
- **"NFLX — do NOT park, and do not read −$44.55 as a name defect"** — **honoured, kept.** The 08-11 loss was the IMP-031 mechanism failure (MFE +0.52R, exactly one 1-min *high* and zero *closes* cleared the break-even trigger), not a name defect. NFLX is post-gate **3W/4 +$1.68** and its chart is fine (+3.7% vs 20MA, −0.6% vs 50MA, 5d +1.7%). **Today is IMP-031's first live session and NFLX is its worked example** — left enabled, as instructed.
- **"COST — new fader watch, trigger = next full-1R STOP fade"** — **checked, un-fired, kept.** 08-11 was an EOD_FLATTEN drift (−$13.44), not a stop. Post-gate **2W/3 +$20.73**; chart flat and tight (−0.03% / −0.64%, ATR 2.01%). No trigger, no action.
- **"WMT — flag, don't park"** — **flagged, not parked.** Post-gate 1W/3 −$31.84, all-time 6W/11 −$66.51; +1.25% / −1.03% vs its MAs. No trigger fired. **New, concrete item for the 08-19 run: WMT reports pre-open on Thu 08-20** — that is a one-day event-park decision for next Wednesday's entry, not today's.
- **"ABNB blocked 20× — blocked ≠ park (SE precedent)"** — **honoured, kept.** Still **+20.9% / +27.1% vs its MAs and 5d +23.4%**, the most extended name on the board, and still **zero post-gate fills**. Expect the VWAP gate to refuse it all day again. Its park trigger remains *a full-1R fade if it ever actually trades*.
- **"AMZN — next full-1R STOP fade parks it"** — **un-fired, held.** No trade on 08-11. Chart is strong (+7.0% / +10.0%), i.e. its absence is gate-vetoing, not dormancy.
- **"QCOM (no trade since 07-27)"** and **"AMD (still zero fills since the 08-06 re-enable — a park needs a fill)"** — **both un-fired, both held.** QCOM's 50MA gap narrowed a fifth session running (−14.7% → **−13.65%**); AMD still has **no fill in five sessions**, so there is nothing to park on. Both are also in today's semi bid.
- **"AAPL — trigger is a close below the 50MA on elevated volume"** — **tested explicitly, HALF-fired, NOT actioned.** AAPL closed **$304.91, −1.50% below its 50MA** (it was −0.5% yesterday), but on **0.67× its 20-day average volume** — the volume leg fails outright. **Kept; stays on watch with the trigger unchanged.**
- **"GOOGL — same test"** — **tested explicitly and this is the one that changed. See below.**
- **"SE stays parked"** — **honoured.** Nothing today touches the 0-for-5 record it was parked on.
- **"Structural: three sessions of spending all three slots in ten minutes — do NOT park names to work around it"** — **honoured. No name was touched for this reason**; it is engine work (concurrency pacing) owned by the daily/weekly review.

### Watchlist review
**Account state: equity $7,482.47, ACTIVE, not blocked, `/v2/positions` returns 0 and `/v2/orders?status=open` returns 0 → NO LOCKED SYMBOLS.** Verified before reading the table and re-verified inside the write script immediately before the UPDATE. Every name was eligible for review.

- **Trade performance.** Last 14 days: **34 closed, net −$112.54**. Post-gate (since 07-24): **46 closed, net −$109.97**. Worst post-gate: META −$78.94 (1W/4), QCOM −$39.66, WMT −$31.84, QQQ −$27.24 (0W/2), AMZN −$23.87 (0W/2), TSM −$23.30, **GOOGL −$18.63 (1W/2)**, AAPL −$16.97 (2W/5). Best: INTC +$55.72, BAC +$44.74 (3W/3), **GOOG +$25.90 (1W/1)**, NVDA +$25.26, SPY +$23.34, COST +$20.73, MSFT +$17.06.
- **All-time, the number that decided today: GOOGL is the worst-performing ACTIVE name on the board — 3W/10, −$326.85.** Only parked ENPH (−$350.85) is worse in the whole table. Third-worst active is AMD (2W/8, −$315.09), then MU (1W/10, −$206.69), ABNB (0W/4, −$186.30), UNH (2W/6, −$185.47).
- **Technicals (daily bars through the 08-11 close; dollar volume is consolidated-tape median 20-day, comparable to the 08-07 entry, NOT to 08-11's IEX figures).**
  - **Below both MAs:** QCOM (−1.1% / −13.7%), TSLA (−1.2% / −11.5%), MU (−1.2% / −10.2%), **AMD (−4.5% / −7.4%, 5d −8.5% — the worst 5-day on the list)**, **GOOGL (−1.3% / −3.2%)**, GOOG (−1.3% / −3.0%), UNH (−3.8% / −2.8%), AAPL (−5.5% / −1.5%), COST (−0.03% / −0.6%), NFLX (+3.7% / −0.6%), WMT (+1.3% / −1.0%), TSM (+3.1% / −0.9%). INTC is +1.6% / −11.0%.
  - **Most extended (and correctly drawing vetoes):** ABNB +20.9% / +27.1%, MSFT +15.7% / +23.0%, CRM +10.0% / +14.3%, AMZN +7.0% / +10.0%, XOM +4.1% / +8.7%, BAC +3.0% / +8.7%, AVGO +5.3% / +5.5%, NVDA +4.7% / +5.5%.
  - **Volatility outliers unchanged and still not park triggers:** **MU ATR 9.02% at $868.52/share** (sizing still pinned at qty 1 — an engine-owned structural inefficiency, not a watchlist defect), AMD 7.63%, INTC 7.42%. Everything else 1.17%–4.59%; SPY tightest at 1.17%.
  - **Liquidity is healthy across the entire active list.** Thinnest is **ABNB at ~$540M/day**; every other name is ≥$1.8B/day. Deepest: MU $38.8B, SPY $34.7B, QQQ $28.6B, NVDA $26.1B. **Nothing on this list is anywhere near an illiquidity threshold** — liquidity is not what is wrong with this bot.
- **GOOGL — the one pre-registered trigger that moved, and the reason for today's single change.** It fell **−3.84% on 08-11 to $343.80** on a day the Nasdaq fell 0.60% — roughly six times the index move — and **closed below its 50-day MA (−3.19%)**, having been *+2.4% above it* yesterday. 5-day **−8.96%**. The catalyst is verified, company-specific and structural, not a tape wobble: **Demis Hassabis stepped down as Google DeepMind CEO and Jeff Dean left to start a new venture**, deepening the AI-leadership exodus this log has tracked as an overhang since 08-06; stacked on a capex guide raised to **$195–205B** (Q2 capex +100% y/y to $44.9B, free cash flow negative for the first time), a **$25B senior-notes offering closed 08-10** plus a $40B ATM equity program, and appellate action seeking to overturn the search-monopoly remedies.
  **Honest reading of the trigger: it fired on price and NOT on volume.** Volume was **29.26M vs a 20-day average of 32.87M = 0.89×** — below average, so the "elevated volume" leg genuinely fails, and I am not going to pretend otherwise. *(GOOG is the same: −3.61%, 0.86× volume.)* **The park below therefore does NOT rest on the trigger.** What the price break did is exactly what the 08-07 and 08-11 entries pre-registered it would do: *"if it breaks, the GOOG/GOOGL double-listing becomes a real decision rather than a theoretical one."* **It broke, so the decision is now live** — and on that decision the evidence is not close (see below).
- **AAPL, UNH, META, MU, TSLA, TSM, QCOM, AMD — all held.** AAPL's trigger half-fired and is recorded above. UNH stays on the fader watch (below both MAs, all-time 2W/6 −$185.47, no trade since 07-22) — parking it would be parking on quietness, which the SE precedent forbids; the background managed-care headline (a report that the administration may scrap subsidies on certain Medicare plans) is directional and multi-week, not a today-binary. META has actually improved (now **+0.14% above its 50MA**, 5d +1.9%) despite being the worst post-gate name. MU/AMD/INTC/NVDA are all in today's SMCI-driven semi bid.
- **Adds: none.** Six independent reasons, any one of which is sufficient. (1) **The −25% review flag has TRIPPED** and the standing instruction from the 08-11 daily review is explicit: *do not add names, do not manufacture activity*. Adding exposure on the morning after the flag trips would be the exact opposite of the required posture. (2) **CPI prints at 08:30 ET with a September HIKE ~52% priced, and this routine cannot see it** — adding names hours before a binary I am blind to is indefensible. (3) **IMP-031 ships live today with n=1 worked example (NFLX)**; changing watchlist composition on its first live session corrupts the attribution, exactly as IMP-029/IMP-030 pre-registered. (4) **Today's real momentum is day-one post-earnings gap momentum** — SMCI +9.5%, CRWV +18% — the single worst fit for a strategy whose VWAP gate exists to refuse stretched gap-chases; ABNB's +23.4% five-day extension and 20 vetoes yesterday are the live demonstration. (5) **Sector coverage is complete at 23 names** against a 3-position concurrency cap: mega-cap tech, semis (5), banks, staples, retail, healthcare, energy, streaming, software, two index ETFs. (6) **The problem is not the watchlist.** All-time the book is 232 trades at 38.4% win, −$2,221.73, PF 0.60, six entry discriminators refuted; **no symbol I could add fixes an entry signal with no demonstrated edge.** Adding names to a book with no edge just buys more of the same distribution.

### Changes applied to watchlist
- **GOOGL: PARKED 2026-08-12** (`is_active = 0`, row **kept**, dated note written; note length asserted at **217 chars** before the write, inside the 255 limit; verified **0 open positions** immediately before the UPDATE, so GOOGL was **not locked**). The case does not rest on the half-fired chart trigger — it rests on three independent legs:
  1. **It is a redundant double-listing, and the redundancy is now costly.** GOOG and GOOGL are the same company, the same bet and the same catalyst, held in a book with **only 3 concurrent slots** that has spent every slot inside the first ten minutes on **three consecutive sessions**. QQQ+SPY already demonstrated on 08-10 what one bet held twice does to this book: two slots frozen for 6.4 hours. Alphabet exposure is **fully retained via GOOG** — this removes a duplicate, not a sector.
  2. **If exactly one Alphabet listing is kept, the record says which one, and it is not close.** **GOOGL: 3W/10, −$326.85 all-time — the worst-performing active name on the entire board.** **GOOG: 4W/8, +$30.89 all-time, and +$25.90 post-gate (1W/1).** Same underlying, opposite records, across 18 combined trades. Keeping the losing listing and trading the winning one is a free choice the bot has simply never made.
  3. **The chart corroborates rather than carries the decision.** Closed below the 50MA (−3.19%) after −3.84% on 08-11 — ~6× the Nasdaq's move — on a verified, company-specific, multi-week structural catalyst (DeepMind leadership exodus + negative FCF + $25B debt + appellate risk), 5d −8.96%. **Volume was 0.89× average, so the pre-registered "close below the 50MA on elevated volume" trigger did NOT fully fire, and this is recorded as a deliberate departure from a strictly literal trigger read, not an oversight.** The pre-registered consequence of the *price* break — *"the double-listing becomes a real decision"* — did fire, and legs 1 and 2 decide it.
  *This reduces exposure on the morning after the −25% flag tripped; it does not widen risk, manufacture activity, or spend a slot. The row is retained and re-enablable by any future run.*
- **No adds. No re-enables. Everything else held.** Parked rows now: BABA, BIRD, C, ENPH, **GOOGL**, JPM, SE, WPM (8 inactive).

### Final watchlist
**23 active** (−1 vs 24: GOOGL parked; no adds; within the 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM GOOG INTC META MSFT MU NFLX NVDA QCOM QQQ SPY TSLA TSM UNH WMT XOM
Service restarted: **yes** — `systemctl is-active` → **active**, MainPID 724083, **NRestarts=0**, ActiveEnterTimestamp **11:50:49 UTC**. `/var/log/ustradewisbot/bot.log` shows a clean **`USTradeWisBot starting (dry_run=False)` at 07:50:52 EDT** followed by `market closed — sleeping ~5936s until next open` — correct for a 09:30 ET open. **0 errors, 0 tracebacks since boot.** The bot's own `get_active_watchlist()` reads back all **23** symbols and no longer contains GOOGL. *(journald holds only systemd lifecycle lines; startup is verified in `bot.log` per IMP-024.)*

### Notes for pre-market research (next session — Thu 08-13)
- **⚠️⚠️ THE −25% FLAG IS TRIPPED, NOT PENDING. Equity $7,482.47 (−25.18%).** State Wednesday's close at the top and say whether it is above or below $7,500. Until a human rules on the formal strategy review, the posture is unchanged: **do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols to get back to flat.** There is no cushion left to spend.
- **Record what July CPI actually printed and how the tape took it** — this routine ran 44 minutes before the release and could not see it. Note the number, the reaction, and whether September-hike odds moved off ~52%. **PPI lands Thu 08-13** (so tomorrow's run has its own blind spot 08:30 ET release), **retail sales + UMich Fri 08-14**.
- **Today is IMP-031's first live session** (break-even armed off the highest price *printed*, not the ~60s sample). **NFLX #244 is its worked example** (−$44.55 → $0.00 in replay). If NFLX or any name peaks ≥+0.5R today, check whether the break-even actually armed — that is the one live read the daily review needs.
- **GOOG is now the sole Alphabet listing and inherits the watch.** It closed **−2.95% below its 50MA** on the same news; its record (4W/8, +$30.89) is why it was kept, but it is not immune. **Pre-registered: if GOOG closes below its 50MA on elevated volume AND produces a full-1R fade, Alphabet leaves the list entirely.** Also note **Google's "Made by Google" Pixel 11 / Gemini event was 18:00 EDT on 08-12 — after the close**, so it was never an in-session binary, but Thursday's session digests it.
- **GOOGL is parked, not deleted.** If a future run wants it back, **re-enable the existing row** (`upsert_watchlist_symbol`) — do not re-insert. The bar for re-entry should be a *demonstrated* change: reclaiming the 50MA **and** a reason to prefer it over GOOG, which given identical exposure and a −$357 record gap is a high bar.
- **AAPL's trigger is now HALF-fired and is the closest live one on the board** — closed **−1.50% below its 50MA** (from −0.5%) but on **0.67× volume**. **Check it first tomorrow.** If it closes below the 50MA on genuinely elevated volume, it is a park candidate on the same logic applied to GOOGL today, though **without** the double-listing leg that carried that decision.
- **AMD: five sessions, still zero fills since the 08-06 re-enable, and now the worst 5-day on the list (−8.5%), below both MAs, 2W/8 −$315.09 all-time.** The rule stands — **a park needs a fill** — but this is the second name where "no fill" has run long enough to be worth naming: **pre-register now that if AMD is still fill-less on Mon 08-17 (10 sessions), the routine should ask whether a name that cannot produce a signal in two weeks is earning its place, independent of the fill rule.** That is a question for the weekly, not a unilateral park.
- **QCOM: sixth session, trigger un-fired, 50MA gap narrowing five sessions running (−13.65%).** Do not park on quietness, do not forget it.
- **WMT REPORTS PRE-OPEN THU 08-20.** The 08-19 run must make the one-day event-park decision (the ABNB 08-06 precedent: park the day before, re-enable once resolved). Flagged eight days early so it is not missed.
- **ABNB is still the most extended name on the board (+20.9% / +27.1%, 5d +23.4%) with zero post-gate fills.** Expect vetoes, not trades. **Blocked ≠ park** (SE precedent); only a full-1R fade parks it.
- **⚠️ Sonar is 7-for-7 unreliable and today missed the CPI print** while re-serving yesterday's AAPL downgrade as new. **Treat as an unverified lead only; never let a park or an add rest on it.** Index levels are cheaper and correct from SPY/QQQ daily bars. **Third escalation to the weekly: drop it or demote it below WebSearch.**
- **Strategy posture unchanged and not this routine's to alter:** `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, paper endpoint, no-overnight rules — all untouched. **No bot source code was modified by this routine.** The post-gate book is at **46 closed trades**; exit geometry, concurrency pacing and the never-green time-stop all belong to the daily/weekly review, not here.

---

## 2026-08-13 — Pre-market Research

### Market context
⚠️ **The −25% flag remains TRIPPED as an open escalation, but the account is back ABOVE the line: broker equity $7,512.68, cash $7,512.68, 0 positions, 0 open orders — $12.68 ABOVE the $7,500 review line (−24.87%).** `last_equity` equals `equity`, so nothing moved overnight. *(The 08-12 daily review recorded the close as $7,512.91; the broker now reports $7,512.68 — a $0.23 settlement difference, immaterial, broker figure used here.)* **A $12.68 cushion is not a reprieve and one green day did not resolve anything** — the formal strategy review is a human decision point and stays open. Every decision below is taken under the unchanged conservative posture: **do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols.**
**Futures modestly higher into the second inflation print in two days.** Dow futures **+0.18% (+99 pts)**, **S&P 500 futures +0.14%**, **Nasdaq-100 futures ~flat**. Wednesday 08-12 closed mostly higher on the in-line CPI: **S&P 500 +0.26%, Nasdaq Composite +0.54%, Dow −0.04%**. My own IEX daily bars agree: **SPY 772.54 (+0.26%), QQQ 723.61 (+0.74%)**.
⚠️ **JULY PPI PRINTS TODAY AT 08:30 ET AND THIS ROUTINE RAN AT ~07:45–07:55 ET — I DID NOT SEE THE NUMBER.** Recorded explicitly, as the 08-12 entry required (it had the same blind spot for CPI). Consensus **headline +0.2% m/m** (from June's −0.3%), **y/y easing to ~4.9% from 5.5%**; **core +0.3% m/m**, core y/y ~4.1–4.2% from 4.7%. **Initial jobless claims 202K vs 199K prior** land in the same 08:30 tape. **The asymmetry is unchanged and still unusual: the live debate is a HIKE, not a cut**, so a hot print is risk-off for a long-only intraday book. It is a **pre-open** release → gap risk only; the bot's first entry comes after 09:30 once it is digested and it holds nothing overnight. **No decision below is contingent on a number I could not see.**
**In-session events are thin but non-zero:** **Cleveland Fed's Hammack speaks 08:15 ET** (pre-open; she dissented in July preferring a hike and said this week that *"some number"* of hikes may be needed — hawkish, and the market's September-hike pricing is live), and the **$25B 30-year auction closes the refunding at 13:00 ET** (yield-sensitive, in-session). **Retail sales + UMich land Fri 08-14; FOMC minutes 08-19.**
**Earnings: NOT ONE ACTIVE WATCHLIST NAME REPORTS TODAY.** ~302 reporters, the busiest day of the week; the headliners are **AMAT after the close** and **JD before the open** — **both off-list**. AMAT (fiscal Q3, call 16:30 ET, cons. ~$9.0B rev / $3.36 EPS) is a semi-equipment bellwether that will gap the semi complex **Friday**, not today — worth noting because five on-list names are semis. Verified the nearest on-list print again: **WMT reports Q2 FY27 Thu 2026-08-20 pre-open** — seven days out, not today. No active name has an in-session print, halt, M&A, FDA or legal binary today.
**Pre-market movers are off-list.** Losers: **CSCO −5.9%, Cerebras −17.4%, Coherent −5.1%** (all post-earnings); gainers **LITE** (AI optical) and **SNDK +4%** (AI storage). **Oil is the one sector move that touches the list: Brent −2% to $87.17, WTI −2.2% to $81.41** as the IEA guided 2026 global demand to contract 1.6 mb/d — a **headwind for XOM today**, and a sector tape read, not a name defect.
⚠️ **Sonar: NINTH consecutive unreliable session.** It returned *"no confirmed overnight/pre-market catalyst"* for **22 of the 23** tickers, gave **no futures direction at all** ("no direct futures quote is provided"), quoted a pre-market print for **GOOGL — a symbol parked yesterday and not in the list I sent it** — and hedged on the single dominant scheduled event of the day (*"the exact PPI row is not fully visible"*). Its one useful contribution was naming jobless claims and a Fed speaker, both of which WebSearch then had to pin down properly. **Running record: 08-03 stale, 08-04 inverted, 08-06 empty, 08-07 fabricated+inverted, 08-11am empty, 08-11pm recycled, 08-12am recycled+stale+missed CPI, 08-12pm recycled+INVERTED, 08-13 empty+no-futures+off-list-ticker.** Everything above and below is WebSearch (TheStreet/TipRanks/XTB/Investing/Yahoo/AMAT IR) + Alpaca bars. **Fourth escalation in three days: drop sonar from this routine or demote it below WebSearch.**

### Carried from daily review
Acted on the **2026-08-12** daily review's "Notes for pre-market research". Every named item was checked and **every pre-registered trigger was tested explicitly and reported un-fired or half-fired — none matured.**
- **"Equity $7,512.91, back above the $7,500 line by $12.91 — state it at the top and say above or below"** — **done, above: $7,512.68, ABOVE by $12.68.** Posture honoured to the letter: **no adds, no re-enables, nothing widened, nothing churned.**
- **"Record what July PPI prints Thu 08-13 at 08:30 ET — tomorrow's routine has the same pre-open blind spot"** — **recorded above, including the consensus and the explicit admission that this run could not see it.** The next daily review inherits the actual number.
- **"QCOM — pre-registered trigger: ONE MORE never-green full-1R stop parks it"** — **tested, UN-FIRED, kept.** #249 (08-12) is the second of the two stops that *created* the trigger, not a third; QCOM has not traded since, so no new never-green stop exists. Chart corroborates holding rather than parking: it closed **+0.26%** on the day and its **50MA gap narrowed for a sixth consecutive session (−13.65% → −12.83%)**, with the 20MA gap now essentially closed at **−0.45%**. **Do not park on quietness (SE precedent); do not forget it.**
- **"SPY / QQQ — a structural question for the weekly, not a park. Do not park them unilaterally"** — **honoured, both kept, untouched.** The finding is real (post-gate 6 trades, all six EOD_FLATTEN, net −$7.04, because their 1R sits at the `MIN_STOP_PCT` 1.50% floor while SPY's whole 08-12 range was 0.45%) but it is an **engine sizing/stop-geometry** issue owned by the weekly, and IMP-032 explicitly recorded parking them as *not this routine's action*. SPY's ATR is **1.08%** and QQQ's **1.88%** — the mismatch persists today.
- **"WMT — reports pre-open Thu 08-20; that is the 08-19 run's one-day event-park decision. Do not read the event risk as a reason to touch it now"** — **honoured, not touched.** WMT was yesterday's best trade (+$49.26, 373/374 green minutes) and is **above both MAs (+3.56% / +1.38%)**. Re-flagged below for 08-19.
- **"BAC quietly continues to be the best name on the board (4W/4 post-gate)"** — **noted, no action needed.** Still above both MAs (+3.98% / +9.54%), tightest ATR on the list after SPY at 1.47%.
- **"AMD is still fill-less (six sessions since the 08-06 re-enable); the pre-registered question stands for Mon 08-17 / 10 sessions, and it is a weekly question, not a unilateral park"** — **honoured, held.** Still zero fills, now below both MAs (−2.34% / −5.64%) with the highest ATR on the list after MU (7.32%). **A park needs a fill — there is nothing to park on.**
- **"Gap-and-fade regime note: the VWAP gate screens extension, not direction, and it did not veto QCOM"** — **carried into today's read.** Yesterday the open was the high on both indexes and the winners were the two names *outside* the gap. Today's futures are only mildly positive into a pre-open PPI, so the same asymmetry is worth expecting; it is an **engine** observation, not a watchlist action.

### Watchlist review
**Account state: equity $7,512.68, ACTIVE, not blocked, `/v2/positions` returns 0 and `/v2/orders?status=open` returns 0 → NO LOCKED SYMBOLS.** Verified before reading the table. Every name was eligible for review; no name required protection from a park.

- **Trade performance.** Last 14 days: **36 closed, net −$64.54, 41.7% win.** Worst: META −$41.02 (1W/3), QCOM −$40.76 (0W/1), NFLX −$34.75, QQQ −$27.24 (0W/2), AMZN −$23.87 (0W/2), TSM −$23.30, COST −$13.44. Best: **INTC +$55.72, BAC +$48.04 (3W/3), NVDA +$25.26 (3W/5), SPY +$20.20, MSFT +$17.54, WMT +$17.42.** All-time: **236 trades, 38.6% win, −$2,191.29, PF 0.61.**
- **Technicals (IEX daily bars through the 08-12 close; last bar date asserted as 2026-08-12 before use).** ⚠️ **Methodology note for future runs: `/v2/stocks/{SYM}/bars` with `start` + `limit` returns the OLDEST bars in the window, not the newest.** A first pass silently produced a table whose last bar was **2026-07-23** — three weeks stale, and it would have read TSLA as −14.6% on the day. Fixed by following `next_page_token` to the end and asserting the last bar date. **Dollar volumes below are IEX-only (a few percent of consolidated tape) and are NOT comparable to the consolidated figures in the 08-12 entry — use them for ranking, not for absolute liquidity thresholds.**
  - **Below both MAs (7):** **AAPL (−5.91% / −2.33%)**, AMD (−2.34% / −5.64%), **GOOG (−1.05% / −2.95%)**, **META (−3.66% / −3.15%)**, QCOM (−0.45% / −12.83%), TSLA (−1.84% / −12.52%), UNH (−2.84% / −2.08%).
  - **Most extended (and correctly drawing VWAP vetoes):** **ABNB +16.5% / +23.0%**, **MSFT +11.8% / +20.0%**, BAC +3.98% / +9.54%, NVDA +7.54% / +8.66%, XOM +3.51% / +8.52%, CRM +6.89% / +12.13%.
  - **Volatility outliers, unchanged and still not park triggers:** **MU ATR 8.61% at $911.30/share** (sizing still pinned at qty 1 — engine-owned structural inefficiency, not a watchlist defect), AMD 7.32%, INTC 7.19%. Everything else 1.08%–4.35%; **SPY tightest at 1.08%**, QQQ 1.88%.
  - **Liquidity is healthy across the whole active list** — every name is a mega- or large-cap trading hundreds of millions to billions a day on consolidated tape. **ABNB is the thinnest by a wide margin** (IEX $35M/day vs $63M for the next name), consistent with the ~$540M consolidated figure recorded on 08-12. **Nothing here is near an illiquidity threshold; liquidity is not what is wrong with this bot.**
- **AAPL — the closest live trigger on the board, tested explicitly: HALF-fired for a SECOND day, NOT actioned.** The pre-registered test is *"closes below the 50MA on genuinely elevated volume."* AAPL closed **$302.20, −2.33% below its 50MA** — deeper than yesterday's −1.50%, and it is now below the 20MA too (−5.91%) — but on **0.91× its 20-day average volume**. **The volume leg fails outright, for the second consecutive session.** Yesterday's entry parked GOOGL *without* a fully-fired trigger, but did so on two legs that AAPL does not have: GOOGL was a **redundant double-listing** of a name held via GOOG, and it was the **worst-performing active name on the board (−$326.85)**. AAPL is neither — it is 2W/5 / −$16.97 post-gate, it is the sole listing of its company, and it was a winner as recently as 08-07. **Kept; the trigger stays exactly as written.**
- **GOOG — inherited the Alphabet watch; its two-leg trigger failed on BOTH legs, held.** The pre-registered test is *"closes below its 50MA on elevated volume **AND** produces a full-1R fade."* It closed **−2.95% below the 50MA** (leg 1 price ✓) but on **0.99× volume** (leg 1 volume ✗), and it **did not trade at all on 08-12**, so there is **no full-1R fade** (leg 2 ✗). It also fell only −0.17% on a day META fell −3.36%. **Un-fired on both legs — Alphabet stays on the list via GOOG alone.**
- **META — a NEW verified catalyst, examined seriously for a park and deliberately NOT parked.** It fell **−3.36% on 08-12 to $579.00**, back **below both MAs (−3.66% / −3.15%)** after the 08-12 entry recorded it as having just reclaimed the 50MA (+0.14%). The catalyst is verified and company-specific: the **29-state children's-data trial opened in Oakland on Wednesday**, with **opening statements 08-18 and a ~7-week run**, alongside BMO calling its AI capex the *"least visible ROI story among peers"*; the stock is down ~20% since 07-15 on the FQ2 EPS miss and a capex guide raised three times to $130–145B. It is also the **worst post-gate name (−$78.94, 1W/4)** and −$41.02 over the last 14 days. **Why it is NOT parked today, stated plainly:** (1) **volume was 0.74× average** — it fails the same elevated-volume standard I just applied to AAPL and GOOG, and applying a looser standard to META than to AAPL on the same morning would be exactly the churn this posture forbids; (2) **there is no pre-registered META trigger to fire** — inventing one post-hoc on a −3.4% day is how overfitting starts; (3) the trial is a **multi-week overhang, not a today-binary** — opening statements are 08-18, and this bot holds nothing overnight; (4) it has **no double-listing leg**, which is what actually carried the GOOGL decision. **Kept — and a trigger is now pre-registered below so the next run does not have to improvise.**
- **ABNB — still the most extended name on the board and still fill-less; kept.** +16.5% / +23.0% vs its MAs, volume 1.49×, the thinnest name on the list, **zero post-gate fills** because the VWAP gate refuses it (20 vetoes on 08-11 alone). **Blocked ≠ park (SE precedent); its trigger remains a full-1R fade if it ever actually trades.**
- **TSLA, UNH, COST, AMZN, NFLX, MU, INTC, TSM, AVGO, CRM, MSFT, NVDA, XOM — all held, no trigger fired on any.** TSLA (−1.84% / −12.52%) and UNH (−2.84% / −2.08%) are below both MAs but neither has a fired trigger and both are liquid mega-caps — **parking them would be parking on quietness, which the SE precedent forbids.** COST and AMZN carry fader watches whose trigger is *the next full-1R STOP fade*; **neither traded on 08-12, so both are un-fired.** MU stays despite ATR 8.61% and qty-1 sizing (engine-owned). **XOM faces a real sector headwind today** — oil −2% on the IEA demand cut — but it is **above both MAs (+3.51% / +8.52%)** and a one-day sector tape is not a name defect.
- **Adds: none.** (1) **The −25% escalation is open** and the standing instruction from both the 08-11 and 08-12 daily reviews is explicit: *do not add names, do not manufacture activity*. A $12.68 cushion does not change that. (2) **PPI prints at 08:30 ET with a September HIKE live and this routine cannot see it** — adding exposure hours before a binary I am blind to is indefensible. (3) **Today's real momentum is day-one post-earnings gap momentum** (LITE, SNDK up; CSCO, Cerebras, Coherent down) — the single worst fit for a strategy whose VWAP gate exists to refuse stretched gap-chases. (4) **Sector coverage is already complete at 23 names** against a **3-position concurrency cap**: mega-cap tech, semis (5), banks, staples, retail, healthcare, energy, streaming, software, two index ETFs. The binding constraint is slots, not candidates. (5) **The problem is not the watchlist.** 236 trades, 38.6% win, PF 0.61, six entry discriminators refuted, the breakout premise disproven and banned, and — per the 08-12 review — **not one of the last session's four trades was even a breakout**. No symbol I could add fixes an entry signal with no demonstrated edge; adding names just buys more of the same distribution.
- **Re-enables: none.** BABA, BIRD, C, ENPH, GOOGL, JPM, SE, WPM all stay parked. The posture forbids re-enabling to get back to flat, and **GOOGL specifically requires a demonstrated change** — reclaiming its 50MA *and* a reason to prefer it over GOOG — which has not happened one session later.

### Changes applied to watchlist
**NO CHANGES. Zero adds, zero parks, zero re-enables — the `watchlist` table was not written to at all.**
This is a deliberate decision, not an idle run. **Eight pre-registered triggers were tested by name and all eight came back un-fired or half-fired:** AAPL (half — price ✓, volume ✗ at 0.91×), GOOG (both legs ✗), QCOM (no new never-green stop), COST (no trade), AMZN (no trade), ABNB (no trade), AMD (no fill — a park needs a fill), WMT (event is 08-20, decision belongs to the 08-19 run). SPY/QQQ are explicitly not this routine's to park. The one genuinely new development — **META's trial opening** — was examined against the same evidentiary bar I applied to AAPL and GOOG this morning and **failed it on volume**, so it was recorded and pre-registered rather than acted on.
**"No changes" is the correct outcome when nothing has changed, and the standing posture after the −25% flag makes churn actively harmful.** Parked rows remain 8: BABA, BIRD, C, ENPH, GOOGL, JPM, SE, WPM.

### Final watchlist
**23 active** (unchanged from 08-12; within the 30 cap):
AAPL ABNB AMD AMZN AVGO BAC COST CRM GOOG INTC META MSFT MU NFLX NVDA QCOM QQQ SPY TSLA TSM UNH WMT XOM
**Service restarted: NO — and deliberately so.** The routine's rule is to restart *if and only if* something changed; nothing did, so a restart would have been pure risk with no benefit. The running process already holds the correct list: it was restarted at **21:43:32 UTC on 08-12** by the daily-review routine, which is **after** that morning's 11:50 UTC GOOGL park, so the live watchlist and the DB agree at 23 symbols. Verified healthy this morning: `systemctl is-active` → **active**, **MainPID 770285**, **NRestarts=0**, and `/var/log/ustradewisbot/bot.log` shows a clean `USTradeWisBot starting (dry_run=False)` at 17:43:33 EDT followed by hourly `market closed — sleeping` lines through 07:43:39 EDT, with **0 errors and 0 tracebacks since boot**.

### Notes for pre-market research (next session — Fri 08-14)
- **Equity $7,512.68 (−24.87%), $12.68 above the $7,500 line. State Thursday's close at the top and say whether it is above or below.** The −25% escalation is **open regardless of which side of the line the account sits on** — it is a human decision point. Posture unchanged: **do not widen risk, do not add names, do not manufacture activity, do not re-enable parked symbols.** There is effectively no cushion.
- **Record what July PPI actually printed and how the tape took it** — this run went 40 minutes before the release. Note the number against the **+0.2% m/m headline / +0.3% m/m core** consensus, whether the y/y fell to ~4.9% from 5.5%, and whether September-hike odds moved. **Retail sales + UMich land Fri 08-14 at 08:30 — tomorrow's run has its own blind spot.** FOMC minutes 08-19.
- **AMAT reported after the close tonight** (fiscal Q3, cons. ~$9.0B / $3.36 EPS, ~108% YTD but ~28% off its June high). It is **off-list but it gaps the semi complex on Friday**, and **five on-list names are semis** (AMD, INTC, MU, NVDA, QCOM, plus TSM/AVGO adjacent). **Check its reaction first tomorrow** — a sympathy gap is a *regime* input for the VWAP gate, not a reason to touch any name.
- **META — trigger now PRE-REGISTERED so the next run does not improvise.** The 29-state children's-data trial opened 08-12 in Oakland; **opening statements are Tue 08-18** and it runs ~7 weeks. META is below both MAs (−3.66% / −3.15%), the worst post-gate name (1W/4, −$78.94), and −20% since 07-15. **Trigger: a close below the 50MA on genuinely elevated volume (≥1.3×) OR a full-1R fade while the trial is live parks META.** It was NOT parked today because volume was 0.74× and the trial is a multi-week overhang rather than a today-binary — but 08-18 is a scheduled escalation and the 08-17 run should look at it before the statements land.
- **AAPL's trigger is HALF-fired for a second straight session and is still the closest live one on the board** — closed **−2.33% below the 50MA** (deepening from −1.50%) and now below the 20MA as well (−5.91%), but on **0.91× volume**. **Check it first tomorrow.** If it closes below the 50MA on genuinely elevated volume, it is a park candidate — **without** the double-listing leg that carried GOOGL.
- **QCOM: seventh session, trigger un-fired, and the chart is quietly healing** — the 50MA gap has narrowed **six sessions running (−13.65% → −12.83%)** and the 20MA gap is nearly closed (−0.45%). Its trigger is still **one more never-green full-1R stop**. Do not park on quietness, do not forget it.
- **AMD: still zero fills since the 08-06 re-enable.** **Mon 08-17 is the pre-registered 10-session mark** where the routine asks whether a name that cannot produce a signal in two weeks earns its place. **That is a weekly question, not a unilateral park**, and the rule that a park needs a fill still stands.
- **WMT REPORTS PRE-OPEN THU 08-20 — the 08-19 run owns the one-day event-park decision** (ABNB 08-06 precedent: park the day before, re-enable once resolved). Flagged seven days out so it is not missed. It is above both MAs and was the best trade of the incubation on 08-12; **do not touch it before 08-19.**
- **⚠️ METHODOLOGY BUG worth inheriting: Alpaca's `/v2/stocks/{SYM}/bars` with `start` + `limit` returns the OLDEST bars in the window.** This run's first technicals pass silently produced a table whose newest bar was **2026-07-23** — three weeks stale — which would have read TSLA as −14.6% on the day and flipped the MA verdict on roughly half the list. **Always follow `next_page_token` to the end and assert the last bar date equals the prior session before using any technical number.** Also: IEX dollar volumes are a few percent of consolidated tape — rank with them, never threshold with them.
- **⚠️ Sonar is now 9-for-9 unreliable**: 22 of 23 tickers "no catalyst", **no futures direction at all**, and it volunteered a pre-market quote for **GOOGL — parked yesterday and not in the list I sent it**. **Treat as an unverified lead only; never let a park or an add rest on it. Fourth escalation in three days: drop it or demote it below WebSearch.**
- **Strategy posture unchanged and not this routine's to alter:** `MAX_RISK_PCT` 2.0, `DAILY_LOSS_HALT_PCT` 8.0, `MAX_CONCURRENT_POSITIONS` 3, `ENTRY_CUTOFF_ET` 15:30, `FLATTEN_ET` 15:55, paper endpoint, no-overnight rules — **all untouched. No bot source code was modified by this routine and the `watchlist` table was not written to.** Exit geometry, concurrency pacing and the SPY/QQQ stop-floor mismatch all belong to the daily/weekly review, not here. **Note for whoever owns it: IMP-031's live code is still uncommitted in the working tree — a `git checkout` or redeploy silently reverts it.**
