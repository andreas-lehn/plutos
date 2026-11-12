"""
data model for trading bot

contains classes for trades, candles, charts,...
"""

import io
import ast
import csv
import sys
import click

from collections import deque
from collections.abc import Iterable
from pathlib import Path

from .trade import Trade
from .sample import VolumeProfile, Sample


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


class Chart():
    """ a chart contains a sequence of Candles all with the same size 
    
    A chart has a limited size.
    New candles cause old candles to disappear.

    """

    def __init__(self, candle_size: int, maxlen: int = None):
        self._candle_size = candle_size
        self._current_candle = Candle()
        self._maxlen = maxlen if maxlen else sys.maxsize
        self._candles = deque()
        self._volumes = VolumeProfile()
        self._callbacks = []

    def register_callback(self, callback):
        self._callbacks.append(callback)

    def unregister_callback(self, callback):
        self._callbacks.remove(callback)

    def _notify_listeners(self, candle):
        for cb in self._callbacks:
            cb(candle, self)

    def average_range(self, n: int = 5) -> int:
        if n == 0:
            return 0
        
        if len(self) < n:
            return self.average_range(len(self))
        
        sum_range = 0
        for i, candle in enumerate(reversed(self._candles)):
            if i == n:
                break # pragma: no cover
            sum_range += candle.range
        return round(sum_range / n)

#    def delta(self, n: int = 5) -> int:
#        return self[-1].average - self[-1 - n].average

#    def moving_average(self, n: int = 5) -> int:
#        sum = 0
#        for i in range(-n - 1, -1):
#            sum += self[i].average
#        return round(sum / n)

    @property
    def volumes(self) -> VolumeProfile:
        return self._volumes

    def from_samples(samples, candle_size, maxlen=None):
        chart = Chart(candle_size, maxlen)
        for sample in samples:
            chart.append(sample)
        return chart

    def append(self, sample: Sample):
        """ appends sample to a chart
        
        Appending samples to a chart is the way to build up a chart.
        Dependingn on the candle size new candles will be addded sone times.

        When a candle is added to a chart, some characteristic propertys often used in trading applications
        are calculated and attached as properties to the candle.
        These properties are:

         * `ema_fast`   exponential moving average with periodicity 3 (short term moving average)
         * `ema_slow`   exponential moving average with periodicity 19 (long term moving average)
         * `direction`  direction, in which the candle is moving expressed as a positiv/negative number showing the strength in ticks
        
        """
        self._current_candle.append(sample)
        self._volumes += sample.volumes
        if len(self._current_candle) >= self._candle_size:
            self._commit_current_candle()
            if len(self._candles) > self._maxlen:
                # chart is full, remove an old one
                self.popleft()            
            self._notify_listeners(self._current_candle)
            self._current_candle = Candle()

    def popleft(self) -> Candle:
        candle = self._candles.popleft()
        self._volumes -= candle.volumes
        return candle

    @property
    def trend_length(self) -> int:
        """ length of the trend """
        length = 0
        direction = None
        for candle in reversed(self._candles):
            if direction == None:
                direction = candle.direction
            elif (average - candle.average) * direction > 0:
                length += 1
            else:
                break
            average = candle.average
        return length

    @property
    def trend_direction(self) -> int:
        """ direction of the trend (in ticks)"""
        direction = 0
        if len(self._candles) > 0:
            direction = self._candles[-1].direction
        return direction
        
    EMA_FAST_FACTOR = 0.5   # = 2 / (3 + 1)
    EMA_SLOW_FACTOR = EMA_FAST_FACTOR / 5

    def _exp_moving_avg(value: float, ema: float, factor: float):
        """ calculates the exponetial moving average of candle """
        return value * factor + ema * (1 - factor)

    def _direction(candle: Candle, last_candle: Candle):
        """ calculates the direction of candle """
        dir = candle.delta
        if last_candle:
            dir_last = candle.average - last_candle.average
            if dir * dir_last > 0:
                dir = dir_last
            else:
                dir = 0
        return dir
    
    def _commit_current_candle(self):
        candle = self._current_candle
        last_candle = None
        if len(self._candles) == 0:
            candle.ema_fast = self._current_candle.average
            candle.ema_slow = self._current_candle.average
            candle.direction = candle.delta
        else:
            last_candle = self[-1]
            candle.ema_fast = Chart._exp_moving_avg(candle.average, last_candle.ema_fast, Chart.EMA_FAST_FACTOR)
            candle.ema_slow = Chart._exp_moving_avg(candle.average, last_candle.ema_slow, Chart.EMA_SLOW_FACTOR)
            candle.direction = Chart._direction(candle, last_candle)
        self._candles.append(candle)

    def to_file(self, file: str | Path, fieldnames = Candle.OHLC_FIELDNAMES): # pragma: no cover
        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([candle.to_filtered_dict(fieldnames) for candle in self])

    def __getitem__(self, index: int) -> int:
        return self._candles[index]

    def look_back(self, n: int) -> int:
        if n >= len(self._candles):
            return self._candles[0]
        return self._candles[-(n + 1)]

    def __iter__(self):
        return self._candles.__iter__()

    def __len__(self):
        return len(self._candles)
    

