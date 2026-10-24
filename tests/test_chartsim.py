#
# test_brockersim.py
#

import pytest
from typing import Iterable
from chartsim import BrokerProxy
from model import Trade

@pytest.fixture
def trades():
    yield iter([
        Trade(timestamp=16000000000, price=30501, volume=1),
        Trade(timestamp=17100000000, price=30502, volume=2),
        Trade(timestamp=18300000000, price=30503, volume=3),
        Trade(timestamp=19400000000, price=30504, volume=4),
        Trade(timestamp=20500000000, price=30505, volume=5),
        Trade(timestamp=21600000000, price=30506, volume=6),
        Trade(timestamp=22700000000, price=30507, volume=7),
        Trade(timestamp=23800000000, price=30508, volume=8),
        Trade(timestamp=24800000000, price=30509, volume=9),
        Trade(timestamp=25000000000, price=30506, volume=10),
        Trade(timestamp=26100000000, price=30505, volume=11),
        Trade(timestamp=27200000000, price=30504, volume=12),
        Trade(timestamp=28200000000, price=30503, volume=13),
        Trade(timestamp=29300000000, price=30502, volume=14),
        Trade(timestamp=30400000000, price=30501, volume=15),
        Trade(timestamp=31500000000, price=30500, volume=16),
    ])


def test_forward_to(trades):
    broker = BrokerProxy(trades)
    assert broker.time == 0
    assert broker.next_trade.timestamp == 16000000000
    broker.forward_to(24700000000)
    assert broker.next_trade.price == 30509
    broker.forward_to(24800000000)
    assert broker.time == 24800000000
    assert broker.next_trade.price == 30506
    broker.forward_to(24700000000)
    assert broker.time == 24800000000
    assert broker.next_trade.price == 30506
    broker.forward_to(24800000000)
    assert broker.time == 24800000000
    assert broker.next_trade.price == 30506

    with pytest.raises(StopIteration):
        broker.forward_to(32000000000)


def test_order_long(trades):
    broker = BrokerProxy(trades)

    broker.forward_to(20000000000)
    assert broker.next_trade.volume == 5
    ordered_trade = broker.order(0, 2)
    assert ordered_trade == None

    ordered_trade = broker.order(3, 2)
    assert ordered_trade.price == 30505
    assert ordered_trade.timestamp == 20500000000
    assert ordered_trade.volume == 3
    assert broker.stop_loss == 30503
    assert broker.contracts == 3

    executed_trade = broker.forward_to(22000000000)
    assert executed_trade is None
    executed_trade = broker.forward_to(30000000000)
    assert executed_trade.price == 30502
    assert executed_trade.timestamp == 29300000000
    assert broker.stop_loss == None
    assert broker.contracts == 0

def test_order_short(trades):
    broker = BrokerProxy(trades)

    broker.forward_to(20000000000)
    assert broker.next_trade.volume == 5
    ordered_trade = broker.order(-3, 2)
    assert ordered_trade.price == 30505
    assert ordered_trade.timestamp == 20500000000
    assert ordered_trade.volume == -3
    assert broker.stop_loss == 30507
    assert broker.contracts == -3

    executed_trade = broker.forward_to(22000000000)
    assert executed_trade is None
    executed_trade = broker.forward_to(25000000000)
    assert executed_trade is not None
    assert executed_trade.price == 30508
    assert executed_trade.timestamp == 23800000000
    assert broker.time == 25000000000
    assert broker.stop_loss is None

def test_stop_loss_long(trades):
    broker = BrokerProxy(trades)
    broker.forward_to(19000000000)
    
    ordered_trade = broker.order(2, 2)
    assert ordered_trade.price == 30504
    assert broker.stop_loss == 30502
    
    executed_trade = broker.forward_to(25000000000)
    assert executed_trade is None
    
    broker.stop_loss = 30500
    assert broker.stop_loss == 30502

    broker.adjust_stop_loss(30504, 30508, 0.5)
    assert broker.stop_loss == 30503

    broker.stop_loss = 30503.9
    assert broker.stop_loss == 30504

    with pytest.raises(StopIteration):
        executed_trade = broker.forward_to(40000000000)

def test_stop_loss_short(trades):
    broker = BrokerProxy(trades)
    broker.forward_to(19000000000)
    ordered_trade = broker.order(-2, 2)
    assert ordered_trade.price == 30504
    assert broker.stop_loss == 30506
 
    broker.stop_loss = 30507
    assert broker.stop_loss == 30506

    broker.stop_loss = 30505.1
    assert broker.stop_loss == 30505

    broker.adjust_stop_loss(30500, 30503, 0.5)
    assert broker.stop_loss == 30504
