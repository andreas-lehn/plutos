import sys
import pandas as pd
import databento as db
from typing import Callable, List, Dict
from datetime import datetime, timezone

class SampleBuilder:
    """ creates 1 sec samples from databento trade records """

    def __init__(self):
        self.timestamp_offset: int = 0
        self.volume: int = 0
        self.volume_x_price: int = 0
        self.high: int = 0
        self.low: int = sys.maxsize
        self.timestamp: int = None
        self.hour = 0

    def on_trade(self, record: db.DBNRecord) -> Dict:
        """ process a databento trade record """
        
        sample = None

        timestamp = record.ts_event // 1_000_000_000 # - self.timestamp_offset
        timestamp -= self.timestamp_offset
        if self.timestamp is None:
            # first sample starts
            self.timestamp_offset = timestamp
            self.timestamp = 0
            timestamp = 0
        elif (timestamp > self.timestamp):
            sample = self.get_sample()
            self.timestamp = timestamp

        price = record.price // 250_000_000
        volume = record.size
        self.volume_x_price += volume * price
        self.volume += volume
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        return sample


    def get_sample(self) -> dict:
        sample = {
            'timestamp': self.timestamp,
            'volume': self.volume,
            'low': self.low,
            'avarage': self.volume_x_price // self.volume,
            'high': self.high,
        }
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

        df = pd.DataFrame(samples)
        df.to_csv(out_name, index=False)
        print(f'{parser.prog}: {len(df)} lines written to {out_name}')

