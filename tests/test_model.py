from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

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
        Trade(timestamp=0, price=12499, volume = 4),
        Trade(timestamp=0, price=12501, volume = 5),
    ]
    return trades

    
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
    
def test_sample_builder(trade_list_5):
    builder = SampleBuilder.from_trades(trade_list_5)
    samples = [ s for s in builder ]
    assert len(samples) == 1
    s0 = samples[0]
    assert s0.open == 12500
    assert s0.high == 12503
    assert s0.low  == 12499
    assert s0.close == 12501
    assert s0.histo == [4, 1, 7, 0, 3]

    samples = [s for s in builder]
    assert len(samples) == 1
    s0 = samples[0]
    assert s0.open == 12500
    assert s0.high == 12503
    assert s0.low  == 12499
    assert s0.close == 12501
    assert s0.histo == [4, 1, 7, 0, 3]

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
    assert samples[6].histo == [19, 10, 8, 6, 4, 26, 10]
    assert samples[7].high == 122667
    assert samples[8].open == 122662

@pytest.fixture
def some_samples():
    return [
        Sample(open=100, low=99,  high=102, close=101, histo=[1, 2, 3, 1]),
        Sample(open=101, low=100, high=103, close=102, histo=[   2, 3, 2, 1]),
        Sample(open=102, low=102, high=104, close=104, histo=[         1, 2, 4]),
        Sample(open=104, low=99,  high=104, close=100, histo=[4, 3, 2, 1, 1, 2]),
    ]                                                      # [4, 7, 8, 5, 4, 6]  

def test_sample_writer(some_samples, csv_out_in_path):

    SampleWriter.to_file(str(csv_out_in_path), some_samples)
    reader = SampleReader.from_file(csv_out_in_path)
    for out, read in zip(some_samples, reader):
        assert out == read

def test_bar(some_samples):
    s0 = some_samples[0]
    bar = Bar.from_sample(s0)
    assert len(bar) == 1
    assert bar.open == s0.open
    assert bar.high == s0.high
    assert bar.average == 101
    assert bar.low  == s0.low
    assert bar.close == s0.close
    assert bar[101] == 3
    assert bar[102] == 1
    assert bar.volume == 7

    bar += some_samples[1]
    assert len(bar) == 2
    assert bar.close == 102
    assert bar.low  == 99
    assert bar.high == 103
    assert bar.volume == 15
    assert bar[99]  == 1
    assert bar[100] == 4

    bar += some_samples[2]
    bar += some_samples[3]
    assert len(bar) == 4
    assert bar.open == 100
    assert bar.low  == 99
    assert bar.high == 104
    assert bar.close == 100
    assert bar[101] == 8
    assert bar[102] == 5


def test_chart(csv_path):
    chart = Chart(2, 3)
    reader = SampleReader.from_file(csv_path)
    for sample in reader:
        chart += sample

    assert len(chart.bars) == 2
    assert chart[122615] == 0
    assert chart[122654] == chart.bars[0][122654] + chart.bars[1][122654]
