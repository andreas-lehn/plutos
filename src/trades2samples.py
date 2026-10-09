#
# this script generates 1-sec-samples out of databento trades
#
# 1-sec-samples are the base for further processing by the python bot
# In the real application there will be a task,
# that communicates with databento and recieves the trade records.
# This tasks converts the trades into 1-sec-samples
# and hands it over via a queue to the trading task.
# The classes in this file will be used by the databento task.
# 
# To test and debug the trading task
# it is convienient to have the generated samples in a CSV file.
# That is exacly what this script does:
# It takes a recorded databento file (.dbn) and replays the records.
# With exacly the same logic than the databento task in the real application
# it generates the 1-sec-samples.
# But instead of sending it to the real application
# it stores these sample in a file.
#
# In addition to that, the module provids a sample loader
# that is able the read in the generated file and stream the 1-sec-samples
# to the trading part of the application.
# With the CSV-file, the to parts: databento task/trading task can be run independently.


import sys
import pandas as pd
import databento as db
from typing import Callable, List, Dict
from datetime import datetime, timezone
from marketdata import Sample


class SampleBuilder:
    """ creates 1 sec samples from databento trade records """

    def __init__(self):
        self.timestamp_offset: int = 0
        self.volume: int = 0
        self.volume_x_price: int = 0
        self.high: int = 0
        self.low: int = sys.maxsize
        self.open: int = None
        self.close: int = None
        self.timestamp: int = None
        self.hour = 0

    def on_trade(self, record: db.DBNRecord) -> Dict:
        """ process a databento trade record """
        
        price = record.price // 250_000_000
        volume = record.size
        timestamp = record.ts_event // 1_000_000_000 - self.timestamp_offset
        return self.update_sample(timestamp, price, volume)

    def update_sample(self, timestamp, price, volume):
        sample = None
        if self.timestamp is None:
            # this is the very first sample
            self.timestamp_offset = timestamp
            timestamp = 0
            self.timestamp = 0
            self.open = price
        elif (timestamp > self.timestamp):
            # sample is ready to be delivered...
            sample = self.get_sample()
            # wir schicken das aktuelle sample erst ab, wenn ein neuer trade da ist.
            # damit verpassen wir mindestens einen Trade.
            # Obwohl wir diesen Trade schon empfangen haben,
            # verwenden wir ihn in unser darauffolgenden verarbeitung nicht.
            # Alternative: den Trade, der das verschiecken auslöst,
            # noch mit in das aktuelle Sample aufnehmen, obwohl es eigentlich zum nächsten gehört.
            # Dann fließt dieser Trade schon mit ein in die Kauf/Verkauf-Entscheidung.
            #
            # Für die Simulation ist das jetzt egal, aber im Live-System muss das so gemacht werden.
            # Deshalb muss das hier nochmal umgebaut werden.
            self.timestamp = timestamp
            self.open = price

        self.volume_x_price += volume * price
        self.volume += volume
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        return sample


    def get_sample(self) -> dict:
        sample = Sample(
            timestamp = self.timestamp,
            volume = self.volume,
            low = self.low,
            average = self.volume_x_price // self.volume,
            high = self.high,
            open = self.open,
            close = self.close
        )
        self.volume = 0
        self.volume_x_price = 0
        self.high = 0
        self.low = sys.maxsize
        return sample

    @property
    def is_sample_available(self) -> bool:
        return self.volume > 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="create samples (1 s) from trades stored in DBNstore files (.dbn)")
    parser.add_argument("files", nargs="+", help=".dbn files with databento trades")
    parser.add_argument("-v", "--verbose", action="store_true", help="activate verbose mode")
    args = parser.parse_args()

    for filename in args.files:
        base_name = filename.removesuffix('.dbn').removesuffix('_trades')
        out_name = base_name + '_samples.csv'

        if args.verbose:
            print(f'{parser.prog}: converting file {filename} to {out_name}')

        print(f'{parser.prog}: replaying file {filename}...', end='')
        data = db.DBNStore.from_file(filename)
        builder = SampleBuilder()
        samples = []
        for record in data:
            sample = builder.on_trade(record)
            if sample is not None:
                samples.append(sample)
        if builder.is_sample_available:
            samples.append(builder.get_sample())
        print('done')

        df = pd.DataFrame([sample.model_dump() for sample in samples])
        df.to_csv(out_name, index=False)
        print(f'{parser.prog}: {len(df)} lines written to {out_name}')

