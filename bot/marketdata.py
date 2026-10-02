"""
Modul: MarketData
Verantwortlich für die Verarbeitung, Kapselung und den Aufbau von 
Marktdatenstrukturen (Volumenbalken, Histogramme) aus einem Tick-Datenstrom.
"""

import csv
import time
import random
import numpy as np
from pydantic import BaseModel, Field
from typing import List, Dict, Iterator, Tuple, Protocol

# =====================================================================
# 1. PYDANTIC MODELLE (Datenkapselung & API-Bereitschaft)
# =====================================================================

class Tick(BaseModel):
    """Kapselt die Daten eines einzelnen Ticks mit Pydantic-Validierung."""
    timestamp_ms: int = Field(..., description="Zeitpunkt des Ticks in Millisekunden seit 1970")
    price: float = Field(..., gt=0, description="Preis des Futures")
    ask_volume: int = Field(..., ge=0, description="Ask-Volumen")
    bid_volume: int = Field(..., ge=0, description="Bid-Volumen")


class VolumeBar(BaseModel):
    """Kapselt die Daten eines fertigen Volumenbalkens (OHLC) inkl. VWAP."""
    start_time: int = Field(..., description="Startzeit des Balkens in Millisekunden")
    end_time: int = Field(..., description="Endzeit des Balkens in Millisekunden")
    open: float = Field(..., description="Eröffnungspreis des Intervalls")
    high: float = Field(..., description="Höchstpreis im Intervalls")
    low: float = Field(..., description="Tiefstpreis im Intervalls")
    close: float = Field(..., description="Schlusskurs des Intervalls")
    volume: int = Field(..., description="Kumuliertes Gesamtvolumen des Balkens")
    vwap: float = Field(..., description="Volumengewichteter Durchschnittspreis (VWAP)")


# =====================================================================
# 2. PROTOKOLLE (Schnittstellen für das Observer-Pattern)
# =====================================================================

class BarListener(Protocol):
    """Schnittstelle für Observer, die auf fertige Volumenbalken reagieren."""
    def on_new_bar(self, bar: VolumeBar, index: int, sender: Sequence[VolumeBar]) -> None:
        """Wird aufgerufen, sobald ein neuer Volumenbalken fertiggestellt wurde."""
        ...


class TickListener(Protocol):
    """Schnittstelle für Observer, die auf den eingehenden Tick-Stream reagieren."""
    def on_new_tick(self, tick: Tick) -> None:
        """Wird bei jedem neuen eintreffenden Tick aufgerufen."""
        ...
        
    def on_ticks_completed(self) -> None:
        """Wird aufgerufen, wenn der Datenstrom beendet ist (z.B. Dateiende oder Session-Ende)."""
        ...


# =====================================================================
# 3. TICK PROVIDER (Publisher für den Datenstrom)
# =====================================================================

class TickProvider:
    """
    Fungiert als Quelle für Tick-Daten (z.B. CSV-Streamer oder Tradovate-API).
    Verteilt Ticks ereignisgesteuert an alle registrierten TickListener.
    """
    def __init__(self):
        self._listeners: List[TickListener] = []

    def add_listener(self, listener: TickListener):
        """Registriert einen neuen Empfänger für Ticks."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: TickListener):
        """Entfernt einen registrierten Empfänger."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_new_tick(self, tick: Tick):
        for listener in self._listeners:
            listener.on_new_tick(tick)
    
    def _notify_ticks_completed(self):
        for listener in self._listeners:
            listener.on_ticks_completed()

    def stream_from_csv(self, filename: str):
        """Liest eine CSV-Datei zeilenweise und streamt sie als validierte Ticks."""
        print(f"[TickProvider] Starte Streaming aus '{filename}'...")
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    tick = Tick(
                        timestamp_ms=int(row['timestamp_ms']),
                        price=float(row['price']),
                        ask_volume=int(row['ask_volume']),
                        bid_volume=int(row['bid_volume'])
                    )
                    self._notify_new_tick(tick)
                except Exception as e:
                    print(f"[TickProvider] Fehler bei Zeilen-Parsing {row}: {e}")
        
        # Stream-Abschluss signalisieren
        print("[TickProvider] Streaming beendet. Sende Abschluss-Signal an alle Listener.")
        self._notify_ticks_completed()


