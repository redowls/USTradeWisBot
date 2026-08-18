"""IMP-036 — era-controlled entry-discriminator testing.

The fixture `ATR_OVER_1R` below is REAL: all 250 closed trades as of
2026-08-18, each reduced to (exit date, symbol, prior-day daily ATR(14) / 1R at
entry, realized P&L). ATR is from Alpaca SIP daily bars; 1R is
entry_price - stop_price from the `trades` table. It is the exact population
that produced the 2026-08-18 finding, so these tests are the regression on a
filter that nearly shipped: the raw split says the ATR/1R >= 2.5 cohort cost
-$1841.08 (80% of the lifetime loss) with a believable mechanism, and both era
control and collateral analysis say do not ship it.
"""

from __future__ import annotations

import pytest

from bot import discriminator as D
from bot.discriminator import Sample

# (exit_date, symbol, prior-day daily ATR(14) / 1R at entry, realized P&L)
ATR_OVER_1R: tuple[tuple[str, str, float, float], ...] = (
    ("2026-06-08","NFLX",11.745,29.5), ("2026-06-08","JPM",10.772,-73.0),
    ("2026-06-08","BAC",8.64,-52.08), ("2026-06-08","NFLX",8.809,-49.41),
    ("2026-06-08","JPM",7.713,-36.51), ("2026-06-08","BAC",8.023,-57.78),
    ("2026-06-08","JPM",7.619,-68.06), ("2026-06-08","NFLX",7.83,80.5),
    ("2026-06-08","XOM",9.929,-49.22), ("2026-06-08","NFLX",7.047,-58.23),
    ("2026-06-08","ABNB",13.676,-40.95), ("2026-06-08","TSM",7.21,-24.78),
    ("2026-06-08","AAPL",5.402,-21.54), ("2026-06-08","INTC",9.31,-57.65),
    ("2026-06-08","TSLA",10.93,88.91), ("2026-06-08","TSLA",12.363,84.25),
    ("2026-06-08","TSLA",11.602,84.01), ("2026-06-08","MU",14.019,-43.65),
    ("2026-06-08","INTC",17.342,-54.32), ("2026-06-08","AMD",19.116,-42.77),
    ("2026-06-08","NFLX",16.263,-40.17), ("2026-06-08","ABNB",27.353,-12.39),
    ("2026-06-09","UNH",4.998,21.15), ("2026-06-09","AMD",6.605,-158.17),
    ("2026-06-09","AMD",6.605,-5.44), ("2026-06-09","NVDA",6.989,-74.66),
    ("2026-06-09","AMD",6.731,-33.39), ("2026-06-09","INTC",5.976,-39.06),
    ("2026-06-09","UNH",4.95,60.5), ("2026-06-09","ABNB",5.796,-41.7),
    ("2026-06-09","MU",5.125,-41.34), ("2026-06-09","GOOGL",3.816,-119.17),
    ("2026-06-09","C",4.182,-47.52), ("2026-06-09","MU",4.626,-37.38),
    ("2026-06-09","BAC",3.904,-45.32), ("2026-06-09","UNH",4.926,-127.89),
    ("2026-06-09","WMT",5.719,-48.51), ("2026-06-09","C",5.031,-132.92),
    ("2026-06-09","GOOG",5.304,-26.78), ("2026-06-10","C",4.634,-101.07),
    ("2026-06-10","BAC",4.071,58.63), ("2026-06-10","GOOG",4.844,-136.71),
    ("2026-06-10","GOOGL",3.984,-108.71), ("2026-06-10","JPM",4.06,-53.6),
    ("2026-06-10","C",4.198,-10.4), ("2026-06-10","GOOG",3.972,-7.29),
    ("2026-06-10","MU",3.514,-24.43), ("2026-06-10","XOM",5.339,61.6),
    ("2026-06-10","WMT",1.883,15.87), ("2026-06-10","BAC",1.341,-14.5),
    ("2026-06-10","AAPL",1.631,-0.99), ("2026-06-11","WMT",1.85,-2.76),
    ("2026-06-11","COST",1.657,-19.06), ("2026-06-11","AAPL",1.667,13.32),
    ("2026-06-12","TSM",2.953,34.39), ("2026-06-12","GOOG",1.963,119.97),
    ("2026-06-12","SE",3.473,-142.35), ("2026-06-12","META",2.319,-121.86),
    ("2026-06-12","BAC",1.367,23.25), ("2026-06-12","GOOGL",1.88,-128.79),
    ("2026-06-12","INTC",2.861,49.0), ("2026-06-15","TSLA",2.913,90.87),
    ("2026-06-15","ENPH",5.266,-30.23), ("2026-06-15","ENPH",5.266,-87.36),
    ("2026-06-15","NFLX",1.545,7.04), ("2026-06-15","C",1.786,-15.93),
    ("2026-06-16","MU",5.153,-35.5), ("2026-06-18","C",1.842,20.25),
    ("2026-06-18","AMZN",2.129,0.0), ("2026-06-18","BAC",1.455,-15.18),
    ("2026-06-22","ENPH",6.645,53.74), ("2026-06-22","META",2.654,-12.14),
    ("2026-06-22","AVGO",4.203,-7.04), ("2026-06-22","TSLA",3.049,203.49),
    ("2026-06-22","SPY",0.982,-15.06), ("2026-06-22","QQQ",1.647,-22.68),
    ("2026-06-22","TSM",2.949,-22.64), ("2026-06-23","XOM",1.867,19.57),
    ("2026-06-23","BAC",1.475,16.56), ("2026-06-23","CRM",3.434,57.69),
    ("2026-06-23","WMT",1.484,1.98), ("2026-06-24","BAC",1.058,-18.19),
    ("2026-06-24","CRM",2.393,-41.48), ("2026-06-24","WMT",1.531,-27.41),
    ("2026-06-25","QCOM",1.604,9.62), ("2026-06-25","TSM",1.959,-32.92),
    ("2026-06-25","AMD",1.714,19.61), ("2026-06-26","COST",1.296,-7.5),
    ("2026-06-26","ENPH",3.668,-132.44), ("2026-06-26","META",2.407,-5.69),
    ("2026-06-26","TSLA",3.356,5.65), ("2026-06-29","AAPL",1.71,-116.55),
    ("2026-06-29","SPY",1.187,9.48), ("2026-06-29","GOOG",2.108,40.9),
    ("2026-06-29","TSLA",2.52,106.87), ("2026-06-29","INTC",5.793,85.79),
    ("2026-06-30","INTC",5.538,90.33), ("2026-06-30","TSM",2.955,96.58),
    ("2026-06-30","MU",7.237,20.27), ("2026-06-30","TSLA",3.01,59.1),
    ("2026-06-30","AAPL",1.935,33.09), ("2026-06-30","AVGO",3.174,-2.33),
    ("2026-07-01","ENPH",2.643,-47.84), ("2026-07-01","SE",3.255,60.3),
    ("2026-07-01","MSFT",2.296,58.52), ("2026-07-01","AAPL",1.892,34.4),
    ("2026-07-01","GOOGL",2.23,42.41), ("2026-07-01","AMZN",2.203,4.59),
    ("2026-07-02","GOOGL",2.445,-35.58), ("2026-07-02","SE",1.857,-99.72),
    ("2026-07-02","CRM",2.125,-12.94), ("2026-07-02","BAC",1.384,0.0),
    ("2026-07-06","GOOGL",1.715,44.62), ("2026-07-06","COST",1.241,-7.81),
    ("2026-07-06","SE",2.39,-55.64), ("2026-07-06","INTC",4.194,-74.16),
    ("2026-07-06","META",2.566,22.48), ("2026-07-07","TSLA",5.922,-20.23),
    ("2026-07-07","GOOGL",2.375,-2.22), ("2026-07-07","META",1.769,85.74),
    ("2026-07-07","AMZN",2.128,-43.97), ("2026-07-07","AAPL",1.866,-16.56),
    ("2026-07-07","AMZN",2.148,-10.98), ("2026-07-08","XOM",1.478,-0.19),
    ("2026-07-08","NVDA",2.217,0.79), ("2026-07-08","WMT",1.659,14.4),
    ("2026-07-08","QCOM",4.785,-37.08), ("2026-07-08","AVGO",2.572,-0.12),
    ("2026-07-08","NVDA",2.248,60.84), ("2026-07-08","QCOM",4.857,-7.38),
    ("2026-07-08","ENPH",6.411,61.76), ("2026-07-09","QQQ",0.965,14.87),
    ("2026-07-09","SE",4.454,228.54), ("2026-07-09","TSM",3.267,-35.11),
    ("2026-07-09","SPY",0.902,9.09), ("2026-07-10","AAPL",4.247,3.77),
    ("2026-07-10","TSLA",2.535,-119.38), ("2026-07-10","BAC",1.18,3.16),
    ("2026-07-10","SPY",0.83,5.59), ("2026-07-10","WMT",1.614,6.24),
    ("2026-07-13","NVDA",2.774,-129.93), ("2026-07-13","GOOGL",3.932,-0.78),
    ("2026-07-13","MSFT",2.055,78.39), ("2026-07-13","AMZN",2.452,-0.36),
    ("2026-07-13","SE",2.096,-41.65), ("2026-07-13","COST",1.391,9.06),
    ("2026-07-14","BAC",0.998,51.47), ("2026-07-14","XOM",1.097,-49.78),
    ("2026-07-14","UNH",1.589,-39.33), ("2026-07-14","AMD",2.522,-0.4),
    ("2026-07-14","GOOG",1.743,18.18), ("2026-07-14","META",2.645,-21.28),
    ("2026-07-15","NVDA",4.017,-66.87), ("2026-07-15","QQQ",1.774,-93.08),
    ("2026-07-15","AVGO",2.476,-37.32), ("2026-07-15","META",2.778,60.68),
    ("2026-07-15","NFLX",2.152,-42.0), ("2026-07-15","AMZN",1.956,-1.99),
    ("2026-07-15","ABNB",2.301,-91.26), ("2026-07-15","NVDA",2.332,19.83),
    ("2026-07-16","GOOG",1.895,-3.28), ("2026-07-16","AAPL",1.653,32.32),
    ("2026-07-16","AMZN",2.036,-37.25), ("2026-07-16","WMT",1.484,5.52),
    ("2026-07-17","CRM",1.936,-55.65), ("2026-07-17","MU",2.814,-0.35),
    ("2026-07-17","UNH",1.942,-40.02), ("2026-07-17","AMD",4.242,-115.32),
    ("2026-07-17","AAPL",1.73,-0.14), ("2026-07-20","QCOM",3.207,-40.32),
    ("2026-07-20","MU",3.248,-25.18), ("2026-07-20","INTC",3.063,-22.12),
    ("2026-07-20","AVGO",2.725,-0.24), ("2026-07-21","AVGO",2.679,13.38),
    ("2026-07-21","QQQ",1.383,16.0), ("2026-07-21","INTC",3.145,49.03),
    ("2026-07-22","AMD",5.356,20.79), ("2026-07-22","BAC",1.518,18.52),
    ("2026-07-22","UNH",1.933,-59.88), ("2026-07-22","ENPH",5.122,-124.8),
    ("2026-07-22","QCOM",2.408,-20.15), ("2026-07-23","MU",4.359,-0.33),
    ("2026-07-23","XOM",1.359,-30.24), ("2026-07-23","MU",3.974,-18.8),
    ("2026-07-23","NFLX",2.582,-15.48), ("2026-07-23","BAC",1.335,-5.33),
    ("2026-07-24","BAC",1.312,21.78), ("2026-07-24","COST",1.291,32.95),
    ("2026-07-24","NFLX",2.28,32.4), ("2026-07-27","AAPL",1.557,-0.19),
    ("2026-07-27","NFLX",2.549,4.03), ("2026-07-27","QCOM",2.849,-39.66),
    ("2026-07-27","META",2.87,-37.92), ("2026-07-27","COST",1.32,1.22),
    ("2026-07-28","GOOG",2.182,25.9), ("2026-07-28","AAPL",1.517,6.22),
    ("2026-07-28","MSFT",2.021,-0.48), ("2026-07-29","ENPH",1.655,-43.68),
    ("2026-07-29","GOOGL",2.351,12.5), ("2026-07-29","AAPL",1.551,-30.06),
    ("2026-07-30","INTC",2.397,55.72), ("2026-07-30","SPY",0.707,7.12),
    ("2026-07-31","BAC",1.382,9.43), ("2026-07-31","NVDA",2.469,44.87),
    ("2026-07-31","SPY",0.718,16.87), ("2026-08-03","AMZN",2.139,-5.09),
    ("2026-08-04","SE",2.831,-4.56), ("2026-08-04","NVDA",2.175,10.71),
    ("2026-08-04","BAC",1.19,13.53), ("2026-08-04","NFLX",2.468,9.8),
    ("2026-08-05","GOOGL",2.598,-31.13), ("2026-08-05","QQQ",1.469,-23.35),
    ("2026-08-05","META",2.407,-41.07), ("2026-08-05","WMT",1.789,-0.4),
    ("2026-08-06","META",2.89,0.13), ("2026-08-06","NVDA",2.381,-36.23),
    ("2026-08-06","WMT",1.631,-36.96), ("2026-08-06","AMZN",2.405,-18.78),
    ("2026-08-06","AAPL",2.087,-0.43), ("2026-08-07","AAPL",2.223,7.49),
    ("2026-08-07","TSM",3.604,-23.3), ("2026-08-07","NVDA",2.324,-0.11),
    ("2026-08-07","META",2.946,-0.08), ("2026-08-07","TSLA",3.099,-6.47),
    ("2026-08-07","NVDA",2.44,6.02), ("2026-08-10","QQQ",1.471,-3.89),
    ("2026-08-10","SPY",0.82,-0.65), ("2026-08-10","MSFT",2.259,17.54),
    ("2026-08-10","SE",2.133,-9.24), ("2026-08-11","COST",1.22,-13.44),
    ("2026-08-11","WMT",1.22,5.52), ("2026-08-11","NFLX",1.64,-44.55),
    ("2026-08-12","WMT",1.498,49.26), ("2026-08-12","BAC",1.038,25.08),
    ("2026-08-12","QCOM",2.888,-40.76), ("2026-08-12","SPY",0.775,-3.14),
    ("2026-08-13","GOOG",1.945,-6.58), ("2026-08-13","NVDA",2.36,1.55),
    ("2026-08-13","CRM",2.565,-39.72), ("2026-08-13","QQQ",1.264,-3.31),
    ("2026-08-14","META",2.857,-25.23), ("2026-08-14","SPY",0.743,-6.55),
    ("2026-08-14","QCOM",2.549,-40.46), ("2026-08-14","AAPL",1.939,0.73),
    ("2026-08-17","QQQ",1.187,-7.83), ("2026-08-17","NVDA",2.073,0.05),
    ("2026-08-17","TSM",2.169,13.24), ("2026-08-18","AAPL",1.772,27.02),
    ("2026-08-18","UNH",1.674,-15.36), ("2026-08-18","WMT",1.329,-2.54),
)


