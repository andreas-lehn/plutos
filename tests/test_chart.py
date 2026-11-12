from pathlib import Path
import pytest

from plutos.trade import Trade
from plutos.sample import VolumeProfile, Sample, SampleBuilder
from plutos.chart import Candle, Chart, MarketModel
from plutos import marketdata


@pytest.fixture
def dbn_path():
    return Path(__file__).resolve().parent / "test_trades.dbn"


@pytest.fixture
def some_samples():
    return [
        Sample(17100000000, VolumeProfile.from_dict({'low': 99,  'high': 102, 'volumes': [1, 2, 3, 1]})),
        Sample(17600000000, VolumeProfile.from_dict({'low': 100, 'high': 103, 'volumes': [   2, 3, 2, 1]})),
        Sample(18200000000, VolumeProfile.from_dict({'low': 102, 'high': 104, 'volumes': [         1, 2, 4]})),
        Sample(18700000000, VolumeProfile.from_dict({'low': 99,  'high': 104, 'volumes': [4, 3, 2, 1, 1, 2]})),
    ]                                                       # [4, 7, 8, 5, 4, 6]  


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
    # candle from Sample: Sample(17100000000, VolumeProfile.from_dict({'low': 99,  'high': 102, 'volumes': [1, 2, 3, 1]}))
    d = candle.to_filtered_dict(['timestamp', 'low', 'volume'])
    assert d == {'timestamp': 17100000000, 'low': 99, 'volume': 7}

    with pytest.raises(KeyError):
        d['high']

    candle.signal = 'sell'
    d = candle.to_filtered_dict(['timestamp', 'signal'])
    assert d == {'timestamp': 17100000000, 'signal': 'sell'}

@pytest.fixture
def trades_12():
    return [
        Trade(timestamp=16000000000, price=30540, volume=1),
        Trade(timestamp=17100000000, price=30520, volume=1),
        Trade(timestamp=18300000000, price=30510, volume=1),
        Trade(timestamp=19400000000, price=30530, volume=1),
        Trade(timestamp=20500000000, price=30520, volume=1),
        Trade(timestamp=21600000000, price=30540, volume=1),
        Trade(timestamp=22700000000, price=30530, volume=1),
        Trade(timestamp=23800000000, price=30550, volume=1),
        Trade(timestamp=24900000000, price=30540, volume=1),
        Trade(timestamp=25000000000, price=30560, volume=1),
        Trade(timestamp=26100000000, price=30530, volume=1),
        Trade(timestamp=27200000000, price=30550, volume=1),
    ]

def test_chart(trades_12):
    chart = Chart(candle_size=2, maxlen=5)

    # convert the trades to samples...
    builder = SampleBuilder(trades_12)
    samples = [s for s in builder]
    assert len(samples) == 12

    chart.append(samples[0])
    assert len(chart) == 0
    assert chart.trend_length == 0
    assert chart.trend_direction == 0
    assert chart.average_range(5) == 0

    chart.append(samples[1])
    assert len(chart) == 1
    assert chart.volumes[30520] == 1
    assert chart.volumes[30540] == 1
    assert chart.trend_length == 0
    assert chart.trend_direction < 0
    assert chart.average_range(5) == 20

    candle_0 = chart[0]
    assert candle_0.ema_fast == candle_0.average
    assert candle_0.ema_slow == candle_0.average
    assert candle_0.direction == candle_0.delta

    chart.append(samples[2])
    chart.append(samples[3])
    assert len(chart) == 2  
    assert chart.trend_length == 0
    assert chart.trend_direction == 0
    assert chart.average_range(5) == 20

    candle_1 = chart[1]
    assert candle_1.ema_fast == Chart.EMA_FAST_FACTOR * candle_1.average + Chart.EMA_FAST_FACTOR * candle_0.average
    assert candle_1.ema_slow == Chart.EMA_SLOW_FACTOR * candle_1.average + (1 - Chart.EMA_SLOW_FACTOR) * candle_0.average
    assert candle_1.direction == 0

    chart.append(samples[4])
    chart.append(samples[5])
    assert len(chart) == 3  
    assert chart.volumes[30520] == 2
    assert chart.volumes[30540] == 2
    assert chart.trend_length == 1
    assert chart.trend_direction == 10

    chart.append(samples[6])
    chart.append(samples[7])
    chart.append(samples[8])
    chart.append(samples[9])
    assert len(chart) == 5
    assert chart.volumes[30540] == 3
    assert chart.trend_length == 3
    assert chart.trend_direction == 10

    chart.append(samples[10])
    chart.append(samples[11])
    assert len(chart) == 5
    assert chart.trend_length == 0
    assert chart.trend_direction == 0

    # len(chart) == 5 => [0, 1, 2, 3, 4]
    assert chart.look_back(0) is chart[4]
    assert chart.look_back(1) is chart[3]
    assert chart.look_back(3) is chart[1]
    assert chart.look_back(4) is chart[0]
    assert chart.look_back(5) is chart[0]

