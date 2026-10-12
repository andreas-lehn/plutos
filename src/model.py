"""
data model for trading bot

contains classes for trades, bars, charts,...
"""


import sys
import csv
import ast

from collections.abc import Iterable
from pathlib import Path
from collections import deque

import databento as db
import pandas as pd
from pydantic import BaseModel


class Trade(BaseModel):
    """ a basic trade at the exchange """

    timestamp: int # original timestamp in ns
    price: int     # price * 4
    volume: int


class Sample(BaseModel):
    """Kapselt die Daten eines Samples"""

    open: int
    high: int
    low: int
    close: int
    histo: list[int]


class SampleReader:
    """ reads samples from a file"""

    def __init__(self, file: str | Path):
        self.file = file

    @classmethod
    def from_file(cls, file: str | Path):
        return cls(file)

    def __iter__(self):
        with open(self.file, mode="r", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                yield Sample(
                    open=int(row["open"]),
                    high=int(row["high"]),
                    low=int(row["low"]),
                    close=int(row["close"]),
                    histo=ast.literal_eval(row["histo"]),
                )


class SampleWriter:
    """ writes samples """

    def to_file(file: str | Path, samples):
        """ writes samples in file as csv """
        if isinstance(file, str):
            file = Path(file)

        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=['open', 'high', 'low', 'close', 'histo'])
            writer.writeheader()
            writer.writerows([sample.model_dump() for sample in samples])


class SampleBuilder:
    """ builds 1 sec samples from trades """

    @classmethod
    def from_trades(cls, trades: Iterable, start_offset: int = 0, duration: int = sys.maxsize, n: int = sys.maxsize):
        """ delivers Samples form trades
        
        trades  source of Trades e.g, marketdata.from_file()
        start_offset    start offest in seconds: 
                        the timestamp of the first trade used to build a sample
                        must be 'start_offset' seconds greater than the timestamp of the first trade received
        duration        duration in seconds:
                        the timestamp of the last trade to be used to build a sample
                        is not longer away as 'duration' from the first trade used to build samples
        n               amount of samples to be build
        """
        return SampleBuilder(trades)

    def __init__(self, trades, start_offset: int = 0, duration: int = sys.maxsize):
        self.trades = trades
        self.timestamp_offset: int = 0
        self.histo: dict[int, int] = {}
        self.open: int = None
        self.high: int = 0
        self.low: int = sys.maxsize
        self.close: int = None
        self.timestamp: int = None
        self.start_offset = start_offset
        self.end_offset = self.start_offset + duration

    def __iter__(self):
        """ iterates of the trades and yields samples """
        for trade in self.trades:
            timestamp = trade.timestamp // 10**9 # timestamp is now in seconds
            price = trade.price
            volume = trade.volume

            if self.timestamp is None:
                # this is the very first sample
                self.timestamp_offset = timestamp
                self.timestamp = 0

            timestamp -= self.timestamp_offset # timestamp is now relative to the start

            if timestamp < self.start_offset:
                continue
            elif timestamp > self.end_offset:
                return

            if self.open is None:
                # this is the first sample sample of the bar
                self.open = price
                self.timestamp = timestamp

            if timestamp > self.timestamp:
                # sample is ready to be delivered...
                yield self._next_sample()
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
                self.open = price

            self.histo[price] = volume + self.histo.get(price, 0)
            self.high = max(self.high, price)
            self.low = min(self.low, price)
            self.close = price

        if len(self.histo) > 0:
            # there is a sample left...
            yield self._next_sample()

    def _next_sample(self) -> dict:
        sample = Sample(
            low=self.low,
            high=self.high,
            open=self.open,
            close=self.close,
            histo=[self.histo.get(i, 0) for i in range(self.low, self.high + 1)],
        )
        self.histo = {}
        self.high = 0
        self.low = sys.maxsize
        return sample


class Histogram:
    """histogram of prices"""

    def __init__(self, low: int, values: Iterable):
        if not isinstance(low, int):
            raise TypeError(f"__init__() argument 'low' must be int, not {type(low).__name__}")
        if not isinstance(values, Iterable):
            raise TypeError(f"__init__() argument 'values' must be an iterable, not {type(values).__name__}")

        self._low = low
        self._values = [Histogram._validate_int(value, "__init__() values in 'values'") for value in values]
        self._volume = 0
        self._price_volume = 0
        for p, v in enumerate(self._values):
            self._volume += v
            self._price_volume += (self._low + p) * v

    @property
    def low(self):
        return self._low

    @property
    def high(self):
        return self._low + len(self._values) - 1

    @property
    def volume(self):
        return self._volume

    @property
    def average(self):
        return round(self._price_volume / self.volume)

    def merge(self, other):
        if not isinstance(other, Histogram):
            raise TypeError(f"merge(other) argument 'other' must be a Histogram, not {type(other).__name__}")

        self._volume += other.volume
        self._price_volume += other._price_volume

        low = min(self.low, other.low)
        high = max(self.high, other.high)
        self._values = [self[i] + other[i] for i in range(low, high + 1)]
        self._low = low
        return self

    def __getitem__(self, index: int) -> int:
        if index < self.low or index > self.high:
            return 0
        return self._values[index - self._low]

    def __setitem__(self, index: int, value: int):
        Histogram._validate_int(value, "__setitem__(): value")
        if index < self.low or index > self.high:
            raise IndexError("Histogram: index out of range")
        if value < 0:
            raise ValueError("__setitem__(): value must not be negative")

        delta = value - self._values[index - self._low]
        self._volume += delta
        self._price_volume += index * delta
        self._values[index - self._low] = value

    def __delitem__(self, index):
        raise TypeError("'Histogram' object does not support item deletion ")

    def __iter__(self):
        for i, v in enumerate(self._values):
            if v > 0:
                yield i + self._low, v

    def __add__(self, other):
        if isinstance(other, Histogram):
            histo = Histogram(self.low, self._values)
            return histo.merge(other)
        return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, Histogram):
            return self.merge(other)
        return NotImplemented

    def _histo_value(low: int, histo: list[int], i) -> int:
        return 0 if (i < low) or i > (low + len(histo) - 1) else histo[i - low]

    def _validate_int(value, text: str) -> int:
        if not isinstance(value, int):
            raise TypeError(f"{text} must be int, not {type(value).__name__}")
        if value < 0:
            raise ValueError(f"{text} must be >= 0")
        return value


