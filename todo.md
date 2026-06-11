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

- [x] Create repo structure:
  ```
  USTradeWisBot/
    bot/
      __init__.py
      config.py          # non-secret tunables (see summary §11)
      secrets.py         # loads .env via python-dotenv, fails fast
      db.py              # SQL Server connection + helpers
      broker.py          # Alpaca client wrapper
    sql/
      schema.sql         # CREATE TABLE statements
    scripts/
      seed_watchlist.py  # seed the watchlist
      smoke_test.py      # Phase 1 acceptance check
    .env.example
    .gitignore           # includes .env
    requirements.txt
    README.md
  ```
- [x] `requirements.txt`: `alpaca-py`, `pyodbc`, `python-dotenv`, `pandas`, `numpy`, `scipy`, `python-telegram-bot`.
- [x] `secrets.py`: `load_dotenv()`, read all keys with `os.getenv()`, raise a clear error if any required one is missing.
- [x] `config.py`: all tunables from summary §11 as constants.
- [x] `sql/schema.sql`: create `watchlist`, `trades`, `signals`, `daily_summary` (see summary §6). Applied via `sqlcmd`.
- [x] `db.py`: open a pyodbc connection (`ODBC Driver 18 for SQL Server`); helper functions use **parameterized queries** only.
- [x] `broker.py`: instantiate `TradingClient(key, secret, paper=True)`; `account_summary()` prints equity & buying power.
- [x] Seed `watchlist` with ~10–20 liquid symbols (15 seeded: AAPL, MSFT, NVDA, etc.).

**Done when:** running a smoke-test script prints your Alpaca **paper account equity** and successfully **reads the seeded watchlist back from SQL Server**. `.env` is gitignored.

> ✅ **Phase 1 complete (2026-06-06).** Smoke test green: Alpaca paper equity USD 1,000.00; 15 active watchlist symbols read back from SQL Server (`USTradeWisBot` DB, local SQL Server 2022, `sa` login). `.env` gitignored + `chmod 600`. Built/run on the VPS with a `.venv` (Python 3.12).

---

## Phase 2 — Market data ingestion

**Goal:** reliably fetch intraday OHLCV bars for every watchlist symbol.

- [x] `data.py`: use `StockHistoricalDataClient` + `StockBarsRequest` to fetch bars at `BAR_TIMEFRAME` (5Min) for a symbol, returning a clean pandas DataFrame (open/high/low/close/volume, time-indexed).
- [x] Function to fetch the last N bars for all active watchlist symbols (`get_watchlist_bars`, one batched API call).
- [x] Set the data **feed** explicitly (`IEX` for now); TODO(SIP) noting the SIP/volume caveat from summary §10 is in `data.py`.
- [x] Handle empty results, missing symbols, and timezones (ET-indexed; missing/empty symbols → empty DataFrame).
- [x] **Bonus:** `regular_hours_only` filter (default on) drops thin extended-hours IEX bars so only 09:30–16:00 ET bars reach the strategy.

**Done when:** you can call one function and get back current 5-min bar DataFrames for the whole watchlist, printed sanely.

> ✅ **Phase 2 complete (2026-06-06).** `scripts/show_bars.py` returns 50× 5-min RTH bars for all 15 symbols, ET-indexed, full-session volume (last bar = 15:55 ET close). Run: `.venv/bin/python -m scripts.show_bars`.

---

## Phase 3 — Indicators & support/resistance detection

**Goal:** turn raw bars into the indicators and S/R levels the strategy needs. Pure functions, easy to unit-test.

- [x] `indicators.py`: functions for **EMA** (both sets 8/10/20 and 21/34/55), **ATR(14)**, **RSI(14)**, **ADX(14)** (+ ±DI), and **relative volume**. ATR/RSI/ADX use Wilder smoothing. Hand-rolled pandas/numpy (no extra deps).
- [x] `levels.py`: **swing-pivot / fractal** detection (`PIVOT_LOOKBACK` bars each side) → resistance & support pivots.
- [x] **Cluster** nearby pivots into a small set of clean levels (`LEVEL_CLUSTER_PCT`); track **touch count** per level. Plus `nearest_resistance_above()` / `nearest_support_below()` helpers for Phase 4.
- [ ] (Optional) stub a volume-profile / POC function for later. *(deferred — optional)*
- [x] Quick visual/printed sanity check on a few symbols + synthetic known-answer math checks (EMA/RSI/ATR/ADX/pivots).

