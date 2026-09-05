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
> **Resolved 2026-06-11:** `DAILY_LOSS_HALT_PCT` stays at **8.0** permanently
> (user decision, commit `b46f185`). Do not raise or lower it.
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

---

## Improvement backlog (auto-discovered)

Ordered by expected impact; each item needs replay validation before code.

⏳ **LEADING IMP-046 CANDIDATE (filed 2026-08-31 by IMP-045) — give the gate
   counterfactual a running series.** Every `scripts/gate_monitor` gate-cost
   report ends *"one session is noise — judge it on the running series, not
   tonight"*, but the `--since` window path skips `_gate_cost` entirely, so the
   running series **cannot actually be computed**. Eight sessions of daily
   reviews have therefore quoted single-day verdicts about the filter that now
   refuses ~26 candidates a week against ~15 taken. Deliberately not bundled into
   IMP-045 (one traceable change per run), and **more valuable now that IMP-045
   has de-biased the per-session number the series would accumulate**.
   Analysis-only; cannot confound the 09-08 IMP-040 verdict. Note the honest
   limit: `bot.log` rotations keep 14 days, so the series is bounded by
   logrotate unless the blocked candidates are persisted (cf. IMP-043).

⏳ **PRE-REGISTERED, BLOCKED UNTIL 2026-09-08 — no-progress exit for the
   never-armed cohort.** IMP-040-era trades that never reach +0.25R (`stop_raises`
   = 0) are **9 trades, −$82.89, 11.1% win**, against **15 armed trades, +$184.11,
   86.7% win** (COST 2026-08-31 is the archetype: held 4h03m, MFE +0.03R,
   flattened −$10.20). **Must NOT ship before 09-08**: it moves trades out of
   `EOD_FLATTEN`, which is pre-registered criterion (a) of the IMP-040 verdict.
   Test to run on 09-08: *if `stop_raises` = 0 at N minutes held predicts a loss
   at >70% across ≥20 trades, exit at N.*

⏳ **BLOCKED UNTIL 2026-09-08 (third consecutive escalation) — anchor the plan
   stop to the FILL, not the signal.** `MIN_STOP_PCT` is applied to the signal
   price, so a slipped entry widens the real 1R: WMT 2026-08-31 planned 1.500%,
   got **1.649%** (+10.0%). Because every ratchet trigger is R-denominated, an
   inflated R silently raises the break-even and trail thresholds on exactly the
   trades that slipped. One-line change; **it changes R, and R is what the 09-08
   verdict is testing**, so it waits.

🚩🚩 **HUMAN DECISION REQUIRED (2026-08-17) — the routine has now shipped LIVE,
   UNVERSIONED code TWICE, and the failure is silent.** IMP-031 (written 08-11,
   discovered 08-12) and IMP-034 (written 08-14, live from the 08-15 restart,
   committed only today 08-17) were both authored, validated and **deployed** by a
   run that then ended before Step 5 (commit + push). In both cases the bot behaved
   *correctly* — the fix was real and running — so nothing alarmed, while the code
   existed **only in the working tree**. A `git checkout`, a redeploy, or a fresh
   clone would have silently reverted a live capital-protection fix on the
   no-overnight path, with no signal at all.
   **Both incidents were caught only because a later run happened to read
   `git status`.** That is luck, not a control.
   **NOT FIXABLE BY THIS ROUTINE** — it is a defect in how the routine and the
   deployment relate, not in the bot. **Two options for the human:**
   (a) make Step 5 non-skippable — commit+push BEFORE `systemctl restart`, so the
       running tree is by construction a committed tree; or
   (b) deploy from a clean checkout rather than the working directory, so
       uncommitted code physically cannot go live.
   **(a) is the cheaper fix and also the safer ordering** — validation already
   completes before deployment, so moving the commit ahead of the restart costs
   nothing and removes the entire failure class.
   ⚠️ Until this is resolved, **every run must check `git status` for live-but-
   uncommitted code before doing anything else**, and the daily review must treat
   an uncommitted `bot/` file as an incident, not as housekeeping.
   **→ 2026-08-19 UPDATE: THIRD OCCURRENCE, and it lands INSIDE Step 5 — which
   means option (a) above is NOT sufficient.** The 08-18 daily-review run authored,
   validated and committed **IMP-036** (`d96d6ff`, 20:49:49 UTC), then died on the
   account's Claude session limit (`rc=1`) **between `git commit` and `git push`**.
   Result: the code existed in exactly one place — this VPS's working tree — with
   **no remote copy, no improvement-log entry and no daily-review entry.** It was
   invisible: the 08-19 catch-up only discovered the missing push because its own
   `git push` printed the range `9be4754..ce10175`, i.e. the remote had never seen
   IMP-036 at all. Tally: IMP-031 live+uncommitted, IMP-034 live+uncommitted+
   undeployed, IMP-036 committed+unpushed+unrecorded.
   **This instance was benign in effect** (analysis-only code, no live-path file,
   no restart owed, bot bit-identical), but the same 30-second interruption one
   commit earlier is precisely IMP-034, which sat live and unversioned for 3 days.
   ⚠️ **Option (a) would not have prevented this one** — the commit had already
   happened; what was lost was the push and the record. **Revised recommendation,
   all three together:**
   (a) commit+push BEFORE `systemctl restart` (unchanged — still right);
   (c) treat **commit+push as ONE step that is retried**, never two, so a tree can
       never be ahead of the remote at the moment a run dies; and
   (d) **memory-first ordering** — write the daily-review/improvement-log entry
       BEFORE touching git, so a mid-run death loses the commit (recoverable, the
       analysis survives) rather than the analysis (unrecoverable).
   **(d) is the highest-value of the three**: code left in a tree is discoverable
   by `git status`, but an unwritten review is simply gone.

