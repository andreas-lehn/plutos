#
# Test Yesterdays Weather trader
#

import pytest

from model import Trade, SampleBuilder, Bar, Chart
from yw import YesterdaysWeather

@pytest.fixture
def long_trend():
    return [
        Trade(timestamp=16000000000, price=30500, volume=1),
        Trade(timestamp=17100000000, price=30520, volume=1),
        Trade(timestamp=18300000000, price=30510, volume=1),
        Trade(timestamp=19400000000, price=30530, volume=1),
    ]

@pytest.fixture
def short_trend():
    return [
        Trade(timestamp=16000000000, price=30500, volume=1),
        Trade(timestamp=17100000000, price=30520, volume=1),
        Trade(timestamp=18300000000, price=30510, volume=1),
        Trade(timestamp=19400000000, price=30490, volume=1),
    ]

@pytest.fixture
def no_longterm_trend():
    return [
        Trade(timestamp=16000000000, price=30500, volume=1),
        Trade(timestamp=17100000000, price=30520, volume=1),
        Trade(timestamp=18300000000, price=30520, volume=1),
        Trade(timestamp=19400000000, price=30500, volume=1),
    ]

@pytest.fixture
def shortterm_too_small():
    return [
        Trade(timestamp=16000000000, price=30500, volume=1),
        Trade(timestamp=17100000000, price=30520, volume=1),
        Trade(timestamp=18300000000, price=30516, volume=1),
        Trade(timestamp=19400000000, price=30524, volume=1),
    ]

def test_contract_size():
    MAX_LOSS = 40
    THRESHOLD = 5
    SL_FACTOR = 1.2

    yw = YesterdaysWeather(max_loss=MAX_LOSS, threshold=THRESHOLD, stop_loss_factor=SL_FACTOR)
    
    RANGE = 10
    STOP_LOSS = RANGE * SL_FACTOR // 2
    CONTRACTS = MAX_LOSS // STOP_LOSS

    contracts, stop_loss = yw.contract_size(4, 5, RANGE)
    assert contracts == 0
    assert stop_loss == 0

    contracts, stop_loss = yw.contract_size(5, 5, RANGE)
    assert contracts == CONTRACTS
    assert stop_loss == -STOP_LOSS

    contracts, stop_loss = yw.contract_size(-5, -5, RANGE)
    assert contracts == -CONTRACTS
    assert stop_loss == STOP_LOSS

def test_trend():
    yw = YesterdaysWeather(threshold=10, look_back=2)
    assert yw.trend(9, 10) == 0
    assert yw.trend(10, 9) == 0
    assert yw.trend(-10, -21) == 0
    assert yw.trend(-10, -20) < 0
    assert yw.trend( 10,  20) > 0
    assert yw.trend(-10,  20) == 0
    assert yw.trend( 10, -20) == 0

def test_on_bar_long(long_trend):
    builder = SampleBuilder(long_trend)
    chart = Chart.from_samples(builder, bar_size = 2)

    yw = YesterdaysWeather(look_back=1)
    bar = chart[-1]
    yw.on_bar(bar, chart)
    assert bar.contracts > 0
    assert bar.stop_loss < 0

def test_on_bar_long(short_trend):
    builder = SampleBuilder(short_trend)
    chart = Chart.from_samples(builder, bar_size = 2)

    yw = YesterdaysWeather(look_back=1)
    bar = chart[-1]
    yw.on_bar(bar, chart)
    assert bar.contracts < 0
    assert bar.stop_loss > 0

def test_on_bar_long(no_longterm_trend):
    builder = SampleBuilder(no_longterm_trend)
    chart = Chart.from_samples(builder, bar_size = 2)

    yw = YesterdaysWeather(look_back=1)
    bar = chart[-1]
    yw.on_bar(bar, chart)
    assert bar.contracts == 0
    assert bar.stop_loss == 0

def test_on_bar_long(shortterm_too_small):
    builder = SampleBuilder(shortterm_too_small)
    chart = Chart.from_samples(builder, bar_size = 2)

    yw = YesterdaysWeather(look_back=1)
    bar = chart[-1]
    yw.on_bar(bar, chart)
    assert bar.contracts == 0
    assert bar.stop_loss == 0

