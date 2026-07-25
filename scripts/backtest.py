"""CLI: 30-day from-scratch backtest of the whole USTradeWisBot strategy.

  python -m scripts.backtest                 # 30 days, top-10 watchlist, print only
  python -m scripts.backtest --days 30 --top 10
  python -m scripts.backtest --telegram      # also send the result to Telegram
  python -m scripts.backtest --out /path/result.json

Fetches enough 5-min history to cover the window plus warmup, runs
``bot.backtest.run_backtest``, prints a compact report, and (optionally) sends it
to Telegram and/or writes a JSON result file for an unattended scheduled run.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from math import ceil

from bot import backtest, config, data, db, notify

DEFAULT_DAYS = 30
DEFAULT_TOP = 10
SESSIONS_PER_MONTH = 22          # ~trading days in 30 calendar days
BARS_PER_SESSION = 78            # 5-min RTH bars


def _arg(argv: list[str], flag: str, default: str) -> str:
    return argv[argv.index(flag) + 1] if flag in argv else default


def _equity() -> float:
    """Live account equity for realistic sizing; fall back to $10k."""
    try:
        from bot import broker
        return float(broker.account_summary()["equity"])
    except Exception:
        return 10_000.0


def format_report(s: dict) -> str:
    lines = [
        "📊 USTradeWisBot — 30-day backtest (whole strategy, incl. IMP-021)",
        f"Window: {s['window']}  ({s['sessions']} sessions)",
        f"Symbols ({len(s['symbols'])}): {', '.join(s['symbols'])}",
        "",
        f"Trades: {s['trades']}   ✅ Wins: {s['wins']}   ❌ Losses: {s['losses']}   "
        f"Win rate: {s['win_pct']}%",
        f"Net P&L: ${s['total_pl']:,.2f}   PF: {s['profit_factor']}   "
        f"avgWin ${s['avg_win']:,.2f} / avgLoss ${s['avg_loss']:,.2f}",
        "",
        "By exit reason:",
    ]
    for reason, b in sorted(s["by_reason"].items(), key=lambda kv: kv[1]["pl"]):
        wr = round(100.0 * b["wins"] / b["n"], 0) if b["n"] else 0
        lines.append(f"  {reason:12} n={b['n']:3}  win%={wr:>3.0f}  ${b['pl']:,.2f}")
    lines.append("")
    lines.append("By symbol:")
    for sym, b in sorted(s["by_symbol"].items(), key=lambda kv: kv[1]["pl"]):
        wr = round(100.0 * b["wins"] / b["n"], 0) if b["n"] else 0
        lines.append(f"  {sym:6} n={b['n']:3}  win%={wr:>3.0f}  ${b['pl']:,.2f}")
    lines.append("")
    lines.append(
        "Sim caveats: fills at signal-bar close (no slippage); stop-before-target "
        "within a bar; MAX_CONCURRENT applied post-hoc. Directional, not exact P&L."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    days = int(_arg(argv, "--days", str(DEFAULT_DAYS)))
    top = int(_arg(argv, "--top", str(DEFAULT_TOP)))
    out = _arg(argv, "--out", "")
    send_tg = "--telegram" in argv

    symbols = [w["symbol"] for w in db.get_active_watchlist()][:top]
    if not symbols:
        print("No active watchlist symbols — aborting.", file=sys.stderr)
        return 1

    equity = _equity()
    # Fetch history: window sessions + warmup, with RTH-filter slack.
    n_bars = ceil(days / 30 * SESSIONS_PER_MONTH) * BARS_PER_SESSION + backtest.EVAL_BARS + 200
    print(f"Fetching {n_bars} × {config.BAR_TIMEFRAME} bars for {len(symbols)} symbols…",
          flush=True)
    all_bars = data.get_bars_for_symbols(symbols, n_bars=n_bars, timeframe=config.BAR_TIMEFRAME)

    summary = backtest.run_backtest(all_bars, symbols, days, equity)
    report = format_report(summary)
    print("\n" + report)

    if out:
        payload = {k: v for k, v in summary.items() if k != "trade_rows"}
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        payload["report_text"] = report
        with open(out, "w") as fh:
            json.dump(payload, fh, indent=2, default=str)
        print(f"\nWrote {out}")

    if send_tg:
        ok = notify.send(report)
        print(f"\nTelegram sent: {ok}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
