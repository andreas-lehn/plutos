import argparse
import os
import sys
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

parser = argparse.ArgumentParser(description="Automatisierter Downloader für historische 1-Minuten-Futures-Kerzen von Yahoo Finance.")
parser.add_argument("-d", "--date", type=str, required=True, help="Das gewünschte Datum im Format YYYY-MM-DD (z.B. 2026-10-01) [Pflichtfeld]")
parser.add_argument("-s", "--symbol", type=str, default="mnq", help="Das Basis-Futures-Symbol (z.B. mnq, nq, es, mes). Default ist 'mnq'.")
parser.add_argument("-c", "--change_dir", type=str, default="", help="Das Zielverzeichnis, in das die CSV-Datei geschrieben werden soll (z.B. data).")
args = parser.parse_args()

base_symbol = args.symbol.upper()
date_str = args.date
target_dir = args.change_dir

try:
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
except ValueError:
    print(f"{parser.prog}: error: wrong date (format YYYY-MM-DD e.g., 2026-10-01)")
    sys.exit(1)

start_date = target_date.strftime("%Y-%m-%d")
end_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")

yahoo_ticker_str = f"{base_symbol}=F"
ticker = yf.Ticker(yahoo_ticker_str)

try:
    raw_symbol = ticker.info.get("underlyingSymbol", yahoo_ticker_str)
    contract_symbol = raw_symbol.replace(".CME", "")
except Exception:
    contract_symbol = base_symbol

print(f"{parser.prog}: loading data for {contract_symbol}...")
data = ticker.history(interval="1m", start=start_date, end=end_date)

if data.empty:
    print(f"{parser.prog}: error: No data available for {contract_symbol} on {start_date}.")
    sys.exit(1)

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

csv_filename = f"{contract_symbol}_{start_date}_1m.csv"

if target_dir:
    # Falls das Verzeichnis nicht existiert, erstellen wir es automatisch
    if not os.path.exists(target_dir):
        print(f"{parser.prog}: error: directory {target_dir}does not exist")
        sys.exit(1)

    # Pfad kombinieren (z.B. data/MNQZ26_2026-10-01_1m.csv)
    full_path = os.path.join(target_dir, csv_filename)
else:
    full_path = csv_filename

clean_data.to_csv(full_path)

print(f"{parser.prog}: {len(clean_data)} lines written to {full_path}")
