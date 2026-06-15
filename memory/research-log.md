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

### Notes for pre-market research (next session)
- Watch MU, AMD, JPM, C closely — four consecutive losses each with 0% win rate; if these persist into next week, park them and reduce symbol count further.
- WPM: if still generating zero signals by Jun 20, park it (precious metals proxy, doesn't fit strategy).
- GOOGL: watch for at least 1 win in next 5 trades; if trend continues (0W 4+L) consider parking and consolidating to GOOG only.
- FOMC decision Jun 17 2PM ET — expect choppy tape Wed afternoon; do not add new symbols until after Warsh press conference digested.
- Account equity at $8,205 (−18% from $10K start) — if drawdown reaches −25% ($7,500), flag for strategy review.

---
