"""
Modul: MarketData
Verantwortlich für die Verarbeitung, Kapselung und den Aufbau von 
Marktdatenstrukturen (Volumenbalken, Histogramme) aus einem Tick-Datenstrom.
"""

import sys
import csv
import ast
import pandas as pd
import databento as db
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Iterator, Tuple, Protocol, Iterable

class Histogram:
    """ histogram of prices """

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
        Histogram._validate_int(value, '__setitem__(): value')
        if index < self.low or index > self.high:
            raise IndexError('Histogram: index out of range')
        if value < 0:
            raise ValueError('__setitem__(): value must not be negative')
        
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

    def _eval(base: int, histo: List[int]) -> (int, int):
        """ computes volume and price volu"""
        return volume, price_volume

    def _histo_value(low: int, histo: List[int], i) -> int:
        return 0 if (i < low) or i > (low + len(histo) - 1) else histo[i - low]

    def _validate_int(value, text: str) -> int:
        if not isinstance(value,int):
            raise TypeError(f"{text} must be int, not {type(value).__name__}")
        if value < 0:
            raise ValueError(f"{text} must be >= 0")
        return value


class Sample(BaseModel):
    """ Kapselt die Daten eines Samples """

    open: int
    high: int
    low: int
    close: int
    histo: List[int]
    
    def from_dbn(filename: str, start: int = 0, duration: int = sys.maxsize) -> []:
        samples = []
        sample_builder = SampleBuilder()

        data = db.DBNStore.from_file(filename)
        start_timestamp = data.metadata.start + start * 10**9
        end_timestamp = start_timestamp + duration * 10**9
        for record in data:
            if record.ts_event < start_timestamp:
                continue
            if record.ts_event > end_timestamp:
                break
            sample = sample_builder.on_trade(record)
            if sample:
                samples.append(sample)

        if sample_builder.is_sample_available:
            samples.append(sample_builder.get_sample())

        return samples


    def stream_csv(csv_path: str | Path, callback: callable):
        """ Öffnet die CSV-Datei und streamt sie Zeile für Zeile. """        
        with open(csv_path, mode='r', newline='') as file:
            reader = csv.DictReader(file, fieldnames=['open', 'high', 'low', 'close', 'histo'])
            next(reader)
            for row in reader:
                sample = Sample(
                    open=int(row['open']),
                    high=int(row['high']),
                    low=int(row['low']),
                    close=int(row['close']),
                    histo=ast.literal_eval(row['histo']),
                )
                callback(sample)
            callback(None) # end of file marker

    def stream_dbn(self, filename: str, start: int, duration: int):
        pass


class SampleBuilder:
    """ builds 1 sec samples from databento trade records """

    def __init__(self):
        self.timestamp_offset: int = 0
        self.histo: Dict[int, int] = {}
        self.open: int = None
        self.high: int = 0
        self.low: int = sys.maxsize
        self.close: int = None
        self.timestamp: int = None

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

        self.histo[price] = volume + self.histo.get(price, 0)
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        return sample


    def get_sample(self) -> dict:
        sample = Sample(
            low = self.low,
            high = self.high,
            open = self.open,
            close = self.close,
            histo = [self.histo.get(i, 0) for i in range(self.low, self.high + 1)],
        )
            
        self.volume = {}
        self.high = 0
        self.low = sys.maxsize
        return sample

    @property
    def is_sample_available(self) -> bool:
        return len(self.histo) > 0


class Bar(BaseModel):
    """ Kapselt die Daten einer fertigen Kerze """

    open: int
    high: int
    average: int
    low: int
    close: int
    volume: int
    price_volume: int
    histo: List[int]

    def volume_at_price(self, price: int) -> int:
        if price < self.low or price > self.high:
            return 0
        return self.histo[price - self.low]


    def _eval_histo(base: int, histo: List[int]) -> (int, int):
        volume = 0
        price_volume = 0
        for i in range(0, len(histo)):
            v = histo[i]
            volume += v
            price_volume = (base + i) * v
        return volume, price_volume


    def _histo_value(low: int, histo: List[int], i) -> int:
        return 0 if (i < low) or i > (low + len(histo) - 1) else histo[i - low]

            
    def _combine_histo(low1: int, histo1: List[int], low2: int, histo2: int) -> (int, List[int]):
        """ combines to histogram into a single """
        low = min(low1, low2)
        high = max(low1 + len(histo1), low2 + len(histo2))
        histo = []
        for i in range(low, high):
            value = Bar._histo_value(low1, histo1, i) + Bar._histo_value(low2, histo2, i)
            histo.append(value)
        return low, histo

    
    def __init__(self, obj):
        """ construct a new bar from another bar or a sample """
        if isinstance(obj, Sample):
            volume, price_volume = Bar._eval_histo(obj.low, obj.histo)
            super().__init__(
                open = obj.open,
                high = obj.high,
                average = round(price_volume / volume),
                volume = volume,
                price_volume = price_volume,
                low = obj.low,
                close = obj.close,
                histo = obj.histo, # no copy needed, because histo of sample will never be changed.
            )
        elif isinstance(obj, Bar):
            super().__init__(
                open = obj.open,
                high = obj.high,
                average = obj.average,
                volume = obj.volume,
                price_volume = obj.price_volume,
                low = obj.low,
                close = obj.close,
                histo = obj.histo.copy() # copy needed, because histo changes when other object are merged
            )
        else:
            raise TypeError('Sample or Bar expected')

    def to_dict(self) -> Dict:
        return {
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'histo': self.histo,
        }
    
    def merge(self, other):
        if isinstance(other, Sample):
            other = Bar(other)
        if isinstance(other, Bar):
            self.high = max(self.high, other.high)
            self.volume += other.volume
            self.price_volume += other.price_volume
            self.average = round(self.price_volume / self.volume)
            self.close = other.close
            self.low, self.histo = Bar._combine_histo(self.low, self.histo, other.low, other.histo)
        else:
            return NotImplemented

        
    def __add__(self, other):
        return Bar(self).merge(other)


    def __iadd__(self, other):
        self.merge(other)