# =====================================================================
# 4. PRICE HISTOGRAM (Eigenständiger Tick-Listener)
# =====================================================================

class PriceHistogram:
    """
    Ein performanter, NumPy-basierter Listener, der ein Preishistogramm aufbaut.
    Optimiert für diskrete 0.25-Schritte des NASDAQ (MNQ) Futures.
    """
    def __init__(self, array_size: int = 8000, price_increment: float = 0.25):
        self._array = np.zeros(array_size, dtype=np.int64)
        self._price_increment = price_increment
        self._price_to_int_factor = 1 / price_increment
        self._size = array_size
        self._center_index = array_size // 2
        
        self._offset_price_int = None
        self._min_index: int | None = None
        self._max_index: int | None = None

    def _price_to_index(self, price: float) -> int:
        """Rechnet einen Float-Preis in einen eindeutigen Array-Index um."""
        if self._offset_price_int is None:
            # Der allererste eintreffende Preis definiert die Mitte des Arrays
            self._offset_price_int = int(price * self._price_to_int_factor)
        
        price_int = int(price * self._price_to_int_factor)
        return self._center_index + (price_int - self._offset_price_int)

    def _index_to_price(self, index: int) -> float:
        """Rechnet einen Array-Index zurück in den realen Float-Preis."""
        if self._offset_price_int is None:
            raise RuntimeError("Histogramm enthält noch keine Daten.")
        price_int = (index - self._center_index) + self._offset_price_int
        return price_int * self._price_increment

    # --- TickListener-Schnittstelle ---
    def on_new_tick(self, tick: Tick) -> None:
        """Verarbeitet eingehende Ticks und aktualisiert das Histogramm."""
        tick_volume = tick.ask_volume + tick.bid_volume
        if tick_volume == 0:
            return
            
        index = self._price_to_index(tick.price)
        
        if 0 <= index < self._size:
            self._array[index] += tick_volume
            
            # Verfolgung des genutzten Preisbereichs
            if self._min_index is None:
                self._min_index = self._max_index = index
            else:
                self._min_index = min(self._min_index, index)
                self._max_index = max(self._max_index, index)
        else:
            # Out of Bounds Schutz (z.B. bei extremen Markt-Sprüngen außerhalb von 8000 Ticks)
            pass

    def on_ticks_completed(self) -> None:
        print("[PriceHistogram] Datenstrom abgeschlossen. Histogramm ist fertig.")

    # --- Schnelle Iteration und Export ---
    def __iter__(self) -> Iterator[Tuple[float, int]]:
        """Iteriert hocheffizient nur über den belegten Preisbereich."""
        if self._min_index is None:
            return
        for index in range(self._min_index, self._max_index + 1):
            volume = self._array[index]
            if volume > 0:
                yield self._index_to_price(index), volume

    def get_histogram(self) -> Dict[float, int]:
        """Gibt das Histogramm als klassisches Python-Dictionary zurück."""
        return {price: volume for price, volume in self}


# =====================================================================
# 5. VOLUME BAR BUILDER (Tick-Listener & Bar-Publisher)
# =====================================================================

