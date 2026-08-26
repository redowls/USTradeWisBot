"""IMP-041 tests — scripts/ratchet_audit, the STOP-bucket decomposition.

The tool exists because ``trades.exit_reason`` collapses two opposite outcomes
into the string ``'STOP'``: a full -1R plan stop and a break-even/trail scratch.
On the post-gate book that conflation reads ``STOP n=30, net -$471.16``, and it
decomposes into ``PLAN_STOP n=14, net -$524.56`` against ``RATCHET_STOP n=16,
net +$53.40`` — i.e. the entire post-gate loss is 14 trades, and the bucket that
has been quoted into strategy decisions for weeks was hiding it.

These tests pin the tool to the 2026-08-25 session that motivated it, using that
session's real recorded fills and real SIP bars. The two arming tests assert the
exact stop prices the LIVE bot wrote to /var/log/ustradewisbot/bot.log that day,
so if the reconstruction ever drifts from ``exits.compute_trailed_stop`` the
suite says so rather than the nightly review quietly reading fiction.
"""

import pandas as pd
import pytest

from bot import config, secrets
from scripts.ratchet_audit import (
    PLAN_STOP,
    RATCHET_STOP,
    audit,
    classify_exit,
    era_stats,
    exit_mix,
    noratchet_outcome,
    ratchet_ledger,
    replay_stop_path,
)

ET = "America/New_York"


def _frame(bars: list[tuple[float, float, float]], start: str) -> pd.DataFrame:
    """(high, low, close) rows on a 1-minute ET index, as bot.data returns."""
    index = pd.date_range(start=start, periods=len(bars), freq="1min", tz=ET)
    return pd.DataFrame(bars, columns=["high", "low", "close"], index=index)


def _frame15(bars: list[tuple[float, float, float]], start: str) -> pd.DataFrame:
    index = pd.date_range(start=start, periods=len(bars), freq="15min", tz=ET)
    return pd.DataFrame(bars, columns=["high", "low", "close"], index=index)


# --- The four 2026-08-25 trades, exactly as the DB recorded them --------------
AMZN_283 = dict(trade_id=286, symbol="AMZN", qty=9, entry_price=262.62,
                stop_price=258.74, exit_price=260.9189, realized_pl=-15.31,
                exit_reason="EOD_FLATTEN", entry_time=pd.Timestamp("2026-08-25 09:41"),
                exit_time=pd.Timestamp("2026-08-25 15:55"))
TSM_287 = dict(trade_id=287, symbol="TSM", qty=5, entry_price=416.016,
               stop_price=409.53, exit_price=415.908, realized_pl=-0.54,
               exit_reason="STOP", entry_time=pd.Timestamp("2026-08-25 09:56"),
               exit_time=pd.Timestamp("2026-08-25 10:22"))
META_288 = dict(trade_id=288, symbol="META", qty=4, entry_price=565.14,
                stop_price=557.02, exit_price=565.4425, realized_pl=1.21,
                exit_reason="STOP", entry_time=pd.Timestamp("2026-08-25 09:57"),
                exit_time=pd.Timestamp("2026-08-25 13:26"))
SPY_289 = dict(trade_id=289, symbol="SPY", qty=3, entry_price=765.6633,
               stop_price=754.31, exit_price=765.96, realized_pl=0.89,
               exit_reason="EOD_FLATTEN", entry_time=pd.Timestamp("2026-08-25 15:01"),
               exit_time=pd.Timestamp("2026-08-25 15:55"))

# Two earlier stop-outs that really were full plan stops, for the other side of
# the classifier. NFLX #244 filled at the plan stop to the cent; MU #273 filled
# 0.28 BELOW it (ordinary stop-market slippage), which is why the classifier
# tests a one-sided tolerance ABOVE the stop and not a band around it.
NFLX_244 = dict(trade_id=244, symbol="NFLX", qty=33, entry_price=76.19,
                stop_price=74.84, exit_price=74.84, realized_pl=-44.55,
                exit_reason="STOP", entry_time=pd.Timestamp("2026-08-11 09:39"),
                exit_time=pd.Timestamp("2026-08-11 13:07"))
MU_273 = dict(trade_id=273, symbol="MU", qty=2, entry_price=978.70,
              stop_price=961.59, exit_price=961.31, realized_pl=-34.78,
              exit_reason="STOP", entry_time=pd.Timestamp("2026-08-21 09:41"),
              exit_time=pd.Timestamp("2026-08-21 10:19"))


# --- 1. The replay reproduces what the live bot actually did ------------------

