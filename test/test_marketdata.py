import unittest
from unittest.mock import Mock

# Importieren der Klassen aus Ihrem MarketData-Modul
# Angenommen, der vorherige Code wurde als 'marketdata.py' gespeichert
from marketdata import (
    Tick,
    VolumeBar,
    PriceHistogram,
    VolumeBarBuilder,
    TickProvider,
    BarListener,
    TickListener
)

class TestPriceHistogram(unittest.TestCase):
    """Testet die PriceHistogram-Klasse isoliert."""

    def setUp(self):
        """Wird vor jedem Test aufgerufen."""
        self.histogram = PriceHistogram(price_increment=0.25)

    def test_initialization(self):
        """Stellt sicher, dass das Histogramm leer initialisiert wird."""
        self.assertEqual(len(self.histogram.get_histogram_dict()), 0)

    def test_on_new_tick(self):
        """Testet das Hinzufügen von Ticks über die Listener-Schnittstelle."""
        self.histogram.on_new_tick(Tick(timestamp_ms=1, price=100.25, ask_volume=5, bid_volume=5))
        self.assertEqual(self.histogram.get_histogram_dict().get(100.25), 10)

    def test_volume_aggregation(self):
        """Stellt sicher, dass Volumen für denselben Preis korrekt summiert wird."""
        self.histogram.on_new_tick(Tick(timestamp_ms=1, price=100.50, ask_volume=10, bid_volume=0))
        self.histogram.on_new_tick(Tick(timestamp_ms=2, price=100.50, ask_volume=3, bid_volume=4))
        self.assertEqual(self.histogram.get_histogram_dict().get(100.50), 17)

    def test_multiple_price_levels(self):
        """Testet das Hinzufügen von Ticks zu unterschiedlichen Preisen."""
        self.histogram.on_new_tick(Tick(timestamp_ms=1, price=100.00, ask_volume=5, bid_volume=5))
        self.histogram.on_new_tick(Tick(timestamp_ms=2, price=100.25, ask_volume=8, bid_volume=0))
        histo_dict = self.histogram.get_histogram_dict()
        self.assertEqual(histo_dict.get(100.00), 10)
        self.assertEqual(histo_dict.get(100.25), 8)

    def test_ticks_completed_does_not_fail(self):
        """Stellt sicher, dass on_ticks_completed ohne Fehler durchläuft."""
        try:
            self.histogram.on_ticks_completed()
        except Exception as e:
            self.fail(f"on_ticks_completed() hat einen Fehler ausgelöst: {e}")