🚩🚩 **HUMAN DECISION REQUIRED (2026-08-13) — the stop is the entire lifetime loss,
   and every alternative to it is a risk-widening change I am not permitted to take.**
   All-time by exit reason: `EOD_FLATTEN` **n=110 +$423.93 PF 1.47**, `TAKE_PROFIT`
   **n=25 +$2,033.75**, **`STOP` n=105 −$4,697.03 PF 0.02, 7.6% win.** Post-gate the
   same shape holds: flattens +$115.76 (PF 1.93), TP +$55.72, **stops −$386.20 (PF
   0.08)**. **Every exit path this bot owns is profitable except the stop.** Holding the
   20 post-gate stopped trades to the 15:55 flatten instead would have been **−$273.26
   vs −$386.20, a +$112.94 delta** (2026-08-13 CRM #253 alone: −$39.72 actual vs
   **+$75.60** held — it stopped at 11:50 and closed near the session high).
   **NOT TAKEN, and not takeable by this routine:** widening or removing a stop is a
   risk limit, and the delta is bought by accepting an **unbounded** intraday tail in
   place of a bounded one — GOOGL #217 would go −$31.13 → **−$116.77** and ENPH #200
   −$43.68 → **−$73.08**. The no-overnight rule caps the horizon but not the size.
   **Options for the human, in order of my preference:**
   (1) do nothing and treat the drawdown as the answer (see the escalation below);
   (2) authorise a *bounded* experiment — e.g. a per-trade hard-dollar cap wider than
       1R but tighter than the session tail — explicitly, in writing, with a sample
       size and a stop-out condition agreed in advance;
   (3) authorise nothing on the stop and instead retire the entry signal.
   **Do not let a routine take this decision by increments.**

🚩🚩 **STRATEGY ESCALATION (restated 2026-08-13, now overdue): no demonstrated edge,
   and the account is back below the −25% review line at $7,464.62 (−25.35%).**
   240 closed trades, 38.6% win, **PF 0.61**, −$2,239.35. The *post-VWAP-gate* book —
   the best version this bot has ever been — is **51 trades, PF 0.61, expectancy
   −$4.21/trade**. **Ten entry/exit discriminators have now been tested and refuted**
   (confidence, volume, extension, time-of-day, index-EMA regime, opening-range
   blackout, never-green time-stop, break-even-trigger sweep, and as of today
   stop-distance/floor-binding and the time-conditioned MFE scratch). The breakout
   premise is disproven and banned; the bot now trades only conf-60–63 `MA` signals.
   Bucketing post-gate trades by *session range ÷ 1R* shows the bot is **net positive
   where its exit logic physically cannot fire (ratio <1.0: +$28.86, PF 2.64) and net
   negative where it can (ratio >2.5: −$88.58, PF 0.39)** — the signature of a
   zero-edge entry plus a −1R tail. **This is a human decision point: fund it, retire
   it, or rebuild the entry signal from scratch. Parameter work is not the answer and
   this routine will keep declining to pretend otherwise.**

★★★ **(NEW #1 LEVER, 2026-08-07 — instrument shipped as IMP-028, change PRE-REGISTERED
   for the next qualifying run) Close the +0.5R..+1.08R trail dead zone.**
   `TRAIL_TRIGGER_R` and `TRAIL_DISTANCE_R` are both **1.0**, so the trail candidate at
   the trigger (`live − 1.0R`) equals the entry price — exactly what the break-even
   stage already set — and `STOP_RATCHET_MIN_PCT` (0.10% of entry) then blocks the
   replace until roughly **+1.08R**. **Across that whole band the protective stop is
   pinned at entry and captures nothing.** Post-gate evidence (36 trades since
   2026-07-25, via `python -m scripts.exit_geometry`): 6 trades peaked ≥ +0.5R carrying
   **$174.12** of combined peak open profit and banked **−$5.29 (capture −3.0%)**; the
   +0.5R..+1.0R band captures **16.3%** vs **52.0%** for trades clearing +1.0R; the whole
   book captures **−22.2%** of $667.55 of peak open profit. 2026-08-07 META #233 is the
   worked case: it *cleared* the 1.0R trigger at +1.07R and the ratchet was blocked **by
   two cents** (candidate 590.97 vs required 590.99), banking −$0.08 on $32.96 of peak.
   **Do NOT ship on the in-sample grid alone.** Three pre-registered conditions, all
   required, so the next run executes a rule rather than a hunch:
   (1) **post-gate sample ≥ 40 closed trades** (the 2026-08-01 weekly's bar; it was
       **36** at the 08-07 close, so ~2 sessions away);
   (2) **an in-sample / held-out split** in the IMP-022 mould — partition post-gate
       trades by entry day and confirm the tightening improves BOTH windows, not just
       the pooled book (the grid below is in-sample only and every value "wins", which
       is itself a reason for suspicion);
   (3) **discount for IEX sparsity** — bars miss minutes and understate true ranges, so
       simulated stops fire *less* often than real ones and any stop-TIGHTENING what-if
       is biased optimistic. Require the delta to clear the noise budget (currently
       **$4.73**) by a wide margin, and prefer the *most conservative* setting that
       still clears it over the best-scoring one.
   In-sample grid for reference (delta vs the live geometry, post-gate book):
   `trail@1R-0.75R +$27.61` · `trail@1R-0.5R +$53.14` · `trail@0.5R-0.5R +$68.82`
   · `trail@1R-0.25R +$72.43` · `trail@0.5R-0.25R +$73.62`.
   **Risk note: this is a pure stop-TIGHTENING change — it can only move a stop UP, never
   widens risk, and touches no risk limit, sizing rule or the no-overnight path.** It does
   not require human sign-off on the risk grounds that gated IMP-019/022, but it DOES
   need the three conditions above. Watch that it does not cut runners: INTC #203 (+1.68R
   → TAKE_PROFIT +$55.72) and NVDA #206 (+1.26R → +$44.87) are the trades to check.

