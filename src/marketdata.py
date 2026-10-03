"""
Modul: MarketData
Verantwortlich für die Verarbeitung, Kapselung und den Aufbau von 
Marktdatenstrukturen (Volumenbalken, Histogramme) aus einem Tick-Datenstrom.
"""

import csv
import numpy as np
import pandas as pd
import pydantic
from typing import List, Dict, Iterator, Tuple, Protocol

# =====================================================================
# 1. PYDANTIC MODELLE (Datenkapselung & API-Bereitschaft)
# =====================================================================

class Tick(pydantic.BaseModel):
    """Kapselt die Daten eines einzelnen Ticks mit Pydantic-Validierung."""

    timestamp: int
    price: float
    ask_volume: int
    bid_volume: int


class VolumeBar(pydantic.BaseModel):
    """Kapselt die Daten eines fertigen Volumenbalkens"""

    start_time: int
    end_time: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    average: float


class Trade(pydantic.BaseModel):
    """Kapselt die Daten eines abgeschlossenen Trades"""

    buy_time: int
    buy_price: float
    sell_time: int
    sell_price: float
    volume: int


class Statistics(pydantic.BaseModel):
    """Statistic data of a trading day"""

    total_profit: float
    number_of_trades: int
    win_rate: float
    profit_factor: float
    max_profit: float
    min_profit: float


# =====================================================================
# 2. PROTOKOLLE (Schnittstellen für das Observer-Pattern)
# =====================================================================

class BarListener(Protocol):
    """Schnittstelle für Observer, die auf fertige Volumenbalken reagieren."""
    def on_new_bar(self, bar: VolumeBar) -> None:
        """Wird aufgerufen, sobald ein neuer Volumenbalken fertiggestellt wurde."""
        ...

    def on_end_of_day() -> None:
        """Wird aufgerufen, wenn der Handelstag zu ende ist"""
        ...


class TickListener(Protocol):
    """Schnittstelle für Observer, die auf den eingehenden Tick-Stream reagieren."""
    def on_new_tick(self, tick: Tick) -> None:
        """Wird bei jedem neuen eintreffenden Tick aufgerufen."""
        ...
        
    def on_ticks_completed(self) -> None:
        """Wird aufgerufen, wenn der Datenstrom beendet ist (z.B. Dateiende oder Session-Ende)."""
        ...

class TraderListener(Protocol):
    """Schnittstelle für Trade Listener"""
    def on_trade_closed(self, trade: Trade) -> None:
        """Wird bei einem abgeschlossenen Trade aufgerufen"""
        ...

class TradeStatisticsListener(Protocol):
    def on_day_closed(self, statistics: Statistics):
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
            listener.on_new_bar(bar)

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



