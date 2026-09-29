"""Volume-confirmation lab — "is the ORB volume gate measuring volume, or the clock?"

**The defect this exists to test (IMP-065, 2026-09-29).** The live ORB entry
requires ``rel_vol >= ORB_MIN_REL_VOL`` (1.3) on the trigger bar, where
``indicators.relative_volume`` is *this bar's volume divided by the mean of the
prior ``REL_VOL_LOOKBACK`` (20) bars*. On a 5-minute chart 20 bars is 100
minutes, so inside the ORB window (breaks legal from bar 6 = 10:00 ET to the
11:30 cutoff) that denominator is **dominated by the opening bars — the highest
volume bars of the day.** Intraday volume is U-shaped; the gate therefore
compares a bar in the volume trough against an average anchored on the peak.

Measured on 216 live sessions of SIP 5-min bars (2026-09-02..09-28, 12 symbols),
the share of bars clearing ``rel_vol >= 1.3``:

====== ============ ================
bar_idx  median rv    % clearing 1.3
====== ============ ================
0 (09:30)     3.90            91.2
2 (09:40)     1.31            48.1
5 (09:55)     0.83            11.1
**6 (10:00)** 0.87        **14.4**   <- first bar an ORB break is legal
7-17          0.49-0.71    0.5-6.9   <- the bulk of the legal window
24 (11:30)    0.70             8.8
====== ============ ================

So the gate is **near-unclearable in exactly the window the entry is allowed to
fire in**: median in-window ``rel_vol`` is ~0.55 against a 1.3 floor, and only
~2-7% of bars clear. It is not asking "is this bar busy?", it is asking "is it
still 09:35?" — and inside the ORB window the answer is always no.

2026-09-28 is the motivating session: **ten distinct in-window ORB candidates,
zero fills, and not one candidate printed ``rel_vol >= 1.3``** (0.567, 0.626,
0.654, 0.676, 0.719, 0.915, 0.942, 1.125, 1.252 — WMT and PANW the near misses).
The breaks that *did* clear 1.3 that day all came AFTER the cutoff (AMZN 13:10 at
8.93, SPY 13:10 at 3.19, PLTR 13:10 at 1.87, MSFT 15:40 at 1.65) — a fresh burst
against a low midday baseline. **The volume gate and the cutoff are fighting each
other: the gate mostly passes candidates the cutoff then refuses.**

★ This is *not* the "loosen the gate" question IMP-063 already refuted. That run
searched ``min_relvol in {0.0, 1.3}`` and 1.3 won on held-out data — i.e.
*removing* volume confirmation is worse. The question here is whether the same
requirement, **measured against a baseline that is not the opening spike**, is
better than both. Three definitions are scored head to head:

* ``live``    — ``vol / mean(prior 20 bars)``; the shipped definition, the
                incumbent cell, and the baseline every candidate must beat.
* ``tod``     — ``vol / median(volume at the SAME bar_idx over the prior N
                sessions)``. Time-of-day normalised: "busier than this time of
                day usually is", which is what a trader means by relative
                volume. Uses strictly prior sessions, so there is no lookahead.
* ``session`` — ``vol / mean(today's bars after the opening range, strictly
                before this one)``. No cross-session history needed; blind at
                exactly bar ``k`` (no prior post-range bar yet), where it fails
                CLOSED.

**Re-aiming, not relaxing.** Every definition keeps a volume floor and the floor
is chosen in-sample; a normalised gate *rejects* early-window breaks that only
passed because the stale denominator was still beatable, as well as admitting
genuine mid-window surges. Whether that trade is worth making is decided by
``entry_sweep.sweep_verdict`` — ``entry_lab.gate`` with the live configuration
supplied as the incumbent — never by the throughput count.

Pure: no DB, no network, no config writes. Features and the market overlay are
passed in, exactly as ``entry_lab.run_rule`` takes them. **Nothing in the live
path imports this module** — it is lab tooling, like ``bot.entry_lab`` and
``bot.entry_sweep``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, entry_lab

#: Sessions of history the ``tod`` baseline medians over. 20 sessions ~= one
#: month: long enough that one abnormal day cannot set the bar, short enough to
#: track a symbol's changing liquidity. Median, not mean, so an earnings day in
#: the window does not lift the baseline for the next month.
TOD_LOOKBACK_SESSIONS = 20

#: Minimum prior sessions before ``tod`` will produce a baseline at all. Below
#: this the baseline is NaN and the gate fails CLOSED — a symbol with no history
#: does not get a free pass, which is the same direction every other gate in
#: this repo fails (``signals.orb_market_ok`` fails closed on missing bars).
TOD_MIN_SESSIONS = 5

#: Column each definition reads. ``live`` deliberately points at the very column
#: ``entry_lab._common`` uses, so the ``live`` cell reproduces ``rule_orb`` at
#: live parameters exactly rather than approximating it.
VOL_COLUMNS: dict[str, str] = {
    "live": "rel_vol",
    "tod": "tod_rel_vol",
    "session": "ses_rel_vol",
}


def tod_volume_baseline(
    f: pd.DataFrame,
    lookback: int = TOD_LOOKBACK_SESSIONS,
    min_sessions: int = TOD_MIN_SESSIONS,
) -> pd.Series:
    """Median volume at each bar's own ``bar_idx`` over the PRIOR sessions.

    ``shift(1)`` on the session axis before the rolling median is what makes this
    causal: a bar is never compared against its own session, so nothing here can
    leak the future into a backtest. Returns NaN until ``min_sessions`` prior
    sessions exist for that ``bar_idx``.
    """
    if f is None or f.empty:
        return pd.Series(dtype=float)
    # A nonsense constant must degrade, not raise: clamp to one prior session and
    # keep min_periods inside the window. Erring toward a SHORTER window is the
    # safe direction here — a short baseline is noisy (measured: a 1-session
    # baseline fails the gate), it never fabricates permission the way a
    # missing/open gate would. Same contract as coverage.check's lookback.
    lookback = max(1, int(lookback))
    min_sessions = min(max(1, int(min_sessions)), lookback)
    wide = (
        pd.DataFrame({
            "day": f["day"].to_numpy(),
            "bar_idx": f["bar_idx"].to_numpy(),
            "volume": f["volume"].astype(float).to_numpy(),
        })
        .pivot_table(index="day", columns="bar_idx", values="volume", aggfunc="last")
        .sort_index()
    )
    base = wide.shift(1).rolling(lookback, min_periods=min_sessions).median()
    vals = base.to_numpy(dtype=float)
    di = base.index.get_indexer(pd.Index(f["day"].to_numpy()))
    ci = base.columns.get_indexer(pd.Index(f["bar_idx"].to_numpy()))
    out = np.full(len(f), np.nan)
    ok = (di >= 0) & (ci >= 0)
    out[ok] = vals[di[ok], ci[ok]]
    return pd.Series(out, index=f.index)


def session_volume_baseline(f: pd.DataFrame, k: int | None = None) -> pd.Series:
    """Mean volume of today's bars from ``bar_idx`` ``k`` up to (not incl.) this one.

    Excluding the first ``k`` bars is the whole point — those are the opening
    range, and including them reintroduces the bias this module exists to
    measure. NaN at and before ``bar_idx == k`` (no prior post-range bar), so the
    first bar an ORB break is legal on is blind and the gate fails CLOSED there.
    """
    if f is None or f.empty:
        return pd.Series(dtype=float)
    k = int(config.ORB_RANGE_BARS if k is None else k)
    v = f["volume"].astype(float)
    post = f["bar_idx"] >= k
    vol_post = v.where(post, 0.0)
    cnt_post = post.astype(float)
    day = f["day"]
    # cumsum minus the current bar == strictly-prior bars of the same session.
    csum = vol_post.groupby(day, sort=False).cumsum() - vol_post
    ccnt = cnt_post.groupby(day, sort=False).cumsum() - cnt_post
    return csum / ccnt.where(ccnt > 0)


def add_volume_features(
    f: pd.DataFrame,
    k: int | None = None,
    lookback: int = TOD_LOOKBACK_SESSIONS,
    min_sessions: int = TOD_MIN_SESSIONS,
) -> pd.DataFrame:
    """``entry_lab.precompute_features`` output plus ``tod_rel_vol`` / ``ses_rel_vol``.

    Returns a copy; the caller's frame is never mutated. Additive by design, so a
    frame carrying these columns is still a valid input to every ``entry_lab``
    rule and the ``live`` definition keeps reading the untouched ``rel_vol``.
    """
    out = f.copy()
    if out.empty:
        for col in ("tod_rel_vol", "ses_rel_vol"):
            out[col] = pd.Series(dtype=float)
        return out
    tod_base = tod_volume_baseline(out, lookback, min_sessions)
    ses_base = session_volume_baseline(out, k)
    vol = out["volume"].astype(float)
    out["tod_rel_vol"] = vol / tod_base.where(tod_base > 0)
    out["ses_rel_vol"] = vol / ses_base.where(ses_base > 0)
    return out


def add_volume_features_all(
    feats: dict[str, pd.DataFrame], k: int | None = None,
    lookback: int = TOD_LOOKBACK_SESSIONS, min_sessions: int = TOD_MIN_SESSIONS,
) -> dict[str, pd.DataFrame]:
    """``add_volume_features`` per symbol. Baselines are per-symbol by construction."""
    return {s: add_volume_features(f, k, lookback, min_sessions) for s, f in feats.items()}


def volume_ok(f: pd.DataFrame, spec) -> pd.Series:
    """Boolean: does each bar clear ``spec`` = ``(definition, threshold)``?

    A NaN baseline (too little history for ``tod``, bar ``k`` for ``session``)
    yields False — fail CLOSED. A falsy threshold disables the leg entirely,
    which is how the "no volume confirmation" reference cell is expressed.
    """
    name, thresh = str(spec[0]), float(spec[1])
    try:
        col = VOL_COLUMNS[name]
    except KeyError:
        raise ValueError(f"unknown volume definition {name!r}; expected one of "
                         f"{sorted(VOL_COLUMNS)}") from None
    if not thresh:
        return pd.Series(True, index=f.index)
    if col not in f.columns:
        raise KeyError(f"{col!r} missing — call add_volume_features() first")
    return (f[col] >= thresh).fillna(False).astype(bool)


def rule_orb_volume(f: pd.DataFrame, p: dict) -> pd.Series:
    """``entry_lab.rule_orb`` with its volume leg replaced by ``p['volume_spec']``.

    Built by calling ``rule_orb`` with ``min_relvol=0.0`` — which switches off the
    live volume leg and nothing else — then AND-ing the chosen definition. That
    construction is why this is provably a **one-dimension** change: the fresh-break
    geometry, the buffer, the above-VWAP leg and the time cutoff are not
    reimplemented here, they are the live rule's own code.
    """
    spec = p.get("volume_spec") or ("live", float(config.ORB_MIN_REL_VOL))
    base = entry_lab.rule_orb(f, {**p, "min_relvol": 0.0})
    return (base & volume_ok(f, spec)).fillna(False).astype(bool)


def live_volume_spec() -> tuple:
    """The volume gate as the running bot is configured — the incumbent cell.

    Read from ``bot.config`` so a sweep can never baseline against a threshold the
    bot no longer runs (the ``entry_sweep.live_orb_params`` discipline).
    """
    return ("live", float(config.ORB_MIN_REL_VOL))


def clearance_profile(
    f: pd.DataFrame, spec, max_bar_idx: int = 26,
) -> pd.DataFrame:
    """Per-``bar_idx`` median ratio and % of bars clearing ``spec`` — the U-shape.

    This is the instrument behind this module's central claim, kept as code so the
    claim is re-measurable on any window instead of quoted from a docstring.
    Indexed by ``bar_idx`` 0..``max_bar_idx``; ``n`` is bars observed, and bars
    with no baseline are counted in ``n`` and as NOT clearing, matching
    ``volume_ok``'s fail-closed behaviour.
    """
    name, thresh = str(spec[0]), float(spec[1])
    col = VOL_COLUMNS[name]
    if f is None or f.empty or col not in f.columns:
        return pd.DataFrame(columns=["median_ratio", "pct_clearing", "n"])
    sub = pd.DataFrame({
        "bar_idx": f["bar_idx"].to_numpy(),
        "ratio": f[col].to_numpy(dtype=float),
    })
    sub = sub[sub["bar_idx"] <= int(max_bar_idx)]
    if sub.empty:
        return pd.DataFrame(columns=["median_ratio", "pct_clearing", "n"])
    sub["clears"] = (sub["ratio"] >= thresh) if thresh else True
    g = sub.groupby("bar_idx")
    return pd.DataFrame({
        "median_ratio": g["ratio"].median().round(3),
        "pct_clearing": (100.0 * g["clears"].mean()).round(2),
        "n": g.size(),
    })


def candidate_admission(
    feats: dict[str, pd.DataFrame], base: dict, specs: list,
    mkt: pd.Series | None = None,
) -> pd.DataFrame:
    """How many ORB *candidates* each spec admits — the throughput number.

    A "candidate" is a bar ``rule_orb`` reaches with its volume leg switched off:
    a fresh in-window break above the range that also clears VWAP and the market
    overlay. Reported as a diagnostic ONLY. Throughput is never a ship reason —
    ``entry_sweep.sweep_verdict`` decides that — but a candidate set is what a
    session's refusal ledger shows, so this is the column that ties the lab back
    to what the live bot was seen doing.
    """
    rows = []
    cand_total = 0
    per_spec: dict[str, int] = {str(s): 0 for s in specs}
    for sym, f in feats.items():
        cand = entry_lab.rule_orb(f, {**base, "min_relvol": 0.0})
        if base.get("mkt") and mkt is not None:
            cand = cand & mkt.reindex(f.index).fillna(False).astype(bool)
        cand_total += int(cand.sum())
        for s in specs:
            per_spec[str(s)] += int((cand & volume_ok(f, s)).sum())
    for s in specs:
        adm = per_spec[str(s)]
        rows.append({
            "spec": str(s),
            "candidates": cand_total,
            "admitted": adm,
            "pct_admitted": round(100.0 * adm / cand_total, 2) if cand_total else 0.0,
        })
    return pd.DataFrame(rows)
