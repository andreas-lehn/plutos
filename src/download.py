import os
import yfinance as yf
import databento as db
import pandas as pd
from tradovate import get_active_symbol
from datetime import datetime, timedelta
from convertdate import databento_download_intervall


def full_path_name(target_dir: str, file_name: str) -> str:
    return file_name if target_dir is None else os.path.join(target_dir, file_name)


def databento_download(prog_name, base_symbol, target_date, target_dir):
    """ load trades for one session from databento """

    symbol = get_active_symbol(base_symbol, target_date)
    date_str = target_date.date().isoformat()
    download_intervall = databento_download_intervall(target_date)
    
    print(f"{prog_name}: loading trades of {symbol} for {download_intervall[0]} ... {download_intervall[1]}")
    #API_KEY = os.getenv("DATABENTO_API_KEY")
    #client = db.Historical(API_KEY) 
    client = db.Historical() # DATABENTO_API_KEY will be used as default, if none is specified.
    data = client.timeseries.get_range(
        dataset="GLBX.MDP3",  # CME Globex Datensatz
        symbols=symbol,
        schema="trades",  # 'trades' lädt die reinen ausgeführten Ticks (vollständige Trades)
        start=download_intervall[0].isoformat(),
        end=download_intervall[1].isoformat(),
    )
    filename = full_path_name(target_dir, f"{symbol}_{date_str}_trades.dbn")
    data.to_file(filename)
    #
    # später das file wieder laden mit:
    #
    #    data = db.DBNStore.from_file("<name>_trades.dbn")
    #
    print(f"{prog_name}: {data.nbytes // 100} records written to {filename}")


def yahoo_download(prog_name, base_symbol, target_date, target_dir):
    start_date = target_date.strftime("%Y-%m-%d")
    end_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")

    yahoo_ticker_str = f"{base_symbol}=F"
    ticker = yf.Ticker(yahoo_ticker_str)

    try:
        raw_symbol = ticker.info.get("underlyingSymbol", yahoo_ticker_str)
        contract_symbol = raw_symbol.replace(".CME", "")
    except Exception:
        contract_symbol = base_symbol

    print(f"{prog_name}: loading data of {contract_symbol} for {start_date}...")
    data = ticker.history(interval="1m", start=start_date, end=end_date)

    if data.empty:
        print(f"{parser.prog}: warning: No data available for {contract_symbol} on {start_date}.")
        return

    data.index = data.index.tz_localize(None)
    ms_since_midnight = (
        data.index.hour * 3600000 + 
        data.index.minute * 60000 + 
        data.index.second * 1000
    )
    data.index = ms_since_midnight.astype(int)
    data.index.name = 'Timestamp'
    data['Average'] = (data['High'] + data['Low']) / 2.0

    clean_data = data[['Open', 'High', 'Average', 'Low', 'Close', 'Volume']]
    filename = full_path_name(target_dir, f"{contract_symbol}_{start_date}_1m.csv")
    clean_data.to_csv(filename)

    print(f"{prog_name}: {len(clean_data)} lines written to {filename}")


def day_range(days: int) -> range:
    return range(days + 1, 1) if (days < 0) else range(0, days)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Automatisierter Downloader für historische 1-Minuten-Futures-Kerzen von Yahoo Finance")
    parser.add_argument("date", type=str, help="Das gewünschte Datum im Format YYYY-MM-DD (z.B. 2026-10-01) [Pflichtfeld]")
    parser.add_argument("-d", "--days", type=int, default=1, help="number of days to download. negative numbers go to the past")
    parser.add_argument("-s", "--symbol", type=str, default="mnq", help="Das Basis-Futures-Symbol (z.B. mnq, nq, es, mes). Default ist 'mnq'")
    parser.add_argument("-c", "--change_dir", type=str, default="", help="Das Zielverzeichnis, in das die CSV-Datei geschrieben werden soll (z.B. data)")
    parser.add_argument("-p", "--provider", type=str, default="yahoo", help="provider of historical data. ( yahoo | databento )")
    args = parser.parse_args()

    base_symbol = args.symbol.upper()
    date_str = args.date
    target_dir = args.change_dir
    days = args.days
    provider = args.provider.lower()

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")

        for offset in day_range(days):
            download_date = target_date + timedelta(days=offset)
            if provider == "yahoo":
                yahoo_download(parser.prog, base_symbol, download_date, target_dir)
            elif provider == "databento":
                databento_download(parser.prog, base_symbol, download_date, target_dir)
            else:
                print(f'{parser.prog}: error: unknown provider "{provider}"')
    except ValueError:
        print(f"{parser.prog}: error: wrong date (format YYYY-MM-DD e.g., 2026-10-01)")
    except Exception as e:
        print(f"{parser.prog}: error: {e}")
