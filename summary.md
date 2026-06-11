# US Intraday Stock Trading Bot — Project Summary

> **Purpose of this file:** the single source of truth for *what* we are building and *why* the logic works the way it does. Read this first in any Claude Code session before touching `todo.md`. `todo.md` is the step-by-step build checklist; this file is the design.

---

## 1. Goal

An automated bot that trades **US stocks intraday** (same-day only — every position is opened and closed within one trading day). It:

1. Watches a list of US stocks stored in the database.
2. Looks for **resistance breakouts** and **triple moving-average alignment** as buy signals.
3. Scores each opportunity with a **0–100 confidence level** and risks **more money when confidence is higher** (within a hard cap).
4. Places orders through **Alpaca** (paper trading first), with an automatic stop-loss and take-profit on every trade.
5. **Closes everything before the market closes** — no overnight holds.
6. Logs every trade, the *reason* for it, and a **daily profit/loss summary** to **SQL Server**.
7. Sends **Telegram alerts** for entries, exits, and the daily summary.
8. Runs continuously on a **VPS**.

---

## 2. Core principles & guardrails

These are not optional. They are baked into the design on purpose.

- **Paper trading first.** The bot connects to Alpaca's *paper* endpoint (`https://paper-api.alpaca.markets`) until we have weeks of results we trust. Live money is a later, deliberate switch — one config flag, not a rewrite.
- **No overnight positions.** This is same-day trading. Two time rules near the 4:00 PM ET close:
  - **No new entries after 15:30 ET** — not enough time left for a trade to work.
  - **Force-flatten all positions at 15:55 ET** — sell everything still open, win or lose. This avoids *overnight gap risk* (when the market is closed, your stop can't protect you; bad news can gap the stock far below your stop before you can react) and keeps each day's P&L clean.
- **Secrets never go in the database.** API keys and the Telegram token live in a `.env` file (loaded with python-dotenv), gitignored, and `chmod 600` on the VPS. *Everything else* — trades, signals, P&L, watchlist — goes in SQL Server as planned. (Plaintext keys in a DB means anyone who reads the table, a backup, or a leaked connection string can drain or trade the account. The safe option costs ~15 minutes.)
- **Risk is capped per trade.** Confidence scales position size, but **no single trade ever risks more than 2% of account equity**, regardless of what the confidence formula says.
- **Realistic expectations.** Intraday breakout edges are real but fragile, and paper results *overstate* live performance (no slippage, perfect fills). The bot logs everything so paper-vs-live can be compared later. This is an engineering project, not a money-printing guarantee.

---

## 3. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Broker / execution | Alpaca (`alpaca-py` SDK) — paper first |
| Market data | Alpaca Market Data API (start on free **IEX** feed; see §10 on its limits) |
| Database | **Microsoft SQL Server** (inspected via SSMS), accessed from Python via **pyodbc** + `ODBC Driver 18 for SQL Server` |
| Indicators | `pandas`, `numpy`, `scipy` (and optionally `pandas-ta` / `TA-Lib`) |
| Alerts | Telegram Bot API via `python-telegram-bot` |
| Config / secrets | `python-dotenv` + `.env` (never committed) |
| Scheduling | Internal main loop + `systemd` service on the VPS |
| Process mgmt (VPS) | `systemd` with `Restart=on-failure` |

---

## 4. High-level architecture

Seven modules, each independently testable. Data flows top to bottom:

```
┌─────────────────────────────────────────────────────────────┐
│ SCHEDULER / MAIN LOOP                                         │
│ • is market open? • respect 15:30 entry cutoff & 15:55 flat   │
└───────────────┬───────────────────────────────────────────────┘
                │ every N seconds during RTH
                ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. DATA INGESTION                                             │
│    pull OHLCV bars (e.g. 5-min) for each watchlist symbol     │
└───────────────┬───────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SIGNAL / STRATEGY ENGINE                                   │
│    S/R levels • breakout check • triple-EMA • regime filter   │
│    • overextension check  →  component scores                 │
└───────────────┬───────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CONFIDENCE + RISK / POSITION SIZING                        │
│    fuse scores → 0–100 confidence → shares to buy (capped)    │
└───────────────┬───────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ORDER EXECUTION                                            │
│    bracket order: entry + stop-loss + take-profit (paper)     │
└───────────────┬───────────────────────────────────────────────┘
                ▼
┌──────────────────────┐        ┌──────────────────────────────┐
│ 5. DATABASE LOGGING  │◀──────▶│ 6. TELEGRAM ALERTING          │
│ trades / signals /   │        │ entry, exit, daily summary,   │
│ daily P&L            │        │ errors, heartbeat             │
└──────────────────────┘        └──────────────────────────────┘
```

Plus a separate **exit manager** that runs each loop to update filled exits, manage any trailing logic, and perform the end-of-day flatten.

---

## 5. Trading strategy & logic (the core)

This section is the heart of the project. The buy decision is a **funnel**: a stock must pass a trend filter, then trigger on a breakout and/or MA alignment, then survive an over-extension check. The surviving signals are fused into a confidence score that decides *whether* to buy and *how much*.

### 5.1 Universe / watchlist
The bot only analyzes symbols in the `watchlist` table (see §6). Keep it focused (e.g. 20–50 liquid, high-volume US stocks). Liquidity matters — breakouts on thin stocks are noisy and hard to fill.

### 5.2 Indicators computed per symbol, per bar
- **EMAs** — two sets:
  - **Short set: 8 / 10 / 20** (entry timing)
  - **Long set: 21 / 34 / 55** (trend / regime — these are Fibonacci numbers commonly used in EMA ribbons)
- **ATR (14)** — volatility, used for stops and position sizing.
- **RSI (14)** — momentum / overbought check.
- **ADX (14)** — trend strength (regime filter).
- **Relative volume** — current bar volume vs the 20-bar average volume.

We use **EMA, not SMA**, because EMA reacts faster — better for intraday.

### 5.3 Support & resistance detection
Detect levels from recent OHLCV using **swing pivots** (a.k.a. Williams fractals):
- A bar is a **resistance pivot** if its high is higher than the highs of `n` bars on each side (start with `n = 3` on 5-min bars).
- A bar is a **support pivot** the mirror way (lowest low).
- **Cluster** nearby pivots into single levels (merge pivots within a small % band, e.g. via simple grouping or `scipy`/agglomerative clustering) so you get a handful of clean levels, not dozens.
- A level is **stronger** the more times price has touched it (track touch count).
- (Optional later: add **volume profile** — high-volume nodes / point of control — which tend to be the most reliable S/R zones.)

> Pivots only confirm after `n` bars complete, so they are a *confirmation* tool, not a predictor. That's fine — we want confirmed levels.

### 5.4 Breakout logic + confirmation (anti-fakeout)
A resistance breakout counts as a buy trigger **only if all of these hold** (false breakouts are common — the filters are the strategy):
1. **Candle CLOSE above the level**, not just an intrabar wick touch.
2. **Buffer**: close is above the level by at least a small margin (e.g. `0.1%` or `0.25 × ATR`) to filter noise.
3. **Volume confirmation**: relative volume ≥ ~1.3× the 20-bar average.
4. **(Optional) prior-touch validity**: the level was tested ≥ 2 times before breaking.
5. **(Optional) retest**: price pulls back to the broken level and holds before entry. *Tradeoff:* a retest filter cuts false entries but misses fast movers. Start without it; add it if the fakeout rate is high.

→ produces a **`breakout_score`** (0–1): strength based on how cleanly conditions 1–4 are met.

### 5.5 Triple moving-average logic
We use **both** EMA sets, each with a job:

- **Long set (21/34/55) = trend / regime gate.** Bullish when **21 > 34 > 55** ("stacked") and ideally sloping up. If not bullish, the stock is not in an uptrend → suppress buys or heavily penalize confidence.
- **Short set (8/10/20) = entry trigger.** A buy signal forms when **8 > 10 > 20** (stacked), preferably with the EMAs *fanning apart* (separation widening) and sloping up — that indicates a strong, accelerating move. Converging EMAs = chop, weak signal.

Signal strength uses two ideas:
- **Slope** — are the EMAs rising?
- **Separation** — is the gap between them widening (strong) or shrinking (weak)?

→ produces an **`ma_score`** (0–1). The discrete rule: fully stacked + rising + separating = high; partially stacked = medium; not stacked = 0.

*(Config note: which set drives entry vs trend is configurable. Default = long set gates, short set triggers.)*

### 5.6 Over-extension / "is it good value or already overpriced?" check
This is the user's "nice to have vs already overprice" question. Even a clean breakout is a bad entry if the stock has already run too far. Penalize chasing:
- **Distance from the 20-EMA in ATR multiples.** Near the EMA = good value. Far above (e.g. > 2–3× ATR above) = overextended → penalize. Very far (e.g. > 4× ATR) = essentially a profit-taking zone, don't enter.
- **RSI** > 70 = overbought → penalize (but note: in strong trends RSI can *stay* overbought, so this lowers the score rather than vetoing outright).
- **Aberrant range** — if the day's range is already far beyond normal (e.g. > 1.75× the 20-day average range), the easy move is likely done.

→ produces a **`value_score`** (0–1, where 1 = great value / not extended, 0 = badly overextended).

### 5.7 Regime filter
Before any of the above earns a buy, require a healthy trend:
- **ADX ≥ 20** (there is a real trend, not chop), and/or
- Long EMA set stacked bullish (21 > 34 > 55).

Range-bound, low-ADX conditions are where breakout + MA strategies whipsaw and bleed money. When the regime is weak, the bot stays flat.

### 5.8 Confidence score (0–100)
Fuse the component scores into one number. Default weighting (tune later, but keep it theory-driven — every tuned weight is an overfitting risk):

```
confidence = 100 * (
    0.35 * breakout_score   +   # did it break resistance, cleanly + volume?
    0.30 * ma_score         +   # is the short EMA set stacked & accelerating?
    0.20 * value_score      +   # is it good value vs overextended?
    0.15 * momentum_score       # RSI/MACD supportive?
) * regime_multiplier           # 1.0 if regime healthy, e.g. 0.5 or 0 if not
```

The DB records **which signals fired** (breakout only / MA only / both) and the **component sub-scores**, so every trade is explainable after the fact.

A trade is only taken when **confidence ≥ `MIN_CONFIDENCE`** (start at 60).

### 5.9 Position sizing — "more confidence = more money" (done safely)
Two ideas combined: **risk a fixed fraction of equity per trade**, and **scale that fraction by confidence**, under a hard cap.

**Step 1 — pick the risk fraction from confidence:**

| Confidence | Risk per trade (% of equity) |
|---|---|
| < 60 | no trade |
| 60–69 | 0.5% |
| 70–79 | 1.0% |
| 80–89 | 1.5% |
| 90–100 | 2.0% (**hard cap — never exceeded**) |

**Step 2 — convert risk into share count using the stop distance:**

```
stop_distance_per_share = ATR * ATR_STOP_MULT        # e.g. 1.0 * ATR (intraday)
dollar_risk             = equity * risk_fraction      # from the table above
shares                  = floor(dollar_risk / stop_distance_per_share)
```

This means a *tighter* stop (low ATR) allows more shares for the same dollar risk, and a *wider* stop fewer shares — risk stays constant in dollars. Higher confidence → bigger `risk_fraction` → more dollars at risk → bigger position, but **capped at 2%**.

> Why not just "spend more money" directly? Because position *value* isn't the risk — the distance to your stop is. Sizing by risk keeps a string of losses survivable. (For the curious: this is fixed-fractional sizing; an aggressive trader might layer fractional-Kelly on top, but never full Kelly — it produces 50–80% drawdowns. Stick with the capped table above.)

Also respect: never let total exposure or correlated positions blow past sane limits (several correlated longs = one concentrated bet). Add a max-concurrent-positions limit (e.g. 3–5).

### 5.10 Entry execution — bracket orders
Every entry is submitted as a **bracket order** through Alpaca, which attaches both exits atomically:
- **Entry**: market or limit buy for the sized share count.
- **Take-profit** leg: limit at `entry + (ATR * ATR_STOP_MULT * RR)` where `RR` (reward:risk) starts at **2.0**.
- **Stop-loss** leg: stop at `entry - (ATR * ATR_STOP_MULT)`.

When one exit fills, the other cancels automatically (OCO). So even if the bot crashes, the position has a server-side stop.

> Note: Alpaca does **not** yet allow a *trailing* stop as the stop leg of a bracket. If we want trailing, the exit manager handles it separately (start with fixed bracket; add trailing later).

### 5.11 Exit logic + end-of-day flatten
- During the day, the bracket's stop/target manage exits automatically.
- The **exit manager** each loop: checks for filled exits, updates the trade record (exit price, realized P&L, P&L %), and (optionally later) ratchets a trailing stop.
- **15:30 ET**: stop generating new entries.
- **15:55 ET**: **flatten** — cancel open orders and market-sell every remaining position. Nothing is held overnight.
- After the close: compute and write the **daily summary** row, send the Telegram daily recap.

---

## 6. Database schema (SQL Server)

Four core tables. Use **parameterized queries everywhere** (`?` placeholders via pyodbc) — never string-format SQL.

### `watchlist` — the US stocks the bot may analyze (the "1 table" of analyzable stocks)
| column | type | notes |
|---|---|---|
| symbol | VARCHAR(10) PK | e.g. 'AAPL' |
| name | NVARCHAR(100) | company name |
| is_active | BIT | only active rows are analyzed |
| added_at | DATETIME2 | |
| notes | NVARCHAR(255) | optional |

### `trades` — one row per trade (buy→sell round trip)
| column | type | notes |
|---|---|---|
| trade_id | BIGINT IDENTITY PK | |
| symbol | VARCHAR(10) | FK → watchlist |
| side | VARCHAR(4) | 'BUY' (long-only for now) |
| qty | INT | shares |
| entry_price | DECIMAL(12,4) | |
| entry_time | DATETIME2 | |
| stop_price | DECIMAL(12,4) | |
| take_profit_price | DECIMAL(12,4) | |
| exit_price | DECIMAL(12,4) NULL | filled on exit |
| exit_time | DATETIME2 NULL | |
| realized_pl | DECIMAL(12,4) NULL | dollars |
| realized_pl_pct | DECIMAL(8,4) NULL | percent |
| status | VARCHAR(12) | 'OPEN' / 'CLOSED' / 'CANCELLED' |
| exit_reason | VARCHAR(20) NULL | 'TAKE_PROFIT' / 'STOP' / 'EOD_FLATTEN' |
| alpaca_order_id | VARCHAR(64) | broker order id |

### `signals` — WHY each trade was taken (the explainability table)
| column | type | notes |
|---|---|---|
| signal_id | BIGINT IDENTITY PK | |
| trade_id | BIGINT NULL | FK → trades (null if signal didn't become a trade) |
| symbol | VARCHAR(10) | |
| ts | DATETIME2 | when evaluated |
| signal_type | VARCHAR(10) | 'BREAKOUT' / 'MA' / 'BOTH' |
| confidence | DECIMAL(5,2) | 0–100 |
| breakout_score | DECIMAL(5,4) | component |
| ma_score | DECIMAL(5,4) | component |
| value_score | DECIMAL(5,4) | component (over-extension) |
| momentum_score | DECIMAL(5,4) | component |
| regime_ok | BIT | passed regime filter? |
| broke_level | DECIMAL(12,4) NULL | the resistance level broken |

### `daily_summary` — per-day P&L recap (what was bought/sold and profit/loss %)
| column | type | notes |
|---|---|---|
| trade_date | DATE PK | |
| num_buys | INT | trades opened |
| num_sells | INT | trades closed |
| wins | INT | |
| losses | INT | |
| gross_pl | DECIMAL(14,4) | dollars |
| realized_pl_pct | DECIMAL(8,4) | day's return % on equity |
| equity_open | DECIMAL(14,4) | |
| equity_close | DECIMAL(14,4) | |
| symbols_traded | NVARCHAR(255) | comma list, optional |

*Optional later:* a `bars` cache table and a `bot_log`/heartbeat table for ops.

---

## 7. Secrets & configuration

- **`.env`** (gitignored, `chmod 600` on the VPS) holds:
  ```
  ALPACA_API_KEY=...
  ALPACA_SECRET_KEY=...
  ALPACA_PAPER=true
  TELEGRAM_BOT_TOKEN=...
  TELEGRAM_CHAT_ID=...
  DB_SERVER=...
  DB_NAME=...
  DB_USER=...
  DB_PASSWORD=...
  ```
- Commit a **`.env.example`** with empty values as documentation.
- A `config.py` (committed) holds **non-secret tunables**: EMA periods, ATR multiplier, RR ratio, MIN_CONFIDENCE, confidence→risk table, entry cutoff / flatten times, max concurrent positions, bar timeframe, poll interval.
- Load secrets with `load_dotenv()` + `os.getenv()`, and **fail fast** if a required secret is missing.

---

## 8. Telegram alerts

- Create the bot via **@BotFather** → get `TELEGRAM_BOT_TOKEN`; get `TELEGRAM_CHAT_ID` from `getUpdates` or @userinfobot.
- Send via `python-telegram-bot` (or a plain `requests` POST to `sendMessage`).
- **Entry alert** contains: symbol, BUY, qty, entry price, confidence + which signals fired, stop & take-profit levels, time.
- **Exit alert**: symbol, exit price, realized P&L and %, reason (target/stop/EOD).
- **Daily summary**: buys/sells, win/loss count, day P&L %, equity close.
- Also: **error alerts** (exceptions) and a **heartbeat** (e.g. "bot started", "market open").

---

## 9. Deployment (VPS)

- Small Linux VPS (e.g. Ubuntu 22.04, 2 GB RAM; a US/NY region reduces latency to US markets).
- Run as a **systemd service** with `Restart=on-failure` and `EnvironmentFile=/path/.env` (do *not* inline secrets in the unit file).
- SSH key auth only; firewall (UFW) deny inbound except SSH.
- Structured logging to a file + the `bot_log` table; add uptime/heartbeat monitoring (e.g. UptimeRobot pinging a heartbeat, or alert if no Telegram heartbeat).
- Confirm the server clock / timezone handling so the 15:30 / 15:55 **ET** rules fire correctly (store/compare in ET explicitly).

---

## 10. Important reality checks & risks

Encode these into expectations, not just code:

- **Free IEX data is ~2% of total market volume.** This directly weakens the volume-confirmation filter (our main anti-fakeout tool) and can mis-place S/R levels. Options: (a) subscribe to Alpaca **SIP** (Algo Trader Plus, ~$99/mo — *verify current price*) for full-volume data, or (b) lean more on price-action confirmation and treat IEX volume as a rough proxy. Decide before trusting volume spikes.
- **Paper fills are optimistic.** No slippage, perfect fills, no market impact — and slippage is worst exactly on fast breakout moves, i.e. correlated with our best signals. Real results will be worse than paper. Log both to measure the gap.
- **Breakout edges are fragile.** Credible research (Zarattini & Aziz, ORB studies) shows strong returns, but they rely on leverage, shorting, careful name-selection, and idealized execution that retail can't fully reproduce. Trading *all* eligible stocks rather than the right ones can drop the Sharpe below buy-and-hold. Keep filters strict and expectations modest.
- **Overfitting is the silent killer.** This system has many knobs (EMA periods, ATR mult, RR, weights, thresholds). Keep tuned parameters few, validate out-of-sample / walk-forward, prefer parameter *ranges* that work over single "best" values. The base rate is humbling: across large studies, well under 1% of day traders reliably beat fees over time.
- **PDT rule (2026 change):** FINRA **eliminated** the $25,000 Pattern Day Trader minimum effective **June 4, 2026**, and Alpaca is **removing the PDT API fields** (`pattern_day_trader`, `daytrade_count`, `daytrading_buying_power`) by **~July 6, 2026**. → **Base position sizing on `buying_power`, not the deprecated PDT fields.** Re-confirm Alpaca's current margin/account behavior at build time.

---

## 11. Key parameters (quick reference — all live in `config.py`)

| Parameter | Default | Meaning |
|---|---|---|
| `BAR_TIMEFRAME` | 5Min | candle size for signals |
| `POLL_INTERVAL_SEC` | 60 | how often the loop runs during RTH |
| `EMA_SHORT` | [8, 10, 20] | entry-trigger EMA set |
| `EMA_LONG` | [21, 34, 55] | trend/regime EMA set |
| `ATR_PERIOD` | 14 | |
| `ATR_STOP_MULT` | 1.0 | stop distance = ATR × this (intraday ≈ 0.6–1.0) |
| `RR_RATIO` | 2.0 | take-profit = stop distance × this |
| `PIVOT_LOOKBACK` | 3 | bars each side for swing-pivot S/R |
| `BREAKOUT_BUFFER` | 0.001 (0.1%) | min close margin above level |
| `VOL_CONFIRM_MULT` | 1.3 | relative-volume threshold for breakout |
| `RSI_OVERBOUGHT` | 70 | over-extension penalty trigger |
| `ADX_MIN` | 20 | regime filter threshold |
| `MIN_CONFIDENCE` | 60 | minimum to take a trade |
| `MAX_RISK_PCT` | 2.0 | **hard cap** on per-trade risk |
| `MAX_CONCURRENT_POSITIONS` | 3 | exposure limit |
| `ENTRY_CUTOFF_ET` | 15:30 | no new entries after |
| `FLATTEN_ET` | 15:55 | force-close all positions |

---

*End of summary. Build order and acceptance criteria are in `todo.md`.*

---

## Improvement Log

### 2026-06-11 · PHASE-001 — test suite + trade-replay harness
- **Problem:** repo had no tests and no backtest capability; today's winners
  (WMT/AAPL MFE +1.05%/+1.17% @13:30) faded into the 15:55 flatten with no
  profit protection, but one 3-trade day (−$8.50) can't justify retuning exits.
- **Root cause:** no validation infrastructure → strategy changes were being
  made on intuition; exit ladder has nothing between fixed bracket and flatten.
- **Changes:** new `bot/replay.py` (pure bar-walk simulator: bracket +
  breakeven-at-NR what-ifs, stop-first conservative), `scripts/replay.py`
  (fidelity baseline + what-if CLI), `tests/` with 22 pytest tests covering
  exits time gates, P&L math, sizing risk caps, replay core (incl. recorded
  WMT fade scenario). No runtime module touched.
- **Validation:** 22/22 tests pass · smoke_test ALL GREEN · imports OK ·
  replay fidelity baseline within $574 cumulative of recorded P&L (52 trades).
- **Expected impact:** none tonight; harness shows breakeven@+0.5R would have
  recovered +$563 sim-to-sim over 52 trades → seeds PHASE-002.
- **Files:** bot/replay.py · scripts/replay.py · tests/* · phases/PHASE-001.md
- **Commit:** (see git log — PHASE-001)