class MarketModel:
    """ MarketModell contains charts and feeds them """

    def __init__(self):
        self.charts = []
        self.time = 0

    def feed_with_samples(self, samples: Iterable[Sample]):
        for sample in samples:
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
        model.charts.append(Chart(candle_size=12, maxlen=15))  #  3 min
        model.charts.append(Chart(candle_size=36, maxlen=60))  # 36 min
        model.charts.append(Chart(candle_size=60, maxlen=36))  # 36 min
        model.charts.append(Chart(candle_size=720, maxlen=120))# 24 Std
        return model

    def simulate_file(self, file: str | Path, duration: int = 0): # pragma: no cover
        """ simulates file for a duration (in seconds) """
    
        from . import marketdata
        from tqdm import tqdm

        if duration == 0:
            duration = marketdata.SECONDS_OF_DAY

        reader = marketdata.from_file(file, duration=duration)
        self.feed_with_samples(tqdm(
            reader, 
            desc=f"Processing file {file}",
            bar_format="{desc}: {n} records read [{elapsed}, {rate_fmt}]")
        )


@click.command('chart')
@click.argument('file', type=click.Path(), help='name of marked data file (.dbn)')
@click.option('-s', '--candle-size', type=int, default=36, help="size of candle in seconds")
@click.option('-n', '--num', type=int, default=0, help='number of candles')
@click.option('-o', '--ohlc-file', type=click.File('w', encoding='utf-8'), help="chart file")
@click.option('-p', '--profile-file', type=click.File('w', encoding='utf-8'), help="volume profile file")
def chart_cmd(file: Path, candle_size: int, num: int, ohlc_file: io.TextIOWrapper, profile_file: io.TextIOWrapper): # pragma: no cover
    """ create a chart from market data """
    main_chart = Chart(candle_size=candle_size)
    model = MarketModel()
    model.charts.append(main_chart)
    model.simulate_file(file, num * candle_size)

    if ohlc_file:    
        fieldnames = ['timestamp', 'open', 'low', 'average', 'high', 'close', 'volume', 'ema_fast', 'ema_slow']
        writer = csv.DictWriter(ohlc_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([candle.to_filtered_dict(fieldnames) for candle in main_chart])

    if profile_file:
        writer = csv.DictWriter(profile_file, fieldnames=['price', "volume", 'smooth_volume'])
        writer.writeheader()
        smoothed_volumes = main_chart.volumes.convolute(main_chart.average_range() // 2)
        for p, v in main_chart.volumes:
            writer.writerow({'price': p, 'volume': v, 'smooth_volume': smoothed_volumes[p]})
