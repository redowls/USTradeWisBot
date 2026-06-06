# US Intraday Stock Trading Bot — Build Plan (Phase by Phase)

> **How to use this with Claude Code:** build one phase at a time, in order. Do **not** start a phase until the previous phase meets its **"Done when"** criteria. Read `summary.md` first — it explains *why* each piece works the way it does. Check off `[x]` items as you go and keep this file updated so any future session knows where things stand.
>
> **Guiding rules for every phase:** paper trading only until Phase 12 explicitly says otherwise · secrets in `.env`, never in code or DB · risk capped at 2% per trade · test each module in isolation before wiring it into the loop.

---

## Phase 0 — Prerequisites (accounts & tools, no code yet)

**Goal:** have every external account and tool ready.

- [ ] Create an **Alpaca** account; generate **paper-trading** API key + secret (paper keys are separate from live).
- [ ] Confirm access to a **SQL Server** instance (local or on the VPS) and that **SSMS** can connect to it.
- [ ] Create a **Telegram bot** via @BotFather; save the bot token; get your chat id (via `getUpdates` or @userinfobot).
- [ ] Provision the **VPS** (Ubuntu 22.04+); confirm SSH key login works.
- [ ] Install Python 3.11+ locally and on the VPS.

**Done when:** you can log into Alpaca paper, connect to SQL Server via SSMS, and message your Telegram bot manually.

---

## Phase 1 — Project skeleton, config, secrets & DB schema

**Goal:** a clean repo that loads config/secrets, connects to Alpaca paper, and has the database tables created.

- [ ] Create repo structure:
  ```
  trade-bot/
    bot/
      __init__.py
      config.py          # non-secret tunables (see summary §11)
      secrets.py         # loads .env via python-dotenv, fails fast
      db.py              # SQL Server connection + helpers
      broker.py          # Alpaca client wrapper
    sql/
      schema.sql         # CREATE TABLE statements
    .env.example
    .gitignore           # MUST include .env
    requirements.txt
    README.md
  ```
- [ ] `requirements.txt`: `alpaca-py`, `pyodbc`, `python-dotenv`, `pandas`, `numpy`, `scipy`, `python-telegram-bot` (and optionally `pandas-ta`).
- [ ] `secrets.py`: `load_dotenv()`, read all keys with `os.getenv()`, raise a clear error if any required one is missing.
- [ ] `config.py`: all tunables from summary §11 as constants.
- [ ] `sql/schema.sql`: create `watchlist`, `trades`, `signals`, `daily_summary` (see summary §6). Run it via SSMS or `db.py`.
- [ ] `db.py`: open a pyodbc connection (`ODBC Driver 18 for SQL Server`); helper functions use **parameterized queries** only.
- [ ] `broker.py`: instantiate `TradingClient(key, secret, paper=True)`; a `get_account()` call that prints equity & buying power.
- [ ] Seed `watchlist` with ~10–20 liquid symbols (AAPL, MSFT, NVDA, etc.).

**Done when:** running a smoke-test script prints your Alpaca **paper account equity** and successfully **reads the seeded watchlist back from SQL Server**. `.env` is gitignored.

---

## Phase 2 — Market data ingestion

**Goal:** reliably fetch intraday OHLCV bars for every watchlist symbol.

- [ ] `data.py`: use `StockHistoricalDataClient` + `StockBarsRequest` to fetch bars at `BAR_TIMEFRAME` (5Min) for a symbol, returning a clean pandas DataFrame (open/high/low/close/volume, time-indexed).
- [ ] Function to fetch the last N bars for all active watchlist symbols.
- [ ] Set the data **feed** explicitly (`IEX` for now); add a TODO noting the SIP/volume caveat from summary §10.
- [ ] Handle empty results, missing symbols, and timezones (work in ET).

**Done when:** you can call one function and get back current 5-min bar DataFrames for the whole watchlist, printed sanely.

---

## Phase 3 — Indicators & support/resistance detection

**Goal:** turn raw bars into the indicators and S/R levels the strategy needs. Pure functions, easy to unit-test.

