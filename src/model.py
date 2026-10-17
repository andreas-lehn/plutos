"""
data model for trading bot

contains classes for trades, bars, charts,...
"""


import ast
import csv
import sys
import math
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

    def convolute(self, n: int) -> int:
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

    def from_dict(d: dict):
        return Sample(d['timestamp'], VolumeProfile.from_dict(d))

    def to_dict(self) -> dict:
        result = self.volumes.to_dict()
        result['timestamp'] = self.timestamp
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


class SampleWriter:
    """ writes samples """

    def to_file(file: str | Path, samples):
        """ writes samples in file as csv """
        if isinstance(file, str):
            file = Path(file)

        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'low', 'high', 'volumes'])
            writer.writeheader()
            writer.writerows([sample.to_dict() for sample in samples])


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
                # this is the first sample sample of the bar
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


class Bar():
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
        bar = Bar()
        bar.append(sample)
        return bar
    
    @classmethod
    def from_samples(cls, samples: Iterable[VolumeProfile | Sample]):
        bar = Bar()
        for sample in samples:
            bar.append(sample)
        return bar
    
    def __iter__(self):
        return self._samples.__iter__()

    def __repr__(self): # pragma: no cover
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


class Chart():
    """ a chart contains a sequence of Bars all with the same size 
    
    A chart has a limited size.
    New bars cause old bars to disappear.

    """

    def __init__(self, bar_size: int, maxlen: int = None):
        self._bar_size = bar_size
        self._current_bar = Bar()
        self._maxlen = maxlen if maxlen else sys.maxsize
        self._bars = deque()
        self._volumes = VolumeProfile()
        self._callbacks = []

    def register_callback(self, callback):
        self._callbacks.append(callback)

    def unregister_callback(self, callback):
        self._callbacks.remove(callback)

    def _notify_listeners(self, bar):
        for cb in self._callbacks:
            cb(bar, self)

    @property
    def open(self) -> int:
        return self._bars[0].open

    @property
    def close(self) -> int:
        return self._bars[-1].close

    @property
    def low(self) -> int:
        return self._volumes.low

    @property
    def high(self) -> int:
        return self._volumes.high

    @property
    def average(self) -> int:
        return self._volumes.average

    def average_range(self, n: int = 5) -> int:
        sum_range = 0
        for i in range(-1, -n-1, -1):
            sum_range += self._bars[i].range
        return round(sum_range / n)

    def filter_range(self, n: int = 5) -> int:
        FILTER_FACTOR_AVERAGE_RANGE = 0.25
        filter_range = math.floor(self.average_range(n) * FILTER_FACTOR_AVERAGE_RANGE)
        if filter_range // 2 == filter_range / 2:
            filter_range += 1
        return filter_range

    def delta(self, n: int = 5) -> int:
        return self[-1].average - self[-1 - n].average
    
    @property
    def volume(self) -> int:
        return self._volumes.volume

    @property
    def volumes(self) -> VolumeProfile:
        return self._volumes

    def from_samples(samples, bar_size, maxlen=None):
        chart = Chart(bar_size, maxlen)
        for sample in samples:
            chart.append(sample)
        return chart

    def append(self, sample: Sample):
        self._current_bar.append(sample)
        self._volumes += sample.volumes
        if len(self._current_bar) >= self._bar_size:
            self._bars.append(self._current_bar)
            if len(self._bars) > self._maxlen:
                # chart is full, remove an old one
                self.popleft()            
            self._notify_listeners(self._current_bar)
            self._current_bar = Bar()

    def popleft(self) -> Bar:
        bar = self._bars.popleft()
        self._volumes -= bar.volumes
        return bar

    def to_file(self, file: str | Path, fieldnames = Bar.OHLC_FIELDNAMES): # pragma: no cover
        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([bar.to_filtered_dict(fieldnames) for bar in self])

    def __getitem__(self, index: int) -> int:
        return self._bars[index]

    def __iter__(self):
        return self._bars.__iter__()

    def __len__(self):
        return len(self._bars)
    

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
                chart.append(sample)

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
        model.charts.append(Chart(bar_size=12, maxlen=15))  #  3 min
        model.charts.append(Chart(bar_size=36, maxlen=60))  # 36 min
        model.charts.append(Chart(bar_size=60, maxlen=36))  # 36 min
        model.charts.append(Chart(bar_size=720, maxlen=120))# 24 Std
        return model

    def simulate_file(self, file: str | Path, duration: int = 0): # pragma: no cover
        """ simulates file for a duration (in seconds) """
    
        import marketdata
        from tqdm import tqdm

        if duration == 0:
            duration = marketdata.SECONDS_OF_DAY

        NANO_SECONDS = 10**9
        reader = marketdata.from_file(file, duration=duration * NANO_SECONDS)
        self.feed_with_trades(tqdm(
            reader, 
            desc=f"Processing file {file}",
            bar_format="{desc}: {n} records read [{elapsed}, {rate_fmt}]")
        )


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="load a file into default market model and put out some statistics")
    parser.add_argument('file', help='name of Databento native file (.dbn)')
    parser.add_argument('-b', '--bar-size', type=int, default=36, help="size of bar in seconds")
    parser.add_argument('-n', '--num', type=int, default=0, help='number of bars')
    parser.add_argument('-o', '--ohlc-file', type=str, help="name of file for OHLCV data")
    parser.add_argument('-p', '--profile-file', type=str, help="name of file for volume profile data")
    args = parser.parse_args()

    main_chart = Chart(bar_size=args.bar_size)
    model = MarketModel()
    model.charts.append(main_chart)
    model.simulate_file(args.file, args.num * args.bar_size)

    if args.ohlc_file:    
        with open(args.ohlc_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = ['timestamp', 'open', 'low', 'average', 'high', 'close', 'volume']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([bar.to_filtered_dict(fieldnames) for bar in main_chart])

    if args.profile_file:
        with open(args.profile_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=['price', "volume", 'smooth_volume'])
            writer.writeheader()
            smoothed_volumes = main_chart.volumes.convolute(main_chart.filter_range())
            for p, v in main_chart.volumes:
                writer.writerow({'price': p, 'volume': v, 'smooth_volume': smoothed_volumes[p]})