**Done when:** for a sample symbol you can print its current EMAs, ATR, RSI, ADX, relative volume, and a short list of support/resistance levels with touch counts.

> ✅ **Phase 3 complete (2026-06-06).** `bot/indicators.py` + `bot/levels.py`. Check: `.venv/bin/python -m scripts.show_indicators` — synthetic math sanity checks pass and live EMAs/ATR/RSI/ADX/relVol + clustered S/R (with touch counts) print for AAPL/NVDA/TSLA.

---

## Phase 4 — Signal engine (breakout + triple MA + regime + over-extension)

**Goal:** produce the component scores for a symbol. Still no orders.

- [x] `signals.py` → `breakout_score`: candle **close** above a resistance level + `BREAKOUT_BUFFER` + relative volume ≥ `VOL_CONFIRM_MULT` (+ touch-count). Returns 0–1 and the level broken.
- [x] `ma_score`: short set **8>10>20** stacked, with slope & separation factored in. Returns 0–1.
- [x] `value_score` (over-extension): distance from 20-EMA in ATR multiples, RSI overbought, aberrant range. Returns 0–1 (1 = good value).
- [x] `momentum_score`: RSI/MACD supportive. Returns 0–1. (MACD added to `indicators.py`.)
- [x] `regime_ok`: `ADX ≥ ADX_MIN` and/or long set **21>34>55** stacked. Returns bool + multiplier (1.0 both / 0.5 one / 0.0 neither).
- [x] A `evaluate(symbol)` function that returns all component scores + `signal_type` ('BREAKOUT'/'MA'/'BOTH'/None) + the broken level.

**Done when:** `evaluate()` on a live symbol returns a sensible dict of component scores and correctly flags whether it broke resistance, has MA alignment, or both — verifiable by eye against the chart.

> ✅ **Phase 4 complete (2026-06-06).** `bot/signals.py` + MACD in `indicators.py`. Check: `.venv/bin/python -m scripts.show_signals` — synthetic known-answer scenarios (breakout / MA / downtrend / over-extension) all pass; live watchlist evaluation prints component scores + classification (regime multiplier correctly zeroes out non-trending names like BAC).

---

## Phase 5 — Confidence scoring & position sizing

**Goal:** fuse scores into 0–100 confidence and compute a capped share count.

- [x] `confidence.py`: weighted blend from summary §5.8 × `regime_multiplier` → 0–100.
- [x] `sizing.py`: map confidence → `risk_fraction` via the summary §5.9 table; compute `stop_distance = ATR * ATR_STOP_MULT`; `shares = floor(equity * risk_fraction / stop_distance)`. Also caps shares by available buying power.
- [x] **Enforce `MAX_RISK_PCT` (2%) as a hard ceiling** — clamped regardless of formula output (verified by sweep).
- [x] Compute stop and take-profit prices (`RR_RATIO`).
- [x] Respect `MAX_CONCURRENT_POSITIONS` and skip symbols already held (`broker.open_position_symbols()`).

**Done when:** given a symbol + account equity, the bot outputs confidence, share count, stop price, and take-profit price — and you've verified a 95-confidence signal never risks more than 2% of equity.

> ✅ **Phase 5 complete (2026-06-06).** `bot/confidence.py` + `bot/sizing.py`. Check: `.venv/bin/python -m scripts.show_sizing` — confidence math, risk table, and the hard 2% cap all verified (worst-case over full ATR×confidence sweep = exactly 2.0000%; 95-conf → 200 sh / $200 / 2.0% on $10k). NOTE: live Alpaca paper account currently funded at $0 — re-fund/reset to $10k before Phase 6 order placement.

---

## Phase 6 — Order execution (bracket orders) on paper

