from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
import sys
import pytest

from model import Trade, Sample, SampleBuilder, SampleReader, SampleWriter, Bar, Chart

@pytest.fixture
def csv_path():
    return Path(__file__).resolve().parent / "test_samples.csv"

@pytest.fixture
def csv_out_in_path():
    return Path(__file__).resolve().parent / "test_out_in_samples.csv"

@pytest.fixture
def dbn_ref_path():
    return Path(__file__).resolve().parent / "test_trades_samples.csv"

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


def test_sample():
    sample = Sample()
    sample.volumes[30712] = 2
    assert sample.open == 30712
    assert sample.low  == 30712
    assert sample.high == 30712
    assert sample.close == 30712
    assert sample.average == 30712
    assert sample.volumes[30712] == 2
    assert sample.volume == 2

    sample.volumes[30714] = 3
    assert sample.open == 30712
    assert sample.low == 30712
    assert sample.high == 30714
    assert sample.close == 30714
    assert sample.average == 30713
    assert sample.volume == 5
    assert sample.volumes[30712] == 2
    assert sample.volumes[30713] == 0
    assert sample.volumes[30714] == 3

    sample.volumes[30713] = 5
    assert sample.open == 30712
    assert sample.low == 30712
    assert sample.high == 30714
    assert sample.close == 30713
    assert sample.average == 30713
    assert sample.volume == 10
    assert sample.volumes[30713] == 5

    sample.volumes[30715] += 3
    assert sample.volume == 13
    assert sample.volumes[30715] == 3

    sample.volumes[30715] += 2
    assert sample.volume == 15
    assert sample.volumes[30715] == 5

    with pytest.raises(ValueError):
        sample.volumes[30713] = 4
        
def test_sample_resize():
    sample = Sample()

    price = 1234
    sample.volumes[price] = 1
    assert sample.volumes[price] == 1

    base_price = sample._base_price
    price_below = base_price - 2 * Sample.VOLUMES_BLOCK_SIZE - 1
    sample.volumes[price_below] = 2
    assert sample.volumes[price] == 1
    assert sample.volumes[price_below] == 2

    max_price = sample._block_max
    price_above = max_price + 2 * Sample.VOLUMES_BLOCK_SIZE + 1
    sample.volumes[price_above] = 3

    assert sample.volumes[price] == 1
    assert sample.volumes[price_below] == 2
    assert sample.volumes[price_above] == 3 

def test_sample_add():
    s0 = Sample()
    s0.volumes[100] = 1
    s0.volumes[102] = 2
    s0.volumes[103] = 3

    s1 = Sample()
    s1.volumes[101] = 2
    s1.volumes[102] = 3
    s1.volumes[103] = 1

    s0 += s1
    assert s0.volumes[100] == 1
    assert s0.volumes[101] == 2
    assert s0.volumes[102] == 5
    assert s0.volumes[103] == 4

    # check that s1 is unchanged
    assert s1.volumes[101] == 2
    assert s1.volumes[102] == 3
    assert s1.volumes[103] == 1

def test_sample_sub():
    s0 = Sample()
    s0.volumes[100] = 1
    s0.volumes[101] = 1
    s0.volumes[102] = 2
    s0.volumes[103] = 3

    s1 = Sample()
    s1.volumes[102] = 2
    s1.volumes[103] = 1

    s0 -= s1
    assert s0.volumes[100] == 1
    assert s0.volumes[101] == 1
    assert s0.volumes[102] == 0
    assert s0.volumes[103] == 2
    assert s0.volume == 4

    # check that s1 is unchanged
    assert s1.volumes[102] == 2
    assert s1.volumes[103] == 1

    # delete low
    s2 = Sample()
    s2.volumes[100] = 1
    s0 -= s2
    assert s0.volumes[100] == 0
    assert s0.volumes[101] == 1
    assert s0.volumes[102] == 0
    assert s0.volumes[103] == 2
    assert s0.volume == 3
    assert s0.low == 101

    # delete high
    s3 = Sample()
    s3.volumes[103] = 2
    s0 -= s3
    assert s0.volumes[101] == 1
    assert s0.volumes[102] == 0
    assert s0.volumes[103] == 0
    assert s0.volume == 1
    assert s0.high == 101

    # delete all
    s4 = Sample()
    s4.volumes[101] = 1
    s0 -= s4
    assert s0.volumes[101] == 0
    assert s0.volume == 0
    assert s0.high == 0
    assert s0.low == sys.maxsize
    assert s0.open == None
    assert s0.close == None

    # check ValueError
    with pytest.raises(ValueError):
        s0 -= s4

    # add after emptiness
    s0 += s1
    assert s0.volumes[102] == 2
    assert s0.volumes[103] == 1
    assert s0.volume == 3
    assert s0.low == 102
    assert s0.high == 103
    assert s0.open == 102
    assert s0.close == 103

def test_sample_type_errors():
    s = Sample()
    s.volumes[102] = 2
    s.volumes[103] = 1

    with pytest.raises(TypeError):
        s += 5

    with pytest.raises(TypeError):
        s -= "bla"


