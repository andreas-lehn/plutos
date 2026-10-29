"""
interface to market data

 * supports funtionality to load, store and stream market data.
 * streams may be live or from files
 * uses Databento as data provider
"""

import sys
import click

from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import databento as db

from .model import Trade

SECONDS_OF_DAY = 86400


def symbol_code(product_code: str, date: date) -> str:
    """ construct the symbol code from a product_code for a given date """
    MONTH_CODE = 'FGHJKMNQUVXZ'
    return f'{product_code.upper()}{MONTH_CODE[date.month-1]}{date.year%10}'


def rollover_day(date: date) -> datetime:
    """ calculates the next roll over date for a given month """

    DAYS_BEFORE_3RD_FRIDAY = 4 # amount of days roll over date is before 3. Friday
    quartal = (date.month - 1) // 3 + 1
    first_day = datetime(date.year, quartal * 3, 1)
    first_weekday = first_day.weekday()  # Wochentag des 1. Tages (0 = Montag, 4 = Freitag, 6 = Sonntag)
    days_to_first_friday = (4 - first_weekday) % 7
    return first_day + timedelta(days=(days_to_first_friday + 14 - DAYS_BEFORE_3RD_FRIDAY))


def active_symbol(symbol: str, date: date):
    """
    Ermittelt automatisch das aktive Kontraktsymbol für ein gegebenes Datum.
    Rollover findet am Montag vor dem 3. Freitag im März, Juni, September und Dezember statt.
    """

    rollover = rollover_day(date)
    dt = datetime(date.year, date.month, date.day)
    if not dt < rollover:
        next_month = dt + timedelta(days=30)
        rollover = rollover_day(next_month)
    return symbol_code(symbol, rollover)


def download_trades(symbol: str, start: str, end: str): # pragma: no cover
    """ downloads trades form Databento

    It downloads the trades for 'symbol' in the intervall (start, end).
    Start is included, end is not included anymore.

    Args:
        symbol: the symbol for which the trades should be downloaded MNQZ6
        start:  start date/time in ISO format
        end:    end date/time in ISO format

        DATABENTO_API_KEY environment variable must contain the databento API key

    Return:
        Data records with trades

    """
    client = db.Historical()  # DATABENTO_API_KEY will be used as default, if none is specified.
    return client.timeseries.get_range(
        dataset="GLBX.MDP3",  # CME Globex Datensatz
        symbols=symbol,
        schema="trades",  # 'trades' lädt die reinen ausgeführten Ticks (vollständige Trades)
        start=start,
        end=end,
    )

class TradesReader:
    """ reads trades from dbn file """

    def __init__(self, data: db.DBNStore, start: int = 0, duration: int = sys.maxsize, n = sys.maxsize):
        self.data = data
        self.start = start # start time in ns
        self.duration = duration # duration in ns
        self.n = n  # amount of trades that should be readed
        self.i = 0  # amount of trades already read

    def __iter__(self):
        start_timestamp = self.data.metadata.start + self.start
        end_timestamp = start_timestamp + self.duration
        for record in self.data:
            if self.i == self.n:
                break
            if record.ts_event < start_timestamp:
                continue
            if record.ts_event > end_timestamp:
                break

            price = record.price // 250_000_000
            volume = record.size
            timestamp = record.ts_event
            yield Trade(
                timestamp=timestamp,
                price=price,
                volume=volume,
                )
            self.i += 1

    @classmethod
    def from_file(cls, file: str | Path, start: int = 0, duration: int = sys.maxsize, n = sys.maxsize):
        return TradesReader.from_data(db.DBNStore.from_file(file), start, duration, n)

    @classmethod
    def from_data(cls, data: db.DBNStore, start: int = 0, duration: int = sys.maxsize, n = sys.maxsize):
        return cls(data, start, duration, n)


def from_file(file: str | Path, start: int = 0, duration: int = sys.maxsize, n = sys.maxsize):
    return TradesReader.from_file(file, start, duration, n)


def data_from_file(file: str | Path) -> db.DBNStore:
    return db.DBNStore.from_file(file)


def from_live_stream(): # pragma: no cover
    """ streams live market data """
    pass


def CME_session(dt: datetime) -> (datetime, datetime):
    """ calculate start and end time of a CME session based on a given date """
    end_date = datetime(dt.year, dt.month, dt.day, 17, 0, tzinfo=ZoneInfo("America/Chicago"))
    start_date = end_date - timedelta(days=1)
    return (start_date.astimezone(UTC), end_date.astimezone(UTC))


@click.command('download')
@click.option('-p', '--product-code', type=str, default='MNQ', help="product code e.g., NQ, MNQ, ES,...)")
@click.argument('date', type=click.DateTime(formats=["%Y-%m-%d"]), required=True, help="date of session in ISO format")
def download_session(product_code: str, date: datetime): #pragma: no cover
    """ download trades of a CME session from databento """

    start_date, end_date = CME_session(date)
    symbol = active_symbol(product_code, end_date.date())
    click.echo(f"loading trades of {symbol} for intervall [{start_date.isoformat()}, {end_date.isoformat()}]")
    data = download_trades(symbol, start_date.isoformat(), end_date.isoformat())
    if data:
        download_start = datetime.fromtimestamp(data.metadata.start // 10**9, timezone.utc)
        download_end = datetime.fromtimestamp(data.metadata.end // 10**9, timezone.utc)
        click.echo(f"downloaded records for intervall [{download_start.isoformat()}, {download_end.isoformat()}]")
        filename = f"{symbol}_{end_date.date().isoformat()}_trades.dbn"
        data.to_file(filename)
        click.echo(f"{data.nbytes} bytes written to {filename}")
    else:
        click.echo(f'download failed.')
