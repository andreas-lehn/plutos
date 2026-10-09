# Generate samples from databento files
#
# The samples are created using pandas data frames.
# Because of this it is independent of the bot software.
# The results can be used to validate the result of the bot software.
#

import databento as db
import pandas as pd
import argparse
from pathlib import Path

def dump_record(record: db.DBNRecord, time_offset: int):
    return {
        'timestamp': (record.ts_event - time_offset) // 10**9,
        'price': record.price // 250_000_000,
        'volume': record.size,
    }

parser = argparse.ArgumentParser(description="extract trades from DBNStore files (.dbn)")
parser.add_argument("filename", help=".dbn file with databento trades")
parser.add_argument("-s", "--start", type=int, default=0, help="start position in seconds (1s default)")
parser.add_argument("-d", "--duration", type=int, default=24*60*60, help="duration of extract in seconds (5s default)")
parser.add_argument("-o", "--outfile", type=str, help="store results in file outfile")
args = parser.parse_args()

data = db.DBNStore.from_file(args.filename)
start_timestamp = data.metadata.start
start_offset = start_timestamp + args.start * 10**9
end_offset = start_offset + args.duration * 10**9

records = []
for record in data:
    if record.ts_event < start_offset:
        continue
    if record.ts_event > end_offset:
        break
    records.append(record)

df = pd.DataFrame([dump_record(record, start_offset) for record in records])

base_name = Path(args.filename).stem
df.to_csv(f'{base_name}_extract.csv')

df['price_volume'] = df['price'] * df['volume']
df['high'] = df['price']
df['low'] = df['price']
df['open'] = df['price']
df['close'] = df['price']
df = df.groupby('timestamp').agg({
    'high': 'max',
    'low': 'min',
    'open': 'first',
    'close': 'last',
    'volume': 'sum',
    'price_volume': 'sum'
})
df['average'] = (df['price_volume'] / df['volume']).round().astype(int)
df = df[['open', 'high', 'average', 'low', 'close', 'volume']]

if args.outfile is not None:
    df.to_csv(args.outfile)
else:
    print(df.to_csv())
