"""
trader module
enthalt alles was mit dem kaufen und verkaufen zu tun hat.
"""

import random
import sys
from collections import deque
from datetime import datetime

import pandas as pd
from pydantic import BaseModel

from marketdata import Bar, BarBuilder, SampleLoader


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
    buy_price: int
    sell_time: int
    sell_price: int
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
    def profit(self) -> int:
        return (self.sell_price - self.buy_price) * self.volume

    @property
    def is_win(self) -> bool:
        return self.profit > 0.0

    def __repr__(self):
        dt_start = datetime.fromtimestamp(self.start_time // 1000).strftime("%H:%M:%S")
        dt_end   = datetime.fromtimestamp(self.end_time // 1000).strftime("%H:%M:%S")
        return f'{dt_start}-{dt_end}  {self.long_short} {self.volume:3d} {self.sell_price/4:8.2f} {self.buy_price/4:8.2f} {self.profit/4:8.2f}'


class Statistics(ToDictMixIn, BaseModel):
    """Statistics data of a trading day"""

    total_profit: int
    total_win: int
    trades: int
    wins: int
    max_profit: int
    min_profit: int
    volume: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades

    @property
    def profit_factor(self) -> float:
        return self.total_win / self.total_loss

    @property
    def total_loss(self) -> int:
        return self.total_win - self.total_profit

    @classmethod
    def from_trades(cls, trades: list[Trade]):
        if not trades:
            return None
        
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
        values = f'{self.total_profit/4:12.2f}  {self.trades:6d}   {(self.win_rate*100):7.2f}% {self.profit_factor:8.2f}  {self.max_profit/4:10.2f}  {self.min_profit/4:10.2f}'
        return title + values

    def __str__(self):
        return self.__repr__()


class Trader:
    """ Base trader that handle buy and sell decision but does no detection of them """

    def __init__(self, stop_loss_factor: float = 1.0):
        self._stop_loss_factor: float = stop_loss_factor
        self._state: str = 'flat'
        self._stop_loss: int = 0
        self._current_trade = {}
        self.trades: list[Trade] = []

    def reset(self) -> None:
        self.trades = []
        self.state = 'flat'
        self._current_trade = {}

    def stop_loss_long(self, bar: Bar, old_stop_loss: int | None = None):
        """calculate stop loss for long trades"""
        stop_loss = bar.average + round((bar.low - bar.average) * self._stop_loss_factor)
        if old_stop_loss is not None:
            stop_loss = max(stop_loss, old_stop_loss) # only increase stop loss 
        return stop_loss 

    def stop_loss_short(self, bar: Bar, old_stop_loss: int | None = None):
        """calculate stop loss for short trades"""
        stop_loss = bar.average + round((bar.high - bar.average) * self._stop_loss_factor)
        if old_stop_loss is not None:
            stop_loss = min(stop_loss, old_stop_loss) # only decreas stopp loss
        return stop_loss
    
    def trade(self, decision: str, bar: Bar):
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
            buy_price = bar.open + 1
            self._current_trade['buy_price'] = buy_price
            if self._stop_loss > buy_price: # stop loss bereits beim kauf unterschritten
                self._stop_loss = buy_price - 1 # stop loss 1 tick unter kaufkurs setzen
            self._current_trade['stop_loss'] = self._stop_loss
            self._state = 'long'


        if self._state == 'long':
            # we are long. so we have to check, if we ran into our stop loss
            # print(f".   stop_loss: {self._stop_loss} | low: {bar.low}")
            if self._stop_loss > bar.low:
                # we assume, that we were stopped out one tick below our stop loss
                self._current_trade['sell_price'] = self._stop_loss - 1
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
            sell_price = bar.open - 1
            self._current_trade['sell_price'] = sell_price
            if self._stop_loss < sell_price:
                self._stop_loss = sell_price + 1
            self._current_trade['stop_loss'] = self._stop_loss
            self._state = 'short'

        if self._state == 'short':
            # we are short, so we have to check, if we ran into out stop loss
            if self._stop_loss < bar.high:
                # we assume that we were stopped out one tick over our stop loss
                self._current_trade['buy_time'] = bar.timestamp
                self._current_trade['buy_price'] = self._stop_loss + 1
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

    def on_new_bar(self, bar: Bar) -> None:
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
        self._average: float | None = None
        self._slope: float = 0.0
        self._old_slope: float = 0.0

    def reset(self):
        super().reset()
        self._average: float = None
        self._slope: float = 0.0
        self._old_slope: float = 0.0

    def decide(self, bar: Bar) -> str:
        """
        analysis the current volume bar and decides what to
        
        returns "none", "buy", "sell"
        """

        if self._average is None:
            self._average = bar.average
            return 'none'
        
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


class YesterdaysWeather(Trader):
    """
    Wenn es steigt, dann steigt es weiter, wenn es fällt, dann fällt es weiter...
    """

    def __init__(self, slope_threshold: float = 0.5, stop_loss_factor: float = 1.0):
        super().__init__(stop_loss_factor)

        self.averages: deque[int] = deque()
        self.slope: int = 0
        self.SLOPE_THRESHOLD = round(slope_threshold * 4)

    def reset(self):
        super().reset()
        self.arverages = deque()
        self.slope = 0

    def decide(self, bar: Bar) -> str:
        """
        wir extrapolieren die Steigung des Mittelwerts als schätzung für den nächsten mittelwert,
        sobald sich der mittelwert 2 mal in die selbe richtung bewegt hat (der kleinst-mögliche trend)
        """

        self.averages.append(bar.average)
        if len(self.averages) < 3:
            return 'None'

        decision = 'None'
        slope = self.averages[2] - self.averages[0]
        if (self.averages[0] - self.averages[1]) * (self.averages[1] - self.averages[2]) > 0:
            # we have a trend
            if slope > self.SLOPE_THRESHOLD:
                decision = 'buy'
                self._stop_loss = bar.low
            if slope < -self.SLOPE_THRESHOLD:
                decision = 'sell'
                self._stop_loss = bar.high
            #self._current_trade['average'] = bar.average
            #self._current_trade['close'] = bar.close
            #self._current_trade['slope'] = slope
            #self._current_trade['decision'] = decision
        self.averages.popleft()
        return decision


class RandomTrader(Trader):
    """
    Ein Trader, der eine Münze wirft, um zu entscheiden, ob gekauft oder verkauft wird.
    """

    def decide(self, bar: Bar) -> str:
        """ entscheidung würfeln """
        decisions = ['buy', 'sell']
        return random.choice(decisions)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trade simulator: Lädt Volumenbalken aus einer CSV-Datei und simuliert Echtzeit-Events.")
    parser.add_argument("filename", help="CSV with volume bars")
    parser.add_argument('-t', '--trader', choices=["kentbeck", 'random', 'yw'], default='kentbeck', help='selects a trader: ( random | kentbeck | yw )')
    parser.add_argument('-m', '--margin', type=float, default=1.0, help='stop loss margin')
    parser.add_argument('-s', '--slope', type=float, default=0.5, help='slope threshold')
    parser.add_argument('-f', '--filter', type=float, default=0.5, help='filter constant for filtering of slope and average')
    parser.add_argument('-b', '--bar_size', type=int, default=30, help="define the size[seconds] of a bar")
    args = parser.parse_args()
    trader_name = args.trader.lower()

    if trader_name == 'kentbeck':
        trader = KentBeckTrader(filter_constant=args.filter, slope_threshold=args.slope, stop_loss_factor=args.margin)
    elif trader_name == 'random':
        trader = RandomTrader(stop_loss_factor=args.margin)
    elif trader_name == 'yw':
        trader = YesterdaysWeather(slope_threshold=args.slope, stop_loss_factor=args.margin)
    else:
        print(f"{parser.prog}: error: unknoen trader '{args.trader}'")
        sys.exit(1)

    loader = SampleLoader()
    builder = BarBuilder(args.bar_size)
    loader.add_listener(builder)
    builder.add_listener(trader)
    loader.load_and_stream(args.filename)

    print(Statistics.from_trades(trader.trades))
