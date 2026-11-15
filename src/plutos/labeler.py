#
# labeler.py
#

import csv
import click
from pathlib import Path
from collections import deque

from . import marketdata
from .chart import MarketModel, Chart, Candle


def generate_chart(file: Path, candle_size: int) -> Chart:  # pragma: no cover
    """ generate a chart from a file with a given candle size """
    main_chart = Chart(candle_size=candle_size)
    model = MarketModel()
    model.charts.append(main_chart)
    model.simulate_file(file)
    return main_chart


def is_trend(averages: list[int]):
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


def label_trends(chart: Chart, length):  # pragma: no cover
    """ label in chart trend starts of a given length """
    averages = deque(maxlen=length + 2)
    for i, candle in enumerate(chart):
        candle.trend_start = 'none'
        averages.append(candle.average)
        if len(averages) == length + 2:
            trend = is_trend(averages)
            if trend > 0:
                chart[i - length].trend_start = 'up'
            elif trend < 0:
                chart[i - length].trend_start = 'down'


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
                chart[i - window_size].profit_chance = 'both'
            elif short_chance:
                chart[i - window_size].profit_chance = 'short'
            elif long_chance:
                chart[i - window_size].profit_chance = 'long'


@click.command('label')
@click.argument('file', type=click.Path(), help='name of market data file (.dbn)')
@click.option('-s', '--candle-size', type=int, default=36, help="size of candle in seconds")
@click.option('-l', '--trend-length', type=int, default=5, help="length of trend (in candles) to be labeled")
@click.option('-r', '--risk', type=int, default=24, help="maximum risk to be taken (in ticks)")
@click.option('-p', '--profit', type=int, default=48, help="profit to be achieved (in ticks)")
@click.option('-w', '--window-size', type=int, default=12, help="size of tripple barrier window in candles")
def label_cmd(file: Path, candle_size: int, trend_length: int, risk: int, profit: int, window_size: int): # pragma: no cover
    chart = generate_chart(file, candle_size)
    label_trends(chart, trend_length)
    label_profit_chances(chart, risk, profit, window_size)

    file_parts = marketdata.parse_path(file)
    file_parts['parent'] = '.'
    file_parts['suffix'] = '.csv'
    file_parts['content'] = 'labeled-chart'
    chart_file = marketdata.assemble_path(file_parts)

    fieldnames = ['index', 'timestamp', 'open', 'low', 'average', 'high', 'close', 'volume', 'ema_fast', 'ema_slow', 'trend_start', 'profit_chance']
    with open(chart_file, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([candle.to_filtered_dict(fieldnames) for candle in chart])
    click.echo(f"Labeled chart written to '{chart_file}'")
