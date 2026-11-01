"""
interface to market data

 * supports funtionality to load, store and stream market data.
 * streams may be live or from files
 * uses Databento as data provider
"""

import sys
import click
import csv

from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import databento as db

from .trade import Trade

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


def parse_path(path: Path | str):
    """ parse a path and return its components 
    
    A plutos file name has the following syntax:

        plutos_file_name ::= PATH '/' file_name
               file-Name ::= SYMBOL '_' ISO_DATE '_' (range '_')? CONTENT '.' SUFFIX
                   range ::= '[' FLOAT ':' FLOAT ']'
    """

    if isinstance(path, str):
        path = Path(path)

    name_parts = path.stem.split('_')
    n_parts = len(name_parts)
    if not n_parts in (3, 4):
        raise ValueError(f"parse_path(): path '{path}' doesn't following Plutos naming convention")
    
    range = None
    if n_parts == 4:
        # range is present
        range_str = name_parts[2][1:-1] # eckige Klammern wegschneiden
        start, end = range_str.split(':')
        range = (float(start), float(end))

    return {
        'parent': path.parent,
        'symbol': name_parts[0],
        'date': date.fromisoformat(name_parts[1]),
        'range': range,
        'content': name_parts[-1],
        'suffix': path.suffix,
    }    


def assemble_path(parts: dict) -> Path:
    """ assemble a Path according to Plutos naming conventions """

    range_str = ""
    if 'range' in parts.keys() and parts['range']:
        range = parts['range']
        start = str(range[0]) if range[0] and range[0] != 0 else ""
        end   = str(range[1]) if range[1] and range[1] < SECONDS_OF_DAY else ""
        range_str = f"[{start}:{end}]_"
        if range_str == '[:]_':
            range_str = ""

    parent = Path('.')
    if 'parent' in parts.keys():
        parent = parts['parent']
        if isinstance(parent, str):
            parent = Path(parent)

    d = parts['date']
    if isinstance(d, str):
        d = date.fromisoformat(d)
    elif isinstance(d, (int, float)):
        d = date.fromtimestamp(d)

    return parent / f"{parts['symbol']}_{d.isoformat()}_{range_str}{parts['content']}{parts['suffix']}" 

@click.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False), help='path to .dbn file')
@click.option('-s', '--start', type=float, help="start offest in seconds")
@click.option('-d', '--duration', type=float, help="duration in seconds")
def trades(file: Path, start: float, duration: float): # pragma: no cover
    """ list trades contained in a Databento file (*.dbn -> *_trades.csv) """

    click.echo(f"reading trades from file '{file}'")
    reader = TradesReader.from_file(file, start * 10**9, duration * 10**9)
    file_parts = parse_path(file)
    file_parts['parent'] = '.'
    file_parts['suffix'] = ".csv"
    file_parts['range'] = (start, start + duration)
    out_file = assemble_path(file_parts)
    n_trades = 0
    with open(out_file, 'w', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=['timestamp', 'date', 'price', 'volume'])
        writer.writeheader()
        for trade in reader:
            writer.writerow({
                'timestamp': trade.timestamp,
                'date': datetime.fromtimestamp(trade.timestamp / 10**9).isoformat(),
                'price': trade.price,
                'volume': trade.volume,
            })
            n_trades += 1
    click.echo(f"{n_trades} trades written to file '{out_file}'")


@click.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False), help='path to .dbn file')
def info(file: Path): # pragma: no cover
    """ info about .dbn file """
    data = db.read_dbn(file)
    click.secho(f"info about {file}:", bold=True)
    meta = data.metadata
    click.echo(f"    {meta.dataset} {meta.schema}")
    click.echo(f"    {', '.join(meta.symbols)}")
    start, end = meta.start, meta.end
    start_date, end_date = datetime.fromtimestamp(start // 10**9), datetime.fromtimestamp(end // 10**9)
    click.echo(f"    {start_date.isoformat()} ({start}) - {end_date.isoformat()} ({end})")


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