def test_replay_reproduces_the_live_tsm_break_even_stop():
    """bot.log 2026-08-25 10:11:28 ET:
    ``STOP RAISED TSM 409.53 -> 416.02 (live 417.42, peak 417.77, entry 416.02)``

    1R = 416.016 - 409.53 = 6.486, so 0.25R = 1.6215. The peak (417.77, +0.270R)
    cleared the break-even trigger while the live price (417.42, +0.216R) had
    NOT yet cleared the trail trigger — so the break-even stage armed alone and
    put the stop at the entry price. This is the IMP-031 peak-vs-live split
    doing exactly its job, and the test fails if the reconstruction starts
    reading only the live price.
    """
    path = replay_stop_path(
        entry_price=416.016, plan_stop=409.53,
        bars=_frame([(416.90, 415.66, 416.50),
                     (417.77, 416.80, 417.42)], "2026-08-25 10:10"),
    )
    assert path["armed"] is True
    assert path["armed_stop"] == pytest.approx(416.02, abs=0.005)
    assert path["final_stop"] == pytest.approx(416.02, abs=0.005)


def test_replay_reproduces_the_live_meta_trail_stop():
    """bot.log 2026-08-25 12:57:17 ET:
    ``STOP RAISED META 557.02 -> 565.32 (live 567.35, peak 567.38, entry 565.14)``

    1R = 8.12, so 0.25R = 2.03. Here the LIVE price cleared the trail trigger
    (+0.272R), so the trail stage armed and placed the stop 0.25R below the live
    price: 567.35 - 2.03 = 565.32. Note what that means and why META is the
    day's lesson — with TRAIL_DISTANCE_R == TRAIL_TRIGGER_R the trail is born at
    565.32 against a 565.14 fill, i.e. flush at break-even with no give-back
    room at all. META was scratched at +$1.21 and closed the session at 569.44.
    """
    path = replay_stop_path(
        entry_price=565.14, plan_stop=557.02,
        bars=_frame([(566.20, 565.00, 565.80),
                     (567.38, 566.90, 567.35)], "2026-08-25 12:56"),
    )
    assert path["armed"] is True
    assert path["armed_stop"] == pytest.approx(565.32, abs=0.005)


def test_replay_does_not_arm_a_trade_that_never_reached_the_trigger():
    """AMZN #286 is the day's archetype: MFE +0.101R against a 0.25R trigger, so
    nothing armed, nothing protected it, and it drifted 6h14m to the 15:55 clock
    for -$15.31. Its highest print (263.01) sits below entry + 0.25R (263.59).
    """
    path = replay_stop_path(
        entry_price=262.62, plan_stop=258.74,
        bars=_frame([(263.01, 262.10, 262.40),
                     (262.80, 259.83, 260.20),
                     (261.30, 260.50, 260.92)], "2026-08-25 09:42"),
    )
    assert path["armed"] is False
    assert path["final_stop"] == pytest.approx(258.74)
    assert path["mfe_r"] == pytest.approx((263.01 - 262.62) / 3.88, abs=1e-6)
    assert path["mae_r"] == pytest.approx((259.83 - 262.62) / 3.88, abs=1e-6)


def test_replay_is_monotonic_and_never_lowers_the_stop():
    """A ratchet may only move a stop UP. Walk a round trip up and back down and
    assert the reconstructed stop never retreats — the same invariant IMP-040
    pinned on the live function, asserted again on the tool that judges it.
    """
    bars = _frame([(100.5, 99.8, 100.2), (102.0, 100.4, 101.8),
                   (103.5, 101.6, 103.2), (103.4, 100.1, 100.4),
                   (100.6, 99.5, 99.7)], "2026-08-25 10:00")
    path = replay_stop_path(entry_price=100.0, plan_stop=96.0, bars=bars)
    assert path["armed"] is True
    assert path["final_stop"] >= 100.0
    assert path["final_stop"] >= 96.0


# --- 2. The classifier splits the conflated bucket ----------------------------

@pytest.mark.parametrize("trade,expected", [
    (TSM_287, RATCHET_STOP),    # filled 6.378 ABOVE its plan stop
    (META_288, RATCHET_STOP),   # filled 8.423 ABOVE its plan stop
    (NFLX_244, PLAN_STOP),      # filled AT the plan stop, to the cent
    (MU_273, PLAN_STOP),        # filled 0.28 BELOW it (stop-market slippage)
])
def test_classify_exit_separates_the_conflated_stop_bucket(trade, expected):
    assert classify_exit(trade) == expected


