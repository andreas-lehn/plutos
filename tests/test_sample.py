from pathlib import Path

import pytest

from marketdata import Sample


@pytest.fixture
def csv_path():
    return Path(__file__).resolve().parent / "test_samples.csv"


@pytest.fixture
def dbn_path():
    return Path(__file__).resolve().parent / "test_trades.dbn"


def test_from_csv_stream(csv_path):
    samples = []
    Sample.from_csv_stream(csv_path, lambda sample: samples.append(sample))
    assert len(samples) == 10
    assert samples[0].open == 122622
    assert samples[1].high == 122667
    assert samples[2].low == 122659
    assert samples[3].close == 122666
    assert samples[4].close == 122662
    assert samples[5].low == 122654
    assert samples[6].histo == [19, 10, 8, 6, 4, 26, 10]
    assert samples[7].high == 122667
    assert samples[8].open == 122662
    assert samples[9] == None


def test_from_dbn(dbn_path):
    all_samples = Sample.from_dbn(dbn_path)
    assert len(all_samples) == 60

    start_30_samples = Sample.from_dbn(dbn_path, start=30)
    assert len(start_30_samples) == 30
    assert start_30_samples[0].open == all_samples[30].open
    assert start_30_samples[29].close == all_samples[59].close

    duration_10_samples = Sample.from_dbn(dbn_path, duration=10)
    assert len(duration_10_samples) == 10
    assert duration_10_samples[0].open == all_samples[0].open
    assert duration_10_samples[9].close == all_samples[9].close


def test_from_dbn_stream(dbn_path):
    samples = []
    Sample.from_dbn_stream(dbn_path, lambda sample: samples.append(sample))
    assert len(samples) == 60

    ref_samples = Sample.from_dbn(dbn_path)
    assert samples[0].open == ref_samples[0].open
    assert samples[59].close == ref_samples[59].close
    assert samples[10].high == ref_samples[10].high
    assert samples[20].low == ref_samples[20].low