- [ ] `indicators.py`: functions for **EMA** (both sets 8/10/20 and 21/34/55), **ATR(14)**, **RSI(14)**, **ADX(14)**, and **relative volume**.
- [ ] `levels.py`: **swing-pivot / fractal** detection (`PIVOT_LOOKBACK` bars each side) → resistance & support pivots.
- [ ] **Cluster** nearby pivots into a small set of clean levels; track **touch count** per level.
- [ ] (Optional) stub a volume-profile / POC function for later.
- [ ] Quick visual/printed sanity check on a few symbols (do the levels look right vs the chart?).

**Done when:** for a sample symbol you can print its current EMAs, ATR, RSI, ADX, relative volume, and a short list of support/resistance levels with touch counts.

---

## Phase 4 — Signal engine (breakout + triple MA + regime + over-extension)

**Goal:** produce the component scores for a symbol. Still no orders.

- [ ] `signals.py` → `breakout_score`: candle **close** above a resistance level + `BREAKOUT_BUFFER` + relative volume ≥ `VOL_CONFIRM_MULT` (+ optional touch-count). Returns 0–1 and the level broken.
- [ ] `ma_score`: short set **8>10>20** stacked, with slope & separation factored in. Returns 0–1.
- [ ] `value_score` (over-extension): distance from 20-EMA in ATR multiples, RSI overbought, aberrant range. Returns 0–1 (1 = good value).
- [ ] `momentum_score`: RSI/MACD supportive. Returns 0–1.
- [ ] `regime_ok`: `ADX ≥ ADX_MIN` and/or long set **21>34>55** stacked. Returns bool + multiplier.
- [ ] A `evaluate(symbol)` function that returns all component scores + `signal_type` ('BREAKOUT'/'MA'/'BOTH') + the broken level.

**Done when:** `evaluate()` on a live symbol returns a sensible dict of component scores and correctly flags whether it broke resistance, has MA alignment, or both — verifiable by eye against the chart.

---

## Phase 5 — Confidence scoring & position sizing

**Goal:** fuse scores into 0–100 confidence and compute a capped share count.

- [ ] `confidence.py`: weighted blend from summary §5.8 × `regime_multiplier` → 0–100.
- [ ] `sizing.py`: map confidence → `risk_fraction` via the summary §5.9 table; compute `stop_distance = ATR * ATR_STOP_MULT`; `shares = floor(equity * risk_fraction / stop_distance)`.
- [ ] **Enforce `MAX_RISK_PCT` (2%) as a hard ceiling** — clamp regardless of formula output.
- [ ] Compute stop and take-profit prices (`RR_RATIO`).
- [ ] Respect `MAX_CONCURRENT_POSITIONS` and skip symbols already held.

**Done when:** given a symbol + account equity, the bot outputs confidence, share count, stop price, and take-profit price — and you've verified a 95-confidence signal never risks more than 2% of equity.

---

## Phase 6 — Order execution (bracket orders) on paper

**Goal:** actually place trades on the **paper** account, each with an attached stop & target.

- [ ] `execution.py`: submit a **bracket order** (`OrderClass.BRACKET` + `TakeProfitRequest` + `StopLossRequest`) for the sized position.
- [ ] Verify the order appears in Alpaca paper with both child legs (TP + SL).
- [ ] Handle order rejections, insufficient buying power, and the 200 req/min rate limit (retry/backoff).
- [ ] Return the broker order id for logging.

**Done when:** the bot places a real paper bracket order from a live signal, and you can see the entry + take-profit + stop-loss legs in the Alpaca paper dashboard.

---

## Phase 7 — Exit management & end-of-day flatten

**Goal:** track exits, record results, and guarantee no overnight holds.

- [ ] `exits.py`: each loop, detect filled exit legs; capture exit price/time and **exit_reason** ('TAKE_PROFIT'/'STOP').
- [ ] Compute `realized_pl` and `realized_pl_pct`.
- [ ] **Entry cutoff**: no new entries after `ENTRY_CUTOFF_ET` (15:30).
- [ ] **Flatten routine** at `FLATTEN_ET` (15:55): cancel open orders, market-sell all open positions, mark `exit_reason = 'EOD_FLATTEN'`.
- [ ] (Optional later) trailing-stop logic managed here.

**Done when:** in a paper session, positions close on target/stop during the day, and any still-open position is force-closed at 15:55 ET with the reason recorded. No position survives to the next day.

---

## Phase 8 — Database logging & daily summary

**Goal:** persist everything to SQL Server, including the daily P&L recap.