class TradeStatistics:
    """Collects trades as a trade listener and calculates statistics on these trades"""

    def __init__(self, filter_constant: float = 0.5):

        self.trades_schema = {
            'buy_time': 'int',
            'buy_price': 'float',
            'sell_time': 'int',
            'sell_price': 'float',
            'volume': int,
            'profit': 'float',
            'duration': 'int'
        }
        self.trades: pd.DataFrame = pd.DataFrame(columns=self.trades_schema.keys())
        self.trades = self.trades.astype(self.trades_schema)
        self._listeners: List[TradeStatisticsListener] = []

    def add_listener(self, listener: TradeStatisticsListener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: TradeStatisticsListener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_day_closed(self, stats: Statistics):
        for listener in self._listeners:
            listener.on_day_closed(stats)
    
    def on_trade_closed(self, closed_trade: Trade) -> None:
        trade = {
            'buy_time': closed_trade.buy_time,
            'buy_price': closed_trade.buy_price,
            'sell_time': closed_trade.sell_time,
            'sell_price': closed_trade.sell_price,
            'volume': closed_trade.volume,
            'profit': (closed_trade.sell_price - closed_trade.buy_price) * closed_trade.volume,
            'duration': abs(closed_trade.buy_time - closed_trade.sell_time)
        }
        new_frame = pd.DataFrame([trade], columns=self.trades_schema.keys()).astype(self.trades_schema)
        self.trades = pd.concat([self.trades, new_frame], ignore_index=True)

    def on_day_closed(self):
        self._notify_day_closed(self.get_statistics())

    @property
    def _win_trades(self):
        return self.trades[self.trades["profit"] > 0.0]

    @property
    def _loss_trades(self):
        return self.trades[self.trades['profit'] <= 0.0]

    @property
    def number_of_trades(self) -> int:
        return len(self.trades)
    
    @property
    def total_profit(self) -> float:
        return self.trades['profit'].sum()

    @property
    def max_profit(self) -> float:
        return self.trades['profit'].max()

    @property
    def min_profit(self) -> float:
        return self.trades['profit'].min()

    @property
    def win_profit(self) -> float:
        return self._win_trades['profit'].sum()
    
    @property
    def loss_profit(self) -> float:
        return self._loss_trades['profit'].sum()
    
    @property
    def win_rate(self) -> float:
        n_wins = len(self._win_trades)
        n_loss = len(self._loss_trades)
        n_total = n_wins + n_loss
        return (n_wins / n_total) if n_total > 0 else 0.0

    @property
    def profit_factor(self) -> float:
        loss_profit = -self.loss_profit
        return self.win_profit / loss_profit if loss_profit != 0.0 else 0.0 

    def get_statistics(self) -> Statistics:
        return Statistics(
            total_profit = self.total_profit,
            number_of_trades = self.number_of_trades,
            win_rate = self.win_rate,
            profit_factor = self.profit_factor,
            max_profit = self.max_profit,
            min_profit = self.min_profit
        )

    def to_csv(filename: str) -> None:
        pass


# Ein einfacher Beispiel-Trader
class KentBeckTrader:
    """ Der einfachste aller Trader, der möglicherweise Gewinn machen könnte """

    def __init__(self, filter_constant: float = 0.5):
        self._filter_constant: float = filter_constant
        self._state = 'flat'
        self._stop_loss: float = 0.0
        self._current_trade = {}

        self.analytics_schema = {
            'time': 'int',
            'average': 'float',
            'slope': 'float',
            'decision': 'str',
        }
        self.analytics_data: pd.DataFrame = pd.DataFrame(columns=self.analytics_schema.keys())
        self.analytics_data = self.analytics_data.astype(self.analytics_schema)
        self._listeners: List[TradeListener] = []


    def add_listener(self, listener: TraderListener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: TraderListener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_trade_closed(self, trade: Trade):
        for listener in self._listeners:
            listener.on_trade_closed(trade)

    def _notify_day_closed(self):
        for listener in self._listeners:
            listener.on_day_closed()

    def analyse(self, bar: VolumeBar) -> Dict:
        analytics = {}
        if self.analytics_data.empty:
            analytics = {
                'time': bar.start_time,
                'average': bar.average,
                'slope': 0.0,
                'decision': 'none' 
            }
        else:
            last = self.analytics_data.iloc[-1]
            current_slope = (bar.average - last['average']) * self._filter_constant
            average = last['average'] + current_slope
            new_slope = last['slope'] + (current_slope - last['slope']) * self._filter_constant
            decision = 'none'
            if (new_slope * last['slope']) < 0.0:
                if new_slope > 0.0:
                    decision = 'buy'
                if new_slope < 0.0:
                    decision = 'sell'
            
            analytics = {
                'time': bar.start_time,
                'average': average,
                'slope': new_slope,
                'decision': decision,
            }
        return analytics

    def trade(self, analytics: Dict, bar: VolumeBar):
        # now we have the analytics, we can make a trade decision based on the slope and the current state
        if self._state == 'flat':
            # we are flat, so we can enter a trade if the decision is buy or sell
            if analytics['decision'] == 'buy':
                self._state = 'buy' # we place a buy order
                self._stop_loss = bar.low
            if analytics['decision'] == 'sell':
                self._state = 'sell' # we place a sell order
                self._stop_loss = bar.high

        if self._state == 'buy':
            # we are in a buy position
            # we assume, that our order was fulfilled one tick over the opening price
            self._current_trade['buy_time'] = bar.start_time
            self._current_trade['buy_price'] = bar.open + 0.25
            self._stop_loss = bar.low
            self._state = 'long'

        if self._state == 'long':
            # we are long. so we have to check, if we ran into our stop loss
            # print(f".   stop_loss: {self._stop_loss} | low: {bar.low}")
            if self._stop_loss > bar.low:
                # we assume, that we were stopped out one tick below our stop loss
                self._current_trade['sell_price'] = self._stop_loss - 0.25
                self._current_trade['sell_time'] = bar.start_time
                self._state = 'flat'
                self._close_current_trade()
            else:
                # we are still going, so adapt stop loss...
                self._stop_loss = bar.low

        if self._state == 'sell':
            # we place a sell order and assume that we could sell is one tick less than the opening price
            self._current_trade['sell_time'] = bar.start_time
            self._current_trade['sell_price'] = bar.open - 0.25
            self._stop_loss = bar.high
            self._state = 'short'

        if self._state == 'short':
            # we are short, so we have to check, if we ran into out stop loss
            if self._stop_loss < bar.high:
                # we assume that we were stopped out one tick over our stop loss
                self._current_trade['buy_time'] = bar.start_time
                self._current_trade['buy_price'] = self._stop_loss + 0.25
                self._state = 'flat'
                self._close_current_trade()
            else:
                # trade is still active. we adjust stop loss...
                self._stop_loss = bar.high


    def _close_current_trade(self):
        self._current_trade['volume'] = 1
        trade = Trade.model_validate(self._current_trade)
        self._notify_trade_closed(trade)
        self._current_trade = {}


    def on_new_bar(self, bar: VolumeBar) -> None:
        analytics = self.analyse(bar)
        self.analytics_data = pd.concat([self.analytics_data, pd.DataFrame([analytics])], ignore_index=True)
        self.trade(analytics, bar)

    def on_end_of_day(self) -> None:
        self._stat = 'flat'
        self._current_trade = {}
        self._notify_day_closed()


class BarLoader:
    """Liest die CSV-Datei chronologisch ein und verteilt die Zeilen als Events."""

    _bar_listeners = []

    def __init__(self):
        self._listeners = []

    def add_bar_listener(self, listener: BarListener):
        """Registriert einen Trader/Bot für die fertigen Balken."""
        if listener not in self._bar_listeners:
            self._bar_listeners.append(listener)

    def remove_bar_listener(self, listener: BarListener):
        """Entfernt einen registrierten Bar-Listener."""
        if listener in self._bar_listeners:
            self._bar_listeners.remove(listener)

    def _notify_new_bar(self, bar: VolumeBar):
        for listener in self._bar_listeners:
            listener.on_new_bar(bar)

    def _notify_end_of_day(self):
        for listener in self._bar_listeners:
            listener.on_end_of_day()

    def load_and_stream(self, csv_path):
        """Öffnet die CSV-Datei und streamt sie Zeile für Zeile an die Listener."""        
        with open(csv_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                bar = VolumeBar(
                    start_time=int(row['Timestamp']),
                    end_time=int(row['Timestamp']),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    average=float(row['Average']),
                    volume=int(row['Volume'])
                )
                self._notify_new_bar(bar)
            self._notify_end_of_day()


if __name__ == "__main__":
    # --- CLI-ARGUMENTE ---
    import argparse

    parser = argparse.ArgumentParser(description="Trade simulator: Lädt Volumenbalken aus einer CSV-Datei und simuliert Echtzeit-Events.")
    parser.add_argument("--filename", help="CSV with volume bars")
    args = parser.parse_args()

    # Setup
    trade_statistics = TradeStatistics()
    trader = KentBeckTrader(filter_constant=0.5)
    trader.add_listener(trade_statistics)
    loader = BarLoader()
    loader.add_bar_listener(trader)     # Trader reagiert auf fertige Balken
    loader.load_and_stream(args.filename)

    stats = trade_statistics.get_statistics()
    print(f"Trades: {stats.number_of_trades}, total profit: {stats.total_profit}, win_rate: {stats.win_rate*100:.2f}%, profit factor: {stats.profit_factor:.2f}, max win: {stats.max_profit:.2f}, max loss: {stats.min_profit:.2f}")
