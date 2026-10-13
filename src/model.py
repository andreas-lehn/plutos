"""
data model for trading bot

contains classes for trades, bars, charts,...
"""


import sys
import csv
import ast
from array import array

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


class Sample():
    """Kapselt die Daten eines Samples"""

    VOLUMES_BLOCK_SIZE = 32

    def __init__(self):
        self.open = None
        self.low = sys.maxsize
        self.high = 0
        self.close = None
        self.volumes = Sample.VolumeProxy(self)
        self._volumes = Sample._new_blocks(3)
        self._base_price = None
        self._volume = 0
        self._price_x_volume = 0

    @property
    def average(self):
        return round(self._price_x_volume / self._volume)

    @property
    def volume(self):
        return self._volume

    def to_dict(self) -> dict:
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volumes": [self.volumes[price] for price in range(self.low, self.high + 1)],
        }

    @classmethod
    def from_dict(cls, data):
        sample = cls()
        sample.low = data['low']
        for i, vol in enumerate(data['volumes']):
            price = sample.low + i
            sample.volumes[price] = vol
        sample.open = data['open']
        sample.close = data['close']
        return sample

    def copy(self):
        return Sample.from_dict(self.to_dict())

    def _resize(self, price):
        if price < self._base_price:
            delta = self._base_price - price
            blocks_needed = delta // Sample.VOLUMES_BLOCK_SIZE + 1
            self._volumes = Sample._new_blocks(blocks_needed) + self._volumes
            self._base_price -= blocks_needed * Sample.VOLUMES_BLOCK_SIZE
        elif price >= self._block_max:
            delta = price - self._base_price + len(self._volumes)
            blocks_needed = delta // Sample.VOLUMES_BLOCK_SIZE + 1
            self._volumes = self._volumes + Sample._new_blocks(blocks_needed)

    def _block_begin(price):
        return (price // Sample.VOLUMES_BLOCK_SIZE) * Sample.VOLUMES_BLOCK_SIZE

    def _new_blocks(n: int):
        """ returns n block of volumes array """
        return array('H', [0] * n * Sample.VOLUMES_BLOCK_SIZE)

    @property
    def _block_max(self):
        return self._base_price + len(self._volumes)

    class VolumeProxy:
        def __init__(self, sample):
            self.sample = sample

        def __getitem__(self, price):
            if self.sample._base_price is None or price < self.sample._base_price or price >= self.sample._block_max:
                return 0
            return self.sample._volumes[price - self.sample._base_price]

        def __setitem__(self, price, volume):
            if volume < self[price]:
                raise ValueError("__set_item__(): 'volume' is below current volume of price. volume can only be increased")

            sample = self.sample

            if sample._base_price is None:
                sample._base_price = Sample._block_begin(price) - Sample.VOLUMES_BLOCK_SIZE
                sample._volumes[price - sample._base_price] = volume
                sample._volume = volume
                sample._price_x_volume = price * volume
                sample.open = price
                sample.close = price
                sample.high = price
                sample.low = price
            else:
                if price < sample._base_price or price >= sample._block_max:
                    sample._resize(price)

                sample._update(price, volume)
                sample.high  = max(sample.high, price)
                sample.low   = min(sample.low, price)
                sample.close = price

        def __iter__(self):
            for price in range(self.sample.low, self.sample.high + 1):
                volume = self[price]
                if volume > 0:
                    yield (price, volume)

    def _update(self, price, volume):
        """ updates the volume of price and all dependant variables """
        delta_volume = volume - self.volumes[price]
        self._volumes[price - self._base_price] = volume
        self._volume += delta_volume
        self._price_x_volume += delta_volume * price

    def __iadd__(self, other):
        if not isinstance(other, Sample):
            raise TypeError("__iadd__() 'other' must be an instance of Sample") # pragma: no cover

        is_first = self.volume == 0
        for price, volume in other.volumes:
            self.volumes[price] += volume

        if is_first:
            self.open = other.open
        self.close = other.close
        return self

    def __isub__(self, other):
        if not isinstance(other, Sample):
            raise TypeError("__isub__() 'other' must be an instance of Sample")

        for price, vol in other.volumes:
            old_volume = self.volumes[price]
            if vol > old_volume:
                raise ValueError('__isub__(): volume to high to be subtracted')
            self._update(price, old_volume - vol)

        if self.volume == 0:
            # we are empty! Bring it back to init state
            self.open = None
            self.low = sys.maxsize
            self.high = 0
            self.close = None
            return self

        while self.volumes[self.low] == 0:
            # low was deleted. search new low...
            self.low += 1

        while self.volumes[self.high] == 0:
            # high was deleted. search new high..
            self.high -= 1

        return self
            

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
                yield Sample.from_dict({
                    'open': int(row["open"]),
                    'high': int(row["high"]),
                    'low':  int(row["low"]),
                    'close': int(row["close"]),
                    'volumes': ast.literal_eval(row["volumes"]),
                })


class SampleWriter:
    """ writes samples """

    def to_file(file: str | Path, samples):
        """ writes samples in file as csv """
        if isinstance(file, str):
            file = Path(file)

        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=['open', 'high', 'low', 'close', 'volumes'])
            writer.writeheader()
            writer.writerows([sample.to_dict() for sample in samples])