class BarListener(Protocol):
    """Schnittstelle für Observer, die auf fertige Volumenbalken reagieren."""
    def on_new_bar(self, bar: Bar) -> None:
        """Wird aufgerufen, sobald ein neuer Volumenbalken fertiggestellt wurde."""
        ...

    def on_end_of_bars(self) -> None:
        """Wird aufgerufen, wenn der Handelstag zu ende ist"""
        ...


class BarBuilder:
    """ Empfängt Samples und konstruiert daraus Bars. """
    
    def __init__(self, bar_size: int):
        self.BAR_SIZE = bar_size 
        self.bars: List[Bar] = []
        self._current_bar: Bar = None
        self._current_size = 0
        self._bar_listeners: List[BarListener] = []


    def add_listener(self, listener: BarListener):
        """Registriert einen Trader/Bot für die fertigen Balken."""
        if listener not in self._bar_listeners:
            self._bar_listeners.append(listener)


    def remove_listener(self, listener: BarListener):
        """Entfernt einen registrierten Bar-Listener."""
        if listener in self._bar_listeners:
            self._bar_listeners.remove(listener)


    def _notify_new_bar(self, bar: Bar):
        for listener in self._bar_listeners:
            listener.on_new_bar(bar)


    def _notify_end_of_bars(self):
        for listener in self._bar_listeners:
            listener.on_end_of_bars()


    def _commit_current_bar(self):
        """Erstellt den finalen Balken, validiert ihn und benachrichtigt Observer."""
        new_bar = self._current_bar
        self.bars.append(new_bar)
        self._current_bar = None
        self._current_size = 0
        self._notify_new_bar(new_bar)


    def on_new_sample(self, sample: Sample) -> None:
        """Verarbeitet einen neues sample und entscheidet, ob ein Balken fertig ist."""

        if self._current_bar:
            self._current_bar.merge(sample)
        else:
            self._current_bar = Bar(sample)

        self._current_size += 1
        if self._current_size >= self.BAR_SIZE:
            self._commit_current_bar()


    def on_end_of_samples(self) -> None:
        """ Sichert, dass der letzte angefangene Balken beim Stream-Ende verschickt wird """
        if self._current_bar:
            self._commit_current_bar()


    # --- Container-Protokoll (Klasse verhält sich wie eine Python-Liste) ---
    def __len__(self) -> int:
        return len(self.bars)

    def __getitem__(self, index: int) -> Bar:
        return self.bars[index]

    def __iter__(self) -> Iterator[Bar]:
        return iter(self.bars)


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="creates samples or bar out of sample or databento files.")
    parser.add_argument("filename", help="name of file with samples (.csv) or databento trade records (.dbn)")
    parser.add_argument('-s', '--start', type=int, default=0, help='start offest (seconds) from where to begin')
    parser.add_argument('-d', '--duration', type=int, default=24*60*60, help='duration (seconds)')
    parser.add_argument('-b', '--barsize', type=int, help='size of the bars to be create. if no bar size is specified, no bars will be create. Output are the samples.')
    parser.add_argument('-o', '--outfile', type=str, help="name of file for the output. no output file means stdout")
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

    if filepath.suffix == '.csv':
        # we generate bars from samples stored in file
        if bar_builder is None:
            print(f'{parser.prog}: barsize must be specified when .csv file is given as input', file=sys.stderr)
            exit(1)
        loader = SampleLoader()
        loader.add_listener(bar_builder)
        loader.load_and_stream(args.filename)
        result = pd.DataFrame([bar.to_dict() for bar in bar_builder])

    elif filepath.suffix == '.dbn':
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
        exit(1)

    if args.outfile is None:
        print(result.to_csv(index=False))
    else:    
        result.to_csv(args.outfile, index=False)
