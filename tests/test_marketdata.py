from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import databento as db
import pytest

from plutos import marketdata


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


def test_CME_session():
    d = date(2026, 10, 1)
    tz = ZoneInfo('America/Chicago')
    start = datetime(2026,  9, 30, 17, tzinfo=tz)
    end   = datetime(2026, 10,  1, 17, tzinfo=tz)
    (s, e) = marketdata.CME_session(d) 
    assert s == start
    assert e == end


def test_parse_path():
    parts = marketdata.parse_path("/data/bento/MNQZ6_2026-10-26_trades.dbn")
    assert parts["parent"] == Path("/data/bento")
    assert parts["symbol"] == "MNQZ6"
    assert parts["date"] == date(2026, 10, 26)
    assert parts["range"] == None
    assert parts["suffix"] == ".dbn"

    parts = marketdata.parse_path("MNQZ6_2026-10-27_[12.5:34]_candles.csv")
    assert parts["parent"] == Path(".")
    assert parts["symbol"] == "MNQZ6"
    assert parts["date"] == date(2026, 10, 27)
    assert parts["range"] == (12.5, 34.0)
    assert parts["suffix"] == ".csv"

    with pytest.raises(ValueError):
        marketdata.parse_path('a_path_with_too_much.csv')

    with pytest.raises(ValueError):
        marketdata.parse_path('too_less.dbn')

    
def test_assemble_path():
    path = marketdata.assemble_path({
        'symbol': 'MNQZ6',
        'date': '2026-10-15',
        'content': 'trades',
        'suffix': '.csv',
    })
    assert path == Path('./MNQZ6_2026-10-15_trades.csv')

    path = marketdata.assemble_path({
        'parent': 'data/bento',
        'symbol': 'MNQZ6',
        'date': date(2026, 10, 17),
        'range': (12, 14),
        'content': 'candles',
        'suffix': '.dbn',
    })
    assert path == Path('data/bento/MNQZ6_2026-10-17_[12:14]_candles.dbn')

    path = marketdata.assemble_path({
        'parent': 'data/bento',
        'symbol': 'MNQZ6',
        'date': date(2026, 10, 17),
        'range': (0, marketdata.SECONDS_OF_DAY),
        'content': 'candles',
        'suffix': '.dbn',
    })
    assert path == Path('data/bento/MNQZ6_2026-10-17_candles.dbn')

    path = marketdata.assemble_path({
        'symbol': 'MNQZ6',
        'date': datetime(2026, 10, 16).timestamp(),
        'content': 'trades',
        'suffix': '.csv',
    })
    assert path == Path('./MNQZ6_2026-10-16_trades.csv')


def test_sample_builder_from_file(dbn_path):
    """ create samples form .dbn file and compare them with Samples created with Pandas in a independent path """

    def dump_record(record: db.DBNRecord):
        """ helper function to convert a record in a dict """
        return {
            "group": record.ts_event // 10**9,
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
    builder = marketdata.from_file(dbn_path)
    for sample in builder:
        ref = df.loc[sample.timestamp // 10**9]
        assert ref.low == sample.low
        assert ref.high == sample.high
        assert ref.timestamp == sample.timestamp

def test_sample_builder_with_range(dbn_path):
    """ create samples form .dbn file with start offset and duration """

    builder = marketdata.from_file(dbn_path, start=0, duration=3)
    ref_sample = [sample for sample in builder]
    assert len(ref_sample) == 3

    start_secound = ref_sample[0].timestamp // 10**9
    builder = marketdata.from_file(dbn_path, start=1, duration=2)
    samples = [sample for sample in builder]  
    assert len(samples) == 2
    assert samples[0].timestamp // 10**9 == start_secound + 1
