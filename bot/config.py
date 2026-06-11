"""Non-secret tunables for the strategy and runtime.

Single source for every knob referenced in summary.md §11. These are committed
to git on purpose (they are not secrets). Tune cautiously — every changed value
is an overfitting risk (summary.md §10).
"""

from __future__ import annotations

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

# Confidence -> risk fraction (% of equity). summary.md §5.9.
# Each entry: (min_confidence_inclusive, risk_pct). Sorted ascending.
CONFIDENCE_RISK_TABLE = [
    (60, 0.5),
    (70, 1.0),
    (80, 1.5),
    (90, 2.0),   # capped at MAX_RISK_PCT
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
