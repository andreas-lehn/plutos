#
# Broker Simulation
#

from typing import Iterator
from model import Trade

SLIPAGE = 200 * 10**6 # slipage in nano seconds

class BrokerSim:

    def __init__(self, trades: Iterator):
        self.contracts = 0
        self.stop_loss = None
        self.take_profit = None
        self.trades = trades
        self.next_trade = None
        self.time = -1
        self.forward_to(0)

    def execute_limits(self, trade: Trade):
        execute = False
        price = trade.price
        if self.contracts > 0:
            execute = (self.stop_loss and price <= self.stop_loss) or (self.take_profit and price >= self.take_profit)
        elif self.contracts < 0:
            execute = (self.stop_loss and price >= self.stop_loss) or (self.take_profit and price <= self.take_profit)
    
        executed_trade = None
        if execute:
            executed_trade = Trade(
                timestamp=trade.timestamp,
                price = price,
                volume=-self.contracts,
            )
            self.contracts = 0
            self.stop_loss = None
            self.take_profit = None
        return executed_trade

    def forward_to(self, time: int) -> None | Trade:
        """ forwards the time and returs a Trade if a stop loss or take profit limit was reached """

        if time <= self.time: # we are already there...
            return

        executed_trade = None
        try:
            while self.next_trade is None or self.next_trade.timestamp <= time:
                if self.contracts != 0:
                    executed_trade = self.execute_limits(self.next_trade)
                self.next_trade = next(self.trades)
        
        except StopIteration:
            self.next_trade = None
        
        self.time = time
        return executed_trade

    def order(self, contracts: int, stop_loss: int, take_profit: int) -> Trade:
        price = self.next_trade.price
        self.stop_loss = price + stop_loss if stop_loss else None
        self.take_profit = price + take_profit if take_profit else None
        self.contracts += contracts
        self.time = self.next_trade.timestamp
        return Trade(
            timestamp=self.next_trade.timestamp,
            price=price,
            volume=contracts
        )

    def adust_bracket(self, stop_loss: int = None, take_profit: int = None):
        if self.contracts != 0:
            self.stop_loss = stop_loss
            self.take_profit = take_profit
