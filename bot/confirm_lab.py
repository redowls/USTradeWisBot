"""Delayed volume confirmation for the ORB entry — "must the volume arrive on the
break bar itself?"

**The question, and why it is not one already answered (IMP-066, 2026-09-30).**
``signals.orb_features`` evaluates two independent conditions on the *same* bar:

* ``fresh`` — this bar closes above the opening-range high and the prior bar did
  not, so a break fires once and never again; and
* ``low_volume`` — that same bar's ``rel_vol`` must reach ``ORB_MIN_REL_VOL``.

The conjunction is the trap. A break that crosses the level on ordinary volume is
refused, and because the break is then no longer ``fresh``, **it can never be
taken again no matter what volume does next.** ★ The motivating case is MSFT on
2026-09-29: it broke its opening range at 10:30 on ``rel_vol`` 0.894 and was
refused, then printed **2.148** on the very next bar and **1.729** on the one
after — both far above the 1.3 floor, both while price held above the level and
above VWAP, both inside the 11:30 window. Volume confirmed the break one bar
late, and the geometry had already disqualified it.

**This is explicitly NOT the "loosen the gate" question, which is refuted twice
over.** IMP-063 swept ``min_relvol`` and IMP-065 re-defined its baseline; the
2026-09-30 IEX re-run of that sweep returned ``CONFIRMED-INCUMBENT`` — 1.3 is the
held-out best of nine values on the feed the bot trades (+0.120R, PF 1.59), and
every relaxation's *added* trades are net negative (−0.026R at 1.2, −0.130R at
0.0). **That result is the premise here, not a contradiction of it:** the volume
floor discriminates, so the fix is to find more bars that clear it, never to
lower it. ``min_relvol`` stays at 1.3 in every cell this module scores.

**Construction — provably a one-dimension change.** The break geometry is
``entry_lab.rule_orb`` itself, called with the confirmation legs switched off, so
the fresh-break definition cannot drift from the live rule. The confirmation legs
are ``entry_lab._common`` — the same private helper every live-mirrored lab rule
shares — so the volume floor, the above-VWAP leg and the time cutoff are the live
code, not a reimplementation. ``confirm_bars=0`` therefore reproduces
``rule_orb`` bar for bar (pinned by ``assert_series_equal`` in the tests).

**Causality.** Every series is built from the current and prior bars only:
``fresh`` uses ``shift(1)``, the armed window counts *forward* from a break that
has already happened, and nothing is read from a bar later than the one being
scored. A break arms a window; the window cannot see into it.

Pure: no DB, no network, no config writes. **Nothing in the live path imports
this module** — it is lab tooling, like ``bot.entry_lab``, ``bot.entry_sweep``
and ``bot.volume_lab``, and a test asserts that by parsing the live modules' ASTs.
"""

from __future__ import annotations

import pandas as pd

from . import config, entry_lab

#: Parameter name of the swept dimension. ``0`` is the live behaviour: the volume
#: confirmation must land on the break bar itself.
DIM = "confirm_bars"

#: Live value of the dimension. The running bot has no such parameter, which is
#: exactly the point — its behaviour IS ``confirm_bars=0``, and naming that makes
#: the incumbent a real cell in the sweep instead of an implicit baseline.
LIVE_CONFIRM_BARS = 0

#: Legs that ``_common`` applies. Switched off to isolate the break geometry.
_GEOMETRY_ONLY = {"min_relvol": 0.0, "above_vwap": False, "cutoff": None}


def break_geometry(f: pd.DataFrame, p: dict) -> pd.Series:
    """The live fresh-break test with every confirmation leg switched off.

    Delegates to ``entry_lab.rule_orb`` so ``k``, the buffer and the
    once-per-break rule are the live rule's own code.
    """
    return entry_lab.rule_orb(f, {**p, **_GEOMETRY_ONLY})


def bars_since_break(f: pd.DataFrame, p: dict) -> pd.Series:
    """Bars elapsed since the most recent fresh break, 0 on the break bar itself.

    ``NaN`` before the session's first break. Resets every session: a break never
    arms a window in the following day. A *new* break re-arms from 0, so a
    re-break supersedes an unconfirmed earlier one rather than extending it.
    """
    fresh = break_geometry(f, p)
    pos = pd.Series(range(len(f)), index=f.index, dtype="float64")
    last = pos.where(fresh).groupby(f["day"], sort=False).ffill()
    return pos - last