class TestVolumeBarBuilder(unittest.TestCase):
    """Testet die VolumeBarBuilder-Klasse isoliert."""

    def setUp(self):
        """Initialisiert einen Builder mit einem einfachen Schwellenwert."""
        self.builder = VolumeBarBuilder(volume_per_bar=100)

    def test_no_bar_creation_before_threshold(self):
        """Kein Balken sollte erstellt werden, bevor das Volumen erreicht ist."""
        self.builder.on_new_tick(Tick(timestamp_ms=1, price=100, ask_volume=40, bid_volume=50)) # Total 90
        self.assertEqual(len(self.builder), 0)

    def test_bar_creation_on_threshold(self):
        """Ein Balken sollte genau dann erstellt werden, wenn das Volumen erreicht ist."""
        self.builder.on_new_tick(Tick(timestamp_ms=1, price=100, ask_volume=50, bid_volume=50)) # Total 100
        self.assertEqual(len(self.builder), 1)

    def test_ohlc_and_vwap(self):
        """Überprüft die korrekten OHLC- und VWAP-Werte."""
        self.builder.on_new_tick(Tick(timestamp_ms=100, price=100, ask_volume=25, bid_volume=0)) # open=100
        self.builder.on_new_tick(Tick(timestamp_ms=101, price=105, ask_volume=25, bid_volume=0)) # high=105
        self.builder.on_new_tick(Tick(timestamp_ms=102, price=95,  ask_volume=25, bid_volume=0)) # low=95
        self.builder.on_new_tick(Tick(timestamp_ms=103, price=102, ask_volume=25, bid_volume=0)) # close=102, total vol=100
        
        self.assertEqual(len(self.builder), 1)
        bar = self.builder[0]
        
        self.assertEqual(bar.open, 100)
        self.assertEqual(bar.high, 105)
        self.assertEqual(bar.low, 95)
        self.assertEqual(bar.close, 102)
        self.assertEqual(bar.volume, 100)
        
        expected_vwap = (100*25 + 105*25 + 95*25 + 102*25) / 100
        self.assertAlmostEqual(bar.vwap, expected_vwap)

    def test_finalize_incomplete_bar(self):
        """Testet, ob 'on_ticks_completed' den letzten, unvollständigen Balken abschließt."""
        self.builder.on_new_tick(Tick(timestamp_ms=1, price=100, ask_volume=60, bid_volume=40)) # Bar 1
        self.builder.on_new_tick(Tick(timestamp_ms=2, price=101, ask_volume=30, bid_volume=30)) # Incomplete Bar 2
        
        self.assertEqual(len(self.builder), 1) # Bisher nur 1 voller Balken
        self.builder.on_ticks_completed() # Finalisieren
        self.assertEqual(len(self.builder), 2) # Jetzt 2 Balken
        
        last_bar = self.builder[-1]
        self.assertEqual(last_bar.volume, 60) # Volumen ist kleiner als der Schwellenwert
        self.assertEqual(last_bar.close, 101)


class TestObserverPattern(unittest.TestCase):
    """Testet das korrekte Zusammenspiel der Komponenten."""

    def test_tick_provider_notifies_listeners(self):
        """Stellt sicher, dass der TickProvider seine Listener aufruft."""
        tick_provider = TickProvider()
        
        # Erstelle Mock-Listener
        mock_listener1 = Mock(spec=TickListener)
        mock_listener2 = Mock(spec=TickListener)
        
        tick_provider.add_listener(mock_listener1)
        tick_provider.add_listener(mock_listener2)
        
        # Simulieren des CSV-Streamings durch manuelles Aufrufen
        test_tick = Tick(timestamp_ms=1, price=100, ask_volume=1, bid_volume=1)
        tick_provider._notify_new_tick(test_tick)
        tick_provider._notify_ticks_completed()
        
        # Überprüfen, ob die Methoden auf den Mocks aufgerufen wurden
        mock_listener1.on_new_tick.assert_called_once_with(test_tick)
        mock_listener2.on_new_tick.assert_called_once_with(test_tick)
        mock_listener1.on_ticks_completed.assert_called_once()
        mock_listener2.on_ticks_completed.assert_called_once()

    def test_bar_builder_notifies_listener(self):
        """Stellt sicher, dass der VolumeBarBuilder seine Listener korrekt benachrichtigt."""
        builder = VolumeBarBuilder(volume_per_bar=10)
        mock_bar_listener = Mock(spec=BarListener)
        
        builder.add_bar_listener(mock_bar_listener)
        
        # Einen Balken erstellen
        tick = Tick(timestamp_ms=1, price=100, ask_volume=5, bid_volume=5)
        builder.on_new_tick(tick)
        
        # Überprüfen, ob on_new_bar mit den richtigen Argumenten aufgerufen wurde
        self.assertEqual(mock_bar_listener.on_new_bar.call_count, 1)
        
        # Argumente des Aufrufs extrahieren
        call_args = mock_bar_listener.on_new_bar.call_args
        bar_arg = call_args.args[0]
        index_arg = call_args.args[1]
        sender_arg = call_args.args[2]

        self.assertIsInstance(bar_arg, VolumeBar)
        self.assertEqual(bar_arg.volume, 10)
        self.assertEqual(index_arg, 0)
        self.assertIs(sender_arg, builder)

if __name__ == '__main__':
    unittest.main(verbosity=2)