> **2026-08-05 — backlog ★ (skip-bearish form) is DEAD; do not re-litigate it.**
> Today's session (0W/4L, four longs into an index closing on its low) is the most
> seductive possible argument for a market-regime gate. `scripts/regime_analysis`
> over all **214** trades still returns **GATE VERDICT: REFUTED** — under
> **QQQ-EMA9** bearish trades *win more* than bullish (**43.9% vs 35.3%, PF 0.64 vs
> 0.60**), under **SPY-VWAP** PF is **0.64 vs 0.60**, and the bot loses in bullish
> regimes too (bullish −$1,401.14, PF 0.62). That is the **fourth** failed pre-trade
> discriminator after confidence (IMP-004), volume, and entry extension (IMP-010).
> Only a materially *different* regime construction could revive ★ — the
> "only go long when SPY/QQQ is above its intraday MA/VWAP" formulation below is
> refuted on the data and must not be shipped on the strength of a single red day.
> The standing #1 **edge** lever is now the never-green / "faded flatten" time-stop
> (39 trades, 0% win, −$833.59 all-time), gated on the weekly's 40–60-post-gate-trade
> bar (currently 25).

> **2026-08-12 — ★ NEVER-GREEN TIME-STOP: GATE REACHED, LEVER REFUTED. DEMOTE IT.**
> The post-gate book hit **47 trades** today, clearing the 40–60 bar above, so the
> lever was tested (IMP-032). It fails on its own terms. Measured from real 1-min
> bars: only **2 of 47** post-gate trades never printed green, and **18 of the 19
> post-gate STOP exits DID print green first** — the losses go green and *reverse*,
> they do not go straight down. A time-scratch what-if peaks at **+$44.90 on 4
> scratched trades (T=15min)** and decays to **+$3.84 at T=45min**: non-monotone
> over a 2-to-6-trade population, i.e. noise. The "faded flatten" half has likewise
> collapsed post-gate — **12 trades, −$114.94, avg −$18.93 → −$9.58**. **The VWAP
> gate (IMP-021/022) appears to have already removed most of the population this
> lever was aimed at**, which is why the all-time figure (39 trades) no longer
> describes the book the bot actually trades. **Do not ship a never-green scratch.**
>
> **What replaces it as the concentration — with an explicit warning attached.**
> Of the 19 post-gate stops, the **10 that reached +0.5R and armed break-even cost
> −$15.77 in total**; the **9 that never reached it cost −$330.71**, essentially the
> entire post-gate stop loss, with peaks clustered just under the trigger (+0.42R,
> +0.39R, +0.28R, +0.18R). That makes `BREAKEVEN_TRIGGER_R` the highest-leverage
> exit parameter — **but it is NOT currently shippable.** The IMP-032 sweep prices
> both sides (rescues *and* winners scratched) and returns **0.5R → −$63.30, 0.4R →
> −$73.86, 0.35R → −$17.18, 0.3R → −$19.49, 0.25R → −$41.49, 0.2R → −$38.12** —
> non-monotone, $56 swings between adjacent triggers, and **every row (including the
> live baseline and every row of the trail grid) inside the $248.18 noise budget.**
> Run `python -m scripts.exit_geometry` before proposing any exit change.
>
> **The real blocker is measurement precision, and it should be the weekly's agenda
> item.** 47 trades and IEX 1-min bars cannot resolve a $50–150 effect against a
> $248 noise budget. Until either the sample grows or the simulation gets a finer
> data source, **no exit-geometry change is justifiable on this evidence — and that
> retroactively weakens the basis for IMP-029.**

> **2026-08-12 — ⚠️ OPS / DEPLOYMENT GAP (needs a human — I am not permitted to
> resolve it): LIVE CODE IS NOT IN VERSION CONTROL.** The 08-11 daily-review run
> wrote and validated **IMP-031** (break-even armed off the highest price *printed*
> rather than the ~60s poll sample — `bot/exits.py` `peak_high_since` +
> `compute_trailed_stop(high_price=...)`, `bot/engine.py` batched 1-min bar fetch)
> but ended before committing. The **08-12 11:50:49 UTC restart loaded it, so it has
> been live since this morning** and drove today's session. It is **not committed**,
> has **no commit hash**, and a `git checkout`/redeploy would **silently revert live
> trading behaviour**. I verified the tree is healthy (**248 tests passed** before my
> own change, smoke + check_exits ALL GREEN, service active, 0 errors) and recorded
> it as IMP-031 in `memory/improvement-log.md`, but the routine's standing rule
> forbids me staging files I did not modify, so **the files remain unstaged**:
> `bot/engine.py`, `bot/exits.py`, `bot/exit_sim.py` (08-11), plus an older
> unrelated set `bot/analytics.py`, `bot/replay.py`, `scripts/replay.py` (07-20/22)
> and `tests/test_exit_sim.py`, `tests/test_replay.py`, `tests/test_trailing_stop.py`.
> **Ask: a human should review and commit (or revert) these.** This is the second
> reliability failure of the routine that drives the improvement loop — see the
> 2026-08-05 OPS note above.

