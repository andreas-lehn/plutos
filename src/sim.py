import argparse
import os
from marketdata import BarLoader
from trader import KentBeckTrader, Trade, Statistics
import pandas as pd
from typing import List, Dict, Iterator, Tuple, Protocol
from pathlib import Path

pd.options.display.float_format = '{:.2f}'.format

data_dir = Path(os.getenv('DATABENTO_DIR', "../databento"))

default_symbol = "MNQZ6"
default_date = "2026-10-01"
default_bar = "30s"

def make_filename(date: str = default_date, bar: str = default_bar, symbol: str = default_symbol):
    return f'{symbol}_{date}_{bar}.csv'

def sim(date: str = default_date, bar: str = default_bar, symbol: str = default_symbol) -> List[Trade]:
    """simulation a symbol"""
    return simulate(data_dir/make_filename(date, bar, symbol))

def simulate(filename: str, filter_constant: float = 0.5, slope_threshold: float = 0.001, margin: float = 1.0)  -> List[Trade]:
    trader = KentBeckTrader(filter_constant, slope_threshold, margin)
    loader = BarLoader()
    loader.add_listener(trader)
    loader.load_and_stream(filename)
    return trader.trades

def simulate_files(file_list: List[str], filter_constant: float = 0.5, slope_threshold: float = 0.001, margin: float = 1.0) -> List[Statistics]:
    stats = []
    for file in file_list:
        print(f"{parser.prog}: simulating {os.path.basename(file)} ...", end='')
        trades = simulate(file, filter_constant, slope_threshold, margin)
        stats.append(Statistics.from_trades(trades))
        print('done.')
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trader simulation.")
    parser.add_argument("-f", "--filter", type=float, default=0.5, help="PT1 filter constant")
    parser.add_argument("-s", "--slope-threshold",type=float,default=0.001, help="threshold for slope")
    parser.add_argument('-m', '--margin', type=float, default=1.0, help='stop loss margin')
    parser.add_argument("files", nargs="+", help="list of CSV file with bars to be simulated")
    args = parser.parse_args()

    stats = simulate_files(args.files, args.filter, args.slope_threshold, args.margin)
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
    text = (f' ', f'{total:.2f}', f'{trades}', f'{win_rate:.2f}', f'{profit_factor:.2f}', f'{max_win:.2f}', f'{max_loss:.2f}')
    for t, w in zip(text, w):
        print(f'{t:>{w}} ', end='')
    print()