class Bar:
    """ Kapselt die Daten einer fertigen Kerze """

    def __init__(self):
        self._len = 0
        self.histo = None
        self.open = None,
        self.close = None,

    @classmethod
    def from_sample(cls, sample):
        bar = cls()
        bar += sample
        return bar

    @property
    def average(self):
        return self.histo.average

    @property
    def volume(self) -> int:
        return self.histo.volume
    
    @property
    def low(self) -> int:
        return self.histo.low

    @property
    def high(self) -> int:
        return self.histo.high
     
    def to_dict(self) -> dict:
        return {
            "open": self.open,
            "high": self.high,
            "average": self.average,
            "low": self.low,
            "close": self.close,
            "len": self._len,
            "histo": list(self.histo),
        }

    def __iadd__(self, other: Sample):
        if not isinstance(other, Sample):
            raise TypeError("__iadd__(): other must be instance of Sample")

        if not self.histo:
            self._len = 1
            self.histo = Histogram(other.low, other.histo.copy())
            self.open = other.open
            self.close = other.close
        else:
            self.histo += Histogram(other.low, other.histo)
            self.close = other.close
            self._len += 1
        return self

    def __getitem__(self, index: int) -> int:
        return self.histo[index]

    def __iter__(self):
        self.histo.__iter__()

    def __len__(self):
        return self._len


class Chart:
    """ a chart contains a sequence of Bars all with the same size 
    
    A chart has a limited size.
    New bars cause old bars to disappear.

    """

    def __init__(self, size: int, bar_size: int):
        self._queue = deque(size)
        self._bar_size = bar_size
        self._new_bar = None
        self.histo = None

    def __len__(self): 
        len(self.queue)

    def __iadd__(self, sample):
        if self._new_bar:
            self._new_bar += sample
        else:
            self._new_bar = Bar(self._bar_size, sample)
        
        if self._new_bar.is_full:
            self._commit_bar()


    def __getitem__(self, index: int) -> int:
        return self._queue[index]

    def __iter__(self):
        self._histo.__iter__()

    def _commit_bar(self):
        if len(self._queue) == self._queue.maxlen:
            self.histo -= self._queue[-1].histo
        self._queue.appendleft(self._new_bar)
        self.histo += self._new_bar.histo
        self._new_bar = None


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="creates samples or bar out of sample or databento files.")
    parser.add_argument("filename", help="name of file with samples (.csv) or databento trade records (.dbn)")
    parser.add_argument("-s", "--start", type=int, default=0, help="start offest (seconds) from where to begin")
    parser.add_argument("-d", "--duration", type=int, default=24 * 60 * 60, help="duration (seconds)")
    parser.add_argument("-b", "--barsize", type=int, help="size of the bars or no bars, if bar size is missing")
    parser.add_argument("-o", "--outfile", type=str, help="name of file for the output. no output file means stdout")
    args = parser.parse_args()

    filepath = Path(args.filename)
    result = None
    bar_builder = None if args.barsize is None else BarBuilder(args.barsize)

    def process_sample(sample):
        # if a new sample is available, it is send to the bar builder of taken over in the sample list
        if sample is None:
            return
        if bar_builder is None:
            samples.append(sample)
        else:
            bar_builder.on_new_sample(sample)

    if filepath.suffix == ".csv":
        # we generate bars from samples stored in file
        if bar_builder is None:
            print(
                f"{parser.prog}: barsize must be specified when .csv file is given as input",
                file=sys.stderr,
            )
            sys.exit(1)
        loader = SampleLoader()
        loader.add_listener(bar_builder)
        loader.load_and_stream(args.filename)
        result = pd.DataFrame([bar.to_dict() for bar in bar_builder])

    elif filepath.suffix == ".dbn":
        # we start from the ground up...
        samples = []
        sample_builder = SampleBuilder()

        data = db.DBNStore.from_file(args.filename)
        start_timestamp = data.metadata.start + args.start * 10**9
        end_timestamp = start_timestamp + args.duration * 10**9
        for record in data:
            if record.ts_event < start_timestamp:
                continue
            if record.ts_event > end_timestamp:
                break
            process_sample(sample_builder.on_trade(record))

        if sample_builder.is_sample_available:
            # there is an open sample that has to be finished...
            process_sample(sample_builder.get_sample())

        if bar_builder is None:
            result = pd.DataFrame([sample.model_dump() for sample in samples])
        else:
            bar_builder.on_end_of_samples()
            result = pd.DataFrame([bar.to_dict() for bar in bar_builder])

    else:
        # unknown file extension
        print(f"{parser.prog}: error: unknow file extension '{filepath.suffix}' (expected .csv or .dbn)")
        sys.exit(1)

    if args.outfile is None:
        print(result.to_csv(index=False))
    else:
        result.to_csv(args.outfile, index=False)