> **2026-08-12 — Index ETFs have unreachable bracket legs (engine, for the weekly).**
> Post-gate SPY+QQQ are **6 trades, ALL SIX exiting EOD_FLATTEN, net −$7.04**. Their
> 1R is pinned at the `MIN_STOP_PCT` **1.50%** floor and their TP at **+2.25%**,
> while SPY's *entire* daily range on 08-12 was **0.45%** (771.30–774.74). Neither
> leg can physically fire, so every index-ETF trade is a guaranteed multi-hour
> flatten coin-flip occupying **1 of only 3** concurrency slots — SPY #250 held one
> for 5h11m today to lose $3.14. They lose almost nothing; they also cannot win.
> This is a **sizing/stop-geometry mismatch** (a floor calibrated for single names
> applied to a low-vol index), **not** a watchlist defect — do not park them from the
> daily routine. Options for the weekly: a per-symbol ATR-relative stop floor, or
> excluding instruments whose typical daily range is below the floor.

> **2026-08-05 — OPS (outside this repo, needs a human or infra-scoped run):**
> the daily-review routine has now silently failed **three times in ~3 weeks** —
> 07-29 (rc=1), **08-04 (rc=127: `timeout: failed to run command 'claude': No such
> file or directory`)**, leaving 08-04 with **no review entry** despite a 4-trade
> session. Root cause looks like a PATH/binary resolution problem in the cron
> wrapper (`/root/claude-routines/run-routine.sh`), not a bot defect. The
> improvement engine is only as reliable as the routine that drives it — this is a
> latent single point of failure on the bot's whole feedback loop.

