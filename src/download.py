import os
import databento as db
from tradovate import active_symbol
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

def download_intervall(date: date) -> (datetime, datetime):
    """ takes a date as a sting in isoforma and return the download intervall for databento of a CME session """
    end_date = datetime(date.year, date.month, date.day, 17, 0, tzinfo=ZoneInfo('America/Chicago'))
    start_date = end_date - timedelta(days=1)
    return (start_date.astimezone(timezone.utc), end_date.astimezone(timezone.utc))


def full_path_name(target_dir: str, file_name: str) -> str:
    return file_name if target_dir is None else os.path.join(target_dir, file_name)


def databento_download(prog_name: str, base_symbol: str, date: date, target_dir: str):
    """ load trades of a CME session from databento """

    symbol = active_symbol(base_symbol, date)
    start_date, end_date  = download_intervall(date)
    filename = full_path_name(target_dir, f"{symbol}_{date.isoformat()}_trades.dbn")
    
    print(f"{prog_name}: loading trades of {symbol} [{start_date.isoformat()}, {end_date.isoformat()}]")
    client = db.Historical() # DATABENTO_API_KEY will be used as default, if none is specified.
    data = client.timeseries.get_range(
        dataset="GLBX.MDP3",  # CME Globex Datensatz
        symbols=symbol,
        schema="trades",  # 'trades' lädt die reinen ausgeführten Ticks (vollständige Trades)
        start=start_date.isoformat(),
        end=end_date.isoformat(),
    )
    download_start = datetime.fromtimestamp(data.metadata.start // 10**9, timezone.utc)
    download_end = datetime.fromtimestamp(data.metadata.end // 10**9, timezone.utc)
    print(f'{prog_name}: records downloaded [{download_start.isoformat()}, {download_end.isoformat()}]')
    data.to_file(filename)

    #
    # später das file wieder laden mit:
    #
    #    data = db.DBNStore.from_file("<name>_trades.dbn")
    #
    print(f"{prog_name}: {data.nbytes // 100} records written to {filename}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Automatisierter Downloader für historische 1-Minuten-Futures-Kerzen von Yahoo Finance")
    parser.add_argument("date", type=str, help="Das gewünschte Datum im Format YYYY-MM-DD (z.B. 2026-10-01) [Pflichtfeld]")
    parser.add_argument("-s", "--symbol", type=str, default="mnq", help="Das Basis-Futures-Symbol (z.B. mnq, nq, es, mes). Default ist 'mnq'")
    parser.add_argument("-c", "--change_dir", type=str, default="", help="Das Zielverzeichnis, in das die CSV-Datei geschrieben werden soll (z.B. data)")
    args = parser.parse_args()

    base_symbol = args.symbol.upper()
    date = date.fromisoformat(args.date)
    target_dir = args.change_dir
    
    databento_download(parser.prog, base_symbol, date, target_dir)
