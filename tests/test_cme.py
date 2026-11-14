from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

from plutos import cme


def test_symbol_code():
    assert cme.symbol_code('mnq', date(2024,  3,  1)) == 'MNQH4'
    assert cme.symbol_code( 'NQ', date(2025,  6,  1)) == 'NQM5'
    assert cme.symbol_code( 'es', date(2026,  9,  1)) == 'ESU6'
    assert cme.symbol_code('MNQ', date(2023, 12,  1)) == 'MNQZ3'


def test_rollover_day_of_month():
    assert cme.rollover_day(date(2026,  1, 1)) == datetime(2026,  3, 16)
    assert cme.rollover_day(date(2026,  2, 1)) == datetime(2026,  3, 16)
    assert cme.rollover_day(date(2026,  3, 1)) == datetime(2026,  3, 16)
    assert cme.rollover_day(date(2026,  4, 1)) == datetime(2026,  6, 15)
    assert cme.rollover_day(date(2026,  5, 1)) == datetime(2026,  6, 15)
    assert cme.rollover_day(date(2026,  6, 1)) == datetime(2026,  6, 15)
    assert cme.rollover_day(date(2026,  7, 1)) == datetime(2026,  9, 14)
    assert cme.rollover_day(date(2026,  8, 1)) == datetime(2026,  9, 14)
    assert cme.rollover_day(date(2026,  9, 1)) == datetime(2026,  9, 14)
    assert cme.rollover_day(date(2026, 10, 1)) == datetime(2026, 12, 14)
    assert cme.rollover_day(date(2026, 11, 1)) == datetime(2026, 12, 14)
    assert cme.rollover_day(date(2026, 12, 1)) == datetime(2026, 12, 14)


def test_active_symbol():
    assert cme.active_symbol('nq', date(2026,  1,  1)) == "NQH6"
    assert cme.active_symbol('nq', date(2026,  3, 15)) == "NQH6"
    assert cme.active_symbol('nq', date(2026,  3, 16)) == "NQM6"
    assert cme.active_symbol('nq', date(2026,  6, 14)) == "NQM6"
    assert cme.active_symbol('nq', date(2026,  6, 15)) == "NQU6"
    assert cme.active_symbol('nq', date(2026,  9, 13)) == "NQU6"
    assert cme.active_symbol('nq', date(2026,  9, 14)) == "NQZ6"
    assert cme.active_symbol('nq', date(2026, 12, 13)) == "NQZ6"
    assert cme.active_symbol('nq', date(2026, 12, 14)) == "NQH7"


def test_session():
    d = date(2026, 10, 1)
    tz = ZoneInfo('America/Chicago')
    start = datetime(2026,  9, 30, 17, tzinfo=tz)
    end   = datetime(2026, 10,  1, 17, tzinfo=tz)
    (s, e) = cme.session(d) 
    assert s == start
    assert e == end


def test_sample_index():
    tz = ZoneInfo('America/Chicago')
    start = datetime(2026,  9, 30, 17, tzinfo=tz)
    end   = datetime(2026, 10,  1, 17, tzinfo=tz)

    for i in range(60):
        ts = start.timestamp() + i + i * 0.01
        assert cme.sample_index(ts) == i
    
    for i in range(60):
        ts = end.timestamp() - (60 - i) + i * 0.01
        assert cme.sample_index(ts) == (24 * 60 * 60 - (60 - i))