★ **(TOP STRATEGY LEVER, elevated 2026-06-26 — see the 2026-08-05 note above: the
   skip-bearish formulation is REFUTED) Market-regime / breakout-quality
   entry gate.** The entire all-time loss lives in STOP exits / false breakouts
   (PF 0.01, −$2,872; IMP-006) and the breakout-containing book (BOTH+BREAKOUT,
   38 trades = −$1,552 of the −$1,833 total). 06-24/06-25/06-26 keep showing the
   edge is **directional-with-the-tape, not symbol- or score-specific**: longs at
   the open on a weak/two-sided tape fade (06-26 ENPH false-broke −3.2%, COST/META
   drifted down with the megacap rotation), and the SAME setups win on a green
   tape. Crucially, **no pre-trade score discriminates a false breakout** —
   confidence (refuted IMP-004), value/momentum (06-26 losers and winners overlap),
   and volume (refuted 06-26: SE broke on 6.15× vol and lost −$142; AMD on 0.59×
   and won) all fail. So the lever is a *market-level* filter, e.g. only take longs
   when SPY/QQQ are above a short intraday MA/VWAP, and/or skip the first N minutes
   on a gap-down open. **Build (multi-run, not a one-shot post-close hack):**
   (1) ingest an intraday index-regime series (SPY/QQQ bars already fetchable);
   (2) extend `scripts/replay.py` to tag each historical entry with the regime at
   entry and simulate "long-only when regime bullish"; (3) verify it cuts red-day
   losers (06-24, 06-26 ENPH) WITHOUT killing green-day winners (06-23). Pure
   *tightening* (skips entries) — never widens risk. This is the work that should
   replace one-day entry/exit tweaks.
   **→ STEP 1 SHIPPED (IMP-011, 2026-07-06): the measurement now exists** —
   `bot/analytics.by_market_regime`/`classify_index_regime` + standalone
   `scripts/regime_analysis.py` tag each closed trade with the SPY intraday regime
   (SPY close vs EMA9 on 5-min bars) at its entry minute and bucket P&L + a
   skip-bearish what-if (offline-tested; NOT wired into the always-on report).
   **First read:** the edge is *regime-dependent* — ALL-TIME it has NO edge
   (bullish PF 0.56 vs bearish PF 0.71, because the pre-fix 06-08→06-12 blowups
   dominate and were regime-agnostic), but on the **post-06-15 live regime it
   separates: bullish 43t +$339 / PF 1.45 vs bearish 13t −$5 / PF 0.98**, and
   skip-bearish keeps the winners while removing a net-negative tail. NOT yet a
   live gate (bearish n=13 small; EMA9 is one proxy). **Next (still multi-run):**
   (a) grow the post-06-15 bearish sample; (b) compare EMA9 vs VWAP vs QQQ vs
   "skip first N min on a red open" as the proxy in regime_analysis/replay;
   (c) only then gate the engine (long-only when bullish) as a tightening.
   **→ UPDATE (IMP-015, 2026-07-09): the NAIVE SPY/QQQ-EMA9 skip-bearish gate is
   REFUTED by the grown sample (step (a) done, gate failed).** The post-06-15
   bearish bucket has grown to **SPY n=23 (+$37.11, PF 1.11) / QQQ n=30 (+$42.66,
   PF 1.11) — NET-POSITIVE under BOTH proxies**, so skip-bearish now REMOVES profit
   (07-09's own loser, TSM, was bullish-tagged under both — an in-sample
   counterexample). All-time it also fails (bearish PF ≥ bullish under both).
   `scripts/regime_analysis.py` now prints a machine `GATE VERDICT` (via
   `analytics.skip_bearish_gate_verdict`, SUPPORTED only if under EVERY proxy
   bearish n≥20 AND skipping removes a net loss AND bearish PF < bullish) so this
   can't be silently reopened. **The remaining path is a DIFFERENT regime
   definition, not a bigger EMA9 sample** — test VWAP and "skip first N min on a
   red open" as proxies (step (b), still open); only a definition that earns
   SUPPORTED under the verdict graduates to a replay-validated engine gate.
   **→ UPDATE (IMP-018, 2026-07-15): VWAP proxy built (step (b) partly done) —
   gate STILL REFUTED, and adding it PREVENTED a false SUPPORTED.** Added
   `bot/indicators.session_vwap` + a 3rd proxy `SPY-VWAP` to regime_analysis;
   the verdict now runs over SPY-EMA9/QQQ-EMA9/SPY-VWAP. On the 07-15 window the
   two EMA proxies both turned bearish-net-NEGATIVE (SPY −$139.16/PF 0.79; QQQ
   −$222.70/PF 0.74) so an **EMA-only verdict computes SUPPORTED** — but
   **SPY-VWAP bearish is PROFITABLE (+$101.86/PF 1.14 > bullish 1.05)** → 3-proxy
   verdict REFUTED. SPY-EMA9 vs SPY-VWAP disagree on 33% of trades (vs 18%
   SPY-vs-QQQ): the regime *definition* is more fragile than the index choice, so
   no index-regime proxy can ship. **Next: a per-symbol signal (opening-range /
   breakout-quality hold), replay-validated — index-regime proxies are exhausted
   (EMA9, time-of-day, VWAP all fail to isolate the high-conf open-fades).**
   **→ UPDATE (IMP-019, 2026-07-16): the per-symbol signal is FOUND — entry
   distance from the symbol's OWN session VWAP at entry is the first non-refuted
   discriminator.** `bot/replay.py` now computes each fill's % vs its session VWAP
   (`session_vwap`/`bars_open_to_entry`/`vwap_distance_rows`/`bucket_vwap_distance`)
   and `scripts/replay.py` prints the band table. On the 63 recent trades with bars
   it is **cleanly monotonic**: `<-0.25%` 57.1% win +$19.07 · `-0.25..0%` 50.0%
   +$22.04 · `0..+0.25%` 50.0% −$10.33 · `+0.25..+0.50%` 38.5% −$20.13 · `≥+0.50%`
   31.6% −$13.72. The sign flips at VWAP: fills at/below the session VWAP are
   net-positive; fills stretched above it fade. **This directly justifies the gate
   proposal below — see ★★.** (Distinct from IMP-018's REFUTED SPY-VWAP *index
   regime*: this is the *symbol's own* VWAP as a per-trade entry-quality filter.)

★★ **(PROPOSED 2026-07-16, IMP-019 — NEEDS HUMAN APPROVAL: entry-logic change)
   VWAP entry-quality gate.** IMP-019's replay diagnostic shows fills stretched
   ≥~+0.25% above the symbol's own session VWAP at entry are net-negative
   (win% 32–38%, exp −$14 to −$20) while fills at/below VWAP are net-positive
   (win% 50–57%, exp +$19 to +$22), cleanly monotonic across 63 recent trades.
   Proposed change (a pure *tightening* — skips entries, never widens risk): in
   `engine.consider_entries`, skip (or deprioritize) a candidate whose fill/last
   price is more than ~+0.25–0.50% above the current session VWAP. **DO NOT SHIP
   WITHOUT SIGN-OFF** — this is an entry-gate change (ground-rule: entry-gate
   changes need explicit human approval). **Pre-ship validation required:** (1) add
   a `--vwap-skip PCT` what-if to `scripts/replay.py` and confirm the P&L delta
   clears the simulation noise budget (baseline sum|error|); (2) confirm it removes
   the above-VWAP open-fade losers WITHOUT killing the at/below-VWAP winners on a
   held-out window; (3) pick the threshold from the band edges (+0.25% is where the
   sign flips), not curve-fit. Only then wire the engine gate.
   **→ STEP (1) DONE (IMP-020, 2026-07-17): the P&L delta CLEARS the noise budget.**
   `scripts/replay.py --vwap-skip PCT` (+ pure `bot/replay.vwap_skip_whatif`) now
   simulates the skip. On the 61 gate-evaluable trades (noise budget $55.81):
   **skip >+0.25% → keep 27 (+$78.49, 44.4% win) / skip 34 (−$688.26, 29.4% win),
   delta +$688.26 (~12× the budget) — the kept book flips NET-POSITIVE**; skip
   >+0.50% delta +$426.59; skip >+1.0% delta +$83.23. +0.25% (the sign-flip band
   edge) is the only threshold that turns the kept book positive → not curve-fit.
   Today (07-17, 0W/5L −$211.48) added 5 more above-VWAP faders (all ≥+0.50%),
   growing the sample. **Gate now ESCALATED for human sign-off.** Remaining before
   any engine change: step (2) confirm on a held-out window (skipping removes the
   above-VWAP losers without killing at/below-VWAP winners), step (3) fix the
   threshold at +0.25%. Do NOT wire `engine.consider_entries` without approval.
   **→ STEP (2) STARTED (IMP-021, 2026-07-20 — ⚠️ NEVER COMMITTED):** the held-out
   / out-of-sample validation tooling (held-out window `bot/replay.py` +
   `scripts/replay.py` + `tests/test_replay.py`) was WRITTEN and the 07-20 daily
   review declared it "SHIPPED IMP-021", but the changes sit **uncommitted** in the
   working tree and **IMP-021 is absent from `memory/improvement-log.md`** (last
   committed IMP is IMP-020 / 23c9692). Held-out finding recorded 07-20: on the
   07-17+07-20 window the skip side removes net-losers but the **kept book stays
   net-negative** → the gate is a partial mitigant, NOT the "kept book flips
   positive" claim from IMP-020's in-sample read. **ACTION for the next
   code-capable run / human:** finalize the IMP-021 commit (stage the three replay
   files) + write the IMP-021 improvement-log entry. (Left untouched by the 07-21
   review per the pre-existing-uncommitted-changes rule; tests pass 116/116 with
   them present, offline tooling only — no live-bot impact.)
   **→ 07-23 UPDATE (strongest single-day evidence FOR the gate; still uncommitted):**
   today closed 0W/5L −$70.18 and **4 of the 5 fills were >+0.25% above session VWAP**
   (XOM +0.60%, MU +1.83%, NFLX +0.92%, BAC +0.59%; only the −$0.33 MU IMP-013 scratch
   was inside at +0.10%). **The >+0.25% gate would have skipped all four faders and
   avoided −$69.85 of the −$70.18 day.** The held-out check (split @2026-07-22, last 2
   sessions) now reads: in-sample keep 25 (+$50.60) / skip 23 (−$420.65); **held-out
   keep 3 (−$41.69) / skip 7 (−$194.01) → GENERALISES on the skip side but the KEPT
   book stays net-negative out-of-sample** (07-22's ENPH/UNH filled at/below VWAP slip
   under the gate). So the gate is a **strong-but-PARTIAL mitigant** — it would have
   near-eliminated *today's* loss but does not catch the at/below-VWAP faders.
   ⚠️ **CRITICAL CONTEXT FOR THE HUMAN: equity $7,593.96 = −24.06% YTD, only $93.96
   above the −25% ($7,500) strategy-review flag.** This is the single highest-value
   open decision. **Please sign off (or decline) the >+0.25%-above-VWAP entry gate** so
   step (2)/(3) can complete and it can be wired into `engine.consider_entries` as a
   pure tightening (skips entries, never widens risk). Also finalize the uncommitted
   IMP-021/IMP-022 tooling (replay held-out check + `by_breakout_momentum` analytics)
   so the evidence base is traceable. Also (backlog item 3 / entry-timing): 07-23 BAC
   entered 15:27, 3 min before the 15:30 cutoff — consider a soft "skip entries within
   N min of the cutoff" rule; queue behind the VWAP gate.

0a. ~~**EOD-flatten P&L accuracy**~~ **[SHIPPED IMP-003, 2026-06-22]** — on 06-22
   SPY/QQQ/TSM were each booked at exit==entry ($0.00) at the flatten while the
   real market-sells filled at 744.12/737.18/466.222 (~$60 hidden loss; day
   reported +$238.05 vs true +$177.67). Fixed: `broker.latest_filled_exit_price()`
   looks up the actual flatten sell; `engine.eod_flatten` records it (mv/entry
   are now last-resort fallbacks only). Today's 3 rows + the daily_summary were
   backfilled to the real fills.
0b. **Flatten after the 16:00 close** (from 06-18 daily review): the loop only
   flattens while `clock.is_open`, so if every tick in 15:55–16:00 fails the
   position strands until the next session. Add a short post-close grace window
   that still runs `eod_flatten` until the book is confirmed flat. (IMP-002's
   cancel-first + per-tick retry already removes the dominant failure mode.)
1. **Breakeven stop at +0.5R** — **DEMOTED 2026-06-26 (noise on post-fix data).**
   The old "+$563 over 52 trades" sim was the **pre-fix** window (06-08→06-12
   overtrading days dominate it). Re-run 06-26 on the 44 trades that still have
   bars: only **1 loser ever saw +1R** before stopping, and the +0.5R sim delta
   (+$103) sits *inside* the simulation noise budget (sum|error| $714) — i.e. not
   signal. IMP-006 also showed the EOD_FLATTEN bucket it targets is already
   profitable (PF 1.29) while the leak is STOP exits (PF 0.01). False-breakout
   losers (e.g. ENPH 06-26) reverse immediately and never reach +0.5R, so a
   breakeven/trailing stop cannot rescue them. **Do not implement** unless a
   future regime shows losers routinely running favorably first.
2. **Entry-near-day-high veto / pullback confirmation** — COST 06-11 entered
   985.93 at 09:47 near the session high, MFE −0.17% (never positive).
   Quantify across history with the replay harness first.
3. **Open-cycle entries on stale bars** — signals at 09:30:12 are computed
   entirely on the prior day's bars (first 5-min bar incomplete). Entries
   before 09:35 ET: 7 trades, −$289.79. Consider requiring ≥1 completed
   intraday bar.
4. **Slot monopolization** — wide stops + RR 1.5 targets mean positions can
   sit all day (3/3 slots held 09:57→15:55 on 06-11); a time-stop or stale-
   position recycle would free capacity. Needs more sessions of data.
5. **Take-profit exit slippage** — realized fills on TAKE_PROFIT exits average
   $28.20/trade worse than the recorded trigger price (−$253.80 across 9 TPs;
   GOOG 06-12: trigger 364.60 vs implied fill ~361.77). Investigate whether TP
   is a resting limit leg or a polled market exit; if polled, hold the limit
   at the broker. Also: STOP/TP `exit_price` vs `realized_pl` disagree in the
   DB while EOD_FLATTEN matches exactly — record actual fill price.
6. **Correlated-pair exposure (SPY/QQQ etc.)** — PHASE-002 covers identical
   underlyings only; watchlist also carries highly correlated pairs. Needs
   data before acting.

## Refuted / closed candidates (do not reopen without new evidence)

- ~~**Raise `MIN_CONFIDENCE` for the MA-only class to ~65**~~ **[REFUTED 2026-06-23]**
  Flagged 06-15 & 06-22 as "the conf-60–63 MA-only drag." Full-history analysis
  refutes it: **MA-only is the *least-bad* bucket** (PF 0.75 / exp −$4.75) and
  **no MA signal has ever scored ≥64** (MA confidence tops at ~63), so a 65 floor
  would disable the entire MA book — killing all 16 MA winners incl. all 4 of
  06-23's winners (XOM/BAC/CRM/WMT, conf 60–62) and TSLA's 3 MA wins. Simulating
  "drop MA<65" makes the portfolio strictly worse (exp −$19.78 → −$41.64). The
  real signal-quality axis is *inverted* from the old read: the 66+ confidence
  band (all BOTH) is the worst (−$1,227 / PF 0.31, though concentrated in the
  06-08/06-09 overtrading days), while 62–64 is ~break-even (PF 1.06). Surfaced
  permanently in `scripts/report.py` by IMP-004 (PF-per-type + confidence bands)
  so this can't be silently reinstated. Any future MA-quality work must target a
  *non-confidence* discriminator (volume confirm, regime, entry timing).

- ~~**Flatten / size-down the `CONFIDENCE_RISK_TABLE` (cut the high-conf risk
  tier)**~~ **[REFUTED 2026-06-26 — regime-overfit].** Tempting because the risk
  tiers run inverted to performance (60-70/0.5% avg −$8.94; 70-80/1.0% −$48.41;
  80-90/1.5% −$60.32; 90+/2.0% +$69.94 on only 2 trades) and 06-26's ENPH (conf
  81.9 → 1.5% → qty 86) was sized 3× the day's MA trades and lost 3×. But
  simulating flat-0.5% only improves **all-time** (−$1,832 → −$1,076) by shrinking
  the **pre-fix 06-08→06-12 overtrading blowups**; on the **post-06-15 regime it is
  WORSE** (−$23 → −$85) because there the high-conf trades were TSLA's big winners.
  The circuit-breaker/throttle/dedup already fixed the regime that made the
  high-conf tier toxic, so re-sizing now optimizes a dead regime. Do not touch the
  sizing table without fresh post-fix evidence that high-conf trades lose at scale.
