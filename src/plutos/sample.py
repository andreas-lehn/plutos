"""
data model for trading bot

contains classes for trades, candles, charts,...
"""

import ast
import csv
import sys
import click

from array import array
from collections import deque
from collections.abc import Iterable
from pathlib import Path
from datetime import datetime

from . import marketdata
from .trade import Trade


class VolumeProfile():
    """ Volume profiel maps volumes to prices """

    VOLUMES_BLOCK_SIZE = 64

    def __init__(self):
        self._low = sys.maxsize
        self._high = 0
        self._volumes = VolumeProfile._alloc_blocks(1)
        self._base_price = None
        self._volume = 0
        self._price_x_volume = 0

    @property
    def low(self) -> int:
        return self._low

    @property
    def high(self) -> int:
        return self._high
    
    @property
    def average(self):
        return round(self._price_x_volume / self._volume) if self.volume != 0 else 0

    @property
    def volume(self):
        return self._volume

    def convolute(self, n: int):
        """ convolutes the profile in range [-n .. n] """
        result = VolumeProfile()
        for i in range(self.low, self.high +1):
            # Einmal über alles
            v = 0
            for j in range(i - n, i + n + 1):
                v += self[j]
            result[i] = round(v / (2 * n + 1))
        return result

    def tangent(self, price: int, n: int = 1) -> int:
        return round((self[price + n] - self[price - n]) / (2 * n))

    def range(self) -> int:
        return self.high - self.low

    FIELDNAMES = ['low', 'high', 'volumes']

    def to_dict(self) -> dict:
        return {
            "low": self.low,
            "high": self.high,
            "volumes": [self[price] for price in range(self.low, self.high + 1)],
        }

    @classmethod
    def from_dict(cls, data):
        sample = cls()
        sample._low = data['low']
        for i, vol in enumerate(data['volumes']):
            price = sample._low + i
            sample[price] = vol
        return sample

    def copy(self):
        return VolumeProfile.from_dict(self.to_dict())

    def _resize(self, price):
        if price < self._base_price:
            delta = self._base_price - price
            blocks_needed = delta // VolumeProfile.VOLUMES_BLOCK_SIZE + 1
            self._volumes = VolumeProfile._alloc_blocks(blocks_needed) + self._volumes
            self._base_price -= blocks_needed * VolumeProfile.VOLUMES_BLOCK_SIZE
        elif price >= self._max_price:
            delta = price - self._base_price + len(self._volumes)
            blocks_needed = delta // VolumeProfile.VOLUMES_BLOCK_SIZE + 1
            self._volumes = self._volumes + VolumeProfile._alloc_blocks(blocks_needed)

    def _alloc_blocks(n: int):
        """ returns n block of volumes array """
        return array('i', [0] * n * VolumeProfile.VOLUMES_BLOCK_SIZE)

    @property
    def _max_price(self):
        return self._base_price + len(self._volumes)

    def __getitem__(self, price):
        if self._base_price is None or price < self._base_price or price >= self._max_price:
            return 0
        return self._volumes[price - self._base_price]

    def __setitem__(self, price, volume):
        self.update(price, volume)

    def __iter__(self):
        for price in range(self._low, self._high + 1):
            volume = self[price]
            if volume > 0:
                yield (price, volume)

    def update(self, price, volume):
        """ updates the volume of price and all dependant variables """
        if self._base_price is None:
            self._base_price = price - VolumeProfile.VOLUMES_BLOCK_SIZE // 2
        else:
            if price < self._base_price or price >= self._max_price:
                self._resize(price)

        self._high = max(self._high, price)
        self._low  = min(self._low, price)

        delta_volume = volume - self[price]
        self._volumes[price - self._base_price] = volume
        self._volume += delta_volume
        self._price_x_volume += delta_volume * price

        while self[self.low] == 0:
            # low was deleted. search new low...
            self._low += 1
            if self._low > self._high:
                # we are empty! Bring it back to init state
                self._low = sys.maxsize
                self._high = 0
                return

        while self[self._high] == 0:
            # high was deleted. search new high..
            self._high -= 1

    def __iadd__(self, other):
        if not isinstance(other, VolumeProfile):
            raise TypeError("__iadd__() 'other' must be an instance of VolumeProfile") # pragma: no cover

        for price, volume in other:
            self[price] += volume
        return self

    def __isub__(self, other):
        if not isinstance(other, VolumeProfile):
            raise TypeError("__isub__() 'other' must be an instance of VolumeProfile")

        for price, volume in other:
            self[price] -= volume
        return self

    def __repr__(self): # pragma: no cover
        return (
            'VolumeProfile('
                f'low={self.low},'
                f'avg={self.average},'
                f'high={self.high},'
                f'volume={self.volume}'
            ')'
        )

