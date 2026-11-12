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

from .sample import Sample, VolumeProfile


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


class SampleBuilder:
    """ builds 1 sec samples from databento records """

    SAMPLE_RATE = 1 * 10**9 # 1 sec
    """ sample rate in nano seconds """

    @classmethod
    def from_file(cls, path: str | Path, start_offset: int = 0, duration: int = sys.maxsize):
        """ delivers Samples form databento file
        
        path  source of Trades e.g, marketdata.from_file()
        start_offset    start offest in seconds: 
                        the timestamp of the first trade used to build a sample
                        must be 'start_offset' seconds greater than the timestamp of the first trade received
        duration        duration in seconds:
                        the timestamp of the last trade to be used to build a sample
                        is not longer away as 'duration' from the first trade used to build samples
        """
        return SampleBuilder(path, start_offset, duration)

    def __init__(self, path, start_offset: int = 0, duration: int = sys.maxsize):
        self.records = db.DBNStore.from_file(path)
        self.start_offset = start_offset
        self.end_offset = self.start_offset + duration

        self.timestamp_offset: int = 0
        self.timestamp: int = None
        self.sample = None

    def __iter__(self):
        """ iterates of the trades and yields samples """
        for record in self.records:
            price = record.price // 250_000_000
            volume = record.size
            timestamp = record.ts_event // SampleBuilder.SAMPLE_RATE # timestamp is now in sample units
            if self.timestamp is None:
                # this is the very first sample
                self.timestamp_offset = timestamp
                self.timestamp = 0

            timestamp -= self.timestamp_offset # timestamp is now relative to the start

            if timestamp < self.start_offset:
                continue
            elif timestamp > self.end_offset:
                return

            if self.sample is None:
                # this is the first sample sample of the candle
                self.sample = Sample(record.ts_event, VolumeProfile())
                self.timestamp = timestamp

            if timestamp > self.timestamp:
                # sample is ready to be delivered...
                yield self.sample
                # wir schicken das aktuelle sample erst ab, wenn ein neuer trade da ist.
                # damit verpassen wir einen Trade.
                # Obwohl wir diesen Trade schon empfangen haben,
                # verwenden wir ihn in unser darauffolgenden verarbeitung nicht.
                # Alternative: den Trade, der das verschiecken auslöst,
                # noch mit in das aktuelle Sample aufnehmen, obwohl es eigentlich zum nächsten gehört.
                # Dann fließt dieser Trade schon mit ein in die Kauf/Verkauf-Entscheidung.
                #
                # Für die Simulation ist das jetzt egal, aber im Live-System muss das so gemacht werden.
                # Deshalb muss das hier nochmal umgebaut werden.
                self.timestamp = timestamp
                self.sample = Sample(record.ts_event, VolumeProfile())

            self.sample.volumes[price] += volume
            self.sample.timestamp = max(self.sample.timestamp, record.ts_event) # timestamp of the sample is the timestamp of the last trade in the sample

        if self.sample and self.sample.volumes.volume > 0:
            # there is a sample left...
            yield self.sample

        # prepare to start again
        self.timestamp_offset: int = 0
        self.timestamp: int = None
        self.sample = None


def from_file(file: str | Path, start: int = 0, duration: int = SECONDS_OF_DAY) -> SampleBuilder:
    return SampleBuilder.from_file(file, start, duration)


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


#
# samples command
#
@click.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False), help='path to .dbn file')
@click.option('-s', '--start', type=int, default=0, help="start offest in seconds")
@click.option('-d', '--duration', type=int, default=SECONDS_OF_DAY, help="duration in seconds")
def samples(file, start: int, duration: int): # pragma: no cover
    """ creates samples form a Datebento file (*.dbn -> *_samples.csv) """

    click.echo(f"reading form file '{file}'")
    reader = from_file(file, start, duration)

    file_parts = parse_path(file)
    file_parts['parent'] = '.'
    file_parts['content'] = 'samples'
    file_parts['suffix'] = '.csv'
    file_parts['range'] = (start, start + duration)
    out_file = assemble_path(file_parts)

    n_samples = 0
    with open(out_file, 'w', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=Sample.FIELDNAMES)
        writer.writeheader()
        for sample in reader:
            writer.writerow(sample.to_dict())
            n_samples += 1

    click.echo(f"{n_samples} samples written to file '{out_file}'")


#
# info command
#
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


#
# download command 
#
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