**Goal:** actually place trades on the **paper** account, each with an attached stop & target.

- [x] `execution.py`: submit a **bracket order** (`OrderClass.BRACKET` + `TakeProfitRequest` + `StopLossRequest`) for the sized position. `build_bracket_request()` is pure/testable.
- [~] Verify the order appears in Alpaca paper with both child legs (TP + SL). *Code + verification path done; final dashboard confirmation pending a funded account + open market.*
- [x] Handle order rejections, insufficient buying power, and the 200 req/min rate limit (retry/backoff on transient errors only). Verified: $0 account returns a clean `rejected` result (`403 insufficient buying power`), no crash.
- [x] Return the broker order id for logging.

**Done when:** the bot places a real paper bracket order from a live signal, and you can see the entry + take-profit + stop-loss legs in the Alpaca paper dashboard.

> ✅ **Phase 6 code complete (2026-06-06).** `bot/execution.py` (+ `get_order`/`cancel_order`). Check: `.venv/bin/python -m scripts.place_test_order` — offline construction/skip/retry checks pass; live submit path exercised and rejection handled cleanly. ⏳ **Pending:** fund the paper account (~$10k) and re-run during market hours to see a real bracket order with both legs (it auto-cancels the test order).

---

## Phase 7 — Exit management & end-of-day flatten

**Goal:** track exits, record results, and guarantee no overnight holds.

- [x] `exits.py`: `detect_exits()` reads each entry order, finds filled bracket legs, and `build_exit_record()` captures exit price/time + **exit_reason** ('TAKE_PROFIT'/'STOP').
- [x] Compute `realized_pl` and `realized_pl_pct` (`compute_pl()`).
- [x] **Entry cutoff**: `entries_allowed()` / `past_entry_cutoff()` — no new entries at/after `ENTRY_CUTOFF_ET` (15:30 ET).
- [x] **Flatten routine** `flatten_all()` / `maybe_flatten()` at `FLATTEN_ET` (15:55): cancel open orders + market-sell all positions, reason `EOD_FLATTEN`.
- [ ] (Optional later) trailing-stop logic managed here. *(deferred)*

**Done when:** in a paper session, positions close on target/stop during the day, and any still-open position is force-closed at 15:55 ET with the reason recorded. No position survives to the next day.

> ✅ **Phase 7 code complete (2026-06-06).** `bot/exits.py` + `broker.cancel_all_orders()`/`close_all_positions()`. Check: `.venv/bin/python -m scripts.check_exits` — time rules (15:30/15:55), P&L, reason classification, and exit-record building all verified offline against fake TP/SL/open/unfilled orders. ⏳ **Pending:** a funded paper session during market hours to watch real target/stop exits and the live 15:55 flatten (same funding dependency as Phase 6).

---

## Phase 8 — Database logging & daily summary

**Goal:** persist everything to SQL Server, including the daily P&L recap.

- [x] On entry: `logbook.record_entry()` inserts `trades` (status OPEN) and `signals` (confidence + all component scores + `signal_type` + broken level).
- [x] On exit: `logbook.record_exit()` / `update_trade_exit()` updates the `trades` row (exit price/time, P&L, P&L %, status CLOSED, exit_reason).
- [x] After the close: `logbook.write_daily_summary()` computes + upserts the `daily_summary` row (buys/sells, wins/losses, gross P&L, day P&L %, equity open/close, symbols traded).
- [x] Verified against the live SQL Server (via `scripts/check_logging.py`, which also self-cleans). Inspect anytime in SSMS.

**Done when:** after a paper session, SSMS shows every trade, a matching `signals` row explaining *why* each was taken, and one accurate `daily_summary` row for the day.

> ✅ **Phase 8 complete (2026-06-06).** `bot/logbook.py` (+ `db.insert_returning_id`). Check: `.venv/bin/python -m scripts.check_logging` — simulated AAPL(TP)+NVDA(STOP) trades + signals round-trip through SQL Server; daily_summary aggregates correctly (2 buys/2 sells/1 win/1 loss/$50/0.5%); test rows cleaned up. Fully verified (no Alpaca funding needed).

