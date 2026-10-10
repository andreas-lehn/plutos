import argparse
import os
from pathlib import Path

import pandas as pd

from marketdata import BarBuilder, SampleLoader
from trader import KentBeckTrader, Statistics, Trade

pd.options.display.float_format = '{:.2f}'.format

DATA_DIR = Path(os.getenv('DATABENTO_DIR', "../databento"))

SYMBOL   = "MNQZ6"
DATE     = "2026-10-01"
BAR_SIZE = "30s"

REFERENCE_DAYS = ['2026-09-14', '2026-09-18', '2026-09-23', '2026-09-28', '2026-10-01']

def filename(date: str = DATE, bar: str = BAR_SIZE, symbol: str = SYMBOL) -> str:
    return f'{symbol}_{date}_{bar}.csv'


def pathname(date: str = DATE, bar: str = BAR_SIZE, symbol: str = SYMBOL) -> str:
    return DATA_DIR/filename(date, bar, symbol)

def run(files: str | list[str], filter_constant: float = 0.5, slope_threshold: float = 0.001, margin: float = 1.0) -> list[Trade] | list[Statistics]:
    if isinstance(files, (str, Path)):
        trader = KentBeckTrader(filter_constant, slope_threshold, margin)
        loader = SampleLoader()
        builder = BarBuilder(60)
        builder.add_listener(trader)
        loader.add_listener(builder)
        loader.load_and_stream(files)
        return trader.trades

    stats = []
    for file in files:
        trades = run(file, filter_constant, slope_threshold, margin)
        stats.append(Statistics.from_trades(trades))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trader simulation.")
    parser.add_argument("-f", "--filter", type=float, default=0.5, help="PT1 filter constant")
    parser.add_argument("-s", "--slope-threshold",type=float,default=0.001, help="threshold for slope")
    parser.add_argument('-m', '--margin', type=float, default=1.0, help='stop loss margin')
    parser.add_argument("files", nargs="+", help="list of CSV file with bars to be simulated")
    args = parser.parse_args()

    stats = run(args.files, args.filter, args.slope_threshold, args.margin)
    df = pd.DataFrame([stat.to_dict() for stat in stats])
    df = df[['total_profit', 'trades', 'win_rate', 'profit_factor', 'max_profit', 'min_profit']]
    print()
    print(df)

    total = df["total_profit"].sum()
    trades = df["trades"].sum()
    win_rate = df["win_rate"].mean() 
    profit_factor = df["profit_factor"].mean()
    max_win = df["max_profit"].max()
    max_loss = df["min_profit"].min()

    formatter = pd.io.formats.format.DataFrameFormatter(df)
    strcols = formatter.get_strcols()
    w = [max(len(zeile) for zeile in spalte) for spalte in strcols]
    w_total = sum(w) + (len(w) - 1)
    text = (' ', f'{total/4:.2f}', f'{trades}', f'{win_rate:.2f}', f'{profit_factor:.2f}', f'{max_win/4:.2f}', f'{max_loss/4:.2f}')
    for t, w in zip(text, w):
        print(f'{t:>{w}} ', end='')
    print()
