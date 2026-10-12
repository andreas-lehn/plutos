from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from model import Trade, Sample, SampleBuilder, SampleReader, SampleWriter

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
    builder = SampleBuilder(trade_list_40)
    samples = [sample for sample in builder]
    assert len(samples) == 8
    assert samples[0].open  == 122243
    assert samples[0].close == 122247
    assert samples[1].open  == 122248
    assert samples[1].close == 122252
    assert samples[2].open  == 122253
    assert samples[7].close == 122282

def test_sample_builder_start_duration(trade_list_40):
    builder = SampleBuilder(trade_list_40, start_offset=2, duration=2)
    samples = [sample for sample in builder]
    assert len(samples) == 2
    assert samples[0].close == 122257
    assert samples[1].open  == 122258    
    
def test_sample_builder(trade_list_5):
    builder = SampleBuilder(trade_list_5)
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

def test_from_csv(csv_path):
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

def test_to_csv(csv_out_in_path):
    out_samples = [
        Sample(open=100, high=102, low=99,  close=101, histo=[1, 2, 3, 1]),
        Sample(open=101, high=103, low=100, close=102, histo=[2, 3, 2, 1]),
        Sample(open=102, high=104, low=102, close=104, histo=[1, 2, 4]),
        Sample(open=104, high=104, low=99,  close=100, histo=[4, 3, 2, 1, 1, 2])
    ]

    SampleWriter.to_file(str(csv_out_in_path), out_samples)
    reader = SampleReader.from_file(csv_out_in_path)
    for out, read in zip(out_samples, reader):
        assert out == read
