"""Non-secret tunables for the strategy and runtime.

Single source for every knob referenced in summary.md §11. These are committed
to git on purpose (they are not secrets). Tune cautiously — every changed value
is an overfitting risk (summary.md §10).
"""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

# --- Market timezone ---
# All entry-cutoff / flatten logic compares against US Eastern explicitly.
MARKET_TZ = ZoneInfo("America/New_York")

# --- Data / loop ---
BAR_TIMEFRAME = "5Min"          # candle size for signals
POLL_INTERVAL_SEC = 60          # how often the main loop runs during RTH
DATA_FEED = "iex"               # free IEX feed for now (see summary §10 caveat)

# --- Indicators ---
EMA_SHORT = [8, 10, 20]         # entry-trigger EMA set (8 > 10 > 20 = stacked)
EMA_LONG = [21, 34, 55]         # trend/regime EMA set (Fibonacci ribbon)
ATR_PERIOD = 14
RSI_PERIOD = 14
ADX_PERIOD = 14
REL_VOL_LOOKBACK = 20           # bars for the average-volume baseline
MACD_FAST = 12                  # MACD fast EMA
MACD_SLOW = 26                  # MACD slow EMA
MACD_SIGNAL = 9                 # MACD signal-line EMA
SLOPE_LOOKBACK = 3              # bars back used to gauge EMA slope/separation

# --- Support / resistance ---
PIVOT_LOOKBACK = 3              # swing-pivot: bars required on each side
LEVEL_CLUSTER_PCT = 0.003       # merge pivots within 0.3% into one level

# --- Breakout confirmation (anti-fakeout) ---
BREAKOUT_BUFFER = 0.001         # min close margin above level (0.1%)
VOL_CONFIRM_MULT = 1.3          # relative-volume threshold for a valid breakout
MIN_LEVEL_TOUCHES = 2           # optional: prior touches before a level "counts"

# --- Risk / sizing ---
ATR_STOP_MULT = 3.0             # stop distance = ATR * this; widened from 1.8 —
                                # 2026-06-10 session: 7 of 8 trades stopped at only
                                # -0.44%..-0.77% from entry (stops still inside 5-min
                                # noise), tripping the daily-loss halt by 11:00 ET.
                                # Wider stop + risk-based sizing keeps $ risk constant
                                # (fewer shares), but lets trades breathe until the
                                # 15:55 EOD flatten instead of dying in minutes.
MIN_STOP_PCT = 1.5              # floor: stop is at least this % of entry price
                                # (raised from 0.5 — sub-1% stops were what kept
                                # getting tagged on 06-10).
RR_RATIO = 1.5                  # take-profit = stop distance * this; with the wider
                                # stop the TP now sits >= ~2.25% above entry, so
                                # winners run longer instead of capping out in minutes.
MAX_RISK_PCT = 2.0              # HARD CAP on per-trade risk (% of equity)
MAX_CONCURRENT_POSITIONS = 3    # exposure limit
MAX_ENTRY_SLIPPAGE_PCT = 1.0    # skip an entry if the LIVE price has moved more than
                                # this % from the signal-bar close (in EITHER direction)
                                # before the market bracket is submitted. The plan's
                                # entry/stop/TP are anchored to the signal close, but the
                                # order fills live; a big gap UP makes the TP
                                # (>= ~entry*1.0225) land below the live price
                                # (AMD 2026-06-30: signal ~542, live 554.29), and a big
                                # gap DOWN makes the stop (~1.5% below the signal close)
                                # land at/above the live price (NVDA 2026-07-01:
                                # base_price 195.02) -> Alpaca 422s the whole bracket and
                                # the entry is silently lost. Even when a smaller gap is
                                # accepted the stop is mispriced vs the real fill.
                                # Recorded fills are <=0.5% off the signal, so 1.0% only
                                # catches the gap-chase. A NEW skip (tightening) — widens
                                # nothing (IMP-008 up-side; IMP-009 down-side symmetry).
                                # IMP-008.

# --- Break-even + trailing stop (IMP-013) ---
# 06-08..07-07 audit (123 closed trades): STOP exits -$3,266 (56 trades, 1 win)
# vs TAKE_PROFIT +$1,577 — but only 20/123 trades ever reached the 1.5R target
# intraday, and 23 of 47 EOD_FLATTEN trades were green at the close after giving
# back most of their open profit. Realized payoff ratio 1.08 vs the ~1.8 a 36%
# win rate needs. Holding overnight is NOT the fix (5-day hold simulation on the
# 47 EOD trades: 21 TP vs 21 stop, ~+$12/trade before gap risk); banking intraday
# progress is. The moved stop lives BROKER-SIDE (bracket-leg replace), so it
# survives the nightly service restart; trades.stop_price in the DB keeps the
# ORIGINAL plan stop because that distance defines 1R.
TRAILING_STOP_ENABLED = True
BREAKEVEN_TRIGGER_R = 0.5       # at +0.5R unrealized, raise the stop to entry —
                                # a trade that showed profit can no longer close red.