def test_sample_builder_streaming(trade_list_40):
    builder = SampleBuilder.from_trades(trade_list_40)
    samples = [sample for sample in builder]
    assert len(samples) == 8
    assert samples[0].open  == 122243
    assert samples[0].close == 122247
    assert samples[1].open  == 122248
    assert samples[1].close == 122252
    assert samples[2].open  == 122253
    assert samples[7].close == 122282

def test_sample_builder_start_duration(trade_list_40):
    builder = SampleBuilder.from_trades(trade_list_40, start_offset=2, duration=2)
    samples = [sample for sample in builder]
    assert len(samples) == 2
    assert samples[0].close == 122257
    assert samples[1].open  == 122258    
    
def test_sample_builder_reread(trade_list_40):
    builder = SampleBuilder.from_trades(trade_list_40)
    samples = [ s for s in builder ]
    assert len(samples) == 8

    #read is a second time
    samples = [ s for s in builder ]
    assert len(samples) == 8
    s0 = samples[0]
    assert samples[0].open  == 122243
    assert samples[0].close == 122247
    assert samples[1].open  == 122248
    assert samples[1].close == 122252
    assert samples[2].open  == 122253
    assert samples[7].close == 122282

def test_sample_reader(csv_path):
    reader = SampleReader.from_file(csv_path)
    samples = [sample for sample in reader]
    assert len(samples) == 9
    assert samples[0].open == 122622
    assert samples[1].high == 122667
    assert samples[2].low == 122659
    assert samples[3].close == 122666
    assert samples[4].close == 122662
    assert samples[5].low == 122654
    for i, p in enumerate([19, 10, 8, 6, 4, 26, 10]):
        assert samples[6].volumes[samples[6].low + i] == p
    assert samples[7].high == 122667
    assert samples[8].open == 122662

@pytest.fixture
def some_samples():
    return [
        Sample.from_dict({'open': 100, 'low': 99,  'high': 102, 'close': 101, 'volumes': [1, 2, 3, 1]}),
        Sample.from_dict({'open': 101, 'low': 100, 'high': 103, 'close': 102, 'volumes': [   2, 3, 2, 1]}),
        Sample.from_dict({'open': 102, 'low': 102, 'high': 104, 'close': 104, 'volumes': [         1, 2, 4]}),
        Sample.from_dict({'open': 104, 'low': 99,  'high': 104, 'close': 100, 'volumes': [4, 3, 2, 1, 1, 2]}),
    ]                                                                                  # [4, 7, 8, 5, 4, 6]  

def test_sample_copy(some_samples):
    s1 = some_samples[1]
    c  = s1.copy()
    assert c.open == s1.open
    assert c.low  == s1.low
    assert c.high == s1.high
    assert c.close == s1.close
    assert c.average == s1.average
    assert c.volume == s1.volume
    for vc, vs in zip(c.volumes, s1.volumes):
        assert vc == vs

    # ckeck that volumes are independant
    c.volumes[c.low] += 5
    assert c.volumes[c.low] != s1.volumes[c.low]
 
def test_sample_writer(some_samples, csv_out_in_path):

    SampleWriter.to_file(str(csv_out_in_path), some_samples)
    reader = SampleReader.from_file(csv_out_in_path)
    for out, read in zip(some_samples, reader):
        assert out.to_dict() == read.to_dict()

def test_bar(some_samples):
    s0 = some_samples[0]
    bar = Bar.from_samples([s0])
    assert bar.size == 1
    assert bar.open == s0.open
    assert bar.high == s0.high
    assert bar.average == 101
    assert bar.low  == s0.low
    assert bar.close == s0.close
    assert bar.volumes[101] == 3
    assert bar.volumes[102] == 1
    assert bar.volume == 7

    bar += some_samples[1]
    assert bar.size == 2
    assert bar.close == 102
    assert bar.low  == 99
    assert bar.high == 103
    assert bar.volume == 15
    assert bar.volumes[99]  == 1
    assert bar.volumes[100] == 4

    bar += some_samples[2]
    bar += some_samples[3]
    assert bar.size == 4
    assert bar.open == 100
    assert bar.low  == 99
    assert bar.high == 104
    assert bar.close == 100
    assert bar.volumes[101] == 8
    assert bar.volumes[102] == 5

def test_bar_to_dict(some_samples):
    bar = Bar.from_samples(some_samples)
    d = bar.to_dict()
    assert d['size'] == bar.size
    assert d['open'] == bar.open
    assert d['low'] == bar.low
    assert d['high'] == bar.high
    assert d['close'] == bar.close
    d_volumes = d['volumes'] 
    for i, v in enumerate(d['volumes']):
        v = bar.volumes[bar.low + i]


def test_chart(csv_path):
    chart = Chart(2, 3)
    reader = SampleReader.from_file(csv_path)
    for sample in reader:
        chart += sample

    assert len(chart) == 2
    assert chart.volumes[122615] == 0
    assert chart.volumes[122654] == chart[0].volumes[122654] + chart[1].volumes[122654]

    for bar in chart:
        assert bar.size == 3
    
