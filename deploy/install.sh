#!/usr/bin/env bash
# Install (or update) the USTradeWisBot systemd service + log rotation.
# Idempotent. Does NOT enable or start the service — do that yourself once the
# Alpaca paper account is funded:   sudo systemctl enable --now ustradewisbot
set -euo pipefail

REPO="/root/USTradeWisBot"
LOG_DIR="/var/log/ustradewisbot"

echo "==> creating log dir $LOG_DIR"
mkdir -p "$LOG_DIR"

echo "==> installing systemd unit"
install -m 0644 "$REPO/deploy/ustradewisbot.service" /etc/systemd/system/ustradewisbot.service

echo "==> installing logrotate config"
install -m 0644 "$REPO/deploy/ustradewisbot.logrotate" /etc/logrotate.d/ustradewisbot

echo "==> systemctl daemon-reload"
systemctl daemon-reload

echo
echo "Installed (service is DISABLED)."
echo "Verify : systemctl status ustradewisbot --no-pager"
echo "Start  : sudo systemctl start ustradewisbot        # run now (foreground-managed)"
echo "Enable : sudo systemctl enable --now ustradewisbot # run now + auto-start on boot"
echo "Logs   : tail -f $LOG_DIR/bot.log   (or: journalctl -u ustradewisbot -f)"
