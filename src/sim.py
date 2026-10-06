import argparse
import os
from marketdata import BarLoader
from trader import TradeStatistics, KentBeckTrader, StatisticsCollector, TradeStatisticsListener
#import pandas as pd
from typing import List, Dict, Iterator, Tuple, Protocol
from pandas.io.formats.format import DataFrameFormatter

def simulate(filename: str, filter_constant: float, slope_threshold: float, margin: float, statistics_listener: TradeStatisticsListener):
    trade_statistics = TradeStatistics()
    trade_statistics.add_listener(statistics_listener)
    trader = KentBeckTrader(filter_constant, slope_threshold, margin)
    trader.add_listener(trade_statistics)
    loader = BarLoader()
    loader.add_listener(trader)
    loader.load_and_stream(filename)

def simulate_files(file_list: List[str], filter_constant: float, slope_threshold: float, margin: float, statistics_listener: TradeStatisticsListener):
    for file in file_list:
        print(f"{parser.prog}: simulating {os.path.basename(file)} ...", end='')
        simulate(file, filter_constant, slope_threshold, margin, statistics_listener)
        print('done.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trader simulation.")
    parser.add_argument("-f", "--filter", type=float, default=0.5, help="PT1 filter constant")
    parser.add_argument("-s", "--slope-threshold",type=float,default=0.001, help="threshold for slope")
    parser.add_argument('-m', '--margin', type=float, default=1.0, help='stop loss margin')
    parser.add_argument("files", nargs="+", help="list of CSV file with bars to be simulated")
    args = parser.parse_args()

    collector = StatisticsCollector()
    simulate_files(args.files, args.filter, args.slope_threshold, args.margin, collector)
    df = collector.data_frame
    print()
    print(df)

    total = df["total_profit"].sum()
    trades = df["trades"].sum()
    win_rate = df["win_rate"].mean() 
    profit_factor = df["profit_factor"].mean()
    max_win = df["max_profit"].max()
    max_loss = df["min_profit"].min()

    formatter = DataFrameFormatter(df)
    strcols = formatter.get_strcols()
    w = [max(len(zeile) for zeile in spalte) for spalte in strcols]
    w_total = sum(w) + (len(w) - 1)
    text = (f' ', f'{total:.2f}', f'{trades}', f'{win_rate:.2f}', f'{profit_factor:.2f}', f'{max_win:.2f}', f'{max_loss:.2f}')
    for t, w in zip(text, w):
        print(f'{t:>{w}} ', end='')
    print()