def samples(rows=ATR_OVER_1R) -> list[Sample]:
    return [Sample(symbol=s, day=d, pl=pl, value=v) for d, s, v, pl in rows]


# --------------------------------------------------------------------------
# The 2026-08-18 trap, locked in as a regression.
# --------------------------------------------------------------------------

def test_the_raw_split_really_is_tempting():
    """Non-vacuity control: the finding this module rejects is a strong-looking one.

    If the raw numbers were weak there would be nothing to protect against, and
    the ERA_ARTEFACT verdict below would be uninteresting. 80% of the lifetime
    loss sits above ATR/1R 2.5, at a 28.7% win rate against 46.7%.
    """
    split = D.split_at(samples(), 2.5)
    assert split["above"]["trades"] == 115
    assert split["above"]["net"] == pytest.approx(-1841.08, abs=0.01)
    assert split["below"]["trades"] == 135
    assert split["below"]["net"] == pytest.approx(-455.20, abs=0.01)
    assert split["above"]["win_rate"] < split["below"]["win_rate"]
    # A filter refusing the above side looks worth +$12.64 per trade.
    assert split["edge"] == pytest.approx(12.64, abs=0.01)
    # ...and it is 80% of the -$2296.28 lifetime loss.
    assert abs(split["above"]["net"]) / abs(
        split["above"]["net"] + split["below"]["net"]) > 0.79


