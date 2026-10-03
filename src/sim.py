import argparse
import os
import marketdata
import pandas as pd
from typing import List, Dict, Iterator, Tuple, Protocol

pd.options.display.float_format = "{:.2f}".format

class StatisticsListener:
    """collects the statistics of each simulated day"""

    def __init__(self):
        self._stats: List[marketdata.Statistics] = []
        self._data_frame: pd.DataFrame = None

    @property
    def data_frame(self) -> pd.DataFrame:
        if self._data_frame is None:
            self._data_frame = pd.DataFrame([stats.model_dump() for stats in self._stats])
        return self._data_frame

    def on_day_closed(self, statistics):
        self._stats.append(statistics)
        self._data_frame = None


def simulate(filename: str, filter_constant: float = 0.5, slope_thershold: float = 0.1, statistics_listener: marketdata.TradeStatisticsListener = None):
    trade_statistics = marketdata.TradeStatistics()
    trade_statistics.add_listener(statistics_listener)
    trader = marketdata.KentBeckTrader(filter_constant=0.5)
    trader.add_listener(trade_statistics)
    loader = marketdata.BarLoader()
    loader.add_bar_listener(trader)     # Trader reagiert auf fertige Balken
    loader.load_and_stream(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trader simulation.")
    parser.add_argument("-f", "--filter", type=float, default=0.5, help="PT1 filter constant")
    parser.add_argument("-s", "--slope-threshold",type=float,default=0.1, help="threshold for slope direction change evaluation") 
    parser.add_argument("files", nargs="+", help="list of CSV file with bars to be simulated")
    args = parser.parse_args()

    statistics = StatisticsListener()

    args.files.sort()
    for file in args.files:
        print(f"{parser.prog}: simulating {os.path.basename(file)} ...", end='')
        simulate(file, filter_constant = args.filter, slope_thershold = args.slope_threshold, statistics_listener = statistics)
        print('done.')

    data_frame = statistics.data_frame
    styled_data_frame = data_frame.style.format({
            "total_profit": "{:.2f}",
            "max_profit": "{:.2f}",
            "min_profit": "{:.2f}",
            "win_rate": "{:.1%}",  # Macht aus 0.556 automatisch 55.6%
            "profit_factor": "{:.2f}",  # Einfach sauber auf 2 Stellen gerundet
        }
    )
    print(data_frame)
    