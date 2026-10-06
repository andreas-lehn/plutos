"""
trader module
enthalt alles was mit dem kaufen und verkaufen zu tun hat.
"""

import random
import numpy as np
import pandas as pd
from pydantic import BaseModel
from typing import List, Dict, Iterator, Tuple, Protocol
from marketdata import BarLoader, VolumeBar
from datetime import datetime

class ToDictMixIn:
    def to_dict(self) -> dict:
        """Konvertiert das Pydantic-Modell in ein Dict inklusive aller @properties."""
        data = self.model_dump()
        # Alle @properties der aktuellen Klasse dynamisch einsammeln
        for name, attr in self.__class__.__dict__.items():
            if isinstance(attr, property):
                data[name] = getattr(self, name)
        return data

class Trade(ToDictMixIn, BaseModel):
    """Kapselt die Daten eines abgeschlossenen Trades"""

    buy_time: int
    buy_price: float
    sell_time: int
    sell_price: float
    volume: int

    @property
    def start_time(self) -> int:
        return min(self.sell_time, self.buy_time)

    @property
    def end_time(self) -> int:
        return max(self.sell_time, self.buy_time)

    @property
    def duration(self) -> int:
        return self.end_time - self.start_time

    @property
    def profit(self) -> float:
        return (self.sell_price - self.buy_price) * self.volume

    @property
    def is_win(self) -> bool:
        return self.profit > 0.0

    @property
    def long_short(self) -> str:
        return 'short' if self.sell_time < self.buy_time else 'long '

    def __repr__(self):
        dt_start = datetime.fromtimestamp(self.start_time // 1000).strftime("%H:%M:%S")
        dt_end   = datetime.fromtimestamp(self.end_time // 1000).strftime("%H:%M:%S")
        return f'{dt_start}-{dt_end}  {self.long_short} {self.volume:3d} {self.profit:8.2f}'


class Statistics(ToDictMixIn, BaseModel):
    """Statistics data of a trading day"""

    total_profit: float
    total_win: float
    trades: int
    wins: int
    max_profit: float
    min_profit: float
    volume: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades

    @property
    def profit_factor(self) -> float:
        return self.total_win / self.total_loss

    @property
    def total_loss(self) -> float:
        return self.total_win - self.total_profit

    @classmethod
    def from_trades(cls, trades: List[Trade]):
        df = pd.DataFrame([trade.to_dict() for trade in trades])
        win_trades = df[df["is_win"]]
        return cls(
            total_profit = df['profit'].sum(),
            trades = len(df),
            wins = len(win_trades),
            total_win = win_trades['profit'].sum(),
            max_profit = df['profit'].max(),
            min_profit = df['profit'].min(),
            volume = df['volume'].sum()
        )

    def __repr__(self):
        title = 'total_profit  trades  win_rate  p_factor  max_profit  min_profit\n' 
        values = f'{self.total_profit:12.2f}  {self.trades:6d}   {(self.win_rate*100):7.2f}% {self.profit_factor:8.2f}  {self.max_profit:10.2f}  {self.min_profit:10.2f}'
        return title + values


class Trader:
    """ Base trader that handle buy and sell decision but does no detection of them """

    def __init__(self, stop_loss_factor: float = 1.0):
        self._stop_loss_factor: float = stop_loss_factor
        self._state: str = 'flat'
        self._stop_loss: float = 0.0
        self._current_trade = {}
        self.trades: List[Trade] = []

    def stop_loss_long(self, bar: VolumeBar, old_stop_loss: float = None):
        """calculate stop loss for long trades"""
        stop_loss = bar.average + (bar.low - bar.average) * self._stop_loss_factor
        stop_loss = round(stop_loss / 0.25) * 0.25
        if old_stop_loss is not None:
            stop_loss = max(stop_loss, old_stop_loss) # only increase stop loss 
        return stop_loss 

    def stop_loss_short(self, bar: VolumeBar, old_stop_loss: float = None):
        """calculate stop loss for short trades"""
        stop_loss = bar.average + (bar.high - bar.average) * self._stop_loss_factor
        stop_loss = round(stop_loss / 0.25) * 0.25
        if old_stop_loss is not None:
            stop_loss = min(stop_loss, old_stop_loss) # only decreas stopp loss
        return stop_loss
    
    def trade(self, decision: str, bar: VolumeBar):
        """
        trades based on the decision and current state
        """

        if self._state == 'flat':
            # we are flat, so we can enter a trade if the decision is buy or sell
            if decision == 'buy':
                self._state = 'buy' # we place a buy order
                self._stop_loss = self.stop_loss_long(bar)
            if decision == 'sell':
                self._state = 'sell' # we place a sell order
                self._stop_loss = self.stop_loss_short(bar)
            return

        if self._state == 'buy':
            # we are in a buy position
            # we assume, that our order was fulfilled one tick over the opening price
            self._current_trade['buy_time'] = bar.timestamp
            self._current_trade['buy_price'] = bar.open + 0.25
            self._stop_loss = self.stop_loss_long(bar, self._stop_loss)
            self._state = 'long'
            return

        if self._state == 'long':
            # we are long. so we have to check, if we ran into our stop loss
            # print(f".   stop_loss: {self._stop_loss} | low: {bar.low}")
            if self._stop_loss > bar.low:
                # we assume, that we were stopped out one tick below our stop loss
                self._current_trade['sell_price'] = self._stop_loss - 0.25
                self._current_trade['sell_time'] = bar.timestamp
                self._state = 'flat'
                self._close_current_trade()
            else:
                # we are still going, so adapt stop loss...
                self._stop_loss = self.stop_loss_long(bar, self._stop_loss)
            return

        if self._state == 'sell':
            # we place a sell order and assume that we could sell is one tick less than the opening price
            self._current_trade['sell_time'] = bar.timestamp
            self._current_trade['sell_price'] = bar.open - 0.25
            self._stop_loss = self.stop_loss_short(bar, self._stop_loss)
            self._state = 'short'
            return

        if self._state == 'short':
            # we are short, so we have to check, if we ran into out stop loss
            if self._stop_loss < bar.high:
                # we assume that we were stopped out one tick over our stop loss
                self._current_trade['buy_time'] = bar.timestamp
                self._current_trade['buy_price'] = self._stop_loss + 0.25
                self._state = 'flat'
                self._close_current_trade()
            else:
                # trade is still active. we adjust stop loss...
                self._stop_loss = self.stop_loss_short(bar, self._stop_loss)
            return

    def _close_current_trade(self):
        self._current_trade['volume'] = 1
        trade = Trade.model_validate(self._current_trade)
        self.trades.append(trade)
        self._current_trade = {}

    def on_end_of_day(self) -> None:
        self._stat = 'flat'
        self._current_trade = {}

    def on_new_bar(self, bar: VolumeBar) -> None:
        decision = self.decide(bar)
        self.trade(decision, bar)


class KentBeckTrader(Trader):
    """
    Der einfachste aller Trader, der möglicherweise Gewinn machen könnte
    
    Er versucht über die Veränderung des gewichteten Durchschnitt von Kerzen ein Trendumkehr zu erkennen.
    Daraus erzeugt er dann Kauf/Verkauf/Haltesignal.
    """

    def __init__(self, filter_constant: float = 0.5, slope_threshold: float = 0.001, stop_loss_factor: float = 1.0):
        super().__init__(stop_loss_factor)
        
        self._filter_constant: float = filter_constant
        self._slope_threshold: float = slope_threshold
        self._state: str = 'flat'
        self._average: float = 0.0
        self._slope: float = 0.0
        self._old_slope: float = 0.0

    def decide(self, bar: VolumeBar) -> str:
        """
        analysis the current volume bar and decides what to
        
        returns "none", "buy", "sell"
        """

        current_slope = (bar.average - self._average) * self._filter_constant
        self._average += current_slope
        self._slope += (current_slope - self._slope) * self._filter_constant
        decision = 'none'
        if (abs(self._slope) > self._slope_threshold):
            if (self._slope * self._old_slope) < 0.0:
                if self._slope > 0.0:
                    decision = 'buy'
                if self._slope < 0.0:
                    decision = 'sell'
            self._old_slope = self._slope
        return decision


class RandomTrader(Trader):
    """
    Ein Trader, der eine Münze wirft, um zu entscheiden, ob gekauft oder verkauft wird.
    """

    def decide(self, bar: VolumeBar) -> str:
        """ entscheidung würfeln """
        decisions = ['buy', 'sell']
        return random.choice(decisions)


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Trade simulator: Lädt Volumenbalken aus einer CSV-Datei und simuliert Echtzeit-Events.")
    parser.add_argument("filename", help="CSV with volume bars")
    parser.add_argument('-t', '--trader', choices=["kentbeck", 'random'], default='kentbeck', help='selects a trader: ( random | kentbeck )')
    parser.add_argument('-m', '--margin', type=float, default=1.0, help='stop loss margin')
    args = parser.parse_args()
    trader_name = args.trader.lower()

    collector = StatisticsCollector()
    trade_statistics = TradeStatistics()
    trade_statistics.add_listener(collector)
    if trader_name == 'kentbeck':
        trader = KentBeckTrader(stop_loss_factor=args.margin)
    elif trader_name == 'random':
        trader = RandomTrader(stop_loss_factor=args.margin)
    else:
        print(f"{parser.prog}: error: unknoen trader '{args.trader}'")
        sys.exit(1)
    trader.add_listener(trade_statistics)
    loader = BarLoader()
    loader.add_listener(trader)     # Trader reagiert auf fertige Balken
    loader.load_and_stream(args.filename)

    print(collector.data_frame)