def test_atr_over_1r_is_an_era_artefact_not_a_filter():
    """The headline finding of 2026-08-18, and why it was not shipped."""
    v = D.verdict(samples(), 2.5)
    assert v["verdict"] == D.ERA_ARTEFACT
    # 92% of the refused cohort's loss is the pre-gate week 2026-06-08..06-14.
    assert v["era_concentration"] == pytest.approx(0.92, abs=0.005)
    # Era-controlled the split does not discriminate at all: -$2.30 vs -$2.72.
    era = v["splits"]["era-controlled"]
    assert era["above"]["avg"] == pytest.approx(-2.30, abs=0.01)
    assert era["below"]["avg"] == pytest.approx(-2.72, abs=0.01)
    assert era["edge"] <= 0
    assert any("era control" in r for r in v["reasons"])


def test_no_atr_over_1r_threshold_is_supported():
    """The regression that stops this filter being shipped as the book grows.

    Every threshold from 1.0 to 5.0 fails, and it matters that they fail for
    TWO different reasons — era concentration at most, collateral damage at
    3.5 — because either check alone would have let one of them through.
    """
    sweep = D.threshold_sweep(samples(), [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])
    assert not D.any_supported(sweep)
    outcomes = {row["threshold"]: row["verdict"] for row in sweep}
    assert outcomes[2.5] == D.ERA_ARTEFACT
    assert outcomes[3.5] == D.REFUTED
    # Non-monotone verdicts across adjacent thresholds = fitting noise.
    assert len({row["verdict"] for row in sweep}) > 1


