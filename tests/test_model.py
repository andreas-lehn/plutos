from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
import sys
import pytest

from model import Trade, VolumeProfile, Sample, SampleBuilder, SampleReader, SampleWriter, Bar, Chart, MarketModel
import marketdata

@pytest.fixture
def csv_path():
    return Path(__file__).resolve().parent / "test_samples.csv"

@pytest.fixture
def csv_out_in_path():
    return Path(__file__).resolve().parent / "test_out_in_samples.csv"

@pytest.fixture
def dbn_path():
    return Path(__file__).resolve().parent / "test_trades.dbn"

@pytest.fixture
def trade_list_40():
    trades = []
    timestamp_offset = 1790632800000000000
    price_offset = 122243
    for i in range(0, 40):
        trades.append(Trade(
            timestamp=timestamp_offset + i * 200 * 10**6, # increment by 200 ms => 5 trades per sample
            price = price_offset + i, # price in sample
            volume = 1 + i % 5,
        ))
    return trades

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


def test_VolumeProfile():
    sample = VolumeProfile()
    sample[30712] = 2
    assert sample.low  == 30712
    assert sample.high == 30712
    assert sample.average == 30712
    assert sample[30712] == 2
    assert sample.volume == 2

    sample[30714] = 3
    assert sample.low == 30712
    assert sample.high == 30714
    assert sample.average == 30713
    assert sample.volume == 5
    assert sample[30712] == 2
    assert sample[30713] == 0
    assert sample[30714] == 3

    sample[30713] = 5
    assert sample.low == 30712
    assert sample.high == 30714
    assert sample.average == 30713
    assert sample.volume == 10
    assert sample[30713] == 5

    sample[30715] += 3
    assert sample.volume == 13
    assert sample[30715] == 3
    assert sample.high == 30715

    sample[30715] += 2
    assert sample.volume == 15
    assert sample[30715] == 5

    sample[30713] = -1
    assert sample.low == 30712
    assert sample[30713] == -1

    sample[30711] = -2
    assert sample.low == 30711

    sample[30716] = -3
    assert sample.high == 30716

    sample[30716] = 0
    assert sample.high == 30715
        
def test_VolumeProfile_resize():
    sample = VolumeProfile()

    price = 1234
    sample[price] = 1
    assert sample[price] == 1

    base_price = sample._base_price
    price_below = base_price - 2 * VolumeProfile.VOLUMES_BLOCK_SIZE - 1
    sample[price_below] = 2
    assert sample[price] == 1
    assert sample[price_below] == 2

    max_price = sample._max_price
    price_above = max_price + 2 * VolumeProfile.VOLUMES_BLOCK_SIZE + 1
    sample[price_above] = 3

    assert sample[price] == 1
    assert sample[price_below] == 2
    assert sample[price_above] == 3 

def test_VolumeProfile_add():
    s0 = VolumeProfile()
    s0[100] = 1
    s0[102] = 2
    s0[103] = 3

    s1 = VolumeProfile()
    s1[101] = 2
    s1[102] = 3
    s1[103] = 1

    s0 += s1
    assert s0[100] == 1
    assert s0[101] == 2
    assert s0[102] == 5
    assert s0[103] == 4

    # check that s1 is unchanged
    assert s1[101] == 2
    assert s1[102] == 3
    assert s1[103] == 1

def test_VolumeProfile_sub():
    s0 = VolumeProfile()
    s0[100] = 1
    s0[101] = 1
    s0[102] = 2
    s0[103] = 3

    s1 = VolumeProfile()
    s1[102] = 2
    s1[103] = 1

    s0 -= s1
    assert s0[100] == 1
    assert s0[101] == 1
    assert s0[102] == 0
    assert s0[103] == 2
    assert s0.volume == 4

    # check that s1 is unchanged
    assert s1[102] == 2
    assert s1[103] == 1

    # delete low
    s2 = VolumeProfile()
    s2[100] = 1
    s0 -= s2
    assert s0[100] == 0
    assert s0[101] == 1
    assert s0[102] == 0
    assert s0[103] == 2
    assert s0.volume == 3
    assert s0.low == 101

    # delete high
    s3 = VolumeProfile()
    s3[103] = 2
    s0 -= s3
    assert s0[101] == 1
    assert s0[102] == 0
    assert s0[103] == 0
    assert s0.volume == 1
    assert s0.high == 101

    # delete all
    s4 = VolumeProfile()
    s4[101] = 1
    s0 -= s4
    assert s0[101] == 0
    assert s0.volume == 0
    assert s0.high == 0
    assert s0.low == sys.maxsize

    # check ValueError
    s0 -= s4
    assert s0[101] == -1

    # add after emptiness
    s0 += s1
    assert s0[101] == -1
    assert s0[102] == 2
    assert s0[103] == 1
    assert s0.volume == 2
    assert s0.low == 101
    assert s0.high == 103

