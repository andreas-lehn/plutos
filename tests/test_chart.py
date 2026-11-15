from pathlib import Path
import pytest

from plutos.trade import Trade
from plutos.sample import VolumeProfile, Sample
from plutos.chart import Candle, Chart, MarketModel
from plutos import marketdata


@pytest.fixture
def dbn_path():
    return Path(__file__).resolve().parent / "test_trades.dbn"


@pytest.fixture
def some_samples():
    return [
        marketdata.make_sample('2026-10-15', 16,  99, [1, 2, 3, 1]),
        marketdata.make_sample('2026-10-15', 17, 100, [2, 3, 2, 1]),
        marketdata.make_sample('2026-10-15', 18, 102, [1, 2, 4]),
        marketdata.make_sample('2026-10-15', 19,  99, [4, 3, 2, 1, 1, 2]),
    ]                                               # [5, 7, 8, 5, 4, 6]  


def test_candle(some_samples):
    s0 = some_samples[0]
    candle = Candle(size=12)
    candle.append(s0)
    assert candle.timestamp == s0.timestamp
    assert candle.index == 16 // 12

    s0 = s0.volumes
    assert candle.open == s0.average
    assert candle.high == s0.high
    assert candle.average == 101
    assert candle.low  == s0.low
    assert candle.close == s0.average
    assert candle.volumes[101] == 3
    assert candle.volumes[102] == 1
    assert candle.volume == 7
    assert candle.range == s0.high - s0.low

    candle.append(some_samples[1])
    assert candle.close == 101
    assert candle.low  == 99
    assert candle.high == 103
    assert candle.volume == 15
    assert candle.volumes[99]  == 1
    assert candle.volumes[100] == 4
    assert candle.delta == some_samples[1].volumes.average - s0.average
    assert candle.timestamp == some_samples[1].timestamp

    candle.append(some_samples[2])
    candle.append(some_samples[3])
    assert candle.open == 101
    assert candle.low  == 99
    assert candle.high == 104
    assert candle.close == 101
    assert candle.volumes[101] == 8
    assert candle.volumes[102] == 5

def test_cancle_invalid_size():
    with pytest.raises(ValueError):
        Candle(size=0)

    with pytest.raises(ValueError):
        Candle(size=-1)

    
def test_candle_range(some_samples):
    candle = Candle(2)
    candle.append(some_samples[0])
    assert candle.sample_index_range == range(16, 18)
    assert candle.last_sample_index == 17

    with pytest.raises(ValueError):
        candle.append(some_samples[2])


def test_candle_to_dict(some_samples):
    candle = Candle(size=12)
    candle.append(some_samples[1])
    d = candle.to_dict()
    assert d['size'] == candle.size
    assert d['timestamp'] == candle.timestamp
    assert d['index'] == candle.index
    assert d['open'] == candle.open
    assert d['low'] == candle.low
    assert d['average'] == candle.average
    assert d['high'] == candle.high
    assert d['close'] == candle.close
    vol = 0
    for v in d['volumes']:
        vol += v
    assert d['volume'] == candle.volume


def test_candle_filtered_dict(some_samples):
    candle = Candle(size=4)
    candle.append(some_samples[0])
    d = candle.to_filtered_dict(['index', 'low', 'volume'])
    assert d == {'index': 4, 'low': 99, 'volume': 7}

    with pytest.raises(KeyError):
        d['high']

    candle.signal = 'sell'
    d = candle.to_filtered_dict(['index', 'signal'])
    assert d == {'index': 4, 'signal': 'sell'}


@pytest.fixture
def more_samples():
    return [
        marketdata.make_sample("2026-10-15", 14, 30500, [1]),
        marketdata.make_sample("2026-10-15", 15, 30520, [1]), # 20
        marketdata.make_sample("2026-10-15", 16, 30510, [1]),
        marketdata.make_sample("2026-10-15", 17, 30500, [1]), # 30
        marketdata.make_sample("2026-10-15", 18, 30500, [1]),
        marketdata.make_sample("2026-10-15", 19, 30530, [1]), # 6０
        marketdata.make_sample("2026-10-15", 20, 30504, [1]),
        marketdata.make_sample("2026-10-15", 21, 30500, [1]), # 64
        marketdata.make_sample("2026-10-15", 22, 30500, [1]),
        marketdata.make_sample("2026-10-15", 23, 30516, [1]), # 8０
        marketdata.make_sample("2026-10-15", 24, 30540, [1]),
        marketdata.make_sample("2026-10-15", 25, 30500, [1]), # 1００
        marketdata.make_sample("2026-10-15", 26, 30500, [1]),
    ]