class Sample:
    """ a Sample associates a volume profile with a timestamp
    
    timestamp is the timestamp of the latest trade in the volume profile
    """

    def __init__(self, timestamp: int = 0, volumes: VolumeProfile = None):
        self.timestamp = timestamp
        self.volumes = volumes

    @property
    def low(self) -> int:
        return self.volumes.low

    @property
    def high(self) -> int:
        return self.volumes.high
    
    def from_dict(d: dict):
        return Sample(d['timestamp'], VolumeProfile.from_dict(d))

    FIELDNAMES = ['timestamp', 'date'] + VolumeProfile.FIELDNAMES

    def to_dict(self) -> dict:
        result = self.volumes.to_dict()
        result['timestamp'] = self.timestamp
        result['date'] = datetime.fromtimestamp(self.timestamp / 10**9).isoformat()
        return result

    def __repr__(self): # pragma: no cover
        return 'Sample(timestamp:' + self.timestamp + ',' + self.volumes.__repr__ + ')'


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
                    'timestamp': int(row['timestamp']),
                    'high': int(row["high"]),
                    'low':  int(row["low"]),
                    'volumes': ast.literal_eval(row["volumes"]),
                })


class SampleBuilder:
    """ builds 1 sec samples from trades """

    SAMPLE_RATE = 1 * 10**9 # 1 sec
    """ sample rate in nano seconds """

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
            timestamp = trade.timestamp // SampleBuilder.SAMPLE_RATE # timestamp is now in sample units
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
                # this is the first sample sample of the candle
                self.sample = Sample(trade.timestamp, VolumeProfile())
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
                self.sample = Sample(trade.timestamp, VolumeProfile())

            self.sample.volumes[trade.price] += trade.volume
            self.sample.timestamp = max(self.sample.timestamp, trade.timestamp)


        if self.sample and self.sample.volumes.volume > 0:
            # there is a sample left...
            yield self.sample

        # prepare to start again
        self.timestamp_offset: int = 0
        self.timestamp: int = None
        self.sample = None

@click.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False), help='path to .dbn file')
@click.option('-s', '--start', type=int, default=0, help="start offest in seconds")
@click.option('-d', '--duration', type=int, default=marketdata.SECONDS_OF_DAY, help="duration in seconds")
def samples(file, start: int, duration: int): # pragma: no cover
    """ creates samples form a Datebento file (*.dbn -> *_samples.csv) """

    click.echo(f"reading form file '{file}'")
    reader = marketdata.from_file(file)
    builder = SampleBuilder(reader, start, duration)

    file_parts = marketdata.parse_path(file)
    file_parts['parent'] = '.'
    file_parts['content'] = 'samples'
    file_parts['suffix'] = '.csv'
    file_parts['range'] = (start, start + duration)
    out_file = marketdata.assemble_path(file_parts)

    n_samples = 0
    with open(out_file, 'w', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=Sample.FIELDNAMES)
        writer.writeheader()
        for sample in builder:
            writer.writerow(sample.to_dict())
            n_samples += 1

    click.echo(f"{n_samples} samples written to file '{out_file}'")


class Candle:
    """ accumulates multipe samples """

    def __init__(self):
        super().__init__()
        self._timestamp: int = 0
        self._samples: Iterable[VolumeProfile] = deque()
        self._volumes: Iterable[int] = VolumeProfile()

    @property
    def timestamp(self) -> int:
        return self._timestamp
    
    @property
    def open(self) -> int:
        return self._samples[0].average if len(self._samples) > 0 else None

    @property
    def low(self) -> int:
        return self._volumes.low

    @property
    def average(self) -> int:
        return self._volumes.average

    @property
    def high(self) -> int:
        return self._volumes.high

    @property
    def close(self) -> int:
        return self._samples[-1].average if len(self._samples) > 0 else None

    @property
    def volume(self) -> int:
        return self._volumes.volume

    @property
    def volumes(self) -> VolumeProfile:
        return self._volumes

    @property
    def range(self) -> int:
        return self.high - self.low

    @property
    def delta(self) -> int:
        return self.close - self.open

    def tangent(self, price: int, n: int = 1) -> int:
        return self.volumes.tangent(price, n) # pragma: no cover
    
    def __len__(self):
        return len(self._samples)
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'low': self.low,
            'average': self.average,
            'high': self.high,
            'close': self.close,
            'volume': self.volume,
            'len': len(self),
            'volumes': [self._volumes[p] for p in range (self.low, self.high + 1)]
        }

    OHLC_FIELDNAMES = ['timestamp', 'open', 'low', 'average', 'high', 'close', 'volume']

    def to_filtered_dict(self, keys: Iterable[str]) -> dict:
        return {key: getattr(self, key) for key in keys}

    def append(self, sample: Sample | VolumeProfile):
        if isinstance(sample, Sample):
            self._timestamp = sample.timestamp
            sample = sample.volumes
        self._samples.append(sample)
        self._volumes += sample

    def popleft(self) -> VolumeProfile:
        sample = self._samples.popleft()
        self._volumes -= sample
        return sample

    @classmethod
    def from_sample(cls, sample: VolumeProfile | Sample):
        candle = Candle()
        candle.append(sample)
        return candle
    
    @classmethod
    def from_samples(cls, samples: Iterable[VolumeProfile | Sample]):
        candle = Candle()
        for sample in samples:
            candle.append(sample)
        return candle
    
    def __iter__(self):
        return self._samples.__iter__()

    def __repr__(self): # pragma: no cover
        return (
            "Candle("
                f"open={self.open},"
                f"low={self.low},"
                f"avg={self.average},"
                f"high={self.high},"
                f"close={self.close},"
                f"vol={self.volume},"
                f"len={len(self)}"
            ")"
        )
