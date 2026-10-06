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


class Statistics(BaseModel):
    """Statistic data of a trading day"""

    total_profit: float
    trades: int
    win_rate: float
    profit_factor: float
    max_profit: float
    min_profit: float


# =====================================================================
# 2. PROTOKOLLE (Schnittstellen für das Observer-Pattern)
# =====================================================================

class TraderListener(Protocol):
    """Schnittstelle für Trade Listener"""
    def on_trade_closed(self, trade: Trade) -> None:
        """Wird bei einem abgeschlossenen Trade aufgerufen"""
        ...

class TradeStatisticsListener(Protocol):
    def on_day_closed(self, statistics: Statistics):
        ...

class StatisticsCollector:
    """collects the trade statistics of each simulated day"""

    def __init__(self):
        self._stats: List[Statistics] = []
        self._data_frame: pd.DataFrame = None

    @property
    def data_frame(self) -> pd.DataFrame:
        if self._data_frame is None:
            self._data_frame = pd.DataFrame([stats.model_dump() for stats in self._stats])
        return self._data_frame

    def on_day_closed(self, statistics):
        self._stats.append(statistics)
        self._data_frame = None


class TradeStatistics:
    """Collects trades as a trade listener and calculates statistics on these trades"""

    def __init__(self):

        self.trades_schema = {
            'buy_time': 'int',
            'buy_price': 'float',
            'sell_time': 'int',
            'sell_price': 'float',
            'volume': int,
            'profit': 'float',
            'duration': 'int'
        }
        self.trades: pd.DataFrame = pd.DataFrame(columns=self.trades_schema.keys())
        self.trades = self.trades.astype(self.trades_schema)
        self._listeners: List[TradeStatisticsListener] = []

    def add_listener(self, listener: TradeStatisticsListener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: TradeStatisticsListener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_day_closed(self, stats: Statistics):
        for listener in self._listeners:
            listener.on_day_closed(stats)
    
    def on_trade_closed(self, closed_trade: Trade) -> None:
        trade = {
            'buy_time': closed_trade.buy_time,
            'buy_price': closed_trade.buy_price,
            'sell_time': closed_trade.sell_time,
            'sell_price': closed_trade.sell_price,
            'volume': closed_trade.volume,
            'profit': (closed_trade.sell_price - closed_trade.buy_price) * closed_trade.volume,
            'duration': abs(closed_trade.buy_time - closed_trade.sell_time)
        }
        new_frame = pd.DataFrame([trade], columns=self.trades_schema.keys()).astype(self.trades_schema)
        self.trades = pd.concat([self.trades, new_frame], ignore_index=True)

    def on_day_closed(self):
        self._notify_day_closed(self.get_statistics())

    @property
    def _win_trades(self):
        return self.trades[self.trades["profit"] > 0.0]

    @property
    def _loss_trades(self):
        return self.trades[self.trades['profit'] <= 0.0]

    @property
    def number_of_trades(self) -> int:
        return len(self.trades)
    
    @property
    def total_profit(self) -> float:
        return self.trades['profit'].sum()

    @property
    def max_profit(self) -> float:
        return self.trades['profit'].max()

    @property
    def min_profit(self) -> float:
        return self.trades['profit'].min()

    @property
    def win_profit(self) -> float:
        return self._win_trades['profit'].sum()
    
    @property
    def loss_profit(self) -> float:
        return self._loss_trades['profit'].sum()
    
    @property
    def win_rate(self) -> float:
        n_wins = len(self._win_trades)
        n_loss = len(self._loss_trades)
        n_total = n_wins + n_loss
        return (n_wins / n_total) if n_total > 0 else 0.0

    @property
    def profit_factor(self) -> float:
        loss_profit = -self.loss_profit
        return self.win_profit / loss_profit if loss_profit != 0.0 else 0.0 

    def get_statistics(self) -> Statistics:
        return Statistics(
            total_profit = self.total_profit,
            trades = self.number_of_trades,
            win_rate = self.win_rate,
            profit_factor = self.profit_factor,
            max_profit = self.max_profit,
            min_profit = self.min_profit
        )

    def to_csv(filename: str) -> None:
        pass


class Trader:
    """ Base trader that handle buy and sell decision but does no detection of them """

    def __init__(self):
        self._state: str = 'flat'
        self._stop_loss: float = 0.0
        self._current_trade = {}
        self._listeners: List[TraderListener] = []

    def add_listener(self, listener: TraderListener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: TraderListener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_trade_closed(self, trade: Trade):
        for listener in self._listeners:
            listener.on_trade_closed(trade)

    def _notify_day_closed(self):
        for listener in self._listeners:
            listener.on_day_closed()

    def trade(self, decision: str, bar: VolumeBar):
        """
        trades based on the decision and current state
        """

        if self._state == 'flat':
            # we are flat, so we can enter a trade if the decision is buy or sell
            if decision == 'buy':
                self._state = 'buy' # we place a buy order
                self._stop_loss = bar.low
            if decision == 'sell':
                self._state = 'sell' # we place a sell order
                self._stop_loss = bar.high

        if self._state == 'buy':
            # we are in a buy position
            # we assume, that our order was fulfilled one tick over the opening price
            self._current_trade['buy_time'] = bar.timestamp
            self._current_trade['buy_price'] = bar.open + 0.25
            self._stop_loss = bar.low
            self._state = 'long'

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
                self._stop_loss = bar.low

        if self._state == 'sell':
            # we place a sell order and assume that we could sell is one tick less than the opening price
            self._current_trade['sell_time'] = bar.timestamp
            self._current_trade['sell_price'] = bar.open - 0.25
            self._stop_loss = bar.high
            self._state = 'short'

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
                self._stop_loss = bar.high

    def _close_current_trade(self):
        self._current_trade['volume'] = 1
        trade = Trade.model_validate(self._current_trade)
        self._notify_trade_closed(trade)
        self._current_trade = {}

    def on_end_of_day(self) -> None:
        self._stat = 'flat'
        self._current_trade = {}
        self._notify_day_closed()

    def on_new_bar(self, bar: VolumeBar) -> None:
        decision = self.decide(bar)
        self.trade(decision, bar)


class KentBeckTrader(Trader):
    """
    Der einfachste aller Trader, der möglicherweise Gewinn machen könnte
    
    Er versucht über die Veränderung des gewichteten Durchschnitt von Kerzen ein Trendumkehr zu erkennen.
    Daraus erzeugt er dann Kauf/Verkauf/Haltesignal.
    """

    def __init__(self, filter_constant: float = 0.5, slope_threshold: float = 0.001):
        super().__init__()
        
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
    parser.add_argument('-t', '--trader', default="kentbeck", help='selects a trader: ( random | kentbeck )')
    args = parser.parse_args()
    trader_name = args.trader.lower()

    collector = StatisticsCollector()
    trade_statistics = TradeStatistics()
    trade_statistics.add_listener(collector)
    if trader_name == 'kentbeck':
        trader = KentBeckTrader()
    elif trader_name == 'random':
        trader = RandomTrader()
    else:
        print("{parser.prog}: error: unknoen trader '{args.trader}'")
        sys.exit(1)
    trader.add_listener(trade_statistics)
    loader = BarLoader()
    loader.add_listener(trader)     # Trader reagiert auf fertige Balken
    loader.load_and_stream(args.filename)

    print(collector.data_frame)