def test_chart(more_samples):
    chart = Chart(candle_size=2, maxlen=5)

    chart.append(more_samples[0])
    assert len(chart) == 0

    chart.append(more_samples[1])
    assert len(chart) == 1
    assert chart.volumes[30500] == 1
    assert chart.volumes[30520] == 1

    candle_0 = chart[0]
    assert candle_0.ema_fast == candle_0.average
    assert candle_0.ema_slow == candle_0.average
    assert candle_0.direction == candle_0.delta

    chart.append(more_samples[2])
    chart.append(more_samples[3])
    assert len(chart) == 2  

    candle_1 = chart[1]
    assert candle_1.ema_fast == Chart.EMA_FAST_FACTOR * candle_1.average + Chart.EMA_FAST_FACTOR * candle_0.average
    assert candle_1.ema_slow == Chart.EMA_SLOW_FACTOR * candle_1.average + (1 - Chart.EMA_SLOW_FACTOR) * candle_0.average

    chart.append(more_samples[4])
    chart.append(more_samples[5])
    assert len(chart) == 3  
    assert chart.volumes[30500] == 3
    assert chart.volumes[30510] == 1
    assert chart.volumes[30520] == 1
    assert chart.volumes[30530] == 1

    chart.append(more_samples[6])
    chart.append(more_samples[7])
    chart.append(more_samples[8])
    chart.append(more_samples[9])
    assert len(chart) == 5
    assert chart.volumes[30500] == 5
    assert chart.volumes[30504] == 1
    assert chart.volumes[30516] == 1

    chart.append(more_samples[10])
    chart.append(more_samples[11])
    assert len(chart) == 5

    # len(chart) == 5 => [0, 1, 2, 3, 4]
    assert chart.look_back(0) is chart[4]
    assert chart.look_back(1) is chart[3]
    assert chart.look_back(3) is chart[1]
    assert chart.look_back(4) is chart[0]
    assert chart.look_back(5) is chart[0]

    for i, candle in enumerate(chart):
        assert candle == chart[i]


def test_direction():
    samples = [
        marketdata.make_sample("2026-10-15", 14, 30500, [1]),
        marketdata.make_sample("2026-10-15", 15, 30501, [1]), # 20
        marketdata.make_sample("2026-10-15", 16, 30501, [1]),
        marketdata.make_sample("2026-10-15", 17, 30501, [1]), # 30
        marketdata.make_sample("2026-10-15", 18, 30501, [1]),
        marketdata.make_sample("2026-10-15", 19, 30503, [1]), # 6０
        marketdata.make_sample("2026-10-15", 20, 30502, [1]),
        marketdata.make_sample("2026-10-15", 21, 30504, [1]), # 64
        marketdata.make_sample("2026-10-15", 22, 30505, [1]),
        marketdata.make_sample("2026-10-15", 23, 30503, [1]), # 8０
        marketdata.make_sample("2026-10-15", 24, 30504, [1]),
        marketdata.make_sample("2026-10-15", 25, 30506, [1]), # 1００
        marketdata.make_sample("2026-10-15", 26, 30500, [1]), # Ein Trade um as letzte sample abzuschicken..
    ]
    
    chart = Chart(candle_size=2)
    chart.append(samples[0])
    chart.append(samples[1])
    b_0 = chart[0]
    assert b_0.direction == 1
    assert chart.trend_direction == 1
    assert chart.trend_length == 0

    chart.append(samples[2])
    chart.append(samples[3])
    assert chart.trend_direction == 0
    assert chart.trend_length == 0

    chart.append(samples[4])
    chart.append(samples[5])
    assert chart.trend_direction == 1
    assert chart.trend_length == 2

    chart.append(samples[6])
    chart.append(samples[7])
    assert chart.trend_direction == 1
    assert chart.trend_length == 3

    chart.append(samples[8])
    chart.append(samples[9])
    assert chart.trend_direction == 0
    assert chart.trend_length == 0

    chart.append(samples[10])
    chart.append(samples[11])
    assert chart.trend_direction == 1
    assert chart.trend_length == 5


