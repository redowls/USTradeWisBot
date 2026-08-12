"""Break-even trigger sweep (IMP-032) — scripts/exit_geometry.breakeven_candidates.

The sweep exists because the post-gate stop loss is concentrated in trades that
peaked BELOW the +0.5R break-even trigger and were never armed. These tests pin
it to the two 2026-08-12 trades that frame the question, using that session's
real IEX 1-min bars so the sweep cannot start reporting rescues it cannot deliver.
"""

import pandas as pd
import pytest

from bot.exit_sim import ExitGeometry, simulate_exit
from scripts.exit_geometry import BREAKEVEN_SWEEP, breakeven_candidates

LIVE = ExitGeometry(breakeven_trigger_r=0.5, trail_trigger_r=0.5,
                    trail_distance_r=0.5, ratchet_min_pct=0.10)

# --- QCOM #249, 2026-08-12 ---------------------------------------------------
# Filled 164.6573 at 09:56:02 ET, plan stop 162.07 (1R = 2.5873), take-profit
# 168.24, stopped out 10:43 at 161.94 for -$40.76. Every 1-min bar from the entry
# minute to the stop, (high, low), exactly as the IEX feed printed them. The
# session high over the whole hold is 164.53 — BELOW the fill — so the trade
# never once traded green.
QCOM_BARS = [
    (164.53, 164.53), (164.30, 164.17), (164.17, 164.16), (164.14, 163.73),
    (163.57, 163.28), (163.18, 162.97), (163.23, 163.23), (163.30, 163.25),
    (163.37, 163.16), (163.57, 163.47), (163.50, 163.45), (163.59, 163.47),
    (163.82, 163.62), (163.77, 163.63), (163.66, 163.47), (163.72, 163.63),
    (163.54, 163.44), (163.53, 163.43), (163.79, 163.68), (163.79, 163.79),
    (164.00, 163.82), (164.03, 164.03), (163.78, 163.68), (164.02, 163.89),
    (164.22, 163.90), (163.95, 163.95), (163.99, 163.88), (163.98, 163.94),
    (163.96, 163.96), (163.73, 163.51), (163.51, 163.41), (163.26, 162.81),
    (162.97, 162.97), (163.01, 163.01), (162.76, 162.76), (162.31, 162.15),
    (162.56, 162.56), (162.60, 162.52), (162.56, 162.56), (162.36, 162.36),
    (162.65, 162.59), (162.51, 162.49), (162.38, 162.25), (162.00, 162.00),
]
QCOM = dict(entry=164.6573, stop=162.07, tp=168.24, fallback=163.22)

# --- WMT #247, 2026-08-12 ----------------------------------------------------
# Filled 113.4943 at 09:43:41 ET, plan stop 111.78 (1R = 1.7143), take-profit
# 116.03, flattened 15:57 at 115.84 for +$49.26 — the day's best trade. Reduced
# to that session's real HOURLY (high, low) extremes from the entry hour to the
# 15:55 flatten; the reduction preserves what the ratchet reads (the running high
# and every low that could take the stop out) without carrying 372 rows.
WMT_BARS = [
    (114.85, 113.40),   # 09:43-09:59, low = the 09:43 entry bar
    (115.39, 114.51),   # 10:xx
    (115.28, 114.64),   # 11:xx
    (115.20, 114.81),   # 12:xx
    (115.59, 115.05),   # 13:xx
    (115.74, 115.24),   # 14:xx
    (115.91, 115.25),   # 15:00-15:55
]
WMT = dict(entry=113.4943, stop=111.78, tp=116.03, fallback=115.86)


def _frame(bars: list[tuple[float, float]]) -> pd.DataFrame:
    return pd.DataFrame(bars, columns=["high", "low"])


def _run(trade: dict, bars: list[tuple[float, float]], geometry: ExitGeometry):
    return simulate_exit(_frame(bars), trade["entry"], trade["stop"],
                         trade["tp"], trade["fallback"], geometry)


def test_sweep_varies_only_the_breakeven_trigger():
    cands = breakeven_candidates(LIVE, [0.3, 0.25])
    assert [c.breakeven_trigger_r for c in cands] == [0.5, 0.3, 0.25]
    for c in cands:
        assert c.trail_trigger_r == LIVE.trail_trigger_r
        assert c.trail_distance_r == LIVE.trail_distance_r
        assert c.ratchet_min_pct == LIVE.ratchet_min_pct
        assert c.trailing_enabled is LIVE.trailing_enabled


def test_sweep_always_carries_the_live_trigger_as_its_baseline():
    """Without the live row the sweep would have no reference to be judged against."""
    assert LIVE.breakeven_trigger_r not in BREAKEVEN_SWEEP
    triggers = [c.breakeven_trigger_r for c in breakeven_candidates(LIVE, BREAKEVEN_SWEEP)]
    assert triggers[0] == LIVE.breakeven_trigger_r
    assert triggers == sorted(triggers, reverse=True)
    assert len(triggers) == len(set(triggers))       # live value not duplicated
    dupe = [c.breakeven_trigger_r for c in breakeven_candidates(LIVE, [0.5, 0.5, 0.3])]
    assert dupe == [0.5, 0.3]


@pytest.mark.parametrize("trigger", [0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.05])
def test_no_breakeven_trigger_can_rescue_qcom_249(trigger):
    """QCOM never printed above its fill, so NO trigger can arm — it is not a
    break-even failure and the sweep must never claim it as a rescue.

    This is the 2026-08-12 loss (-$40.76, MFE -0.05R) that motivated IMP-032:
    it is an ENTRY-quality loss, and lowering the exit trigger is not its fix.
    """
    res = _run(QCOM, QCOM_BARS, ExitGeometry(trigger, 0.5, 0.5, 0.10))
    assert res.exit_reason == "STOP"
    assert res.exit_price == pytest.approx(QCOM["stop"])
    assert res.armed_breakeven is False
    assert res.armed_trail is False
    # ExitSimResult.mfe is floored at 0.0 by simulate_exit, so "no favorable
    # excursion was ever recorded" is the strongest statement available here.
    # The raw-bar MFE is -0.05R (session high 164.53 vs the 164.6573 fill).
    assert res.mfe == 0.0
    assert max(h for h, _ in QCOM_BARS) < QCOM["entry"]


@pytest.mark.parametrize("trigger", [0.5, 0.4, 0.35, 0.3, 0.25, 0.2])
def test_lowering_the_trigger_does_not_scratch_wmt_247(trigger):
    """The day's winner must survive every trigger in the sweep.

    WMT's lowest print after the ratchet first armed was 114.39, comfortably
    above the 113.4943 entry, so an earlier break-even stop is never touched and
    the trade still runs to the flatten. This is the cost side the raw
    'stops rescued' count ignores — the sweep has to keep pricing it.
    """
    res = _run(WMT, WMT_BARS, ExitGeometry(trigger, 0.5, 0.5, 0.10))
    assert res.exit_reason == "EOD_FLATTEN"
    assert res.exit_price == pytest.approx(WMT["fallback"])
    assert res.final_stop > WMT["entry"]     # trail carried it above entry
    assert res.armed_breakeven is True
