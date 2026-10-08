import sys
import pandas as pd
import databento as db
from typing import Callable, List, Dict
from datetime import datetime, timezone

class SampleCollector:

    def __init__(self):
        self.samples: List[Dict] = []

    def on_sample(self, sample):
        self.samples.append(sample)


class SampleBuilder:
    """ creates 1 sec samples from databento trade records """

    def __init__(self, callout: Callable[int, int, int]):
        """ callout is called when ever a new sample is finished or the stream is over """
        self.callout = callout
        self.timestamp_offset: int = 0
        self.volume: int = 0
        self.volume_x_price: int = 0
        self.high: int = 0
        self.low: int = sys.maxsize
        self.timestamp: int = None
        self.hour = 0

    def on_trade(self, record: db.DBNRecord):
        """ process a databento trade record """
        timestamp = record.ts_event // 1_000_000_000 # - self.timestamp_offset
        timestamp -= self.timestamp_offset
        if self.timestamp is None:
            # first sample starts
            self.timestamp_offset = timestamp
            self.timestamp = 0
            timestamp = 0
        elif (timestamp > self.timestamp):
            self._commit_sample()
            self.timestamp = timestamp

        price = record.price // 250_000_000
        volume = record.size
        self.volume_x_price += volume * price
        self.volume += volume
        self.high = max(self.high, price)
        self.low = min(self.low, price)

    def _commit_sample(self):
        self.callout({
            'timestamp': self.timestamp,
            'volume': self.volume,
            'low': self.low,
            'avarage': self.volume_x_price // self.volume,
            'high': self.high,
        })
        self.volume = 0
        self.volume_x_price = 0
        self.high = 0
        self.low = sys.maxsize

    def close(self) -> None:
        """ closes the current session """
        if self.volume > 0:
            # sample already started
            self._commit_sample()


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
        collector = SampleCollector()
        builder = SampleBuilder(collector.on_sample)
        data.replay(builder.on_trade)
        builder.close()
        print('done')

        df = pd.DataFrame(collector.samples)
        df.to_csv(out_name, index=False)
        print(f'{parser.prog}: {len(df)} lines written to {out_name}')