class VolumeBarBuilder:
    """
    Empfängt Ticks und konstruiert daraus Volumenbalken (OHLC + VWAP).
    Verhält sich wie eine schreibgeschützte Liste für fertige Balken.
    Benachrichtigt registrierte BarListener in Echtzeit.
    """
    def __init__(self, volume_per_bar: int):
        if volume_per_bar <= 0:
            raise ValueError("volume_per_bar muss größer als 0 sein.")
            
        self.volume_per_bar = volume_per_bar
        self.volume_bars: List[VolumeBar] = []
        
        self._current_bar_data: Dict = {}
        self._bar_listeners: List[BarListener] = []
        self._reset_current_bar()

    def add_bar_listener(self, listener: BarListener):
        """Registriert einen Trader/Bot für die fertigen Balken."""
        if listener not in self._bar_listeners:
            self._bar_listeners.append(listener)

    def remove_bar_listener(self, listener: BarListener):
        """Entfernt einen registrierten Bar-Listener."""
        if listener in self._bar_listeners:
            self._bar_listeners.remove(listener)

    def _notify_bar_listeners(self, bar: VolumeBar, index: int):
        for listener in self._bar_listeners:
            listener.on_new_bar(bar, index, self)

    def _reset_current_bar(self):
        """Setzt den Konstruktionspuffer für den nächsten Balken zurück."""
        self._current_bar_data = {}

    def _commit_current_bar(self):
        """Erstellt den finalen Balken, validiert ihn und benachrichtigt Observer."""
        if not self._current_bar_data or self._current_bar_data.get('volume', 0) == 0:
            return

        bar_volume = self._current_bar_data['volume']
        vwap = self._current_bar_data['price_volume_sum'] / bar_volume
        
        # Erstelle valides VolumeBar-Modell
        payload = self._current_bar_data.copy()
        payload['vwap'] = vwap
        del payload['price_volume_sum']  # Hilfsfeld entfernen
        
        new_bar = VolumeBar(**payload)
        self.volume_bars.append(new_bar)
        
        # Listener in Echtzeit triggern
        new_bar_index = len(self.volume_bars) - 1
        self._notify_bar_listeners(new_bar, new_bar_index)
        
        self._reset_current_bar()

    # --- TickListener-Schnittstelle ---
    def on_new_tick(self, tick: Tick) -> None:
        """Verarbeitet einen neuen Tick und entscheidet, ob ein Balken fertig ist."""
        tick_volume = tick.ask_volume + tick.bid_volume
        if tick_volume == 0:
            return

        # Wenn neuer Balken gestartet wird
        if not self._current_bar_data:
            self._current_bar_data = {
                'start_time': tick.timestamp_ms,
                'end_time': tick.timestamp_ms,
                'open': tick.price,
                'high': tick.price,
                'low': tick.price,
                'close': tick.price,
                'volume': 0,
                'price_volume_sum': 0.0
            }

        # Akkumulieren
        self._current_bar_data.update({
            'volume': self._current_bar_data['volume'] + tick_volume,
            'price_volume_sum': self._current_bar_data['price_volume_sum'] + (tick.price * tick_volume),
            'high': max(self._current_bar_data['high'], tick.price),
            'low': min(self._current_bar_data['low'], tick.price),
            'close': tick.price,
            'end_time': tick.timestamp_ms
        })

        # Schwellenwert-Prüfung
        if self._current_bar_data['volume'] >= self.volume_per_bar:
            self._commit_current_bar()

    def on_ticks_completed(self) -> None:
        """Sichert, dass der letzte angefangene Balken beim Stream-Ende gebaut wird."""
        print("[VolumeBarBuilder] Datenstrom-Ende signalisiert. Schließe letzten Balken ab.")
        self._commit_current_bar()

    # --- Container-Protokoll (Klasse verhält sich wie eine Python-Liste) ---
    def __len__(self) -> int:
        return len(self.volume_bars)

    def __getitem__(self, index: int) -> VolumeBar:
        return self.volume_bars[index]

    def __iter__(self) -> Iterator[VolumeBar]:
        return iter(self.volume_bars)


# Ein einfacher Beispiel-Trader
class Trader:
    def on_new_bar(self, bar: VolumeBar, index: int):
        print(f"Balken #{index} gebaut! Close: {bar.close} | VWAP: {bar.vwap:.2f}")

if __name__ == "__main__":
    # --- CLI-ARGUMENTE ---
    import argparse

    parser = argparse.ArgumentParser(description="Tradovate API - Automatischer MNQ Tages-Tick-Downloader")
    parser.add_argument("--filename", help="CSV with tick data")
    args = parser.parse_args()

    # Setup
    tick_provider = TickProvider()
    bar_builder = VolumeBarBuilder(volume_per_bar=1000)
    histogram = PriceHistogram()
    trader = Trader()

    # Registrierungen (Wer lauscht auf wen?)
    tick_provider.add_listener(bar_builder)  # Baut die Kerzen
    tick_provider.add_listener(histogram)    # Baut das High-Speed-Histogramm

    bar_builder.add_bar_listener(trader)     # Trader reagiert auf fertige Balken

    # Starten
    tick_provider.stream_from_csv("deine_tick_daten.csv")
