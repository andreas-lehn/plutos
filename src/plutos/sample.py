"""
data model for trading bot

contains classes for trades, candles, charts,...
"""

import ast
import csv
import sys

from array import array
from pathlib import Path
from datetime import datetime

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

    @property
    def average(self) -> int:
        return self.volumes.average 

    @property
    def volume(self) -> int:
        return self.volumes.volume 
    
    def from_dict(d: dict):
        return Sample(d['timestamp'], VolumeProfile.from_dict(d))

    FIELDNAMES = ['timestamp', 'date'] + VolumeProfile.FIELDNAMES

    def to_dict(self) -> dict:
        result = self.volumes.to_dict()
        result['timestamp'] = self.timestamp
        result['date'] = datetime.fromtimestamp(self.timestamp).isoformat()
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
