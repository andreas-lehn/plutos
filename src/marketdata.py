"""
Modul: MarketData
Verantwortlich für die Verarbeitung, Kapselung und den Aufbau von 
Marktdatenstrukturen (Volumenbalken, Histogramme) aus einem Tick-Datenstrom.
"""

import csv
import pandas as pd
from pydantic import BaseModel
from typing import List, Dict, Iterator, Tuple, Protocol


class Sample(BaseModel):
    """ Kapselt die Daten eines Samples """

    timestamp: int
    low: int
    average: int
    high: int
    volume: int


class SampleListener(Protocol):

    def on_new_sample(self, sample: Sample) -> None:
        """ recieve a new sample """
        ...

    def on_end_of_samples(self):
        """ end of sample stream reached """
        ...


class SampleLoader:
    """ Liest die Samples aus einer CSV-Datei ein und verschickt sie an ihre Listener """

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
                    low=float(row['low']),
                    average=float(row['average']),
                    high=float(row['high']),
                    volume=int(row['volume'])
                )
                self._notify_new_sample(sample)
            self._notify_end_of_samples()


class Bar(BaseModel):
    """ Kapselt die Daten einer fertigen Kerze """

    timestamp: int
    open: int
    low: int
    average: int
    high: int
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
        vwap = self._current_bar_data['price_volume_sum'] // bar_volume
        
        # Erstelle valides Bar-Modell
        self._current_bar_data['average'] = vwap
        del self._current_bar_data['price_volume_sum']  # Hilfsfeld entfernen
        
        new_bar = Bar(**self._current_bar_data)
        self.bars.append(new_bar)
        self._notify_new_bar(new_bar)


    def _start_new_bar(self, timestamp: int, sample: Sample) -> None:
        self._current_bar_data = {
            'timestamp': timestamp,
            'open': sample.average,
            'high': sample.high,
            'low': sample.low,
            'close': sample.average,
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
            self._start_new_bar(self._current_bar_data['timestamp'] + 1, sample) # das kann schief gehen!
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
            'close': sample.average,
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

    parser = argparse.ArgumentParser(description="Lädt Samples aus einer CSV-Datei und simuliert Echtzeit-Events.")
    parser.add_argument("filename", help="filename with trade data as CSV")
    parser.add_argument('-s', '--size', default=30, help='size of bar in seconds')
    args = parser.parse_args()

    builder = BarBuilder(args.size)
    loader = SampleLoader()
    loader.add_listener(builder)
    loader.load_and_stream(args.filename)
    print(builder.bars_in_data_frame())