- ~~**Require volume confirmation (rel_vol ≥ threshold) to TRIGGER a breakout
  entry**~~ **[REFUTED 2026-06-26 — non-discriminating].** rel_vol at entry does
  not separate breakout winners from losers: SE #59 broke on **6.15× and lost
  −$142**, META #60 on 2.26× lost −$122, GOOGL #62 on 1.53× lost −$129; meanwhile
  AMD #89 on **0.59× won +$20** and TSM #57 on 0.43× won +$34. A rel_vol≥1.0 gate
  would skip 06-26 ENPH (0.40×) but also two real winners and would miss the
  biggest (high-volume) losers; the "low-vol loses" read is driven by ENPH itself
  (overfit) and only 17 of 38 breakout trades even have reconstructable bars.
  Volume stays a *soft* score input (it already is), not a hard gate.
- ~~**Cap entry extension above the broken level (don't "chase" the breakout)**~~
  **[REFUTED 2026-06-29 — non-discriminating].** Prompted by AAPL #94 (filled 1.62%
  above its 281.81 level, false-broke, −$116.55) being the lone loser on a 4W day
  whose two winning breakouts filled tight (TSLA 0.30%, INTC 0.13%). But the full
  book inverts the read: of 41 breakout-type trades the **tightest** bucket is the
  WORST — ≤0.5%: 28 trades, 32.1% win, −$1,047, PF 0.36; 0.5-1.0%: 11, 18.2% win,
  −$331; **only 2 trades ever exceeded 1.0% extension**. False breakouts stop out at
  *tight* entries too, so an extension cap would overfit AAPL, cut tight winners, and
  leave the leak untouched. Surfaced permanently as `by_entry_extension` in
  `scripts/report.py` (IMP-007). Third failed per-trade discriminator after
  confidence (IMP-004) and volume — reinforces backlog ★ (market-regime gate) as the
  only viable lever.

