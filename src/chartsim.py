#
# Chart Simulation
#

import csv
from typing import Iterator, Iterable
from model import Trade, TradePair, TradeMatcher
import marketdata
import pandas as pd
from pathlib import Path

SLIPAGE = 150 * 10**6 # slipage in nano seconds

class BrokerProxy:

    @classmethod
    def from_file(cls, market_data: Path): # pragma: no cover
        return cls(iter(marketdata.from_file(market_data)))

    def __init__(self, trades: Iterator[Trade]):
        self.contracts: int = 0
        self._stop_loss: int = None
        self.trades: Iterator[Trade] = trades
        self.next_trade: Trade = None
        self.time: int = -1
        self.forward_to(0)
        self.time_offset: int = self.next_trade.timestamp

    def execute_limits(self, trade: Trade):
        execute = False
        price = trade.price
        if self.contracts > 0:
            execute = price < self._stop_loss
        elif self.contracts < 0:
            execute = price > self._stop_loss
    
        executed_trade = None
        if execute:
            executed_trade = Trade(
                timestamp=trade.timestamp,
                price = price,
                volume=-self.contracts,
            )
            self.contracts = 0
            self._stop_loss = None
        return executed_trade

    def forward_to(self, time: int) -> None | Trade:
        """ forwards the time and returs a Trade if a stop loss or take profit limit was reached """

        if time <= self.time: # we are already there...
            return

        executed_trade = None
        while self.next_trade is None or self.next_trade.timestamp <= time:
            if self.contracts != 0:
                executed_trade = self.execute_limits(self.next_trade)
            self.next_trade = next(self.trades)
    
        self.time = time
        return executed_trade

    def order(self, contracts: int, stop_loss: int) -> Trade:
        if contracts == 0:
            return

        price = self.next_trade.price
        self._stop_loss = price - (stop_loss * contracts // abs(contracts))
        self.contracts += contracts
        self.time = self.next_trade.timestamp
        return Trade(
            timestamp=self.next_trade.timestamp,
            price=price,
            volume=contracts
        )

    @property
    def stop_loss(self) -> int:
        return self._stop_loss

    @stop_loss.setter
    def stop_loss(self, new_stop_loss: int):
        if self.contracts > 0:
            self._stop_loss = max(self.stop_loss, round(new_stop_loss))
        elif self.contracts < 0:
            self._stop_loss = min(self.stop_loss, round(new_stop_loss))

    def adjust_stop_loss(self, low: int, high: int, filter_constant: float):
        if self.contracts > 0:
            # we are long: adjust stop-loss based on low of current candle
            self.stop_loss = filter_constant * low + (1 - filter_constant) * self.stop_loss
        elif self.contracts < 0:
            # we are short: adjust stop-loss base on high of current candle
            self.stop_loss = filter_constant * high + (1 - filter_constant) * self.stop_loss


class ChartSimulator:

    def __init__(self, broker: BrokerProxy, candles_file: Path, stop_loss_factor: float): # pragma: no cover
        self.broker = broker
        self.candles_file = candles_file
        self.stop_loss_factor = stop_loss_factor

    def __iter__(self): # pragma: no cover
        """ simulates chart file """
        with open(self.candles_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for trade in self.execute_candle(
                                    timestamp = int(row['timestamp']),
                                    low = int(row['low']),
                                    high = int(row['high']),
                                    contracts = int(row['contracts']),
                                    stop_loss=int(row['stop_loss']),
                                ):
                    if trade:
                        yield trade
                    else:
                        break

    def execute_candle(self, timestamp: int, low: int, high: int, contracts: int, stop_loss: int): #pragma: no cover
        try:
            executed_trade = self.broker.forward_to(timestamp + SLIPAGE)
            if executed_trade:
                yield executed_trade
        except StopIteration:
            # no more trades available to market data file
            return

        if self.broker.contracts == 0:
            # no trade active, we may oder...
            ordered_trade = self.broker.order(contracts, stop_loss)
            if ordered_trade:
                yield ordered_trade
        else:
            self.broker.adjust_stop_loss(low, high, self.stop_loss_factor)

    @classmethod
    def simulate(cls, market_data: Path, **kwargs) -> Iterable[Trade]: # pragma: no cover
        """ create a simulator """
        broker = BrokerProxy.from_file(market_data)
        return cls(broker, **kwargs)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="simulate trades generated by Plutos on historical data")
    parser.add_argument('file', type=Path, help='chart file to be simulated')
    parser.add_argument('-d', '--market-data', type=Path, required=True, help='name of Databento native file (.dbn)')
    parser.add_argument('-s', '--stop-loss-factor', type=float, default=0.6, help="filter factor for adaption of stop-loss")
    parser.add_argument('-o', '--out-file', type=Path, help="result file with generated trades.")
    args = parser.parse_args()

    simulator = ChartSimulator.simulate(
        market_data=args.market_data,
        candles_file=args.file,
        stop_loss_factor=args.stop_loss_factor
    )
    matcher = TradeMatcher(simulator)

    df = pd.DataFrame([pair.to_dict() for pair in matcher])
    if len(df) == 0:
        print(f'{parser.prog}: no trade pairs available')
        exit()

    df['is_win'] = df['tick_capture'] > 0
    print(df.head(25).to_string())

    wins = df['is_win'].sum()
    total_trades = len(df)
    sum_ticks = df['tick_capture'].sum()
    sum_total = df['total_ticks'].sum()

    print(f'sum ticks: {sum_ticks}, sum_total: {sum_total}, trades: {total_trades}, win rate: {wins/total_trades}')
