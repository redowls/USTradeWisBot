#!/usr/bin/env bash
# One-shot: report how the IMP-021/IMP-022 entry gates performed on the current
# session. Sends to Telegram, writes a JSON result, then removes its own cron
# line so it runs exactly once.
set -uo pipefail

cd /root/USTradeWisBot || exit 1
LOG=/root/USTradeWisBot/gate_monitor.log
OUT=/root/USTradeWisBot/gate_monitor_result.json

{
  echo "===== gate_monitor $(date -u '+%Y-%m-%d %H:%M:%S UTC') ====="
  .venv/bin/python -m scripts.gate_monitor --telegram --out "$OUT"
  echo "===== done (exit $?) ====="
} >> "$LOG" 2>&1

crontab -l 2>/dev/null | grep -v 'run_gate_monitor_once.sh' | crontab -