def test_direction():
    trades =  [
        Trade(timestamp=14000000000, price=30500, volume=1),
        Trade(timestamp=15600000000, price=30501, volume=1), # 20
        Trade(timestamp=16000000000, price=30501, volume=1),
        Trade(timestamp=17500000000, price=30501, volume=1), # 30
        Trade(timestamp=18000000000, price=30501, volume=1),
        Trade(timestamp=19000000000, price=30503, volume=1), # 60
        Trade(timestamp=20000000000, price=30502, volume=1),
        Trade(timestamp=21000000000, price=30504, volume=1), # 64
        Trade(timestamp=22000000000, price=30505, volume=1),
        Trade(timestamp=23500000000, price=30503, volume=1), # 80
        Trade(timestamp=24000000000, price=30504, volume=1),
        Trade(timestamp=25500000000, price=30506, volume=1), # 100
        Trade(timestamp=26000000000, price=30500, volume=1), # Ein Trade um as letzte sample abzuschicken..
    ]
    builder = SampleBuilder(trades)
    samples = [s for s in builder]
    
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
    trades =  [
        Trade(timestamp=14000000000, price=30600, volume=1),
        Trade(timestamp=15600000000, price=30599, volume=1), # 20
        Trade(timestamp=16000000000, price=30599, volume=1),
        Trade(timestamp=17500000000, price=30599, volume=1), # 30
        Trade(timestamp=18000000000, price=30599, volume=1),
        Trade(timestamp=19000000000, price=30597, volume=1), # 60
        Trade(timestamp=20000000000, price=30598, volume=1),
        Trade(timestamp=21000000000, price=30596, volume=1), # 64
        Trade(timestamp=22000000000, price=30595, volume=1),
        Trade(timestamp=23500000000, price=30597, volume=1), # 80
        Trade(timestamp=24000000000, price=30596, volume=1),
        Trade(timestamp=25500000000, price=30594, volume=1), # 100
        Trade(timestamp=26000000000, price=30600, volume=1), # Ein Trade um as letzte sample abzuschicken..
    ]
    builder = SampleBuilder(trades)
    samples = [s for s in builder]
    
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
    

def test_average_range():
    trades =  [
        Trade(timestamp=16000000000, price=30500, volume=1),
        Trade(timestamp=17100000000, price=30520, volume=1), # 20
        Trade(timestamp=18300000000, price=30510, volume=1),
        Trade(timestamp=19400000000, price=30500, volume=1), # 30
        Trade(timestamp=20500000000, price=30500, volume=1),
        Trade(timestamp=21600000000, price=30530, volume=1), # 60
        Trade(timestamp=22700000000, price=30504, volume=1),
        Trade(timestamp=23800000000, price=30500, volume=1), # 64
        Trade(timestamp=24900000000, price=30500, volume=1),
        Trade(timestamp=25000000000, price=30516, volume=1), # 80
        Trade(timestamp=26100000000, price=30540, volume=1),
        Trade(timestamp=27200000000, price=30500, volume=1), # 100
        Trade(timestamp=28200000000, price=30500, volume=1), # Ein Trade um as letzte sample abzuschicken..
    ]
    builder = SampleBuilder(trades)
    samples = [s for s in builder]

    chart = Chart(candle_size=2, maxlen=5)
    chart.append(samples[0])
    chart.append(samples[1])
    assert chart.average_range(5) == 20

    chart.append(samples[2])
    chart.append(samples[3])
    assert chart.average_range(5) == 15

    chart.append(samples[4])
    chart.append(samples[5])
    assert chart.average_range(5) == 20

    chart.append(samples[6])
    chart.append(samples[7])
    assert chart.average_range(5) == 16

    chart.append(samples[8])
    chart.append(samples[9])

    assert chart.average_range(5) == 16

    chart.append(samples[10])
    chart.append(samples[11])
    assert chart.average_range(5) == 20

def test_chart_from_samples(trades_12):
    builder = SampleBuilder(trades_12)
    chart = Chart.from_samples(builder, candle_size=4)
    assert len(chart) == 3

    volume = 0
    for candle in chart:
        volume += candle.volume
    assert volume == 12

def test_chart_callbacks(trades_12):
    class Callee:
        called = False
        def cb(candle, chart):
            Callee.called = True
    
    chart = Chart(4)
    chart.register_callback(Callee.cb)
    for sample in SampleBuilder(trades_12):
        chart.append(sample)
    assert Callee.called == True

    Callee.called = False
    chart.unregister_callback(Callee.cb)
    for sample in SampleBuilder(trades_12):
        chart.append(sample)
    assert Callee.called == False

def test_market_model(dbn_path):
    reader = marketdata.from_file(dbn_path, n=10)
    trades = [trade for trade in reader]

    class Feeder:
        def __init__(self, trades, duration: int = 720):
            self.trades = trades
            self.duration = duration

        def __iter__(self):
            for time_offset in range(0, self.duration):
                for trade in trades:
                    trade.timestamp = time_offset * 10**9
                    yield trade

    model = MarketModel.default_model()
    model.feed_with_trades(Feeder(trades))

    assert len(model.charts[0]) == 15
    assert len(model.charts[1]) == 720 // 36
    assert len(model.charts[2]) == 720 // 60
    assert len(model.charts[3]) == 1

