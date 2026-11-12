from pathlib import Path
import pytest
import databento as db
import pandas as pd

from plutos.trade import Trade, TradePair, TradeMatcher


def test_TradePair_from_trades():
    t_1 = Trade(timestamp=101, price=12501, volume=2)
    t_2 = Trade(timestamp=102, price=12502, volume=-2)
    pair = TradePair.from_trades(t_1, t_2)
    assert pair.size == 2
    assert pair.open_time == 101
    assert pair.open_price == 12501
    assert pair.close_time == 102
    assert pair.close_price == 12502
    assert pair.tick_capture == 1
    assert pair.total_ticks == 2
    assert pair.duration == 1
    assert t_1.volume == 0
    assert t_2.volume == 0

    t_1 = Trade(timestamp=101, price=12501, volume=-2)
    t_2 = Trade(timestamp=102, price=12502, volume=2)
    pair = TradePair.from_trades(t_1, t_2)
    assert pair.size == -2
    assert pair.tick_capture == -1
    assert pair.total_ticks == -2
    assert t_1.volume == 0
    assert t_2.volume == 0

    t_1 = Trade(timestamp=101, price=12501, volume=1)
    t_2 = Trade(timestamp=102, price=12502, volume=-2)
    pair = TradePair.from_trades(t_1, t_2)
    assert pair.size == 1    
    assert pair.tick_capture == 1
    assert pair.total_ticks == 1
    assert t_1.volume == 0
    assert t_2.volume == -1

    t_1 = Trade(timestamp=101, price=12501, volume=3)
    t_2 = Trade(timestamp=102, price=12502, volume=-2)
    pair = TradePair.from_trades(t_1, t_2)
    assert pair.size == 2
    assert pair.tick_capture == 1
    assert pair.total_ticks == 2
    assert t_1.volume == 1
    assert t_2.volume == 0

    t_1 = Trade(timestamp=101, price=12501, volume=-3)
    t_2 = Trade(timestamp=102, price=12502, volume=2)
    pair = TradePair.from_trades(t_1, t_2)
    assert pair.size == -2
    assert pair.tick_capture == -1
    assert pair.total_ticks == -2
    assert t_1.volume == -1
    assert t_2.volume == 0

    with pytest.raises(ValueError):
        TradePair.from_trades(t_1, t_1)

def test_TradePair_to_dict():
    t_1 = Trade(timestamp=101, price=12501, volume=2)
    t_2 = Trade(timestamp=102, price=12502, volume=-2)
    pair = TradePair.from_trades(t_1, t_2)
    d = pair.to_dict()
    assert d['size'] == 2
    assert d['open_time'] == 101
    assert d['open_price'] == 12501
    assert d['close_time'] == 102
    assert d['close_price'] == 12502

@pytest.fixture
def trade_list_5():
    trades = [ 
        Trade(timestamp=0, price=12500, volume = 1),
        Trade(timestamp=0, price=12501, volume = 2),
        Trade(timestamp=0, price=12503, volume = 3),
        Trade(timestamp=1, price=12499, volume = 4),
        Trade(timestamp=1, price=12501, volume = 5),
    ]
    return trades

def test_TradeMatcher():
    matcher = TradeMatcher.for_trades([
        Trade(timestamp=0, price=12501, volume = 2),
        Trade(timestamp=1, price=12503, volume = 3),
        Trade(timestamp=2, price=12499, volume = 4),
        Trade(timestamp=3, price=12501, volume = -3),
        Trade(timestamp=4, price=12501, volume = -1),
        Trade(timestamp=5, price=12501, volume = -6),
        Trade(timestamp=6, price=12501, volume = 1),
    ])
    trade_pairs = [pair for pair in matcher]
    assert len(trade_pairs) == 6
    assert trade_pairs[0].size == 2
    assert trade_pairs[1].size == 1
    assert trade_pairs[2].size == 1
    assert trade_pairs[3].size == 1
    assert trade_pairs[4].size == 4
    assert trade_pairs[5].size == -1
    assert matcher.is_flat
