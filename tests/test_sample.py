from pathlib import Path
import sys
import pytest
import databento as db
import pandas as pd
from datetime import datetime

from plutos.trade import Trade
from plutos.sample import VolumeProfile, Sample, SampleBuilder, SampleReader
from plutos import marketdata

@pytest.fixture
def csv_path():
    return Path(__file__).resolve().parent / "test_samples.csv"

@pytest.fixture
def csv_out_in_path(tmp_path):
    return tmp_path / "test_out_in_samples.csv"

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
    samples = [sample for sample in builder]
    assert len(samples) == 8
    assert samples[0].low  == 122243
    assert samples[0].high == 122247
    assert samples[1].low  == 122248
    assert samples[1].high == 122252
    assert samples[2].low  == 122253
    assert samples[7].high == 122282

    d = samples[0].to_dict()
    d['timestamp'] == 1790632800800000000
    d['date'] == datetime(2026, 9, 29, 0, 0)
    d['low']  == 122243
    d['high'] == 122247


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

def test_sample_builder_from_file(dbn_path):
    """ create samples form .dbn file and compare them with Samples created with Pandas in a independent path """

    def dump_record(record: db.DBNRecord):
        """ helper function to convert a record in a dict """
        return {
            "group": record.ts_event // SampleBuilder.SAMPLE_RATE,
            "timestamp": record.ts_event,
            "data": datetime.fromtimestamp(record.ts_event / 10**9),
            "price": record.price // 250_000_000,
            "volume": record.size,
        }

    data = db.DBNStore.from_file(dbn_path)
    df = pd.DataFrame([dump_record(record) for record in data])
    df = df.groupby("group").agg(
        timestamp=('timestamp', 'last'),
        low=('price',  min),
        high=('price', max),
        volume=('volume', sum),
    )
    # df contains the reference samples
    # now we build the samples with SampleBuilder and assert that they are equal.
    reader = marketdata.from_file(dbn_path)
    builder = SampleBuilder(reader)
    for sample in builder:
        ref = df.loc[sample.timestamp // 10**9]
        assert ref.low == sample.low
        assert ref.high == sample.high
        assert ref.timestamp == sample.timestamp


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
