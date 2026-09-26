"""Review-coverage detection — "a session traded and nobody reviewed it".

IMP-064 (weekly, 2026-09-26). Between 2026-09-21 and 2026-09-25 the review loop
skipped **three consecutive sessions** — 09-22, 09-23 and 09-24 — and 09-24 had a
fill (META, +$23.20). Two of those runs died mid-flight and left uncommitted,
untested, unlogged code in the working tree, which then collided over the IMP
number. **Nothing anywhere noticed.** The gap was found four days later by a
human-shaped act: the 09-25 run happening to read the file it appends to.

This is IMP-061's defect in a third instrument, and the shape is now familiar
enough to name: *the bot has an instrument for every number except the one that
says whether an instrument ran.* IMP-061 compared the broker to the ledger
because no code did. This compares **the sessions that happened** to **the
sessions that were written up**, because no code does that either.

Why it matters beyond tidiness: every governance promise this bot has made is
discharged by the daily review. The 30-trade ORB kill criterion is counted there.
The stop-exit doctrine's buckets are applied there. IMP-061's reconciliation
alarm is *scored* there. A session that is never reviewed is a session in which
all of those silently did not happen — and the weekly review inherits a hole it
cannot tell apart from a quiet week.

The alarm is deliberately narrow, for the reason reconcile.py states: an alert
that fires every evening is an alert nobody reads.

    Alarm on the NEWEST session that is past its grace period and has no review.

One specific session per evening, and it **self-clears** the moment that review
lands — no acknowledgement list, no floor date, no config to maintain. Replayed
against the real history it fires on exactly the three nights it should have
(09-23 about 09-22, 09-24 about 09-23, 09-25 about 09-24) and is silent on every
other evening in the file, including after the 09-25 run recovered the backlog.

Older gaps inside the lookback window are **reported and logged but do not
alarm**. That split is the point: a backlog the newest review already accounted
for is context, whereas yesterday's missing review is actionable tonight. The
full window is what `scripts/check_coverage.py` prints, so a weekly review can
audit its own coverage instead of trusting that it was reviewed.

⚠️ **Changes no trading behaviour and touches no risk invariant.** No orders, no
sizing, no exits, no halt. It reads `daily_summary` rows and a markdown file and
decides whether to send a Telegram message. Detection, not control.

`check()` and everything above it are pure — no DB, no network, no clock — so any
evening in the file can be replayed in a test. The two `load_*` / `read_*`
helpers at the bottom are the only impure code here and are kept deliberately
separate and best-effort: this module must be unable to break the post-close
path, so a missing memory file or an unreadable table degrades to "cannot check",
never to an alarm and never to an exception.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from . import config

# memory/daily-review.md, resolved from this file so it does not depend on the
# process working directory (the service runs from a systemd unit, the CLI from a
# shell, and the two must agree on which file is authoritative).
REVIEW_PATH = Path(__file__).resolve().parent.parent / "memory" / "daily-review.md"

# Daily-review entries are `## YYYY-MM-DD — Daily Review` (the trailing prose
# varies and is not matched on purpose: a run that titles its entry differently
# still counts as having reviewed the day). Anchored to the start of a line so a
# date quoted inside body text cannot be mistaken for an entry heading.
REVIEW_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})", re.MULTILINE)


def _f(value, default: float = 0.0) -> float:
    """Float or ``default`` — Decimals from pyodbc, None from an empty column."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_date(value) -> date | None:
    """Coerce a pyodbc date / datetime / ISO string to a `date`, else None.

    Returns None rather than raising: an unparseable trade_date should drop one
    session from the check, never break the post-close path.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def parse_reviewed_dates(text: str | None) -> set[date]:
    """Dates that have a `## YYYY-MM-DD` entry in `memory/daily-review.md`.

    A malformed date in a heading is skipped rather than raising — the file is
    hand-appended prose and one bad line must not blind the whole check.
    """
    out: set[date] = set()
    for raw in REVIEW_HEADING_RE.findall(text or ""):
        parsed = _as_date(raw)
        if parsed is not None:
            out.add(parsed)
    return out


def had_fills(summary: dict) -> bool:
    """Did this session actually close a trade?

    ``num_sells`` is the exit count `logbook.write_daily_summary` records, and an
    exit is what produces a ledger row worth reviewing. Falls back to a non-zero
    ``gross_pl`` so a session that moved money is never classed as quiet just
    because the count is NULL.
    """
    return int(_f(summary.get("num_sells"))) > 0 or _f(summary.get("gross_pl")) != 0.0


def sessions_from_summaries(summaries: list[dict]) -> list[dict]:
    """`daily_summary` rows → `{date, had_fills, net_pl}`, oldest first.

    Rows whose ``trade_date`` will not parse are dropped (see `_as_date`).
    """
    out = []
    for row in summaries or []:
        when = _as_date(row.get("trade_date"))
        if when is None:
            continue
        out.append({"date": when, "had_fills": had_fills(row),
                    "net_pl": round(_f(row.get("gross_pl")), 2)})
    out.sort(key=lambda s: s["date"])
    return out


def check(summaries: list[dict], review_text: str | None, *, today: date,
          lookback: int | None = None) -> dict:
    """Compare the sessions that happened to the sessions that were written up.

    Returns a dict that is always safe to read:

    ``ok``            the check ran (there was at least one eligible session)
    ``gapped``        the alarm condition — only ever True when ``ok``
    ``stale``         the newest eligible session, when it has no review
    ``missing``       every unreviewed session in the window, oldest first
    ``reviewed``      how many of the window's eligible sessions do have entries
    ``reason``        why the check could not run / did not alarm

    ``today`` is passed in rather than read from a clock so this stays pure and
    so a test can replay any evening in the file. Sessions dated ``today`` are
    **exempt**: `post_close_summary` runs at the close and that night's review is
    written hours later, so alarming on it would fire every single evening — the
    exact noise this module is built to avoid.

    An empty window returns ``ok=False``. That is IMP-061's rule reused: ``0
    missing of 0 sessions`` would read as *fine*, and this check must never
    report fine when it does not know.
    """
    window = lookback if lookback is not None else config.COVERAGE_LOOKBACK_SESSIONS
    sessions = sessions_from_summaries(summaries)
    eligible = [s for s in sessions if s["date"] < today][-max(int(window), 1):]
    if not eligible:
        return {"ok": False, "gapped": False, "stale": None, "missing": [],
                "reviewed": 0, "sessions": 0, "today": today,
                "reason": "no completed sessions in window"}

    reviewed = parse_reviewed_dates(review_text)
    missing = [s for s in eligible if s["date"] not in reviewed]
    newest = eligible[-1]
    # Only the newest eligible session can raise the alarm. Anything older is
    # backlog: reported and logged, but a review that already recovered it (as
    # the 09-25 entry did) should not keep paging about it every evening.
    stale = newest if newest["date"] not in reviewed else None
    return {
        "ok": True,
        "gapped": stale is not None,
        "stale": stale,
        "missing": missing,
        "reviewed": len(eligible) - len(missing),
        "sessions": len(eligible),
        "today": today,
        "reason": None if stale is not None else "newest session reviewed",
    }


def describe(result: dict) -> str:
    """One-line human summary of a `check()` result, for the log and the alert."""
    if not result.get("ok"):
        return f"review coverage skipped — {result.get('reason')}"
    missing = result.get("missing") or []
    backlog = ""
    if missing:
        backlog = " · unreviewed in window: " + ", ".join(
            f"{s['date']}{'*' if s['had_fills'] else ''}" for s in missing)
    if not result.get("gapped"):
        return (f"review coverage ok — {result['reviewed']}/{result['sessions']} "
                f"completed sessions reviewed{backlog}")
    stale = result["stale"]
    fills = (f"{stale['net_pl']:+,.2f} over fills" if stale["had_fills"]
             else "no fills")
    return (f"review coverage GAP — {stale['date']} has no daily review "
            f"({fills}); {result['reviewed']}/{result['sessions']} "
            f"reviewed{backlog}")


# --- impure edges: the only DB / filesystem access in this module ---

def read_review_text(path: Path | str | None = None) -> str | None:
    """`memory/daily-review.md` as text, or None if it cannot be read.

    None is distinct from `""`: an unreadable file must make `check()` report
    that it cannot check, not that nothing was ever reviewed (which would alarm
    on a perfectly-reviewed history the first time a permission changed).
    """
    try:
        return Path(path or REVIEW_PATH).read_text(encoding="utf-8")
    except OSError:
        return None


def load_sessions(lookback: int | None = None) -> list[dict]:
    """Recent `daily_summary` rows, newest-relevant window, via `bot.analytics`.

    Imported lazily so `bot.coverage` stays importable (and its pure half
    testable) without a database driver present. Calendar days are taken as ~3x
    the session count because a trading week is five sessions in seven days and
    holidays stretch it further; `check()` then trims to the last ``lookback``
    completed sessions, so over-fetching here is harmless.
    """
    from . import analytics

    window = lookback if lookback is not None else config.COVERAGE_LOOKBACK_SESSIONS
    return analytics.load_daily_summaries(analytics.since_days(max(int(window), 1) * 3))
