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
        Sample(16100000000, VolumeProfile.from_dict({'low': 99,  'high': 102, 'volumes': [1, 2, 3, 1]})),
        Sample(17600000000, VolumeProfile.from_dict({'low': 100, 'high': 103, 'volumes': [   2, 3, 2, 1]})),
        Sample(18200000000, VolumeProfile.from_dict({'low': 102, 'high': 104, 'volumes': [         1, 2, 4]})),
        Sample(19700000000, VolumeProfile.from_dict({'low': 99,  'high': 104, 'volumes': [4, 3, 2, 1, 1, 2]})),
    ]                                                                                  # [5, 7, 8, 5, 4, 6]  


def test_candle(some_samples):
    s0 = some_samples[0]
    candle = Candle.from_sample(s0)
    assert candle.timestamp == s0.timestamp

    s0 = s0.volumes
    assert len(candle) == 1
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
    assert len(candle) == 2
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
    assert len(candle) == 4
    assert candle.open == 101
    assert candle.low  == 99
    assert candle.high == 104
    assert candle.close == 101
    assert candle.volumes[101] == 8
    assert candle.volumes[102] == 5

    sample = candle.popleft()
    assert candle.volumes[101] == 8 - sample[101]
    candle.popleft()
    assert candle.open != 101
    assert candle.close == 101


def test_candle_iter(some_samples):
    candle = Candle.from_samples(some_samples)
    for b, s in zip(candle, some_samples):
        assert b.low  == s.volumes.low
        assert b.high == s.volumes.high


def test_candle_to_dict(some_samples):
    candle = Candle.from_sample(some_samples[1])
    d = candle.to_dict()
    assert d['len'] == len(candle)
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
    candle = Candle.from_sample(some_samples[0])
    d = candle.to_filtered_dict(['timestamp', 'low', 'volume'])
    assert d == {'timestamp': 16100000000, 'low': 99, 'volume': 7}

    with pytest.raises(KeyError):
        d['high']

    candle.signal = 'sell'
    d = candle.to_filtered_dict(['timestamp', 'signal'])
    assert d == {'timestamp': 16100000000, 'signal': 'sell'}


@pytest.fixture
def more_samples():
    return [
        Sample.from_dict({'timestamp': 14000000000, 'low': 30500, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 15600000000, 'low': 30520, 'volumes': [1]}), # 20
        Sample.from_dict({'timestamp': 16000000000, 'low': 30510, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 17500000000, 'low': 30500, 'volumes': [1]}), # 30
        Sample.from_dict({'timestamp': 18000000000, 'low': 30500, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 19000000000, 'low': 30530, 'volumes': [1]}), # 6０
        Sample.from_dict({'timestamp': 20000000000, 'low': 30504, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 21000000000, 'low': 30500, 'volumes': [1]}), # 64
        Sample.from_dict({'timestamp': 22000000000, 'low': 30500, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 23500000000, 'low': 30516, 'volumes': [1]}), # 8０
        Sample.from_dict({'timestamp': 24000000000, 'low': 30540, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 25500000000, 'low': 30500, 'volumes': [1]}), # 1００
        Sample.from_dict({'timestamp': 26000000000, 'low': 30500, 'volumes': [1]}),
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


def test_direction():
    samples = [
        Sample.from_dict({'timestamp': 14000000000, 'low': 30500, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 15600000000, 'low': 30501, 'volumes': [1]}), # 20
        Sample.from_dict({'timestamp': 16000000000, 'low': 30501, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 17500000000, 'low': 30501, 'volumes': [1]}), # 30
        Sample.from_dict({'timestamp': 18000000000, 'low': 30501, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 19000000000, 'low': 30503, 'volumes': [1]}), # 6０
        Sample.from_dict({'timestamp': 20000000000, 'low': 30502, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 21000000000, 'low': 30504, 'volumes': [1]}), # 64
        Sample.from_dict({'timestamp': 22000000000, 'low': 30505, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 23500000000, 'low': 30503, 'volumes': [1]}), # 8０
        Sample.from_dict({'timestamp': 24000000000, 'low': 30504, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 25500000000, 'low': 30506, 'volumes': [1]}), # 1００
        Sample.from_dict({'timestamp': 26000000000, 'low': 30500, 'volumes': [1]} ), # Ein Trade um as letzte sample abzuschicken..
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
        Sample.from_dict({'timestamp': 14000000000, 'low': 30600, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 15600000000, 'low': 30599, 'volumes': [1]}), # 20
        Sample.from_dict({'timestamp': 16000000000, 'low': 30599, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 17500000000, 'low': 30599, 'volumes': [1]}), # 30
        Sample.from_dict({'timestamp': 18000000000, 'low': 30599, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 19000000000, 'low': 30597, 'volumes': [1]}), # 6０
        Sample.from_dict({'timestamp': 20000000000, 'low': 30598, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 21000000000, 'low': 30596, 'volumes': [1]}), # 64
        Sample.from_dict({'timestamp': 22000000000, 'low': 30595, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 23500000000, 'low': 30597, 'volumes': [1]}), # 8０
        Sample.from_dict({'timestamp': 24000000000, 'low': 30596, 'volumes': [1]}),
        Sample.from_dict({'timestamp': 25500000000, 'low': 30594, 'volumes': [1]}), # 1００
        Sample.from_dict({'timestamp': 26000000000, 'low': 30600, 'volumes': [1]} ), # Ein Trade um as letzte sample abzuschicken..
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


def test_chart_from_samples(some_samples):
    chart = Chart.from_samples(some_samples, candle_size=2)
    assert len(chart) == 2

    volume = 0
    for candle in chart:
        volume += candle.volume
    assert volume == sum([s.volume for s in some_samples])


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