def test_direction_mirrowed():
    samples = [
        marketdata.make_sample("2026-10-15", 14, 30600, [1]),
        marketdata.make_sample("2026-10-15", 15, 30599, [1]), # 20
        marketdata.make_sample("2026-10-15", 16, 30599, [1]),
        marketdata.make_sample("2026-10-15", 17, 30599, [1]), # 30
        marketdata.make_sample("2026-10-15", 18, 30599, [1]),
        marketdata.make_sample("2026-10-15", 19, 30597, [1]), # 6０
        marketdata.make_sample("2026-10-15", 20, 30598, [1]),
        marketdata.make_sample("2026-10-15", 21, 30596, [1]), # 64
        marketdata.make_sample("2026-10-15", 22, 30595, [1]),
        marketdata.make_sample("2026-10-15", 23, 30597, [1]), # 8０
        marketdata.make_sample("2026-10-15", 24, 30596, [1]),
        marketdata.make_sample("2026-10-15", 25, 30594, [1]), # 1００
        marketdata.make_sample("2026-10-15", 26, 30600, [1]),
    ]

    chart = Chart(candle_size=2)
    chart.append(samples[0])
    chart.append(samples[1])
    assert chart.trend_direction == -1
    assert chart.trend_length == 0

    chart.append(samples[2])
    chart.append(samples[3])
    assert chart.trend_direction == 0
    assert chart.trend_length == 0

    chart.append(samples[4])
    chart.append(samples[5])
    assert chart.trend_direction == -1
    assert chart.trend_length == 2

    chart.append(samples[6])
    chart.append(samples[7])
    assert chart.trend_direction == -1
    assert chart.trend_length == 3

    chart.append(samples[8])
    chart.append(samples[9])
    assert chart.trend_direction == 0
    assert chart.trend_length == 0

    chart.append(samples[10])
    chart.append(samples[11])
    assert chart.trend_direction == -1
    assert chart.trend_length == 5
    

def test_average_range(more_samples):
    chart = Chart(candle_size=2, maxlen=5)
    assert chart.average_range(5) == 0
    
    chart.append(more_samples[0])
    chart.append(more_samples[1])
    assert chart.average_range(5) == 20

    chart.append(more_samples[2])
    chart.append(more_samples[3])
    assert chart.average_range(5) == 15

    chart.append(more_samples[4])
    chart.append(more_samples[5])
    assert chart.average_range(5) == 20

    chart.append(more_samples[6])
    chart.append(more_samples[7])
    assert chart.average_range(5) == 16

    chart.append(more_samples[8])
    chart.append(more_samples[9])

    assert chart.average_range(5) == 16

    chart.append(more_samples[10])
    chart.append(more_samples[11])
    assert chart.average_range(5) == 20


def test_chart_callbacks(dbn_path):
    class Callee:
        called = False
        def cb(candle, chart):
            Callee.called = True
    
    chart = Chart(4)
    chart.register_callback(Callee.cb)
    for sample in marketdata.from_file(dbn_path, duration=10):
        chart.append(sample)
    assert Callee.called == True

    Callee.called = False
    chart.unregister_callback(Callee.cb)
    for sample in marketdata.from_file(dbn_path, duration=2):
        chart.append(sample)
    assert Callee.called == False


def test_market_model(dbn_path):
    reader = marketdata.from_file(dbn_path, duration=60)
    model = MarketModel.default_model()
    model.feed_with_samples(reader)

    assert len(model.charts[0]) == 60 // 12
    assert len(model.charts[1]) == 60 // 36
    assert len(model.charts[2]) == 60 // 60
    assert len(model.charts[3]) == 60 // 720
