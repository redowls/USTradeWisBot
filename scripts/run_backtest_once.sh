#!/usr/bin/env bash
# One-shot 30-day backtest of the whole USTradeWisBot strategy.
# Runs once (see the self-removing crontab line at the end), sends the result to
# Telegram, and writes a JSON result file for the chat to surface later.
set -uo pipefail

cd /root/USTradeWisBot || exit 1
LOG=/root/USTradeWisBot/backtest_once.log
OUT=/root/USTradeWisBot/backtest_result.json

{
  echo "===== run_backtest_once $(date -u '+%Y-%m-%d %H:%M:%S UTC') ====="
  .venv/bin/python -m scripts.backtest --days 30 --top 10 --telegram --out "$OUT"
  echo "===== done (exit $?) ====="
} >> "$LOG" 2>&1

# Self-remove this job so it runs exactly once ("only 1 run").
crontab -l 2>/dev/null | grep -v 'run_backtest_once.sh' | crontab -