TRAIL_TRIGGER_R = 0.5           # IMP-029 (weekly): was 1.0. With TRAIL_DISTANCE_R
                                # also 1.0 the trail candidate at the trigger was
                                # live - 1R == ENTRY — exactly the level break-even
                                # had already set — so STOP_RATCHET_MIN_PCT blocked
                                # the replace until ~+1.08R and the whole
                                # +0.5R..+1.08R band captured NOTHING (the trail was
                                # inert by arithmetic, cf. the sibling bot's IMP-018).
                                # Now the trail arms at the SAME point break-even
                                # does, so the two stages are one continuous ratchet
                                # with no dead band between them.
TRAIL_DISTANCE_R = 0.5          # trail this many R below the live price (ratchet:
                                # the stop only ever moves UP). Must stay < 1.0 or
                                # the dead band returns; see tests/test_exit_sim.py
                                # ::test_trail_is_not_inert_at_the_trigger.
STOP_RATCHET_MIN_PCT = 0.10     # skip replaces that improve the stop by less than
                                # this % of entry — the loop ticks every 60s and
                                # Alpaca rotates the order id on every replace
                                # (USTradeBot's 422 "already replaced" saga); don't
                                # churn the leg for pennies.

# --- Daily-loss circuit breaker (#1) ---
DAILY_LOSS_HALT_PCT = 8.0       # was 3.0; raised 2026-06-10 to un-halt after the
                                # morning's tight-stop losses, then confirmed by the
                                # user on 2026-06-11 as the PERMANENT setting (do not
                                # lower without explicit user approval).
                                # halt ALL new entries once the day's realized loss
                                # reaches this % of session-open equity. Added after
                                # 2026-06-09 (-9.4% over 17 trades): stop the bleed
                                # early instead of trading the whole day down. Exits
                                # on already-open positions are unaffected.

# --- Re-entry throttle (#2) ---
REENTRY_COOLDOWN_MIN = 30          # after a symbol's trade closes, wait this many
                                   # minutes before re-entering it. Kills the same-name
                                   # chasing seen 06-09 (AMD 3x, UNH 4x — all stopped).
MAX_ENTRIES_PER_SYMBOL_PER_DAY = 2 # hard cap on entries per symbol per session.

# --- Underlying-equivalence guard (#3, PHASE-002) ---
# Share classes of one company are ONE underlying: holding or recently trading
# any member blocks entries in every other member (held-skip, cooldown and the
# daily entry cap all apply across the group). Added 2026-06-12: GOOG hit TP at
# 11:24 and the bot bought GOOGL 39s later at the top (-$128.79); on 06-10 it
# held GOOG and GOOGL simultaneously (hidden 2x single-name exposure).
EQUIVALENT_UNDERLYINGS: list[set[str]] = [
    {"GOOG", "GOOGL"},
]


def equivalent_symbols(symbol: str) -> set[str]:
    """All symbols sharing ``symbol``'s underlying (always includes itself)."""
    for group in EQUIVALENT_UNDERLYINGS:
        if symbol in group:
            return set(group)
    return {symbol}


# Confidence -> risk fraction (% of equity). summary.md §5.9.
# Each entry: (min_confidence_inclusive, risk_pct). Sorted ascending.
#
# IMP-035 (weekly, 2026-08-15) — FLAT. The ladder used to read
# (60,0.5) (70,1.0) (80,1.5) (90,2.0), i.e. "more confidence = more money", up to
# 4x risk at the top rung. The whole-book record says the confidence score is
# ANTI-predictive, monotonically, across every band it has ever reached (n=244):
#
#   conf band    n     avg P&L    avg notional
#   <65        176     -$3.03        $3,763
#   65-75       28    -$15.10        $5,879
#   75-85       28    -$30.25        $9,254
#   >=85        12    -$42.28       $11,446
#
# The 68 trades at conf >=65 are 28% of the book and -$1,777 of the -$2,311
# lifetime loss (77%). This is not an era artefact: over the window where both
# signal families were live (06-08..07-24), breakout-carrying signals averaged
# -$26.04/trade on $8,385 notional vs -$2.39/trade on $4,360 for MA-only.
# The ladder was sizing UP in proportion to a score that predicts losses.
#
# IMP-027 already found this trap and built tests to WATCH it
# (tests/test_sizing_ladder.py) but left it armed; it is currently dormant only
# because IMP-021's veto pins live confidence into a ~3-point band at the floor.
# Dormant is not disarmed — one scorer change re-arms 3-4x sizing on the leg that
# lost $1,784. Flattening is risk-REDUCING and touches no risk invariant:
# MAX_RISK_PCT stays 2.0, DAILY_LOSS_HALT_PCT 8.0, MAX_CONCURRENT_POSITIONS 3.
#
# Re-steepening this table requires evidence that confidence predicts P&L with
# the correct SIGN. `sizing.ladder_risk_is_non_increasing()` enforces that.
CONFIDENCE_RISK_TABLE = [
    (60, 0.5),
    (70, 0.5),
    (80, 0.5),
    (90, 0.5),
]
MIN_CONFIDENCE = 60             # minimum confidence to take a trade
MA_SIGNAL_MIN = 0.6             # ma_score at/above this counts as an MA signal
VALUE_VETO_FLOOR = 0.25         # veto breakout/BOTH entries when value_score (the
                                # over-extension check) is below this — don't chase a
                                # breakout that has already run too far above EMA20.
                                # Added 2026-06-09 after BOTH went 0/5: JPM/XOM/ABNB
                                # were flagged badly-extended (value 0.20/0.00/0.24)
                                # yet still cleared confidence because value is only
                                # 20% of the blend and could never veto.