class SampleBuilder:
    """ builds 1 sec samples from trades """

    @classmethod
    def from_trades(cls, trades: Iterable, start_offset: int = 0, duration: int = sys.maxsize):
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
        return SampleBuilder(trades, start_offset, duration)

    def __init__(self, trades, start_offset: int = 0, duration: int = sys.maxsize):
        self.trades = trades
        self.start_offset = start_offset
        self.end_offset = self.start_offset + duration

        self.timestamp_offset: int = 0
        self.timestamp: int = None
        self.sample = None

    def __iter__(self):
        """ iterates of the trades and yields samples """
        for trade in self.trades:
            timestamp = trade.timestamp // 10**9 # timestamp is now in seconds
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
                # this is the first sample sample of the bar
                self.sample = Sample()
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
                self.sample = Sample()

            self.sample.volumes[trade.price] += trade.volume

        if self.sample.volume > 0:
            # there is a sample left...
            yield self.sample

        # prepare to start again
        self.timestamp_offset: int = 0
        self.timestamp: int = None
        self.sample = None


class Bar(Sample):
    """ accumulates multipe samples """

    def __init__(self):
        super().__init__()
        self._size = 0

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['size'] = self._size
        return d

    def __iadd__(self, other: Sample):
        super().__iadd__(other)
        self._size += 1
        return self

    @property
    def size(self):
        return self._size

    @classmethod
    def from_samples(cls, samples: Iterable):
        bar = Bar()
        for sample in samples:
            bar += sample
        return bar


class Chart(Sample):
    """ a chart contains a sequence of Bars all with the same size 
    
    A chart has a limited size.
    New bars cause old bars to disappear.

    """

    def __init__(self, size: int, bar_size: int):
        super().__init__()
        self._bars = deque(maxlen=size)
        self._bar_size = bar_size
        self._new_bar = None

    def __iadd__(self, sample):
        super().__iadd__(sample)

        if not self._new_bar:
            self._new_bar = Bar()
        self._new_bar += sample

        if self._new_bar.size >= self._bar_size:
            self._commit_bar()

        return self

    def __getitem__(self, index: int) -> int:
        return self._bars[index]

    def __iter__(self):
        return self._bars.__iter__()

    def __len__(self):
        return len(self._bars)
    
    def _commit_bar(self):
        if len(self._bars) == self._bars.maxlen:
            self -= self._bars[-1]
        self._bars.appendleft(self._new_bar)
        self._new_bar = None
        self.open = self._bars[-1].open
        self.close = self._bars[0].close