- ~~**Use the stop distance / whether the `MIN_STOP_PCT` 1.5% floor binds as an entry
  discriminator**~~ **[REFUTED 2026-08-13].** Motivated by that day's three
  EOD_FLATTEN trades whose 1R stop was **wider than the symbol's entire session
  range** (GOOG 1.74% stop vs a 0.99% range = 0.57×; QQQ 1.49% vs 1.35%; NVDA 1.47%
  vs 1.55%), which makes the whole exit apparatus — break-even, trail, target, stop —
  physically unreachable. The *outcome* split is real (post-gate range/1R <1.0 →
  +$28.86 PF 2.64; >2.5 → −$88.58 PF 0.39), but the **entry-time** proxy is flat:
  all-time floor-bound (stop ≤1.55%) **n=167 PF 0.63** vs ATR-driven (>1.55%) **n=73
  PF 0.56**; post-gate **0.61 vs 0.60**. Realised range, not entry-time ATR, is what
  separates the buckets, and realised range is not knowable at entry. Ninth failed
  per-trade discriminator.

- ~~**Time-conditioned "scratch the trade if MFE hasn't reached X·R by T minutes"**~~
  **[REFUTED 2026-08-13].** The successor to IMP-032's never-green time-stop, aimed at
  a much larger population: post-gate, trades peaking below **+0.25R** are **n=20,
  −$313.05, 10% win, PF 0.02** — more than the entire post-gate loss. Swept a **42-cell
  grid** (X ∈ {0.15, 0.20, 0.25, 0.30, 0.40, 0.50}R × T ∈ {15, 20, 30, 45, 60, 90,
  120} min) against the real 1-min bars of all 51 post-gate trades. **Every
  non-degenerate cell is negative** (0.25R@45min −$36.15; 0.20R@30min −$44.04;
  0.30R@30min −$88.72; 0.15R@60min −$80.39). The only positive cells are the
  15-minute corner (0.50R@15 **+$176.12**, 0.40R@15 +$122.31), which cut ~45 of 51
  trades and profit purely by removing exposure from a negative-expectancy book.
  **An exit rule whose optimum is "stop trading" is the no-edge result in disguise,
  not a rule** — it belongs to the strategy escalation above, not to the exit logic.
  Tenth failed discriminator.

