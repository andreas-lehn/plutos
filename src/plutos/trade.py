"""
data model for trading bot

contains classes for trades
"""

from collections import deque
from collections.abc import Iterable
from pydantic import BaseModel


class Trade(BaseModel):
    """ a basic trade at the exchange """

    timestamp: int # original timestamp in ns
    price: int     # price * 4
    volume: int


class TradePair():
    """ matching pair of trades """

    def __init__(self, size: int, open_time: int, open_price: int, close_time: int, close_price: int):
        self.size = size
        self.open_time = open_time
        self.open_price = open_price
        self.close_time = close_time
        self.close_price = close_price

    @property
    def total_ticks(self):
        return (self.close_price - self.open_price) * self.size

    @property
    def tick_capture(self):
        """ amount of ticks won or lost with this trade pair"""
        return self.total_ticks // abs(self.size)

    @property
    def duration(self):
        return self.close_time - self.open_time

    @classmethod
    def from_trades(cls, open: Trade, close: Trade):
        """ creates a trade pair with maximum size and reduces the volumes of the trades accordingly """
        if open.volume * close.volume >= 0:
            raise ValueError(f'__init__(): sizes of open and close do not match')

        size = 0
        if abs(open.volume) > abs(close.volume):
            size = -close.volume
            close.volume = 0
            open.volume -= size
        else:
            size = open.volume
            open.volume = 0
            close.volume += size

        return cls(size, open.timestamp, open.price, close.timestamp, close.price)

    def to_dict(self) -> dict:
        return {
            'open_time': self.open_time,
            'open_price': self.open_price,
            'close_time': self.close_time,
            'close_price': self.close_price,
            'size': self.size,
        }

class TradeMatcher:
    """ represents a position """

    def __init__(self, trades):
        self.open_trades = deque()
        self.trades_source = trades

    @classmethod
    def for_trades(cls, trades: Iterable[Trade]):
        return cls(trades)
    
    @property
    def is_flat(self):
        return len(self.open_trades) == 0

    @property
    def size(self) -> int:
        sum = 0
        for trade in self.open_trades:
            sum += trade.volume
        return sum
    
    def process(self, new_trade: Trade) -> TradePair:
        if self.size * new_trade.volume >= 0:
            self.open_trades.append(new_trade)
        else:
            # Build Trade-pairs
            while len(self.open_trades) > 0:
                trade = self.open_trades[0]
                pair = TradePair.from_trades(trade, new_trade)
                yield pair
                if trade.volume == 0:
                    self.open_trades.popleft()
                if new_trade.volume == 0:
                    break
            if new_trade.volume != 0:
                self.open_trades.append(new_trade)

    def __iter__(self):
        for trade in self.trades_source:
            for pair in self.process(trade):
                yield pair

