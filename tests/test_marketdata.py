from pathlib import Path
from datetime import date, datetime
import pytest
import csv

from model import Sample
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
def dbn_ref_path():
    return Path(__file__).resolve().parent / "test_trades_samples.csv"


def test_symbol_code():
    assert marketdata.symbol_code('mnq', date(2024,  3,  1)) == 'MNQH4'
    assert marketdata.symbol_code( 'NQ', date(2025,  6,  1)) == 'NQM5'
    assert marketdata.symbol_code( 'es', date(2026,  9,  1)) == 'ESU6'
    assert marketdata.symbol_code('MNQ', date(2023, 12,  1)) == 'MNQZ3'

def test_rollover_day_of_month():
    assert marketdata.rollover_day(date(2026,  1, 1)) == datetime(2026,  3, 16)
    assert marketdata.rollover_day(date(2026,  2, 1)) == datetime(2026,  3, 16)
    assert marketdata.rollover_day(date(2026,  3, 1)) == datetime(2026,  3, 16)
    assert marketdata.rollover_day(date(2026,  4, 1)) == datetime(2026,  6, 15)
    assert marketdata.rollover_day(date(2026,  5, 1)) == datetime(2026,  6, 15)
    assert marketdata.rollover_day(date(2026,  6, 1)) == datetime(2026,  6, 15)
    assert marketdata.rollover_day(date(2026,  7, 1)) == datetime(2026,  9, 14)
    assert marketdata.rollover_day(date(2026,  8, 1)) == datetime(2026,  9, 14)
    assert marketdata.rollover_day(date(2026,  9, 1)) == datetime(2026,  9, 14)
    assert marketdata.rollover_day(date(2026, 10, 1)) == datetime(2026, 12, 14)
    assert marketdata.rollover_day(date(2026, 11, 1)) == datetime(2026, 12, 14)
    assert marketdata.rollover_day(date(2026, 12, 1)) == datetime(2026, 12, 14)

def test_active_symbol():
    assert marketdata.active_symbol('nq', date(2026,  1,  1)) == "NQH6"
    assert marketdata.active_symbol('nq', date(2026,  3, 15)) == "NQH6"
    assert marketdata.active_symbol('nq', date(2026,  3, 16)) == "NQM6"
    assert marketdata.active_symbol('nq', date(2026,  6, 14)) == "NQM6"
    assert marketdata.active_symbol('nq', date(2026,  6, 15)) == "NQU6"
    assert marketdata.active_symbol('nq', date(2026,  9, 13)) == "NQU6"
    assert marketdata.active_symbol('nq', date(2026,  9, 14)) == "NQZ6"
    assert marketdata.active_symbol('nq', date(2026, 12, 13)) == "NQZ6"
    assert marketdata.active_symbol('nq', date(2026, 12, 14)) == "NQH7"

def test_from_csv(csv_path):
    samples = marketdata.from_file(csv_path)
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

    marketdata.to_file(csv_out_in_path, out_samples)
    in_samples = marketdata.from_file(csv_out_in_path)
    assert out_samples == in_samples

def test_from_dbn(dbn_path, dbn_ref_path):
    samples = marketdata.from_file(dbn_path)
    assert len(samples) == 60

    with open(dbn_ref_path, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for sample, ref in zip(samples, [r for r in reader]):
            assert sample.open == int(ref["open"])
            assert sample.high == int(ref["high"])
            assert sample.low  == int(ref["low"])
            assert sample.close== int(ref["close"])
            assert sum(sample.histo) == int(ref['volume'])
