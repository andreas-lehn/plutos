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
        Trade(timestamp=103300000000, price=30520, volume=1), #   1  Kontinuierlich steigen, aber kein Long, weil trend_length noch nicht erreicht
        Trade(timestamp=104400000000, price=30520, volume=1),
        Trade(timestamp=105500000000, price=30530, volume=1), #   2  trend_length == 2
        Trade(timestamp=106600000000, price=30530, volume=1),
        Trade(timestamp=107700000000, price=30540, volume=1), #   3. erster trend der länge 3
        Trade(timestamp=108800000000, price=30540, volume=1), 
        Trade(timestamp=109900000000, price=30550, volume=1), #   4  Nochmal ein SignalBei 30550 Höhepunkt erreicht
        Trade(timestamp=110000000000, price=30540, volume=1),
        Trade(timestamp=111100000000, price=30530, volume=1), #   5  Abfallen auslösen
        Trade(timestamp=112200000000, price=30530, volume=1), 
        Trade(timestamp=113000000000, price=30520, volume=1), #   6  Kontinuierlich weiter fallen und Short wegen Trend auslösen
        Trade(timestamp=114400000000, price=30520, volume=1),
        Trade(timestamp=115500000000, price=30510, volume=1), #   7  trend_length == 3
        Trade(timestamp=116200000000, price=30510, volume=1),
        Trade(timestamp=117300000000, price=30500, volume=1), #   8  Nochmal ein Signal
        Trade(timestamp=118400000000, price=30500, volume=1),
        Trade(timestamp=119500000000, price=30510, volume=1), #   9  Abwärtstrend beendet
        Trade(timestamp=120500000000, price=30520, volume=1), # Abschluss Trade, um das letzte Sample abzuschicken...
    ]

def test_on_bar(trades):
    builder = SampleBuilder(trades)
    yw = YesterdaysWeather(trend_length=3, max_loss=60, stop_loss_factor=0.6)
    chart = Chart(bar_size=2)
    chart.register_callback(yw.on_bar)
    for sample in builder:
        chart.append(sample)

    assert len(chart) == 10
    assert chart[0].contracts == 0
    assert chart[1].contracts == 0
    assert chart[2].contracts == 0
    assert chart[3].contracts > 0
    assert chart[4].contracts > 0
    assert chart[5].contracts == 0
    assert chart[6].contracts == 0
    assert chart[7].contracts < 0
    assert chart[8].contracts < 0
    assert chart[9].contracts == 0

    bar_3 = chart[3] 
    assert bar_3.stop_loss > 0
    assert bar_3.contracts * bar_3.stop_loss <= yw.MAX_LOSS
    assert (bar_3.contracts + 1) * bar_3.stop_loss > yw.MAX_LOSS

    d = bar_3.to_filtered_dict(yw.FIELDNAMES)
    assert d['contracts'] == bar_3.contracts
    assert d['stop_loss'] == bar_3.stop_loss

    bar_7 = chart[7] 
    assert bar_7.stop_loss > 0
    assert bar_7.contracts * bar_7.stop_loss >= -yw.MAX_LOSS
    assert (bar_7.contracts - 1) * bar_7.stop_loss < yw.MAX_LOSS