@pytest.fixture
def sample_square():
    """ 
        price:   100 101 102 103 104 105 106 107 108 109 110
        sample:    0   1   4   9  16  25  16   9   4   1   0
    """
    sample = VolumeProfile()
    price = 101
    for i in range(1, 6):
        sample[price] = i*i
        price += 1
    for i in range(4, 0, -1):
        sample[price] = i*i
        price += 1
    return sample

def test_VolumeProfile_convolute(sample_square):
    sample = sample_square
    # price:   100 101 102 103 104 105 106 107 108 109 110
    # sample:    0   1   4   9  16  25  16   9   4   1   0
    # conv_1:    0   5  14  29  50  57  50  29  14   5   0 
    # conv_2:    0  14  27  55  70  75  70  55  27  14   0

    conv_1 = sample.convolute(1)
    assert conv_1.low  == 101
    assert conv_1.high == 109
    assert [conv_1[p] for p in range(conv_1.low, conv_1.high + 1)] == [2, 5, 10, 17, 19, 17, 10, 5, 2]

    conv_2 = sample.convolute(2)
    assert [conv_2[p] for p in range(conv_2.low, conv_2.high + 1)] == [3, 6, 11, 14, 15, 14, 11, 6, 3]

def test_VolumeProfile_tangent(sample_square):
    sample = sample_square
    # price:   100 101 102 103 104 105 106 107 108 109 110
    # sample:    0   1   4   9  16  25  16   9   4   1   0
    assert sample.tangent(101, 1) == 2
    assert sample.tangent(102, 2) == 4
    assert sample.tangent(105, 3) == 0
    assert sample.tangent(106, 2) == -3

def test_VolumeProfile_range(sample_square):
    assert sample_square.range() == 8

def test_VolumeProfile_type_errors():
    s = VolumeProfile()
    s[102] = 2
    s[103] = 1

    with pytest.raises(TypeError):
        s += 5

    with pytest.raises(TypeError):
        s -= "bla"


def test_sample_builder_streaming(trade_list_40):
    builder = SampleBuilder.from_trades(trade_list_40)
    samples = [sample.volumes for sample in builder]
    assert len(samples) == 8
    assert samples[0].low  == 122243
    assert samples[0].high == 122247
    assert samples[1].low  == 122248
    assert samples[1].high == 122252
    assert samples[2].low  == 122253
    assert samples[7].high == 122282

def test_sample_builder_start_duration(trade_list_40):
    builder = SampleBuilder.from_trades(trade_list_40, start_offset=2, duration=2)
    samples = [sample.volumes for sample in builder]
    assert len(samples) == 2
    assert samples[0].high == 122257
    assert samples[1].low  == 122258    
    
def test_sample_builder_reread(trade_list_40):
    builder = SampleBuilder.from_trades(trade_list_40)
    samples = [s.volumes for s in builder ]
    assert len(samples) == 8

    #read is a second time
    samples = [s.volumes for s in builder ]
    assert len(samples) == 8
    s0 = samples[0]
    assert samples[0].low  == 122243
    assert samples[0].high == 122247
    assert samples[1].low  == 122248
    assert samples[1].high == 122252
    assert samples[2].low  == 122253
    assert samples[7].high == 122282

def test_sample_reader(csv_path):
    reader = SampleReader.from_file(csv_path)
    samples = [sample.volumes for sample in reader]
    assert len(samples) == 9
    assert samples[1].high == 122667
    assert samples[2].low == 122659
    assert samples[5].low == 122654
    for i, p in enumerate([19, 10, 8, 6, 4, 26, 10]):
        assert samples[6][samples[6].low + i] == p
    assert samples[7].high == 122667

def test_sample_reader_timestamp(csv_path):
    reader = SampleReader.from_file(csv_path)
    FIRST_TIMESTAMP_IN_FILE = 17100000000
    TIME_INCREMENT = 100000000
    timestamp = FIRST_TIMESTAMP_IN_FILE
    for sample in reader:
        assert timestamp == timestamp
        timestamp += TIME_INCREMENT

@pytest.fixture
def some_samples():
    return [
        Sample(17100000000, VolumeProfile.from_dict({'low': 99,  'high': 102, 'volumes': [1, 2, 3, 1]})),
        Sample(17600000000, VolumeProfile.from_dict({'low': 100, 'high': 103, 'volumes': [   2, 3, 2, 1]})),
        Sample(18200000000, VolumeProfile.from_dict({'low': 102, 'high': 104, 'volumes': [         1, 2, 4]})),
        Sample(18700000000, VolumeProfile.from_dict({'low': 99,  'high': 104, 'volumes': [4, 3, 2, 1, 1, 2]})),
    ]                                                       # [4, 7, 8, 5, 4, 6]  