def rule_orb_confirm(f: pd.DataFrame, p: dict) -> pd.Series:
    """ORB break whose volume confirmation may arrive up to ``confirm_bars`` late.

    A bar triggers when (a) a fresh break happened on it or within the previous
    ``confirm_bars`` bars of the same session, (b) price is **still** above the
    broken level — a break that has already failed back through it is dead, not
    pending — and (c) the live confirmation legs pass on *this* bar: ``rel_vol >=
    min_relvol``, above session VWAP, at or before the cutoff. Only the FIRST
    qualifying bar of each armed window fires, so one break is still one entry.

    ``confirm_bars=0`` is ``entry_lab.rule_orb``, exactly.
    """
    n = int(p.get(DIM, LIVE_CONFIRM_BARS))
    if n <= 0:
        return entry_lab.rule_orb(f, p)

    k = int(p.get("k", 6))
    level = f[f"or{k}_high"] * (1.0 + float(p.get("buffer_pct", 0.0)) / 100.0)
    age = bars_since_break(f, p)
    armed = age.notna() & (age <= n)
    # Still above the level: the thesis must survive the wait. Without this a
    # break that round-tripped below the range would be bought on the next
    # volume spike, which is a different (and worse) trade than a breakout.
    cond = armed & (f["close"] > level) & (f["bar_idx"] >= k)
    trig = entry_lab._common(f, p, cond)

    # One entry per break: keep the first qualifying bar in each armed window.
    # ``age`` identifies the window (bars sharing a break share ``pos - age``).
    window = (pd.Series(range(len(f)), index=f.index, dtype="float64") - age).fillna(-1.0)
    rank = trig.astype(int).groupby(window, sort=False).cumsum()
    return (trig & (rank == 1)).fillna(False).astype(bool)


def live_confirm_params() -> dict:
    """The running ORB gate, plus the dimension's live value.

    Reads ``bot.config`` through ``entry_sweep.live_orb_params`` so the base cell
    IS the running bot and cannot drift from it.
    """
    from . import entry_sweep

    return {**entry_sweep.live_orb_params(), DIM: LIVE_CONFIRM_BARS}


def confirmation_profile(
    f: pd.DataFrame, p: dict, max_bars: int = 6, mkt: pd.Series | None = None
) -> dict:
    """Diagnostic: of the fresh breaks this gate refuses on volume alone, how many
    print a qualifying ``rel_vol`` within 1..``max_bars`` bars?

    ``refused`` counts breaks that cleared every live leg *except* volume, so the
    numerator and denominator describe the same population the rule acts on.
    Returns ``{"admitted": n, "refused": n, "rescued": {bars: n}}``.
    """
    admitted = rule_orb_confirm(f, {**p, DIM: 0})
    if mkt is not None:
        m = mkt.reindex(f.index).fillna(False).astype(bool)
        admitted = admitted & m
    novol = entry_lab._common(f, {**p, "min_relvol": 0.0}, break_geometry(f, p))
    if mkt is not None:
        novol = novol & mkt.reindex(f.index).fillna(False).astype(bool)
    refused = novol & ~admitted
    out = {"admitted": int(admitted.sum()), "refused": int(refused.sum()), "rescued": {}}
    for n in range(1, int(max_bars) + 1):
        later = rule_orb_confirm(f, {**p, DIM: n})
        if mkt is not None:
            later = later & mkt.reindex(f.index).fillna(False).astype(bool)
        # A window that fires later than bar 0 is one the live gate had refused.
        out["rescued"][n] = int((later & ~admitted).sum())
    return out


def risk_invariants() -> dict:
    """The capital-protection constants, read back for the run's own record.

    This module cannot change them — it never writes config — and this function
    exists so a test can assert they are what the routine's mandate requires.
    """
    return {
        "MAX_RISK_PCT": float(config.MAX_RISK_PCT),
        "DAILY_LOSS_HALT_PCT": float(config.DAILY_LOSS_HALT_PCT),
        "MAX_CONCURRENT_POSITIONS": int(config.MAX_CONCURRENT_POSITIONS),
        "ENTRY_CUTOFF_ET": str(config.ENTRY_CUTOFF_ET),
        "FLATTEN_ET": str(config.FLATTEN_ET),
        "ORB_MIN_REL_VOL": float(config.ORB_MIN_REL_VOL),
        "BREAKEVEN_TRIGGER_R": float(config.BREAKEVEN_TRIGGER_R),
        "TRAIL_TRIGGER_R": float(config.TRAIL_TRIGGER_R),
    }
