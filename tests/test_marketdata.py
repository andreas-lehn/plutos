from pathlib import Path
from datetime import date, datetime
import pytest

import marketdata


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