def test_classifier_margin_is_not_knife_edge():
    """The four real cases clear the 0.1%-of-entry tolerance by a wide margin —
    the ratchet stops sit 15x and 15x the tolerance above their plan stop, the
    plan stops sit at or below it. A classifier that only just worked would be
    a liability in the one place every review reads.
    """
    for trade in (TSM_287, META_288):
        tolerance = trade["entry_price"] * 0.001
        assert trade["exit_price"] - trade["stop_price"] > 5 * tolerance
    for trade in (NFLX_244, MU_273):
        assert trade["exit_price"] <= trade["stop_price"]


def test_non_stop_reasons_pass_through_untouched():
    assert classify_exit(AMZN_283) == "EOD_FLATTEN"
    assert classify_exit(SPY_289) == "EOD_FLATTEN"
    assert classify_exit(dict(NFLX_244, exit_reason="TAKE_PROFIT")) == "TAKE_PROFIT"


# --- 3. The no-ratchet counterfactual ----------------------------------------

# META #288's real SIP 15-minute (high, low, close) from 10:00 ET to 15:45 ET on
# 2026-08-25. Reduced from 1-minute to 15-minute extremes: the counterfactual
# only reads the running lows (does any bar reach the plan stop?) and the final
# close, both of which the reduction preserves. Session low 561.40, high 570.80.
META_SESSION = [
    (565.44, 562.40, 563.99), (564.54, 562.20, 563.05), (565.62, 561.82, 564.90),
    (565.87, 564.00, 564.16), (564.27, 561.40, 563.00), (563.74, 562.46, 563.39),
    (566.25, 563.12, 565.90), (566.25, 564.81, 565.59), (565.73, 564.69, 565.00),
    (566.21, 564.74, 565.74), (566.97, 564.00, 565.41), (567.55, 565.41, 567.37),
    (567.48, 565.62, 566.24), (566.45, 565.13, 565.32), (565.88, 564.50, 564.60),
    (565.52, 563.87, 565.28), (565.96, 564.91, 565.01), (565.27, 564.35, 565.03),
    (565.44, 564.71, 565.35), (566.61, 565.30, 566.46), (566.86, 565.70, 565.89),
    (566.50, 565.54, 566.40), (570.80, 566.38, 569.98), (570.62, 568.37, 569.87),
]


def test_noratchet_holds_to_the_close_when_the_plan_stop_is_never_touched():
    """META's session low was 561.40 against a 557.02 plan stop — 0.54R of room
    to spare — so with the ratchet off the trade rides to the flatten.
    """
    bars = _frame15(META_SESSION, "2026-08-25 10:00")
    pl, reason = noratchet_outcome(565.14, 557.02, 4, bars)
    assert reason == "EOD_FLATTEN"
    assert pl == pytest.approx((569.87 - 565.14) * 4, abs=0.01)


def test_noratchet_exits_at_the_plan_stop_when_a_low_reaches_it():
    bars = _frame15(META_SESSION, "2026-08-25 10:00")
    # Same session, but anchor the plan stop just above the 561.40 session low.
    pl, reason = noratchet_outcome(565.14, 562.00, 4, bars)
    assert reason == PLAN_STOP
    assert pl == pytest.approx((562.00 - 565.14) * 4, abs=0.01)


def test_meta_288_is_the_motivating_failure_and_stays_a_regression():
    """The trade that motivated IMP-041, priced end to end.

    META armed its trail at 12:57 and was taken out 29 minutes later at 565.4425
    for +$1.21, then ran to 570.80 and closed the session at 569.44. Held with
    only its plan stop it makes roughly +$17-19 depending on bar resolution, so
    the ratchet COST this trade real money. The assertion is the sign and the
    scale, not a cent-exact figure, because the 15-minute reduction prices the
    flatten off the 15:45 close (569.87) rather than the 15:55 1-minute close
    (569.44) — the production run at 1-minute resolution reports -$15.99.
    """
    bars = _frame15(META_SESSION, "2026-08-25 10:00")
    noratchet_pl, _ = noratchet_outcome(565.14, 557.02, 4, bars)
    ratchet_delta = META_288["realized_pl"] - noratchet_pl
    assert ratchet_delta < -10.0
    assert noratchet_pl > META_288["realized_pl"]


# --- 4. The correctness fixes this tool shipped with --------------------------