- [ ] On entry: insert into `trades` (status OPEN) and `signals` (confidence + all component scores + `signal_type` + broken level).
- [ ] On exit: update the `trades` row (exit price/time, P&L, P&L %, status CLOSED, exit_reason).
- [ ] After the close: compute and insert the `daily_summary` row (buys/sells, wins/losses, gross P&L, day P&L %, equity open/close, symbols traded).
- [ ] Verify in **SSMS** that a full day's trades, their reasons, and the summary row are all present and correct.

**Done when:** after a paper session, SSMS shows every trade, a matching `signals` row explaining *why* each was taken, and one accurate `daily_summary` row for the day.

---

## Phase 9 — Telegram alerts

**Goal:** real-time notifications.

- [ ] `notify.py`: send entry, exit, daily-summary, error, and heartbeat messages (content per summary §8).
- [ ] Wire alerts into execution (entry), exits (exit), end-of-day (summary), and a global exception handler (error).
- [ ] Format messages cleanly (symbol, prices, confidence, P&L).

**Done when:** a paper trade triggers an entry alert and later an exit alert on your phone, and you receive a daily summary message after the close.

---

## Phase 10 — Scheduler / main loop (market-hours aware)

**Goal:** tie all modules into one continuously-running process.

- [ ] `main.py`: loop that runs every `POLL_INTERVAL_SEC` during **regular trading hours** only.
- [ ] Use Alpaca's clock/calendar (or an ET market-hours check) to know when the market is open; sleep otherwise.
- [ ] Each tick: ingest data → evaluate watchlist → score & size → execute new entries (before cutoff) → manage exits → log → alert.
- [ ] Enforce entry cutoff (15:30) and flatten (15:55) inside the loop.
- [ ] Send a heartbeat at startup and at market open; graceful shutdown handling.
- [ ] Robust try/except around each tick so one symbol's error doesn't kill the loop.

**Done when:** `python main.py` runs a full simulated trading day end-to-end on paper unattended — entering, managing, exiting, flattening, logging, and alerting — without manual intervention.

---

## Phase 11 — VPS deployment & monitoring

**Goal:** run the bot 24/7 reliably on the VPS.

- [ ] Copy the repo to the VPS; create the `.env` there and `chmod 600 .env`.
- [ ] Create a **systemd** service: `Restart=on-failure`, `EnvironmentFile=` pointing at `.env`, correct working dir and Python path.
- [ ] Confirm the VPS **timezone / ET handling** so 15:30 & 15:55 fire correctly.
- [ ] File logging + log rotation; verify the `bot_log`/heartbeat (if added).
- [ ] Add uptime monitoring (e.g. alert if no heartbeat / UptimeRobot).
- [ ] Lock down: SSH keys only, UFW firewall deny inbound (except SSH).
- [ ] Reboot the VPS and confirm the service restarts automatically.

**Done when:** the bot runs as a systemd service, survives a reboot, logs to disk, and sends its market-open heartbeat from the VPS.

---

## Phase 12 — Paper incubation & validation (before any live money)

**Goal:** prove the strategy on paper before risking real capital. **Do not skip.**

- [ ] Run on paper for **several weeks** of full trading days.
- [ ] Review `daily_summary` and `signals`: win rate, average P&L %, false-breakout rate, which signal types perform best.
- [ ] Sanity checks: is the false-breakout rate < ~40%? Is expectancy positive over 50–100+ trades? Are correlated positions concentrating risk?
- [ ] Tune cautiously (few parameters, watch for overfitting per summary §10); decide on the IEX-vs-SIP data question.
- [ ] **Only then**, if results justify it: flip `ALPACA_PAPER=false`, fund a small live account, start with reduced size, and watch the paper-vs-live slippage gap closely.

**Done when:** you have weeks of logged paper results you understand and trust — and a deliberate, eyes-open decision about whether/when to go live.

---

## Build order summary (dependency chain)

```
0 Prereqs → 1 Skeleton+DB → 2 Data → 3 Indicators+S/R → 4 Signals
→ 5 Confidence+Sizing → 6 Execution → 7 Exits+Flatten → 8 DB Logging
→ 9 Telegram → 10 Main Loop → 11 VPS → 12 Incubate → (maybe) Live
```

*Each phase builds on the last. Resist the urge to jump ahead to live trading — the guardrails are what keep the account alive.*
