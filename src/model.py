"""
data model for trading bot

contains classes for trades, bars, charts,...
"""


import ast
import csv
import sys
from array import array
from collections import deque
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel


class Trade(BaseModel):
    """ a basic trade at the exchange """

    timestamp: int # original timestamp in ns
    price: int     # price * 4
    volume: int


class VolumeProfile():
    """ Volume profiel maps volumes to prices """

    VOLUMES_BLOCK_SIZE = 64

    def __init__(self):
        self.low = sys.maxsize
        self.high = 0
        self.volumes = VolumeProfile.VolumeProxy(self)
        self._volumes = VolumeProfile._new_blocks(1)
        self._base_price = None
        self._volume = 0
        self._price_x_volume = 0

    @property
    def average(self):
        return round(self._price_x_volume / self._volume) if self.volume != 0 else 0

    @property
    def volume(self):
        return self._volume

    def convolute(self, n: int):
        result = VolumeProfile()
        for i in range(self.low, self.high +1):
            # Einmal über alles
            v = 0
            for j in range(i - n, i + n + 1):
                v += self.volumes[j]
            result.volumes[i] = round(v / (2 * n + 1))
        return result

    def tangent(self, n: int):
        result = VolumeProfile()
        for i in range(self.low, self.high + 1):
            result.volumes[i] = self.volumes[i + n] - self.volumes[i - n]
        return result

    def to_dict(self) -> dict:
        return {
            "low": self.low,
            "high": self.high,
            "volumes": [self.volumes[price] for price in range(self.low, self.high + 1)],
        }

    @classmethod
    def from_dict(cls, data):
        sample = cls()
        sample.low = data['low']
        for i, vol in enumerate(data['volumes']):
            price = sample.low + i
            sample.volumes[price] = vol
        return sample

    def copy(self):
        return VolumeProfile.from_dict(self.to_dict())

    def _resize(self, price):
        if price < self._base_price:
            delta = self._base_price - price
            blocks_needed = delta // VolumeProfile.VOLUMES_BLOCK_SIZE + 1
            self._volumes = VolumeProfile._new_blocks(blocks_needed) + self._volumes
            self._base_price -= blocks_needed * VolumeProfile.VOLUMES_BLOCK_SIZE
        elif price >= self._block_max:
            delta = price - self._base_price + len(self._volumes)
            blocks_needed = delta // VolumeProfile.VOLUMES_BLOCK_SIZE + 1
            self._volumes = self._volumes + VolumeProfile._new_blocks(blocks_needed)

    def _new_blocks(n: int):
        """ returns n block of volumes array """
        return array('i', [0] * n * VolumeProfile.VOLUMES_BLOCK_SIZE)

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
            self.sample.update(price, volume)

        def __iter__(self):
            for price in range(self.sample.low, self.sample.high + 1):
                volume = self[price]
                if volume > 0:
                    yield (price, volume)

    def update(self, price, volume):
        """ updates the volume of price and all dependant variables """
        if self._base_price is None:
            self._base_price = price - VolumeProfile.VOLUMES_BLOCK_SIZE // 2
        else:
            if price < self._base_price or price >= self._block_max:
                self._resize(price)

        self.high = max(self.high, price)
        self.low  = min(self.low, price)

        delta_volume = volume - self.volumes[price]
        self._volumes[price - self._base_price] = volume
        self._volume += delta_volume
        self._price_x_volume += delta_volume * price

        while self.volumes[self.low] == 0:
            # low was deleted. search new low...
            self.low += 1
            if self.low > self.high:
                # we are empty! Bring it back to init state
                self.low = sys.maxsize
                self.high = 0
                return

        while self.volumes[self.high] == 0:
            # high was deleted. search new high..
            self.high -= 1


    def __iadd__(self, other):
        if not isinstance(other, VolumeProfile):
            raise TypeError("__iadd__() 'other' must be an instance of VolumeProfile") # pragma: no cover

        for price, volume in other.volumes:
            self.volumes[price] += volume
        return self

    def __isub__(self, other):
        if not isinstance(other, VolumeProfile):
            raise TypeError("__isub__() 'other' must be an instance of VolumeProfile")

        for price, volume in other.volumes:
            self.volumes[price] -= volume
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
                yield VolumeProfile.from_dict({
                    'high': int(row["high"]),
                    'low':  int(row["low"]),
                    'volumes': ast.literal_eval(row["volumes"]),
                })


class SampleWriter:
    """ writes samples """

    def to_file(file: str | Path, samples):
        """ writes samples in file as csv """
        if isinstance(file, str):
            file = Path(file)

        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=['low', 'high', 'volumes'])
            writer.writeheader()
            writer.writerows([sample.to_dict() for sample in samples])


class SampleBuilder:
    """ builds 1 sec samples from trades """

    SAMPLE_RATE_NS = 1 * 10**9 # 1 sec

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
            timestamp = trade.timestamp // SampleBuilder.SAMPLE_RATE_NS # timestamp is now in seconds
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
                self.sample = VolumeProfile()
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
                self.sample = VolumeProfile()

            self.sample.volumes[trade.price] += trade.volume

        if self.sample.volume > 0:
            # there is a sample left...
            yield self.sample

        # prepare to start again
        self.timestamp_offset: int = 0
        self.timestamp: int = None
        self.sample = None