def test_the_35_threshold_is_caught_by_collateral_not_by_era():
    """The collateral check is load-bearing, not decoration.

    At 3.5 the era-controlled edge is genuinely POSITIVE (+$7.39/trade on
    n=24), so era control alone would have waved this one through. It is
    refused because the cohort it discards contains TSLA and SE, both net
    winners — a filter that buys its aggregate by throwing away the symbols
    that work has not been shown to help.
    """
    v = D.verdict(samples(), 3.5)
    assert v["splits"]["era-controlled"]["edge"] > 0
    assert v["splits"]["era-controlled"]["above"]["trades"] >= D.MIN_ERA_CONTROLLED_N
    assert v["verdict"] == D.REFUTED
    assert v["collateral_fraction"] > D.MAX_COLLATERAL_FRACTION
    assert v["collateral"][0]["symbol"] == "TSLA"
    assert any("net-positive symbols" in r for r in v["reasons"])


def test_tslas_whole_record_sits_inside_the_refused_cohort():
    """The concrete cost the aggregate hides: the best symbol the bot has traded."""
    tsla = [s for s in samples() if s.symbol == "TSLA"]
    assert len(tsla) == 11
    assert sum(s.pl for s in tsla) == pytest.approx(577.07, abs=0.01)
    assert all(s.value >= 2.5 for s in tsla)


