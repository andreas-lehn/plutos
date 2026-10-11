"""
interface to market data

 * supports funtionality to load, store and stream market data.
 * streams may be live or from files
 * uses Databento as data provider
"""

import os
import csv
import ast

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

import databento as db
from model import Sample, SampleBuilder


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


def download_trades(symbol: str, start: str, end: str):
    """downloads trades form Databento

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


def _stream_csv_file(file: Path, callback: callable) -> list[Sample]:
    """ streams samples from file with sample data as cvs """
    with open(file, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            sample = Sample(
                open=int(row["open"]),
                high=int(row["high"]),
                low=int(row["low"]),
                close=int(row["close"]),
                histo=ast.literal_eval(row["histo"]),
            )
            callback(sample)


def _stream_dbn_file(file: Path, callback: callable, start: int = 0, duration: int = SECONDS_OF_DAY) -> list[Sample]:
    sample_builder = SampleBuilder()

    data = db.DBNStore.from_file(file)
    start_timestamp = data.metadata.start + start * 10**9
    end_timestamp = start_timestamp + duration * 10**9
    for record in data:
        if record.ts_event < start_timestamp:
            continue
        if record.ts_event > end_timestamp:
            break

        price = record.price // 250_000_000
        volume = record.size
        timestamp = record.ts_event // 1_000_000_000
        sample = sample_builder.on_trade(timestamp, price, volume)
        if sample:
            callback(sample)

    if sample_builder.is_sample_available:
        callback(sample_builder.get_sample())


def stream_file(file: str | Path, callback: callable):
    """ streams market data from a file """
    if isinstance(file, str):
        file = Path(file)
    suffix = file.suffix
    if suffix == '.csv':
        _stream_csv_file(file, callback)
    elif suffix == '.dbn':
        _stream_dbn_file(file, callback)
    else:
        raise ValueError(f"from_file(): unknown suffix '{suffix}'. must be 'csv' or 'dbn'")


def from_file(file: str | Path) -> list[Sample]:
    """ loads samples from file (.csv | .dbn) """
    samples = []
    stream_file(file, lambda sample: samples.append(sample))
    return samples


def stream_live(callback: callable):
    """ streams live market data """
    pass


def to_file(file: str | Path, samples):
    """ stores samples in file as csv """
    if isinstance(file, str):
        file = Path(file)

    with open(file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=['open', 'high', 'low', 'close', 'histo'])
        writer.writeheader()
        writer.writerows([sample.model_dump() for sample in samples])


def CME_session(date: date) -> (datetime, datetime):
    """ calculate start and end time of a CME session based on a given date """
    end_date = datetime(date.year, date.month, date.day, 17, 0, tzinfo=ZoneInfo("America/Chicago"))
    start_date = end_date - timedelta(days=1)
    return (start_date.astimezone(UTC), end_date.astimezone(UTC))


def full_path_name(target_dir: str, file_name: str) -> str:
    return file_name if target_dir is None else os.path.join(target_dir, file_name)


def download_session(prog_name: str, base_symbol: str, date: date, target_dir: str):
    """load trades of a CME session from databento"""

    symbol = active_symbol(base_symbol, date)
    start_date, end_date = download_intervall(date)
    filename = full_path_name(target_dir, f"{symbol}_{date.isoformat()}_trades.dbn")

    print(f"{prog_name}: loading trades of {symbol} [{start_date.isoformat()}, {end_date.isoformat()}]")
    data = download_trades(symbol, start_date.isoformat(), end_date.isoformat())
    download_start = datetime.fromtimestamp(data.metadata.start // 10**9, UTC)
    download_end = datetime.fromtimestamp(data.metadata.end // 10**9, UTC)
    print(f"{prog_name}: records downloaded [{download_start.isoformat()}, {download_end.isoformat()}]")
    data.to_file(filename)
    print(f"{prog_name}: {data.nbytes // 100} records written to {filename}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Downloader for trades")
    parser.add_argument("date", type=str, help="Date in YYYY-MM-DD format")
    parser.add_argument("-s", "--symbol", type=str, default="mnq", help="base symbol (mnq, nq, es,...)")
    parser.add_argument("-c", "--change_dir", type=str, help="destination dir")
    args = parser.parse_args()

    databento_download(
        prog_name=parser.prog,
        base_symbol=args.symbol.upper(),
        date=date.fromisoformat(args.date),
        target_dir=args.change_dir,
    )
