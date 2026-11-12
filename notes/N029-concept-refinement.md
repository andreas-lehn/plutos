Konzeption eines Nasdaq-Future-Microtrend-Trading-Bots
======================================================

Zielsetzung und strategische Nische
---------------------------------------

Ziel ist ein Intraday-Trading-Bot für den Micro E-mini Nasdaq-100 Future (MNQ),
der kurzfristige gerichtete Bewegungen erkennt und an ihnen partizipiert.

Der Bot soll ausdrücklich **kein Hochfrequenzhandelssystem** sein.
Er versucht nicht, institutionelle Händler bei der Entstehung eines Moves auf Millisekundenebene zu schlagen.
Die angestrebte Nische liegt zeitlich dahinter:

 1. Institutioneller Orderflow verändert den Marktzustand.
 2. Eine Momentum-Ignition wird erkennbar.
 3. Der Bot prüft, ob noch genügend handelbare Bewegung verbleibt.
 4. Der Einstieg erfolgt vor späten, häufig rein chartorientierten Marktteilnehmern.

Der zunächst zu untersuchende Handelshorizont liegt ungefähr zwischen **30 und 120 Sekunden**.
Diese Spanne ist eine Arbeitshypothese und muss mit Walk-forward-Tests gegen Alternativen
wie 15, 30, 60, 120 und 300 Sekunden geprüft werden.


Marktdaten und Orderbuchtiefe
--------------------------------

### Ausgangspunkt: Databento MBP-1

Für die erste Version ist **MBP-1** ausreichend.
Damit lassen sich unter anderem folgende Informationen erzeugen:

 - Best Bid und Best Ask
 - Bid-/Ask-Größe am Top of Book
 - Anzahl der Orders am Best Bid und Best Ask
 - Spread und Midprice
 - Microprice
 - Trades und Trade-Aggressoren
 - Top-of-book Order Flow Imbalance
 - Veränderungen und Depletion am BBO
 - Event- und Trade-Intensität

### L3/MBO ist keine Voraussetzung

MBO/L3 wäre vor allem für folgende Features erforderlich:

 - Lebensdauer einzelner Orders
 - individuelle Cancels und Modifikationen
 - persistente gegenüber flüchtiger Liquidität
 - Queue-Dynamik und Queue-Position
 - vollständige Orderverfolgung über Order-IDs

Diese Informationen sind wahrscheinlich besonders für sehr kurze Prognosehorizonte relevant.
Für den geplanten Horizont von mehreren zehn Sekunden sollte MBP-1 tragfähig sein.


Zeitarchitektur
------------------

### Feste Sampling Rate von 12 Sekunden

Der Bot erzeugt **alle 12 Sekunden** genau ein Feature-Set und trifft nur zu diesen Zeitpunkten eine neue Entscheidung.
Die 12 Sekunden sind die **Entscheidungsfrequenz**,
nicht die Auflösung der Marktdaten und nicht die einzige Rückblicklänge der Features.

Vorteile:

 - deterministisches Laufzeitverhalten
 - klar abschätzbarer Rechenbedarf
 - reproduzierbare Trainings- und Live-Zeitpunkte
 - bewusste Distanz zum HFT-Bereich
 - höchstens fünf reguläre Entscheidungen pro Minute

### Eventgetriebene Verarbeitung im Hintergrund

Die eingehenden MBP-1-Events werden fortlaufend verarbeitet.
Rolling States und Ringbuffer werden inkrementell aktualisiert.
Beim 12-Sekunden-Tick wird daraus nur ein Snapshot gebildet.
Damit wird vermieden, bei jeder Entscheidung mehrere Minuten Rohdaten neu einzulesen.

### Multi-Horizon-Features

Jedes Feature-Set enthält Informationen über unterschiedliche Rückblickfenster.

| Zweck           | Beispielhorizonte |
|-----------------|-------------------|
| Microstructure  | 1 / 3 / 6 / 12s   |
| Flow-Persistenz | 12 / 24 / 48 s    |
| Momentum        | 6 / 12 / 24 / 60s |
| Volatilität     | 30 / 60 / 300 s   |
| Marktregime     | 5 / 15 / 30 min   |

Dadurch kann das Modell nicht nur einen aktuellen Zustand erkennen, sondern auch dessen Veränderung:

    OFI_3s   = +0.81
    OFI_12s  = +0.63
    OFI_48s  = +0.19

Dies deutet beispielsweise auf beschleunigenden positiven Orderflow hin.


Feature-Gruppen
----------------

### Preis und Momentum

 - Returns über 1, 3, 6, 12, 24 und 60 Sekunden
 - kurzfristige Ranges
 - Momentum-Geschwindigkeit und -Beschleunigung
 - Distanz zu kurzfristigen Hochs und Tiefs
 - MFE/MAE der bereits zurückliegenden Bewegung
 - Trendalter

### Microprice

    microprice_edge
    microprice_change_3s
    microprice_change_6s
    microprice_change_12s
    microprice_velocity
    microprice_acceleration

Der Microprice bildet die Asymmetrie der Größen am Best Bid und Best Ask ab
und kann eine kurzfristige Verschiebung des Gleichgewichtspreises anzeigen.


