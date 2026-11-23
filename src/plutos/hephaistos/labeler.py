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


def low_high_diff(chart: Chart, index: int, window_size: int):
    """ calculates in a given chart intervall low, high and change """

    min_low, max_low, min_high, max_high = None, None, None, None
    for i in range(index, index + window_size):
        candle = chart[i]
        if not min_low:
            min_low  = max_low  = candle.low
            min_high = max_high = candle.high
        else:
            min_low  = min(min_low, candle.low)
            max_low  = max(max_low, candle.low)
            min_high = min(min_high, candle.high)
            max_high = max(max_high, candle.high)
    return min_low, max_low, min_high, max_high


def is_short_precondition(swing_high: int, close: int) -> bool:
    return (
            close < swing_high - config.MIN_SWING_DISTANCE 
        and close > swing_high - config.RISK 
    )

def is_short_signal(swing_high: int, close: int, min_high: int, max_high: int) -> bool:
    return (
            min_high < close - config.PROFIT
        and max_high < swing_high
    )

def is_long_precondition(swing_low: int, close: int) -> bool:
    return (
            close > swing_low + config.MIN_SWING_DISTANCE
        and close < swing_low + config.RISK
    )

def is_long_signal(swing_low: int, close: int, min_low: int, max_low: int) -> bool:
    return (
            max_low > close + config.PROFIT
        and min_low > swing_low
    )

def label_candle(chart: Chart, index):
    """ labels candle at index """
    candle = chart[index]
    close = candle.close
    min_low, max_low, min_high, max_high = low_high_diff(chart, index + 1, config.WINDOW_SIZE)     
    candle.pre_short = is_short_precondition(candle.swing_high, close)
    candle.target_short = is_short_signal(candle.swing_high, close, min_high, max_high)
    candle.pre_long = is_long_precondition(candle.swing_low, close)
    candle.target_long = is_long_signal(candle.swing_low, close, min_low, max_low)

def label(chart: Chart):
    """ label a chart """
    for i, candle in enumerate(chart):
        candle.target_short = False
        candle.target_long = False
        if len(chart) > config.WINDOW_SIZE + 1:
            label_candle(chart, i - config.WINDOW_SIZE)


def generate_chart(file: Path, candle_size: int) -> Chart:  # pragma: no cover
    """ generate a chart from a file with a given candle size """
    main_chart = Chart(candle_size=candle_size)
    model = MarketModel()
    model.charts.append(main_chart)
    model.simulate_file(file)
    return main_chart


@click.command('label')
@click.argument('file', type=click.Path(), help='name of market data file (.dbn)')
def label_cmd(file: Path): # pragma: no cover
    """ create a labeled chart """
    chart = generate_chart(file, config.CANDLE_SIZE)
    label(chart)

    pre_short, target_short, pre_target_short = 0, 0, 0
    pre_long,  target_long,  pre_target_long  = 0, 0, 0
    for candle in chart:
        if candle.pre_short: pre_short += 1
        if candle.target_short: target_short += 1
        if candle.pre_short and candle.target_short: pre_target_short += 1
        if candle.pre_long: pre_long += 1
        if candle.target_long: target_long += 1
        if candle.pre_long and candle.target_long: pre_target_long += 1

    click.secho('              short   long', bold=True)
    click.echo(f'precondition  {pre_short:5d}  {pre_long:5d}')
    click.echo(f'target        {target_short:5d}  {target_long:5d}')
    click.echo(f'pre & target  {pre_target_short:5d}  {pre_target_long:5d}')
    click.echo(f'ratio pre     {100*pre_target_short/pre_short:5.2f}  {100*pre_target_long/pre_long:5.2f}')
    click.echo(f'ratio target  {100*pre_target_short/target_short:5.2f}  {100*pre_target_long/target_long:5.2f}')

    file_parts = marketdata.parse_path(file)
    file_parts['parent'] = '.'
    file_parts['suffix'] = '.csv'
    file_parts['content'] = 'labeled-chart'
    chart_file = marketdata.assemble_path(file_parts)

    fieldnames = Candle.FIELDNAMES + ['pre_short', 'target_short', 'pre_long', 'target_long']
    with open(chart_file, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([candle.to_filtered_dict(fieldnames) for candle in chart])
    click.echo(f"Labeled chart written to '{chart_file}'")
