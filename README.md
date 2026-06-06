# USTradeWisBot

Automated **US intraday stock trading bot** (same-day only — every position
opened and closed within one trading day). Strategy: resistance **breakouts** +
**triple-EMA** alignment, scored into a 0–100 **confidence** level that sizes
positions under a hard **2%-per-trade** risk cap. Trades run through **Alpaca**
(paper first), each with an attached stop-loss and take-profit, and everything is
**flattened before the close**. Trades, signals, and daily P&L log to **SQL
Server**; alerts go to **Telegram**; it runs as a **systemd** service on a VPS.

> Design rationale lives in [`summary.md`](summary.md). The phase-by-phase build
> plan and acceptance gates live in [`todo.md`](todo.md). Read `summary.md` first.

## Status

- ✅ **Phase 1 — Project skeleton, config, secrets & DB schema** (complete)
- ✅ **Phase 2 — Market data ingestion** (complete)
- ✅ **Phase 3 — Indicators & support/resistance detection** (complete)
- ⬜ Phase 4 — Signal engine (next)

## Layout

```
bot/
  config.py    # non-secret tunables (summary §11)
  secrets.py   # loads .env via python-dotenv, fails fast on missing secrets
  db.py        # SQL Server connection + parameterized query helpers
  broker.py    # Alpaca client wrapper (account access; orders arrive Phase 6)
  data.py      # market-data ingestion: ET-indexed OHLCV bars (RTH-filtered)
  indicators.py # EMA, ATR, RSI, ADX(+DI/-DI), relative volume (Wilder)
  levels.py    # swing-pivot support/resistance, clustered with touch counts
sql/
  schema.sql   # CREATE TABLE statements (idempotent)
scripts/
  seed_watchlist.py  # seed watchlist with default liquid symbols
  smoke_test.py      # Phase 1 acceptance check
  show_bars.py       # Phase 2 check — print watchlist bars
  show_indicators.py # Phase 3 check — indicators + S/R + math sanity checks
.env.example   # template — copy to .env (gitignored) and fill in
requirements.txt
```

## Setup

```bash
# 1. Python env
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Secrets — copy the template and fill in real values
cp .env.example .env && chmod 600 .env
#   ALPACA_API_KEY / ALPACA_SECRET_KEY  (use PAPER keys)
#   DB_PASSWORD                          (SQL Server login)
#   TELEGRAM_*                           (needed from Phase 9)

# 3. Database — create it, then apply the schema
sqlcmd -S localhost,1433 -U sa -P '***' -C -Q "IF DB_ID('USTradeWisBot') IS NULL CREATE DATABASE USTradeWisBot;"
sqlcmd -S localhost,1433 -U sa -P '***' -C -d USTradeWisBot -i sql/schema.sql

# 4. Seed the watchlist
.venv/bin/python -m scripts.seed_watchlist

# 5. Verify everything (Phase 1 acceptance gate)
.venv/bin/python -m scripts.smoke_test
```

A green smoke test prints the Alpaca **paper** account equity and reads the
seeded watchlist back from SQL Server.

## Guardrails (non-negotiable — see summary §2)

- **Paper trading only** until Phase 12 says otherwise (`ALPACA_PAPER=true`).
- **No overnight positions**: no new entries after 15:30 ET; flatten at 15:55 ET.
- **Secrets never in code or the DB** — only in `.env` (gitignored, `chmod 600`).
- **Max 2% equity risk per trade**, regardless of confidence.

## Tech stack

Python 3.11+ · Alpaca (`alpaca-py`) · SQL Server via `pyodbc` + ODBC Driver 18 ·
`pandas`/`numpy`/`scipy` · `python-telegram-bot` · `python-dotenv` · systemd.