---

## Phase 9 — Telegram alerts

**Goal:** real-time notifications.

- [x] `notify.py`: send entry, exit, daily-summary, error, and heartbeat messages (content per summary §8). Best-effort (never raises); no-op if Telegram unconfigured.
- [~] Wire alerts into execution (entry), exits (exit), end-of-day (summary), and a global exception handler (error). *Functions ready; wired into the main loop in Phase 10.*
- [x] Format messages cleanly (symbol, prices, confidence, P&L) with HTML + emojis.

**Done when:** a paper trade triggers an entry alert and later an exit alert on your phone, and you receive a daily summary message after the close.

> ✅ **Phase 9 complete (2026-06-06).** `bot/notify.py` (stdlib HTTPS POST to the Bot API). Check: `.venv/bin/python -m scripts.check_notify` — all five alert types (heartbeat/entry/exit/daily-summary/error) sent live to chat 7739672535 and received on phone. Wiring into the live loop happens in Phase 10.

---

## Phase 10 — Scheduler / main loop (market-hours aware)

**Goal:** tie all modules into one continuously-running process.

- [x] `main.py` (entrypoint) + `bot/engine.py` (`Engine`): loop runs every `POLL_INTERVAL_SEC` during **regular trading hours** only.
- [x] Uses Alpaca's clock (`broker.get_clock()`) to know when the market is open; sleeps until next open otherwise.
- [x] Each tick: manage exits → (before cutoff) ingest → evaluate → score & size → execute new entries → log → alert.
- [x] Enforces entry cutoff (15:30, `consider_entries`) and flatten (15:55, `eod_flatten`) inside the loop; daily summary written once after close.
- [x] Heartbeats at startup and at market open; SIGINT/SIGTERM graceful shutdown (interruptible sleep).
- [x] try/except around each tick (error alert sent) so one symbol's error can't kill the loop.

**Done when:** `python main.py` runs a full simulated trading day end-to-end on paper unattended — entering, managing, exiting, flattening, logging, and alerting — without manual intervention.

> ✅ **Phase 10 code complete (2026-06-06).** `bot/engine.py` + root `main.py` (`--dry-run` flag). Check: `.venv/bin/python -m scripts.check_engine` — dry-run proves the full ingest→evaluate→score→size chain, entry-cutoff gating, exit management, and flatten path (NFLX surfaced as the would-trade candidate at conf 63.9). ⏳ **Pending:** funded account + open market for a real unattended session (same dependency as Phase 6/7).

---

## Phase 11 — VPS deployment & monitoring

**Goal:** run the bot 24/7 reliably on the VPS.

- [x] Repo already on the VPS at `/root/USTradeWisBot`; `.env` present and `chmod 600`.
- [x] Created a **systemd** service (`deploy/ustradewisbot.service`): `Restart=on-failure`, correct WorkingDirectory + venv Python path. Secrets loaded by the app via python-dotenv (no secrets in the unit). Installed via `deploy/install.sh` (currently **disabled** per request).
- [x] Confirmed **timezone / ET handling**: bot uses `ZoneInfo("America/New_York")` explicitly + Alpaca clock, independent of the system TZ (which is UTC) — 15:30 & 15:55 fire correctly.
- [x] File logging to `/var/log/ustradewisbot/bot.log` + logrotate (daily, 14 kept, copytruncate); also visible via `journalctl`.
- [x] Monitoring: `Restart=on-failure`, Telegram error alerts + startup/open/shutdown heartbeats; UptimeRobot option documented in `DEPLOY.md`.
- [ ] Lock down: SSH keys only, UFW deny inbound (except SSH). *Documented in `DEPLOY.md` with cautions (SSH lockout / remote SSMS on 1433); left for deliberate manual action.*
- [ ] Reboot the VPS and confirm the service restarts automatically. *Do after enabling (post-funding); steps in `DEPLOY.md`.*

**Done when:** the bot runs as a systemd service, survives a reboot, logs to disk, and sends its market-open heartbeat from the VPS.