- ~~**Block entries in the last N minutes before `ENTRY_CUTOFF_ET` ("no time to
  reach the target before the 15:55 flatten")**~~ **[REFUTED 2026-08-19 —
  BACKWARDS].** Prompted by AAPL #269, entered 15:29:06 (51s before the cutoff),
  green on **0 of its 26 minutes** and flattened for −$1.37, with a 1.48R target
  it could not reach while its stop stayed fully live. The mechanism is
  believable and the conclusion is the opposite: run through
  `bot/discriminator.py --stat time-of-day` at seven thresholds (240/270/285/300/
  315/330/345 min after the open), the edge of refusing late entries is
  **negative at every one** (−$1.97 to −$20.01/trade). Late entries are the
  bot's **best** cohort — at ≥315 min (14:45 ET) **n=11, +$76.25, PF 4.60, 36.4%
  win**, era-controlled identical (all 11 post-date the pre-gate week), against a
  book that loses overall; collateral 122–128% (ENPH +$61.76, NVDA +$25.85).
  Twelfth failed discriminator. **Do not reopen on the strength of another late
  scratch — n=1 late losers are already priced into the +$76.25.**

- ~~**Refuse entries whose fill is more than X% ABOVE the signal-bar close
  (entry-slippage filter)**~~ **[REFUTED 2026-08-19 — COLLATERAL].** Unusually
  strong on two of three checks: **positive edge in all three cohorts at every
  threshold** (+$2.28…+$26.06/trade) and it **passes the era control outright** —
  the pre-gate share of the refused cohort's P&L is **0%**, so unlike the ATR/1R
  trap this is a wholly modern effect. Killed on **collateral**: at +0.10–0.20%
  it discards **51–65%** worth of net-positive symbols (**GOOGL +$87.03, META
  +$44.67, BAC +$36.44, AAPL +$32.32**) against the 25% cap; at ≥0.25% the
  era-controlled cohort also falls under n=20. Thirteenth failed discriminator.
  **The finding underneath it is real and was NOT discarded** — the trades are
  mispriced in SIZE, not in selection, and that is what **IMP-037** fixes
  (`sizing.resize_for_live_risk`, refuses nothing). Any future attempt to gate on
  entry slippage must first explain why sizing-to-live-risk is insufficient.

- ~~**Concurrency pacing: "do not spend all three slots in the first N minutes"**~~
  **[REFUTED 2026-08-20 — ERA SIGN-FLIP + INSUFFICIENT MODERN SAMPLE].** Carried
  since 2026-08-11 as *"the strongest un-refuted entry-side idea"* and deferred
  three times for sample. Motivated again on 08-20: all three slots filled
  09:41:36-09:43:51 (135 seconds), two of the three trades were red within four
  minutes and green on 3% of their minutes, and the book was frozen for 6h12m on
  a -1.0% Nasdaq day. Distinct from the opening-range blackout (REFUTED 2026-08-10,
  IMP-030) — the mechanism is slot *allocation*, not time of day. Tested through
  `bot/discriminator.py` (encoding: value 1.0 for a trade that was the 3rd
  CONCURRENT position AND entered within X minutes of the open, 0.0 otherwise;
  threshold 1.0): **NOT SUPPORTED at any window — ERA_ARTEFACT (X=10),
  INSUFFICIENT_DATA (X=15), REFUTED (X=20/30/45/60).** The kill is a clean sign
  flip: era-controlled, the early 3rd slot is the bot's **best** cohort (X=15:
  **n=19, +$228.84, PF 1.78**, so refusing it costs **-$15.82/trade**), while
  post-gate it is **n=5, -$102.53, PF 0.15**. Post-gate n is 3-15 at every
  window, far under the 20-trade bar; at X=45 the rule discards **83% worth of
  net-positive symbols** (TSLA +$262.59, MSFT +$95.45, GOOG +$40.90) against the
  25% cap. **Fourteenth failed discriminator.** Do not reopen on another day
  where the book froze early and the tape reversed — 08-10, 08-11 and 08-20 all
  look like that, and era-controlled that is the profitable cohort. A future
  tooling IMP could add this encoding to `scripts/entry_discriminator.py` as a
  built-in `--stat slot-pace` so it re-runs as the book grows.

## Completed phases

- **2026-06-11 · PHASE-001** — pytest suite (22 tests: exits gates, P&L,
  sizing caps, replay core) + trade-replay/what-if harness
  (`bot/replay.py`, `scripts/replay.py`). Tooling only; no strategy change.
- **2026-06-12 · PHASE-002** — underlying-equivalence guard: GOOG/GOOGL now
  count as one stock for held-skip, re-entry cooldown and daily entry cap
  (`config.EQUIVALENT_UNDERLYINGS`, engine gate, 6 regression tests). Fixes
  the 06-12 GOOGL top-tick re-entry (−$128.79) and 06-10 dual-class exposure.

## ESCALATION (weekly review 2026-09-05) — human decisions required

1. **`uswisbot-weekly-review` starts ~60 min late (third consecutive week).** Scheduled 20:00 UTC with a 21:10 hard kill, actually launching ~21:00 UTC. Effect: no budget for the mandated `sonar-deep-research` call (600s) and none for a code change (20:40 cutoff), so three consecutive weekly reviews have been analysis-only. Please move the schedule earlier or raise the kill time.
2. **Retire-or-rebuild the entry — open three weeks.** Five consecutive weeks of "no demonstrated edge". The exit ratchet (IMP-013/040) works; the entry is an unfiltered MA crossover (breakout leg dormant since 2026-07-24) paying 2 of 17 trades. Options: (A) retire the strategy, (B) fund an entry rebuild, (C) keep running as a ratchet study. This is a capital-allocation call, not a parameter tweak.
3. **Five files uncommitted for seven weeks** (`bot/analytics.py`, `bot/exit_sim.py`, `bot/replay.py`, `scripts/replay.py`, `tests/test_replay.py`). `bot/exit_sim.py` feeds the 09-08 IMP-040 verdict and is not in version control. The weekly routine may stage only memory files, so it cannot fix this.
