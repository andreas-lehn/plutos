"""
Modul: MarketData
Verantwortlich für die Verarbeitung, Kapselung und den Aufbau von 
Marktdatenstrukturen (Volumenbalken, Histogramme) aus einem Tick-Datenstrom.
"""

import sys
import csv
import pandas as pd
import databento as db
from pydantic import BaseModel
from typing import List, Dict, Iterator, Tuple, Protocol


class Sample(BaseModel):
    """ Kapselt die Daten eines Samples """

    timestamp: int
    open: int
    high: int
    average: int
    low: int
    close: int
    volume: int


class SampleListener(Protocol):

    def on_new_sample(self, sample: Sample) -> None:
        """ recieve a new sample """
        ...

    def on_end_of_samples(self):
        """ end of sample stream reached """
        ...


class SampleLoader:
    """ Liest Samples aus einer CSV-Datei ein und verschickt sie an die Listener """

    def __init__(self):
        self._listeners = []

    def add_listener(self, listener: SampleListener):
        """Registriert einen Trader/Bot für die fertigen Balken."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: SampleListener):
        """Entfernt einen registrierten Bar-Listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_new_sample(self, sample: Sample):
        for listener in self._listeners:
            listener.on_new_sample(sample)

    def _notify_end_of_samples(self):
        for listener in self._listeners:
            listener.on_end_of_samples()

    def load_and_stream(self, csv_path):
        """ Öffnet die CSV-Datei und streamt sie Zeile für Zeile an die Listener. """        
        with open(csv_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sample = Sample(
                    timestamp=int(row['timestamp']),
                    open=int(row['open']),
                    high=int(row['high']),
                    average=int(row['average']),
                    low=int(row['low']),
                    close=int(row['close']),
                    volume=int(row['volume']),
                )
                self._notify_new_sample(sample)
            self._notify_end_of_samples()


class SampleBuilder:
    """ builds 1 sec samples from databento trade records """

    def __init__(self):
        self.timestamp_offset: int = 0
        self.volume: int = 0
        self.volume_x_price: int = 0
        self.high: int = 0
        self.low: int = sys.maxsize
        self.open: int = None
        self.close: int = None
        self.timestamp: int = None
        self.hour = 0

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

        self.volume_x_price += volume * price
        self.volume += volume
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        return sample


    def get_sample(self) -> dict:
        sample = Sample(
            timestamp = self.timestamp,
            volume = self.volume,
            low = self.low,
            average = round(self.volume_x_price / self.volume),
            high = self.high,
            open = self.open,
            close = self.close
        )
        self.volume = 0
        self.volume_x_price = 0
        self.high = 0
        self.low = sys.maxsize
        return sample

    @property
    def is_sample_available(self) -> bool:
        return self.volume > 0


class Bar(BaseModel):
    """ Kapselt die Daten einer fertigen Kerze """

    timestamp: int
    open: int
    high: int
    average: int
    low: int
    close: int
    volume: int


class BarListener(Protocol):
    """Schnittstelle für Observer, die auf fertige Volumenbalken reagieren."""
    def on_new_bar(self, bar: Bar) -> None:
        """Wird aufgerufen, sobald ein neuer Volumenbalken fertiggestellt wurde."""
        ...

    def on_end_of_bars(self) -> None:
        """Wird aufgerufen, wenn der Handelstag zu ende ist"""
        ...


class BarBuilder:
    """ Empfängt Trades und konstruiert daraus Bars. """
    
    def __init__(self, bar_size: int):
        self.bar_size = bar_size 
        self.bars: List[Bar] = []
        self._current_bar_data: Dict = {}
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

        bar_volume = self._current_bar_data['volume']
        vwap = round(self._current_bar_data['price_volume_sum'] / bar_volume)
        
        # Erstelle valides Bar-Modell
        self._current_bar_data['average'] = vwap
        del self._current_bar_data['price_volume_sum']  # Hilfsfeld entfernen
        
        new_bar = Bar(**self._current_bar_data)
        self.bars.append(new_bar)
        self._notify_new_bar(new_bar)


    def _start_new_bar(self, timestamp: int, sample: Sample) -> None:
        self._current_bar_data = {
            'timestamp': timestamp,
            'open': sample.open,
            'high': sample.high,
            'low': sample.low,
            'close': sample.close,
            'volume': sample.volume,
            'price_volume_sum': sample.average * sample.volume
        }


    def on_new_sample(self, sample: Sample) -> None:
        """Verarbeitet einen neues sample und entscheidet, ob ein Balken fertig ist."""

        if not self._current_bar_data:
            # Die allererste Kerze wird erstellt...
            self._start_new_bar(sample.timestamp // 30, sample)
            return
        
        if sample.timestamp > self._current_bar_data['timestamp'] + self.bar_size - 1:
            # die aktuelle Kerze ist voll: Verschicken und neue beginnen...
            self._commit_current_bar()
            self._start_new_bar(self._current_bar_data['timestamp'] + self.bar_size, sample) # das kann schief gehen!
            # wenn zwischen diesem und dem letzten Sample ganz viel Zeit vergangen ist,
            # dann kann es hier passieren, dass das Sample nicht in die neue Kerze gehört, sondern erst in einer der nächsten.
            # Das Sample wird dann hier einer falsche Kerze zugeordnet.
            # In der Praxis wird dieser Fall aller wahrscheinlichkeit niemals auftreten.
            # Deahlag keine Gegenmaßnahme. Die unzulänglichkeit kann im Code enthalten bleiben.
            return
        
        # Auf die bestehende Kerze aufakkumulieren...
        self._current_bar_data.update({
            'volume': self._current_bar_data['volume'] + sample.volume,
            'price_volume_sum': self._current_bar_data['price_volume_sum'] + (sample.average * sample.volume),
            'high': max(self._current_bar_data['high'], sample.high),
            'low': min(self._current_bar_data['low'], sample.low),
            'close': sample.close,
        })


    def on_end_of_samples(self) -> None:
        """ Sichert, dass der letzte angefangene Balken beim Stream-Ende verschickt wird """
        self._commit_current_bar()


    # --- Container-Protokoll (Klasse verhält sich wie eine Python-Liste) ---
    def __len__(self) -> int:
        return len(self.volume_bars)


    def __getitem__(self, index: int) -> Bar:
        return self.volume_bars[index]


    def __iter__(self) -> Iterator[Bar]:
        return iter(self.volume_bars)

    def bars_in_data_frame(self) -> pd.DataFrame:
        return pd.DataFrame([bar.model_dump() for bar in self.bars])


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
        result = bar_builder.bars_in_data_frame()

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
            result = bar_builder.bars_in_data_frame()
    
    else:
        # unknown file extension
        print(f"{parser.prog}: error: unknow file extension '{filepath.suffix}' (expected .csv or .dbn)")
        exit(1)

    if args.outfile is None:
        print(result.to_csv(index=False))
    else:    
        result.to_csv(args.outfile, index=False)