> ✅ **Phase 11 code/install complete (2026-06-06).** `deploy/` (service + logrotate + install.sh) + `DEPLOY.md`. Unit installed, passes `systemd-analyze verify`, currently **disabled + inactive** (left so until the paper account is funded). ⏳ **Pending (after funding):** `systemctl enable --now ustradewisbot`, reboot test, optional UFW lockdown.

---

## Phase 12 — Paper incubation & validation (before any live money)

**Goal:** prove the strategy on paper before risking real capital. **Do not skip.**

- [~] Run on paper for **several weeks** of full trading days. *(IN PROGRESS — live on paper since 2026-06-08; only 3 sessions so far, weeks still needed.)*
- [x] Tooling to review `daily_summary` and `signals`: `bot/analytics.py` + `scripts/report.py` compute win rate, avg P&L %, expectancy, profit factor, performance by signal type, and false-breakout rate.
- [x] Sanity-check tooling: `incubation_verdict()` flags false-breakout ≥ ~40%, non-positive expectancy, and insufficient sample (<50 trades). *(Correlated-position concentration: review manually / future enhancement.)*
- [~] Tune cautiously (few parameters, watch for overfitting per summary §10); decide on the IEX-vs-SIP data question. *(IN PROGRESS — 3 risk-tuning iterations so far, see below. IEX-vs-SIP not yet decided.)*
- [ ] **Only then**, if results justify it: flip `ALPACA_PAPER=false`, fund a small live account, start with reduced size, and watch the paper-vs-live slippage gap closely. *(NOT MET — results are negative; nowhere near a go-live decision.)*

**Done when:** you have weeks of logged paper results you understand and trust — and a deliberate, eyes-open decision about whether/when to go live.

> ### 📍 CURRENT STAGE (2026-06-11): Phase 12 — paper incubation, IN PROGRESS
>
> All code (Phases 0–11) is built, deployed, and live. The bot runs 24/7 as the
> `ustradewisbot` systemd service (enabled + active), paper account funded ($10k),
> watchlist = 31 symbols, Telegram alerts working.
>
> **Incubation results so far are poor — this is why we paper-trade first:**
>
> | Session | Trades | W/L | Day P&L |
> |---|---|---|---|
> | 2026-06-08 | 22 | 5/17 | −4.15% |
> | 2026-06-09 | 17 | 2/15 | −9.37% |
> | 2026-06-10 | 12 | 3/9 | −3.87% |
> | **Total (51 closed)** | **51** | **10/41** | **−$1,634 (≈ −16%)** |
>
> Win rate **19.6%**, expectancy **−$32/trade**, **false-breakout rate 90.5%**
> (the breakout edge is not working on IEX intraday data as-is). Verdict from
> `scripts/report.py`: **NEEDS WORK**.
>
> **Tuning iterations applied (committed):**
> - `acf9c75` — wider stops + over-extension veto after the first paper day.
> - `da0493e` — daily-loss circuit breaker + per-symbol re-entry throttle.
> - `bcfdf0e` — widened stops (3×ATR, 1.5% floor) so trades survive intraday noise.
>
> **⚠️ Open item:** `config.py` `DAILY_LOSS_HALT_PCT` is temporarily set to **8.0**
> (normal 3.0) for the 2026-06-10 session only — the inline comment says revert to
> 3.0 after that close (now past). Uncommitted; needs reverting.
>
> **Next:** keep incubating, diagnose the 90.5% false-breakout rate (the core
> problem — likely the breakout/volume filters on thin IEX data; revisit
> SIP vs IEX and entry confirmation), and do NOT consider live money until
> expectancy is positive over a much larger, longer sample.

---

## Build order summary (dependency chain)

```
0 Prereqs → 1 Skeleton+DB → 2 Data → 3 Indicators+S/R → 4 Signals
→ 5 Confidence+Sizing → 6 Execution → 7 Exits+Flatten → 8 DB Logging
→ 9 Telegram → 10 Main Loop → 11 VPS → 12 Incubate → (maybe) Live
```

*Each phase builds on the last. Resist the urge to jump ahead to live trading — the guardrails are what keep the account alive.*
