"""Telegram alerts (todo.md Phase 9).

Sends entry, exit, daily-summary, error, and heartbeat messages to the configured
chat (summary.md §8). Sending is best-effort and never raises — a Telegram outage
must not crash the trading loop. If Telegram isn't configured, calls are no-ops.

Uses a plain HTTPS POST to the Bot API sendMessage endpoint (stdlib only).
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime

from . import config, secrets

_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = 10


def _f(value, default: float = 0.0) -> float:
    """Coerce DB Decimals / strings / None to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _esc(text) -> str:
    """Escape the HTML special chars Telegram's HTML parse mode cares about."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ts(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(config.MARKET_TZ)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.MARKET_TZ)
    return dt.astimezone(config.MARKET_TZ).strftime("%Y-%m-%d %H:%M %Z")


def send(text: str, *, disable_notification: bool = False) -> bool:
    """Send a raw HTML message. Returns True on success, False otherwise (never raises)."""
    if not secrets.telegram_configured():
        return False
    payload = urllib.parse.urlencode({
        "chat_id": secrets.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
        "disable_notification": "true" if disable_notification else "false",
    }).encode()
    url = _API.format(token=secrets.TELEGRAM_BOT_TOKEN)
    try:
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return bool(json.loads(resp.read()).get("ok"))
    except Exception as exc:  # noqa: BLE001 - alerts must not crash the bot
        print(f"[notify] Telegram send failed: {exc}", file=sys.stderr)
        return False


# --- Typed alerts -----------------------------------------------------------

def heartbeat(message: str) -> bool:
    """Liveness ping, e.g. 'bot started' / 'market open'."""
    return send(f"💓 {_esc(message)}", disable_notification=True)


def entry_alert(plan, evaluation: dict, confidence: float,
                entry_time: datetime | None = None) -> bool:
    """Notify on a new bracket entry."""
    sig = evaluation.get("signal_type") or "—"
    text = (
        f"🟢 <b>ENTRY {_esc(plan.symbol)}</b>\n"
        f"BUY {plan.shares} @ ${plan.entry_price:.2f}\n"
        f"Confidence <b>{confidence:.0f}</b> ({_esc(sig)})\n"
        f"Stop ${plan.stop_price:.2f} | Target ${plan.take_profit_price:.2f}\n"
        f"Risk ${_f(plan.dollar_risk):.2f} ({_f(plan.dollar_risk_pct):.2f}%)\n"
        f"<i>{_ts(entry_time)}</i>"
    )
    return send(text)


def exit_alert(exit_record: dict) -> bool:
    """Notify on a position exit (target / stop / EOD flatten)."""
    pl = _f(exit_record.get("realized_pl"))
    pct = _f(exit_record.get("realized_pl_pct"))
    emoji = "✅" if pl >= 0 else "🔻"
    text = (
        f"{emoji} <b>EXIT {_esc(exit_record.get('symbol'))}</b>\n"
        f"Sold {exit_record.get('qty')} @ ${_f(exit_record.get('exit_price')):.2f}\n"
        f"P&amp;L <b>${pl:+.2f}</b> ({pct:+.2f}%)\n"
        f"Reason: {_esc(exit_record.get('exit_reason'))}"
    )
    return send(text)


def daily_summary_alert(summary: dict) -> bool:
    """Post-close recap of the day's trading."""
    gross = _f(summary.get("gross_pl"))
    pct = _f(summary.get("realized_pl_pct"))
    text = (
        f"📊 <b>Daily Summary {_esc(summary.get('trade_date'))}</b>\n"
        f"Trades: {summary.get('num_buys')} in / {summary.get('num_sells')} out\n"
        f"Wins {summary.get('wins')} | Losses {summary.get('losses')}\n"
        f"Gross P&amp;L <b>${gross:+.2f}</b> ({pct:+.2f}%)\n"
        f"Equity ${_f(summary.get('equity_open')):,.2f} → "
        f"${_f(summary.get('equity_close')):,.2f}\n"
        f"Symbols: {_esc(summary.get('symbols_traded') or '—')}"
    )
    return send(text)


def error_alert(message: str) -> bool:
    """Notify on an unexpected exception (wired into the global handler in Phase 10)."""
    return send(f"⚠️ <b>ERROR</b>\n<code>{_esc(message)}</code>")