### Order Flow Imbalance

    ofi_1s
    ofi_3s
    ofi_6s
    ofi_12s
    ofi_24s
    ofi_48s
    ofi_velocity
    ofi_acceleration

Wichtig ist nicht nur das Niveau, sondern auch die Persistenz und Beschleunigung des Orderflows.

### Trade Flow

    aggressive_buy_volume
    aggressive_sell_volume
    trade_imbalance
    buy_trade_count
    sell_trade_count
    mean_buy_trade_size
    mean_sell_trade_size
    max_buy_trade_size
    max_sell_trade_size
    trade_intensity
    trade_intensity_acceleration

### Top-of-book-Liquidität

    bbo_imbalance
    bid_size_change
    ask_size_change
    bid_depletion
    ask_depletion
    bid_order_count
    ask_order_count
    average_bid_order_size
    average_ask_order_size
    spread

### Preisreaktion und Absorption

Wesentlich ist die Beziehung zwischen aggressivem Flow und tatsächlicher Preisbewegung.

Beispiele:

 - hoher Buy-Flow und starke Preisreaktion: Käufer bewegen den Markt
 - hoher Buy-Flow und geringe Preisreaktion: mögliche Ask-Absorption
 - steigender Preis bei sinkendem Buy-Impact: mögliche Erschöpfung

Mögliche Features:

    price_impact_per_buy_volume
    price_impact_per_sell_volume
    buy_absorption
    sell_absorption
    return_per_unit_ofi

### Aktivität und Regime

    events_per_second
    trades_per_second
    relative_volume
    realized_volatility_30s
    realized_volatility_5m
    spread_regime
    time_of_day
    time_since_us_open


Positions- und Stop-Management
-------------------------------

Der Stop wird **niemals aufgeweitet**.
Wenn der Trend wieder stärker wird, wird der bestehende Stop nicht zurückgesetzt.
Stattdessen wird er lediglich weniger aggressiv weiter nachgezogen.


### Trailing-Geschwindigkeit statt direkter Stop-Prognose

Das Continuation-Modell sollte nicht direkt einen Stoppreis vorhersagen.
Es liefert eine Fortsetzungswahrscheinlichkeit, aus der eine deterministische Risk Engine die Trailing-Aggressivität ableitet.

Beispiel:

| Continuation-Wahrscheinlichkeit | Verhalten |
|---:|---|
| sehr hoch | Stop kaum oder langsam nachziehen |
| hoch | langsam nachziehen |
| mittel | normal nachziehen |
| niedrig | aggressiv nachziehen |
| sehr niedrig | sehr aggressiv absichern |

Wenn die Continuation-Wahrscheinlichkeit wieder steigt, liegt der neue Candidate Stop möglicherweise weiter entfernt.
Durch die Max-Funktion bleibt der bereits angehobene Stop trotzdem unverändert.


### Kombination mit Marktstruktur

Ein sinnvoller Stop kann mehrere Komponenten kombinieren:

 - letzter relevanter Pullback
 - kurzfristiges Microstructure-Level
 - volatilitätsbasierter Candidate Stop
 - bereits bestehender Stop


### Glättung und Hysterese

Ein Gradient-Boosting-Output kann von Entscheidung zu Entscheidung schwanken.
Deshalb sollte die Trailing-Aggressivität nicht auf jedes einzelne Wahrscheinlichkeitsrauschen reagieren.

Mögliche Maßnahmen:

 - EWMA-Glättung der Continuation-Wahrscheinlichkeit
 - Verschlechterung muss zwei Decision Points anhalten
 - unterschiedliche Schwellen für Wechsel in aggressivere und weniger aggressive Modi
 - Mindestabstand zwischen zwei Stop-Anhebungen


Zentrale Hypothesen, die empirisch geprüft werden müssen
------------------------------------------------------------

 1. MBP-1 enthält für einen Horizont von 30 bis 120 Sekunden genügend Information.
 3. Eine 12-Sekunden-Entscheidungsraster bietet einen guten Kompromiss aus Reaktion, Noise und Rechenaufwand.
 4. Bullseye erkennt Ignition besser als ein reines Triple-Barrier-Label.
 5. Triple Barrier filtert zu späte oder wirtschaftlich ungünstige Entries.
 6. Continuation Entries können verpasste Ignitions teilweise kompensieren.
 7. Ein monotoner, probabilitätsgesteuerter Trailing Stop erhält lange Gewinner besser als ein binärer ML-Exit.
 8. Microstructure-Features liefern nach Gebühren, Spread und Slippage einen stabilen Out-of-Sample-Mehrwert.


Wichtigste Designregel
----------------------------

Das System trennt bewusst drei Fragen:

 1. **Ignition:** Entsteht gerade ein neuer Trend?
 2. **Tradeability:** Ist ein Einstieg vom aktuellen Preis aus noch attraktiv?
 3. **Continuation:** Wie aggressiv soll der bereits bestehende Stop weiter nachgezogen werden?

Diese Trennung ist der Kern des Ansatzes.
Sie ermöglicht, den Trendstart zu erkennen, verspätete Entries zu vermeiden,
verpasste Ignitions über Continuation Entries aufzufangen und Gewinne abzusichern,
ohne einen wiedererstarkenden Trend durch einen unnötigen Sofortausstieg abzuschneiden.
