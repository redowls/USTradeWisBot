"""IMP-021 regression tests — strong-breakout ("fade") entry veto.

Root cause (holdout-validated 2026-07-25): breakout_score is bimodal — a signal
either has no breakout (score ~0) or a real one (score >= 0.5). Joining all 189
recorded entry signals to their realized P&L showed the real-breakout leg is the
ENTIRE loss driver: skipping every entry with breakout_score >= 0.5 lifted the
whole book from -$2,024 to -$12. The effect held OUT-OF-SAMPLE — on the last 5
held-out sessions the skipped trades stayed net-losing (-$183) and the kept book
flipped positive (+$25). Fresh resistance breakouts fade (the same open-fade leak
IMP-017 chased), so we now veto the entry entirely rather than chase the spike.

This mirrors the existing VALUE_VETO_FLOOR over-extension veto: a vetoed breakout
does NOT fall back to an MA entry on the same bar — buying the breakout bar is the
problem regardless of the MA component. Pure-MA signals (no breakout) are untouched.
"""

from bot import config, signals


def test_strong_breakout_is_vetoed():
    # bo_score at/above the ceiling with healthy value -> skip entirely.
    assert config.BREAKOUT_FADE_CEILING == 0.5
    assert signals._classify(0.75, ma=0.0, value=0.9) is None
    assert signals._classify(0.5, ma=0.0, value=0.9) is None


def test_strong_breakout_with_ma_still_vetoed_not_both():
    # A strong breakout that also carries an MA signal must NOT become "BOTH" —
    # the breakout bar is the problem regardless of the MA component.
    assert signals._classify(0.6, ma=0.9, value=0.9) is None


def test_weak_breakout_still_allowed():
    # A sub-ceiling breakout with healthy value is still a BREAKOUT entry.
    assert signals._classify(0.25, ma=0.0, value=0.9) == "BREAKOUT"


def test_pure_ma_untouched_by_veto():
    # No breakout component -> MA entry, unaffected by the breakout ceiling.
    assert signals._classify(0.0, ma=0.9, value=0.9) == "MA"


def test_value_veto_still_applies_below_ceiling():
    # The pre-existing over-extension veto still fires for a weak, extended breakout.
    assert signals._classify(0.25, ma=0.0, value=0.10) is None
