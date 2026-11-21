#
# labeler.py
#

import csv
import click
from pathlib import Path
from collections import deque

from .. import marketdata
from ..chart import MarketModel, Chart, Candle
from . import config


def generate_chart(file: Path, candle_size: int) -> Chart:  # pragma: no cover
    """ generate a chart from a file with a given candle size """
    main_chart = Chart(candle_size=candle_size)
    model = MarketModel()
    model.charts.append(main_chart)
    model.simulate_file(file)
    return main_chart


def is_trend_start(averages: list[int]):
    """ test if a trend starts at 'average[1]' """
    deltas = [averages[i] - averages[i - 1] for i in range(1, len(averages))]
    trend = 0
    if (deltas[0] * deltas[1]) <= 0:
        # delta of must change direction at average[1] to start a trend
        trend = deltas[1] # direction of trend to be started
        for i in range(2, len(deltas)):
            if (trend * deltas[i]) <= 0:
                trend = 0
                break
    return trend


def label_trend_starts(chart: Chart, length):  # pragma: no cover
    """ label in chart trend starts of a given length """
    averages = deque(maxlen=length + 2)
    for i, candle in enumerate(chart):
        candle.trend_start = 'none'
        averages.append(candle.average)
        if len(averages) == length + 2:
            trend = is_trend_start(averages)
            if trend > 0:
                chart[i - length].trend_start = 'up'
            elif trend < 0:
                chart[i - length].trend_start = 'down'


def label_trade_chance(chart: Chart, window_length: int):
    """ label a sidewards movment """
    for i, candle in enumerate(chart):
        candle.target_trade = False
        if len(chart) > window_length:
            candle_to_label = chart[i - window_length]
            if (candle_to_label.high < candle.low or candle_to_label.low > candle.high):
                candle_to_label.target_trade = True


def tripple_barrier(low: int, high: int, values: list[int]) -> int:
    """ executes a tripple barrier check
    
    returns:
        -1 if low barrier is passed
         0 if no barrier is passed
         1 if high barrier is passed
    """
    result = 0
    for value in values:
        if value < low:
            result = -1
            break
        elif value > high:
            result = 1
            break
    return result


def is_short_chance(start, risk, profit, values) -> bool:
    """ checks if this is a short chance """
    return tripple_barrier(start - profit, start + risk, values) == -1


def is_long_chance(start, risk, profit, values) -> bool:
    """ checks if this is a long chance """
    return tripple_barrier(start - risk, start + profit, values) == 1


def label_profit_chances(chart: Chart, risk: int, profit: int, window_size):  # pragma: no cover
    """ label in chart profit chances """

    open = deque(maxlen=window_size)
    low  = deque(maxlen=window_size)
    high = deque(maxlen=window_size)

    for i, candle in enumerate(chart):
        candle.profit_chance = 'none'
        open.append(candle.open)
        low.append(candle.low)
        high.append(candle.high)
        if len(open) == window_size:
            short_chance = is_short_chance(open[0], risk, profit, high)
            long_chance = is_long_chance(open[0], risk, profit, low)
            if short_chance and long_chance:
                raise ValueError(f"label_profit_chances(): short and long chance detected.")
            elif short_chance:
                chart[i - window_size].profit_chance = 'short'
            elif long_chance:
                chart[i - window_size].profit_chance = 'long'


def label_profit_trade(chart: Chart, look_ahead: int, profit: int):
    """ labels trade """
    for i, candle in enumerate(chart):
        candle.target_long = False
        candle.target_short = False

        if i <= look_ahead: continue

        candle_to_label = chart[i - look_ahead]
        start_candle = chart[i - look_ahead + 1]
        open = start_candle.open
        close = candle.close
        if close < open - profit:
            stopped = False
            for j in range(i - look_ahead + 1, i + 1):
                if chart[j].high > candle_to_label.high:
                    stopped = True
                    break
            if not stopped:
                candle_to_label.target_short = True
        if close > open + profit: 
            stopped = False
            for j in range(i - look_ahead + 1, i + 1):
                if chart[j].low < candle_to_label.low:
                    stopped = True
                    break
            if not stopped:
                candle_to_label.target_long = True


def label(chart: Chart):
    """ labels a chart """
    #label_trend_starts(chart, trend_length)
    #label_profit_chances(chart, risk, profit, window_size)
    label_profit_trade(chart, config.LOOK_AHEAD, config.PROFIT)
    label_trade_chance(chart, config.WINDOW_SIZE)


@click.command('label')
@click.argument('file', type=click.Path(), help='name of market data file (.dbn)')
def label_cmd(file: Path): # pragma: no cover
    """ create a labeled chart """
    chart = generate_chart(file, config.CANDLE_SIZE)
    label(chart)

    file_parts = marketdata.parse_path(file)
    file_parts['parent'] = '.'
    file_parts['suffix'] = '.csv'
    file_parts['content'] = 'labeled-chart'
    chart_file = marketdata.assemble_path(file_parts)

    fieldnames = ['index', 'timestamp', 'open', 'low', 'average', 'high', 'close', 'volume', 'ema_fast', 'ema_slow', 'target_trade', 'target_short', 'target_long']
    with open(chart_file, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([candle.to_filtered_dict(fieldnames) for candle in chart])
    click.echo(f"Labeled chart written to '{chart_file}'")