def test_refusing_the_LOW_range_cohort_is_also_refuted():
    """The opposite direction — the hypothesis five reviews actually carried.

    2026-08-13 through 2026-08-18 recorded "range/1R below some bound means
    neither bracket leg can fire, so decline the entry" as the bot's
    best-evidenced structural defect. Flipping the sign of the statistic turns
    "refuse the above side" into "refuse the LOW side", and the era-controlled
    edge is NEGATIVE at every bound: the low-volatility cohort is the better
    one, so that filter would have made the book worse.
    """
    inverted = [Sample(symbol=s.symbol, day=s.day, pl=s.pl, value=-s.value)
                for s in samples()]
    for bound in (1.6, 1.25, 1.0, 0.8):
        v = D.verdict(inverted, -bound)
        assert v["verdict"] != D.SUPPORTED
        assert v["splits"]["era-controlled"]["edge"] <= 0


def test_todays_three_trades_would_not_have_been_touched():
    """2026-08-18's own session, the day the trap was found.

    All three fills sit well below any threshold considered, so no version of
    this filter would have changed today's +$9.12 — which is itself a reason
    the day gave no mandate for an engine change.
    """
    today = {s.symbol: s for s in samples() if s.day == "2026-08-18"}
    assert set(today) == {"AAPL", "UNH", "WMT"}
    assert today["AAPL"].value == pytest.approx(1.772, abs=0.001)
    assert today["UNH"].value == pytest.approx(1.674, abs=0.001)
    assert today["WMT"].value == pytest.approx(1.329, abs=0.001)
    assert all(s.value < 2.5 for s in today.values())


# --------------------------------------------------------------------------
# The verdict function must still be able to say yes.
# --------------------------------------------------------------------------

