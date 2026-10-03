import argparse
import os
import marketdata
import pandas as pd
from typing import List, Dict, Iterator, Tuple, Protocol


def simulate(filename: str, filter_constant: float = 0.5, slope_thershold: float = 0.1, statistics_listener: marketdata.TradeStatisticsListener = None):
    trade_statistics = marketdata.TradeStatistics()
    trade_statistics.add_listener(statistics_listener)
    trader = marketdata.KentBeckTrader(filter_constant=0.5)
    trader.add_listener(trade_statistics)
    loader = marketdata.BarLoader()
    loader.add_bar_listener(trader)
    loader.load_and_stream(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trader simulation.")
    parser.add_argument("-f", "--filter", type=float, default=0.5, help="PT1 filter constant")
    parser.add_argument("-s", "--slope-threshold",type=float,default=0.1, help="threshold for slope direction change evaluation") 
    parser.add_argument("files", nargs="+", help="list of CSV file with bars to be simulated")
    args = parser.parse_args()

    collector = marketdata.StatisticsCollector()

    args.files.sort()
    for file in args.files:
        print(f"{parser.prog}: simulating {os.path.basename(file)} ...", end='')
        simulate(file, filter_constant = args.filter, slope_thershold = args.slope_threshold, statistics_listener = collector)
        print('done.')

    print()
    print(collector.data_frame)
    