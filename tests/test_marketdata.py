from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import csv

from model import Trade
import marketdata


@pytest.fixture
def dbn_path():
    return Path(__file__).resolve().parent / "test_trades.dbn"

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

def test_from_file(dbn_path):
    reader = marketdata.from_file(dbn_path, n = 10)
    trades = [trade for trade in reader]
    assert len(trades) == 10

    start_offset = 5 * 10**9 # 5 sec offset
    offset_trades = [trade for trade in marketdata.from_file(dbn_path, start=start_offset, duration=1)]
    start_timestamp = trades[0].timestamp_ns + start_offset
    for trade in offset_trades:
        assert trade[0].timestamp == start_timestamp

    no_trades = [trade for trade in marketdata.from_file(dbn_path, start=start_offset, duration=0)]
    assert len(no_trades) == 0

    no_trades = [trade for trade in marketdata.from_file(dbn_path, start=start_offset, n=0)]
    assert len(no_trades) == 0

def test_data_from_file(dbn_path):
    data = marketdata.data_from_file(dbn_path)
    TIMESTAMP_SESSION_START = 1791504000000000000
    assert data.metadata.start == TIMESTAMP_SESSION_START
    assert data.metadata.end   >  TIMESTAMP_SESSION_START

def test_CME_session():
    d = date(2026, 10, 1)
    tz = ZoneInfo('America/Chicago')
    start = datetime(2026,  9, 30, 17, tzinfo=tz)
    end   = datetime(2026, 10,  1, 17, tzinfo=tz)
    (s, e) = marketdata.CME_session(d) 
    assert s == start
    assert e == end