BREAKOUT_FADE_CEILING = 0.5     # veto entries whose breakout_score is at/above this
                                # (IMP-021, 2026-07-25). Holdout-validated: breakout_score
                                # is bimodal (~0 or >=0.5); the real-breakout leg was the
                                # ENTIRE loss driver — skipping it lifted the recorded book
                                # from -$2,024 to -$12 and held out-of-sample (last 5
                                # sessions: skipped set net -$183, kept book +$25). Fresh
                                # resistance breakouts fade; don't chase the spike bar.
BREAKOUT_VETO_LIVE_FROM = date(2026, 7, 25)
                                # date BREAKOUT_FADE_CEILING went live. Analysis-only
                                # marker (no trading effect): lets diagnostics split the
                                # pre- and post-veto eras instead of conflating them.
                                # See scripts/check_sizing_ladder.py (IMP-027).
VWAP_MAX_DIST_PCT = 0.25        # skip entries filled more than this % ABOVE the symbol's
                                # session VWAP (IMP-022, 2026-07-25). Two independent
                                # validations: the recorded-trade holdout (IMP-019/020) and
                                # a from-scratch 30-day backtest both show entry-vs-session-
                                # VWAP is the one clean separator — fills at/below VWAP make
                                # money, fills stretched above it fade. Gating >+0.25% flipped
                                # the 30-day backtest from -$183 to +$53 (win% 35->43).

# --- Signal filters / thresholds ---
RSI_OVERBOUGHT = 70             # over-extension penalty trigger
ADX_MIN = 20                    # regime filter threshold
EXT_ATR_PENALTY = 2.0           # distance above 20-EMA (in ATR) where penalty starts
EXT_ATR_VETO = 4.0             # distance above 20-EMA (in ATR) where we don't enter

# Confidence-blend weights (summary.md §5.8). Must sum to 1.0.
WEIGHT_BREAKOUT = 0.35
WEIGHT_MA = 0.30
WEIGHT_VALUE = 0.20
WEIGHT_MOMENTUM = 0.15

# Regime multiplier applied to the weighted blend.
REGIME_MULT_OK = 1.0
REGIME_MULT_WEAK = 0.5          # not stacked but ADX ok (or vice versa)
REGIME_MULT_FAIL = 0.0          # no trend -> suppress

# --- Time rules (US Eastern) ---
ENTRY_CUTOFF_ET = "15:30"       # no new entries after this
FLATTEN_ET = "15:55"            # force-close all positions at/after this
FLATTEN_SETTLE_TIMEOUT_SEC = 8.0  # bounded wait for the CANCEL phase: the bracket legs must
                                # actually release the shares before the liquidation is sent,
                                # or DELETE /v2/positions is rejected held_for_orders. Measured
                                # leg-cancel latency: 3.1s (2026-08-13), 5.0s (2026-08-14), so
                                # 8s clears the worst on record with room. IMP-033.
FLATTEN_FILL_TIMEOUT_SEC = 25.0  # bounded wait for the FILL phase: the liquidation orders are
                                # already in flight, so this only decides whether the flatten
                                # CONFIRMS itself or hands a false "incomplete" to the caller.
                                # Sized off the broker record, 16 sessions / 36 EOD liquidations
                                # (07-24..08-14): median fill 2.8s, p90 8.7s, max 15.0s — and the
                                # worst fill of the SESSION is what this must cover, which
                                # exceeded 8s on 3 of those 16 (08-06 8.1s, 08-10 8.7s, 08-14
                                # 15.0s). 25s covers every session on record at 1.7x the max and
                                # both phases together still fit inside one 60s poll and the
                                # five-minute 15:55->16:00 runway. IMP-034.
FLATTEN_SETTLE_POLL_SEC = 0.5

# --- Default watchlist seed (liquid, high-volume US names) ---
DEFAULT_WATCHLIST = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corp."),
    ("NVDA", "NVIDIA Corp."),
    ("AMZN", "Amazon.com Inc."),
    ("GOOGL", "Alphabet Inc."),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),
    ("AMD", "Advanced Micro Devices"),
    ("NFLX", "Netflix Inc."),
    ("AVGO", "Broadcom Inc."),
    ("JPM", "JPMorgan Chase & Co."),
    ("BAC", "Bank of America Corp."),
    ("XOM", "Exxon Mobil Corp."),
    ("COST", "Costco Wholesale Corp."),
    ("CRM", "Salesforce Inc."),
]


def _assert_weights() -> None:
    total = WEIGHT_BREAKOUT + WEIGHT_MA + WEIGHT_VALUE + WEIGHT_MOMENTUM
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Confidence weights must sum to 1.0 (got {total}).")


_assert_weights()
