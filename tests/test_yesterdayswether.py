#
# Test Yesterdays Weather trader
#

import pytest

from model import Trade, SampleBuilder, Bar, Chart
from yw import YesterdaysWeather

@pytest.fixture
def trades():
    return [          
        Trade(timestamp=100000000000, price=30500, volume=1), # Bar  Comment
        Trade(timestamp=101100000000, price=30510, volume=1), #   0  Bei 30500 beginnen und aufsteigen
        Trade(timestamp=102200000000, price=30510, volume=1),
        Trade(timestamp=103300000000, price=30520, volume=1), #   1  Kontinuierlich steigen, aber kein Long wegen oberhalt EMA_5
        Trade(timestamp=104400000000, price=30520, volume=1),
        Trade(timestamp=105500000000, price=30530, volume=1),
        Trade(timestamp=106600000000, price=30530, volume=1),
        Trade(timestamp=107700000000, price=30540, volume=1),
        Trade(timestamp=108800000000, price=30540, volume=1), 
        Trade(timestamp=109900000000, price=30550, volume=1), #   4  Bei 30550 Höhepunkt erreich
        Trade(timestamp=110000000000, price=30545, volume=1),
        Trade(timestamp=111100000000, price=30540, volume=1), #   5  Abfallen und Short auslösen
        Trade(timestamp=112200000000, price=30540, volume=1), 
        Trade(timestamp=113000000000, price=30530, volume=1), #   6 Continuierlich weiter fallen und Short wegen Trend auslösen
        Trade(timestamp=114400000000, price=30530, volume=1),
        Trade(timestamp=115500000000, price=30520, volume=1), #   7 nochmal Dreierreihe ausgelöst
        Trade(timestamp=116200000000, price=30530, volume=1),
        Trade(timestamp=117300000000, price=30540, volume=1), #   8 Trend gestoppt
        Trade(timestamp=118400000000, price=30540, volume=1),
        Trade(timestamp=119500000000, price=30550, volume=1), #   9 Dreier Serie aufwärts aber kein Long wegen oberhalb EMA
        Trade(timestamp=120500000000, price=30520, volume=1), # Abschluss Trade, um das letzte Sample abzuschicken...
    ]

def test_on_bar(trades):
    builder = SampleBuilder(trades)
    yw = YesterdaysWeather()
    chart = Chart(bar_size=2)
    chart.register_callback(yw.on_bar)
    for sample in builder:
        chart.append(sample)

    assert len(chart) == 10
    assert chart[0].contracts == 0
    assert chart[1].contracts == 0
    assert chart[2].contracts == 0
    assert chart[3].contracts == 0
    assert chart[4].contracts == 0
    assert chart[5].contracts <  0
    assert chart[6].contracts <  0
    assert chart[7].contracts <  0
    assert chart[8].contracts == 0
    assert chart[9].contracts == 0

    bar_5 = chart[5] 
    assert bar_5.stop_loss >  0
    assert bar_5.contracts * bar_5.stop_loss > -yw.MAX_LOSS
    assert (bar_5.contracts - 1) * bar_5.stop_loss < -yw.MAX_LOSS

    d = bar_5.to_filtered_dict(yw.FIELDNAMES)
    assert d['contracts'] == bar_5.contracts
    assert d['stop_loss'] == bar_5.stop_loss

def test_on_bar_inverted(trades):
    def invert_trade(trade):
        return Trade(
            timestamp=trade.timestamp,
            price=61000 - trade.price,
            volume=trade.volume,
        )
    inverted_trades = [invert_trade(trade) for trade in trades]
    builder = SampleBuilder(inverted_trades)
    yw = YesterdaysWeather()
    chart = Chart(bar_size=2)
    chart.register_callback(yw.on_bar)
    for sample in builder:
        chart.append(sample)

    assert len(chart) == 10
    assert chart[0].contracts == 0
    assert chart[1].contracts == 0
    assert chart[2].contracts == 0
    assert chart[3].contracts == 0
    assert chart[4].contracts == 0
    assert chart[5].contracts >  0
    assert chart[6].contracts >  0
    assert chart[7].contracts >  0
    assert chart[8].contracts == 0
    assert chart[9].contracts == 0

    bar_6 = chart[6]
    assert bar_6.stop_loss <  0
    assert bar_6.contracts * -bar_6.stop_loss < yw.MAX_LOSS
    assert (bar_6.contracts + 1) * -bar_6.stop_loss > yw.MAX_LOSS

    d = bar_6.to_filtered_dict(yw.FIELDNAMES)
    assert d['contracts'] == bar_6.contracts
    assert d['stop_loss'] == bar_6.stop_loss
