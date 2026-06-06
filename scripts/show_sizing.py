"""Phase 5 check (todo.md Phase 5 "Done when").

Part 1 — confidence math, the confidence->risk table, and the HARD 2% cap
(swept across many ATRs / confidences) verified against known answers.
Part 2 — live: pull account equity, evaluate the watchlist, and print confidence
+ a sized plan (shares / stop / take-profit / risk) for each symbol, asserting
no plan ever risks more than MAX_RISK_PCT of equity.

Run from the project root:  python -m scripts.show_sizing
"""

from __future__ import annotations

import sys

from bot import broker, confidence, config, signals, sizing


def _math_checks() -> bool:
    print("[1] Confidence + sizing math (known answers)")
    ok = True

    # Confidence: perfect signal -> 100, empty -> 0, hand-calc mid case.
    perfect = {"breakout_score": 1, "ma_score": 1, "value_score": 1,
               "momentum_score": 1, "regime_multiplier": 1.0}
    if confidence.score(perfect) != 100.0:
        print(f"  FAIL: perfect confidence != 100 ({confidence.score(perfect)})"); ok = False
    if confidence.score({"regime_multiplier": 1.0}) != 0.0:
        print("  FAIL: empty confidence != 0"); ok = False
    mid = {"breakout_score": 0.8, "ma_score": 0.6, "value_score": 1.0,
           "momentum_score": 0.4, "regime_multiplier": 1.0}
    expected = 100 * (0.35*0.8 + 0.30*0.6 + 0.20*1.0 + 0.15*0.4)  # = 72.0
    if abs(confidence.score(mid) - expected) > 1e-9:
        print(f"  FAIL: mid confidence {confidence.score(mid)} != {expected}"); ok = False
    # Regime multiplier scales it.
    half = {**mid, "regime_multiplier": 0.5}
    if abs(confidence.score(half) - expected / 2) > 1e-9:
        print("  FAIL: regime multiplier not applied"); ok = False
    print(f"  OK confidence: perfect=100, mid={confidence.score(mid)}, half={confidence.score(half)}")

    # Risk table boundaries.
    cases = {59: 0.0, 60: 0.5, 69.9: 0.5, 70: 1.0, 80: 1.5, 89.9: 1.5, 90: 2.0, 100: 2.0}
    for conf, exp in cases.items():
        got = sizing.risk_fraction_for_confidence(conf)
        if got != exp:
            print(f"  FAIL: risk_fraction({conf}) = {got}, expected {exp}"); ok = False
    print("  OK risk table: " + ", ".join(f"{c}->{p}%" for c, p in cases.items()))

    # HARD 2% CAP: sweep ATRs and confidences; actual risk must never exceed 2%.
    equity, buying_power, entry = 10_000.0, 40_000.0, 100.0
    worst = 0.0
    for conf in (60, 70, 80, 90, 95, 100):
        for atr in (0.02, 0.1, 0.5, 1.0, 2.0, 5.0):
            plan = sizing.plan_position("CAP", conf, entry, atr, equity, buying_power)
            worst = max(worst, plan.dollar_risk_pct)
            if plan.dollar_risk_pct > config.MAX_RISK_PCT + 1e-9:
                print(f"  FAIL: risk {plan.dollar_risk_pct}% > cap at conf={conf} atr={atr}"); ok = False
            if plan.notional > buying_power + 1e-6:
                print(f"  FAIL: notional {plan.notional} > buying power"); ok = False
    print(f"  OK hard cap: worst-case risk over full sweep = {worst:.4f}% (cap {config.MAX_RISK_PCT}%)")

    # Specific: 95-confidence never risks more than 2% (the acceptance example).
    p95 = sizing.plan_position("NINE5", 95, 100.0, 1.0, 10_000.0, 40_000.0)
    if not (p95.tradable and p95.dollar_risk_pct <= config.MAX_RISK_PCT + 1e-9):
        print(f"  FAIL: 95-conf plan risk {p95.dollar_risk_pct}% > 2%"); ok = False
    else:
        print(f"  OK 95-conf plan: {p95.shares} sh, stop {p95.stop_price}, "
              f"tp {p95.take_profit_price}, risk ${p95.dollar_risk} ({p95.dollar_risk_pct}%)")

    # Skip conditions.
    skips = {
        "confidence<60": sizing.plan_position("S", 50, 100, 1, 10_000, 40_000),
        "already_held": sizing.plan_position("S", 95, 100, 1, 10_000, 40_000, held_symbols={"S"}),
        "max_concurrent": sizing.plan_position("S", 95, 100, 1, 10_000, 40_000,
                                               open_positions_count=config.MAX_CONCURRENT_POSITIONS),
    }
    for reason, plan in skips.items():
        if plan.tradable or plan.skip_reason is None:
            print(f"  FAIL: expected skip '{reason}' but plan tradable"); ok = False
    print("  OK skips: " + ", ".join(f"{p.skip_reason}" for p in skips.values()))

    print("  ALL OK" if ok else "  FAILURES above")
    return ok


def _live() -> bool:
    print("\n[2] Live: account + sized plans for the watchlist")
    acct = broker.account_summary()
    equity, bp = acct["equity"], acct["buying_power"]
    print(f"  account: equity ${equity:,.2f}  buying power ${bp:,.2f}  ({'PAPER' if acct['paper'] else 'LIVE'})")
    held = broker.open_position_symbols()
    print(f"  open positions: {sorted(held) or 'none'}")

    results = signals.evaluate_watchlist()
    rows = []
    for ev in results:
        conf = confidence.score(ev)
        plan = sizing.plan_position(
            ev["symbol"], conf, ev["close"] or 0.0, ev["atr"] or 0.0, equity, bp,
            held_symbols=held, open_positions_count=len(held),
        )
        rows.append((ev, conf, plan))

    rows.sort(key=lambda r: r[1], reverse=True)
    print(f"\n  {'SYM':6} {'conf':>6} {'type':8} {'shares':>6} {'entry':>8} {'stop':>8} {'tp':>8} {'risk$':>7} {'risk%':>6}  note")
    print("  " + "-" * 86)
    ok = True
    for ev, conf, p in rows:
        if p.dollar_risk_pct > config.MAX_RISK_PCT + 1e-9:
            ok = False
        note = p.skip_reason or "TRADE"
        print(f"  {p.symbol:6} {conf:6.2f} {str(ev['signal_type'] or '—'):8} "
              f"{p.shares:6d} {p.entry_price:8.2f} {p.stop_price:8.2f} {p.take_profit_price:8.2f} "
              f"{p.dollar_risk:7.2f} {p.dollar_risk_pct:6.3f}  {note}")
    tradable = sum(1 for _, _, p in rows if p.tradable)
    print(f"\n  {tradable}/{len(rows)} symbols would trade now. "
          f"Max risk on any plan <= {config.MAX_RISK_PCT}%: {'YES' if ok else 'NO'}")
    return ok


def main() -> int:
    print("=" * 72)
    print("USTradeWisBot — Phase 5: confidence scoring & position sizing")
    print("=" * 72)
    ok = _math_checks()
    ok = _live() and ok
    print("\n" + "=" * 72)
    print("RESULT:", "ALL GREEN ✅" if ok else "FAILURES ❌")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
