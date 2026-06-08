# Deployment & Operations (Phase 11)

The bot runs as a **systemd** service on the VPS. The service is installed but
left **disabled** until the Alpaca paper account is funded and you're ready to
let it trade.

## Install / update the service

```bash
sudo bash /root/USTradeWisBot/deploy/install.sh
```

This copies the unit to `/etc/systemd/system/ustradewisbot.service`, installs the
logrotate config, creates `/var/log/ustradewisbot/`, and runs `daemon-reload`.
It does **not** enable or start anything.

## Run it (once the paper account is funded)

```bash
sudo systemctl start ustradewisbot            # run now (with Restart=on-failure)
sudo systemctl enable --now ustradewisbot     # run now AND auto-start on boot
sudo systemctl status ustradewisbot --no-pager
```

Stop / restart:

```bash
sudo systemctl stop ustradewisbot     # sends SIGTERM; the loop shuts down cleanly
sudo systemctl restart ustradewisbot
```

## Logs

- File (rotated daily, 14 kept): `tail -f /var/log/ustradewisbot/bot.log`
- Journal: `journalctl -u ustradewisbot -f`

## Timezone / ET handling

The bot does **not** rely on the system timezone — every time rule uses
`ZoneInfo("America/New_York")` explicitly (see `bot/config.py`), and entries/
exits gate on Alpaca's market clock. So the 15:30 cutoff and 15:55 flatten fire
correctly regardless of the server's local time. (`timedatectl` is informational.)

## Monitoring / uptime

- **Restart on crash:** handled by `Restart=on-failure` in the unit.
- **Error alerts:** any tick exception sends a Telegram `⚠️ ERROR` message.
- **Heartbeats:** Telegram messages on startup, at market open, and on shutdown.
- **External uptime (optional):** point UptimeRobot (or similar) at a heartbeat,
  or add a periodic "still alive" Telegram ping if you want continuous assurance.

## Reboot test (do after enabling)

```bash
sudo systemctl enable ustradewisbot   # ensure enabled for boot
sudo reboot
# after it comes back:
systemctl is-enabled ustradewisbot    # -> enabled
systemctl status ustradewisbot --no-pager
```

## Firewall (UFW) — review before enabling ⚠️

Summary §9 recommends SSH-key-only access and a default-deny inbound firewall.
**Do not enable UFW blindly** — two cautions for this box:

1. Make sure SSH is allowed *before* enabling, or you can lock yourself out.
2. SQL Server listens on **1433**. If you connect to it remotely (e.g. SSMS from
   your laptop), denying inbound will break that. Keep 1433 local-only, or allow
   your IP explicitly.

Recommended (run deliberately, not via automation):

```bash
sudo ufw allow OpenSSH                 # or: sudo ufw allow 22/tcp
# Only if you need remote SSMS, restrict 1433 to your IP:
# sudo ufw allow from <YOUR_IP> to any port 1433 proto tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
```

The bot only makes **outbound** connections (Alpaca, Telegram, local SQL Server),
so it needs no inbound ports of its own.