def test_a_genuinely_supported_discriminator_passes():
    """Non-vacuity in the other direction: SUPPORTED is reachable.

    A statistic that separates in all three eras, has enough modern trades
    above the line, and discards no working symbol must come back SUPPORTED —
    otherwise this module is a rubber stamp that always says no.
    """
    rows: list[Sample] = []
    for day in ("2026-06-10", "2026-07-01", "2026-08-01"):
        for i in range(15):
            rows.append(Sample(symbol=f"BAD{i}", day=day, pl=-20.0, value=3.0))
            rows.append(Sample(symbol=f"OK{i}", day=day, pl=10.0, value=1.0))
    v = D.verdict(rows, 2.0)
    assert v["verdict"] == D.SUPPORTED
    assert v["splits"]["era-controlled"]["above"]["trades"] == 30
    assert v["collateral"] == []
    assert all(s["edge"] > 0 for s in v["splits"].values())


def test_enough_modern_data_but_a_pre_gate_only_effect_is_still_flagged():
    """A pre-gate-only effect with plenty of modern trades reads ERA_ARTEFACT."""
    rows: list[Sample] = []
    for i in range(30):
        rows.append(Sample(symbol=f"A{i}", day="2026-06-10", pl=-100.0, value=3.0))
    for i in range(30):
        rows.append(Sample(symbol=f"B{i}", day="2026-08-01", pl=-1.0, value=3.0))
        rows.append(Sample(symbol=f"C{i}", day="2026-08-01", pl=-1.0, value=1.0))
    v = D.verdict(rows, 2.0)
    assert v["verdict"] == D.ERA_ARTEFACT
    assert v["splits"]["all-time"]["edge"] > 0
    assert v["splits"]["era-controlled"]["edge"] == 0


# --------------------------------------------------------------------------
# Pure helpers.
# --------------------------------------------------------------------------

def test_bucket_stats_handles_the_empty_and_all_winner_cases():
    assert D.bucket_stats([]) == {"trades": 0, "net": 0.0, "avg": 0.0,
                                 "win_rate": 0.0, "profit_factor": None}
    allwin = D.bucket_stats([1.0, 2.0])
    assert allwin["profit_factor"] is None      # no gross loss to divide by
    assert allwin["win_rate"] == 100.0
    mixed = D.bucket_stats([10.0, -5.0])
    assert mixed["profit_factor"] == 2.0
    assert mixed["net"] == 5.0


def test_split_at_reports_no_edge_when_one_side_is_empty():
    rows = [Sample("X", "2026-08-01", 1.0, 5.0)]
    assert D.split_at(rows, 99.0)["edge"] is None
    assert D.split_at(rows, 0.0)["edge"] is None


def test_cohort_boundaries_are_exact():
    rows = [
        Sample("A", D.PRE_GATE_ERA_END, 1.0, 3.0),          # last pre-gate day
        Sample("B", "2026-06-15", 1.0, 3.0),
        Sample("C", D.POST_GATE_START, 1.0, 3.0),           # first post-gate day
    ]
    groups = D.cohorts(rows)
    assert [s.symbol for s in groups["all-time"]] == ["A", "B", "C"]
    assert [s.symbol for s in groups["era-controlled"]] == ["B", "C"]
    assert [s.symbol for s in groups["post-gate"]] == ["C"]


def test_era_concentration_and_collateral_edge_cases():
    assert D.era_concentration([], 1.0) is None
    assert D.collateral_fraction([], 1.0) is None
    # A cohort that nets exactly zero has no meaningful fraction.
    flat = [Sample("A", "2026-08-01", 5.0, 3.0), Sample("A", "2026-08-01", -5.0, 3.0)]
    assert D.era_concentration(flat, 2.0) is None
    # Net-negative symbols are not collateral; ordering is best-first.
    rows = [
        Sample("WIN", "2026-08-01", 50.0, 3.0),
        Sample("MID", "2026-08-01", 5.0, 3.0),
        Sample("LOSS", "2026-08-01", -80.0, 3.0),
        Sample("BELOW", "2026-08-01", 999.0, 1.0),          # wrong side of the line
    ]
    coll = D.collateral_symbols(rows, 2.0)
    assert [r["symbol"] for r in coll] == ["WIN", "MID"]


def test_no_split_at_all_is_insufficient_data():
    rows = [Sample("A", "2026-08-01", 1.0, 5.0), Sample("B", "2026-08-01", 2.0, 5.0)]
    v = D.verdict(rows, 99.0)
    assert v["verdict"] == D.INSUFFICIENT_DATA