class Bar():
    """ accumulates multipe samples """

    def __init__(self):
        super().__init__()
        self._samples: Iterable[VolumeProfile] = deque()
        self._volumes: Iterable[int] = VolumeProfile()

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
    
    def __len__(self):
        return len(self._samples)
    
    def to_dict(self) -> dict:
        return {
            'open': self.open,
            'low': self.low,
            'average': self.average,
            'high': self.high,
            'close': self.close,
            'volume': self.volume,
            'len': len(self),
            'volumes': [self.volumes.volumes[p] for p in range (self.low, self.high + 1)]
        }

    def append(self, sample: VolumeProfile):
        self._samples.append(sample)
        self._volumes += sample

    def popleft(self) -> VolumeProfile:
        sample = self._samples.popleft()
        self._volumes -= sample
        return sample

    @classmethod
    def from_samples(cls, samples: Iterable):
        bar = Bar()
        for sample in samples:
            bar.append(sample)
        return bar

    def __iter__(self):
        return self._samples.__iter__()

    def __repr__(self):
        return (
            "Bar("
                f"open={self.open},"
                f"low={self.low},"
                f"avg={self.average},"
                f"high={self.high},"
                f"close={self.close},"
                f"vol={self.volume},"
                f"len={len(self)}"
            ")"
        )


class Chart(VolumeProfile):
    """ a chart contains a sequence of Bars all with the same size 
    
    A chart has a limited size.
    New bars cause old bars to disappear.

    """

    def __init__(self, bar_size: int, size: int = None):
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

    class Exporter:
        """ liefert eine liste mit jeweils einem dict für jede bar
        
        Convention:
         * Columns starting with an Upper letter contain real price values in float not in integer.
         * if prices are in integer, columns start with lower letters.

        """
        def __init__(self, bars: Iterable[Bar], bar_size):
            self.bars = reversed(bars)
            self.bar_size = bar_size
            self.timestamp = 0

        def __iter__(self):
            for bar in self.bars:
                yield {
                    'Timestamp': self.timestamp,
                    'Open': bar.open/4,
                    'Low': bar.low/4,
                    'Average': bar.average/4,
                    'High': bar.high/4,
                    'Close': bar.close/4,
                    'Volume': bar.volume,
                }
                self.timestamp += self.bar_size
            self.timestamp = 0

    def export(self):
        """ return a chart exporter (generator) """
        return Chart.Exporter(self._bars, self._bar_size)


class MarketModel:
    """ MarketModell contains charts and feeds them """

    def __init__(self):
        self.charts = []
        self.time = 0

    def feed_with_trades(self, trades: Iterable[Trade]):
        builder = SampleBuilder(trades)
        for sample in builder:
            self.time += 1
            for chart in self.charts:
                chart += sample

    @classmethod
    def default_model(cls):
        """ default model contain a short, mid, retail and long term chart
        
         * short term chart is 12s
         * mid term chart is 36s
         * retail chart is 60s 
         * long term chart is 720s (12 min)

        all charts are unlimited
        """
        model = cls()
        model.charts.append(Chart(bar_size=12, size=15))  #  3 min
        model.charts.append(Chart(bar_size=36, size=60))  # 36 min
        model.charts.append(Chart(bar_size=60, size=36))  # 36 min
        model.charts.append(Chart(bar_size=720, size=120))# 24 Std
        return model

if __name__ == '__main__':
    import argparse
    import marketdata
    import os
    import pandas as pd
    from tqdm import tqdm

    parser = argparse.ArgumentParser(description="load a file into default market model and put out some statistics")
    parser.add_argument('file', help='name of Databento native file (.dbn)')
    parser.add_argument('-s', '--start', type=int, default=0, help="start offset in seconds")
    parser.add_argument('-d', '--duration', type=int, default=marketdata.SECONDS_OF_DAY, help="duration of replay in seconds")
    parser.add_argument('-e', '--export', required=True, choices=['fast', 'main', '1-min', 'day'], help="exports one of these charts")
    args = parser.parse_args()

    RECORD_SIZE_BYTES = 48
    estimated_records = os.path.getsize(args.file) // RECORD_SIZE_BYTES

    NANO_SECONDS = 10**9
    reader = marketdata.from_file(args.file, args.start * NANO_SECONDS, args.duration * NANO_SECONDS)
    model = MarketModel.default_model()

    model.feed_with_trades(tqdm(
            reader, 
            total=estimated_records, 
            desc=f"Processing file {args.file}",
            bar_format="{desc}: {n} records read [{elapsed}, {rate_fmt}]")
        )
    
    chart = None
    for i, name in enumerate(['fast', 'main', '1-min', 'day']):
        if name == args.export:
            chart = model.charts[i]
            break

    exporter = chart.export()
    with open(args.export + "_bar_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=['Timestamp', 'Open', 'Low', 'Average', 'High', 'Close', 'Volume'])
        writer.writeheader()
        writer.writerows([e for e in exporter])

    with open(args.export + "_volume_profile.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=['Price', "Volume"])
        writer.writeheader()
        writer.writerows([{'Price': p/4, 'Volume': v} for p, v in chart.volumes])