def test_volume_profile_copy(some_samples):
    s1 = some_samples[1].volumes
    c  = s1.copy()
    assert c.low  == s1.low
    assert c.high == s1.high
    assert c.average == s1.average
    assert c.volume == s1.volume
    for vc, vs in zip(c, s1):
        assert vc == vs

    # ckeck that volumes are independant
    c[c.low] += 5
    assert c[c.low] != s1[c.low]
 
def test_sample_writer(some_samples, csv_out_in_path):

    SampleWriter.to_file(str(csv_out_in_path), some_samples)
    reader = SampleReader.from_file(csv_out_in_path)
    for out, read in zip(some_samples, reader):
        assert out.to_dict() == read.to_dict()

def test_bar(some_samples):
    s0 = some_samples[0]
    bar = Bar.from_sample(s0)
    assert bar.timestamp == s0.timestamp

    s0 = s0.volumes
    assert len(bar) == 1
    assert bar.open == s0.average
    assert bar.high == s0.high
    assert bar.average == 101
    assert bar.low  == s0.low
    assert bar.close == s0.average
    assert bar.volumes[101] == 3
    assert bar.volumes[102] == 1
    assert bar.volume == 7
    assert bar.range == s0.high - s0.low


    bar.append(some_samples[1])
    assert len(bar) == 2
    assert bar.close == 101
    assert bar.low  == 99
    assert bar.high == 103
    assert bar.volume == 15
    assert bar.volumes[99]  == 1
    assert bar.volumes[100] == 4
    assert bar.delta == some_samples[1].volumes.average - s0.average
    assert bar.timestamp == some_samples[1].timestamp
    bar.append(some_samples[2])
    bar.append(some_samples[3])
    assert len(bar) == 4
    assert bar.open == 101
    assert bar.low  == 99
    assert bar.high == 104
    assert bar.close == 101
    assert bar.volumes[101] == 8
    assert bar.volumes[102] == 5

    sample = bar.popleft()
    assert bar.volumes[101] == 8 - sample[101]
    bar.popleft()
    assert bar.open != 101
    assert bar.close == 101

def test_bar_iter(some_samples):
    bar = Bar.from_samples(some_samples)
    for b, s in zip(bar, some_samples):
        assert b.low  == s.volumes.low
        assert b.high == s.volumes.high

def test_bar_to_dict(some_samples):
    bar = Bar.from_sample(some_samples[1])
    d = bar.to_dict()
    assert d['len'] == len(bar)
    assert d['open'] == bar.open
    assert d['low'] == bar.low
    assert d['average'] == bar.average
    assert d['high'] == bar.high
    assert d['close'] == bar.close
    vol = 0
    for v in d['volumes']:
        vol += v
    assert d['volume'] == bar.volume

def test_bar_filtered_dict(some_samples):
    bar = Bar.from_sample(some_samples[0])
    # bar from Sample: Sample(17100000000, VolumeProfile.from_dict({'low': 99,  'high': 102, 'volumes': [1, 2, 3, 1]}))
    d = bar.to_filtered_dict(['timestamp', 'low', 'volume'])
    assert d == {'timestamp': 17100000000, 'low': 99, 'volume': 7}

    with pytest.raises(KeyError):
        d['high']

    bar.signal = 'sell'
    d = bar.to_filtered_dict(['timestamp', 'signal'])
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
    chart = Chart(bar_size=2, maxlen=5)

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

    bar_0 = chart[0]
    assert bar_0.ema_9 == bar_0.average
    assert bar_0.ema_50 == bar_0.average
    assert bar_0.direction == bar_0.delta

    chart.append(samples[2])
    chart.append(samples[3])
    assert len(chart) == 2  
    assert chart.trend_length == 0
    assert chart.trend_direction == 0
    assert chart.average_range(5) == 20

    bar_1 = chart[1]
    assert bar_1.ema_9  == 0.2 * bar_1.average + 0.8 * bar_0.average
    assert bar_1.ema_50 == Chart.EMA_50_FACTOR * bar_1.average + (1 - Chart.EMA_50_FACTOR) * bar_0.average
    assert bar_1.direction == 0

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
    
    chart = Chart(bar_size=2)
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
    
    chart = Chart(bar_size=2)
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

    chart = Chart(bar_size=2, maxlen=5)
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

def test_chart_from_sample(trades_12):
    builder = SampleBuilder(trades_12)
    chart = Chart.from_samples(builder, bar_size=4)
    assert len(chart) == 3

    volume = 0
    for bar in chart:
        volume += bar.volume
    assert volume == 12

def test_chart_callbacks(trades_12):
    class Callee:
        called = False
        def cb(bar, chart):
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

