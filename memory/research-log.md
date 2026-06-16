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