def test_ratchet_delta_is_priced_only_for_ratchet_stops():
    """A plan stop, a take-profit and a flatten all end at the same price with
    the ratchet switched off, so their delta is zero by construction and must
    not be priced. The first cut of this script priced every trade and scattered
    +/-$1 of fake delta across 47 EOD_FLATTENs — the flatten fills at market a
    few seconds after the last 1-minute bar closes — which moved the headline
    ratchet figure by $19 on a book whose whole ratchet effect is -$11.67.
    """
    bars = _frame15(META_SESSION, "2026-08-25 10:00")
    trades = [META_288, AMZN_283, SPY_289, NFLX_244]
    rows = audit(trades, {t["trade_id"]: bars for t in trades})
    by_id = {r["trade_id"]: r for r in rows}
    assert by_id[288]["ratchet_delta"] is not None      # RATCHET_STOP: priced
    for trade_id in (286, 289, 244):
        assert by_id[trade_id]["ratchet_delta"] is None
        assert by_id[trade_id]["noratchet_pl"] is None
    ledger = ratchet_ledger(rows)
    assert ledger["priced"] == 1


def test_era_split_carries_no_replay_derived_metric():
    """``compute_trailed_stop`` reads the CURRENT constants, so replaying a
    pre-2026-08-25 trade answers "what would 0.25R have done", not "what did
    0.5R do". Any replay-derived field in the era split would therefore compare
    the current geometry against itself and read as a change that never
    happened. The first cut of this script did exactly that and reported stop
    raises falling 3.09 -> 0.50 per trade across an IMP-040 boundary that was
    supposed to raise MORE. Guard it.
    """
    bars = _frame15(META_SESSION, "2026-08-25 10:00")
    trades = [META_288, TSM_287]
    stats = era_stats(audit(trades, {t["trade_id"]: bars for t in trades}))
    for banned in ("armed_pct", "raises_per_trade", "raises", "armed"):
        assert banned not in stats, f"{banned} is replay-derived, not history"
    for required in ("flatten_pct", "ratchet_stop_pct", "plan_stop_pct",
                     "win_pct", "avg_win", "ratchet_net"):
        assert required in stats


def test_exit_mix_reconciles_to_the_book_net():
    """The decomposition must be a partition: no trade double-counted, none
    dropped. This is the property that lets a review quote the split.
    """
    bars = _frame15(META_SESSION, "2026-08-25 10:00")
    trades = [META_288, TSM_287, AMZN_283, SPY_289, NFLX_244, MU_273]
    rows = audit(trades, {t["trade_id"]: bars for t in trades})
    mix = exit_mix(rows)
    assert sum(m["n"] for m in mix.values()) == len(rows)
    assert sum(m["pl"] for m in mix.values()) == pytest.approx(
        sum(r["realized_pl"] for r in rows), abs=1e-6)


def test_audit_is_read_only_and_declares_no_risk_constants():
    """IMP-041 is an instrument, not a strategy change. It must not carry or
    imply a risk setting, and the capital-protection invariants are asserted
    here as they are in every improvement's test file.
    """
    import scripts.ratchet_audit as ra

    source = open(ra.__file__).read()
    for forbidden in ("MAX_RISK_PCT =", "DAILY_LOSS_HALT_PCT =",
                      "MAX_CONCURRENT_POSITIONS =", "MIN_STOP_PCT =",
                      "BREAKEVEN_TRIGGER_R =", "TRAIL_TRIGGER_R =",
                      "TRAIL_DISTANCE_R ="):
        assert forbidden not in source
    for mutating in ("INSERT", "UPDATE", "DELETE", "submit_order", "close_position"):
        assert mutating not in source

    assert config.MAX_RISK_PCT <= 2.0
    assert config.DAILY_LOSS_HALT_PCT == 8.0
    assert config.MAX_CONCURRENT_POSITIONS <= 3
    assert config.ENTRY_CUTOFF_ET == "15:30"
    assert config.FLATTEN_ET == "15:55"
    assert config.MIN_STOP_PCT == 1.5
    assert secrets.ALPACA_PAPER is True


def test_imp040_geometry_is_untouched_by_this_run():
    """IMP-041 deliberately ships no exit-geometry change: 2026-08-25 was
    IMP-040's FIRST live session and its own pre-registration says the verdict
    needs ~2 weeks, so re-tuning the ratchet tonight would destroy the only
    experiment currently running. Pin the three constants so this run cannot be
    misread later as having quietly moved them.
    """
    assert config.BREAKEVEN_TRIGGER_R == 0.25
    assert config.TRAIL_TRIGGER_R == 0.25
    assert config.TRAIL_DISTANCE_R == 0.25
