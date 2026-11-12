Intraday-Microtrend-Strategie: Bullseye + Triple Barrier
==========================================================

Zielbild
-----------

Ziel ist ein automatisierter Intraday-Bot fuer MNQ, der kurzfristige Trends moeglichst frueh erkennt
und anschliessend moeglichst lange an einer tragfaehigen Bewegung partizipiert.

Der Ansatz ist bewusst kein HFT-System.
Entscheidungen werden in einem deterministischen Raster von **12 Sekunden** getroffen.

Die Kernidee besteht aus **zwei parallel laufenden ML-Modellen**,
die exakt denselben Feature-Vektor `X(t)` erhalten, aber unterschiedliche Targets lernen:

 1. **Bullseye-Modell:** Beginnt gerade ein neuer Trend?
 2. **Triple-Barrier-Modell:** Ist ein Long- oder Short-Einstieg jetzt wirtschaftlich attraktiv?

```text
              MBP-1 + Trades
                    |
                    v
           12-s Feature Engine
                    |
                  X(t)
                    |
          +---------+---------+
          |                   |
          v                   v
   Bullseye-Modell     Triple-Barrier-Modell
   Trendstart?          Trade attraktiv?
          |                   |
          +---------+---------+
                    |
                    v
              Decision Engine
                    |
             LONG / WAIT / SHORT
                    |
                    v
            Position Management
```

Daten- und Ausfuehrungsarchitektur
-----------------------------------

Die geplante Trennung lautet:

```text
Databento
CME / MNQ / MBP-1
        |
        v
  eigener Webservice
        |
        +--> Raw/Event Storage
        |
        +--> Feature Engine
        |       |
        |       v
        |   12-s Features
        |       |
        |       +--> Bullseye-Modell
        |       |
        |       +--> Triple-Barrier-Modell
        |               |
        +---------------+
                |
                v
          Decision Engine
                |
                v
          Tradovate API
                |
                v
            CME / MNQ
```

Damit sind **Market Data und Execution getrennt**.
Der Bot ist nicht vom Market-Data-Feed des Brokers abhaengig.


Gemeinsame Feature-Pipeline
------------------------------

Beide Modelle arbeiten auf **demselben Feature-Vektor**.

Beispielgruppen:

### Preis und Momentum

 - Returns ueber 12 s, 24 s, 60 s, 120 s usw.
 - Momentum
 - Preissteigung
 - Aenderung der Steigung / Acceleration
 - Abstand zu VWAP
 - Abstand zu lokalen Hochs/Tiefs

### Top-of-Book / MBP-1

 - Best Bid / Best Ask
 - Spread
 - Bid Size / Ask Size
 - Order-Book-Imbalance am Top of Book
 - Microprice und Abweichung zum Mid-Price
 - Quote-Aenderungsrate

### Trades / Orderflow

 - aggressives Kauf-/Verkaufsvolumen
 - Trade Imbalance
 - Trade Arrival Rate
 - Beschleunigung der Trade Rate
 - Volumen in mehreren Rolling Windows

### Volatilitaet und Regime

 - kurzfristige realisierte Volatilitaet
 - robuste Volatilitaet, z. B. MAD
 - Volatilitaetsaenderung
 - Tageszeit / Session-Kontext

Die Feature-Berechnung erfolgt alle 12 Sekunden,
kann aber beispielsweise Rolling Windows von 24 s bis mehreren Minuten verwenden.


Modell A: Bullseye
--------------------

Das Bullseye-Modell beantwortet:

> Beginnt an diesem Zeitpunkt ein neuer gerichteter Trend?

Es geht nicht darum zu erkennen, ob bereits ein Trend laeuft.

Das Modell ist ein 3-Klassen-Klassifikator:

```text
0 = kein Trendstart
1 = Start nach oben
2 = Start nach unten
```

`kein Trendstart` umfasst daher auch:

 - Seitwaertsphase
 - Rauschen
 - bereits laufenden Aufwaertstrend
 - bereits laufenden Abwaertstrend
 - Pullbacks
 - Trendende

Der entscheidende Unterschied lautet:

      kein Trend --> Aufwaertstrend  = START_UP
      kein Trend --> Abwaertstrend   = START_DOWN
      Aufwaertstrend --> Aufwaertstrend = NO_START


## Algorithmisches Bullseye-Labeling

Der Bullseye-Punkt wird **offline** aus Vergangenheit und Zukunft bestimmt.

Gesucht ist ein Knickpunkt:

```text
Vergangenheit                 Zukunft
keine klare Richtung          persistenter Trend

----------------------*--------------------/
                      ^
                   Bullseye
```

Beim Labeling darf die Zukunft verwendet werden.
Im Live-Betrieb sieht das trainierte Modell natuerlich nur Informationen bis `t`.

## Gewichteter 12-s-Preis

Fuer jedes 12-s-Sample wird ein repraesentativer gewichteter Preis berechnet.

Ein einfacher Kandidat ist VWAP.
Alternativ koennen zeitgewichteter Mid-Price oder Microprice untersucht werden.


## Trenddefinition

Ein Trend soll nicht durch perfekte Monotonie definiert werden.
Ein gesunder Trend darf kleine Pullbacks enthalten.
Fuer ein Fenster werden deshalb mindestens vier Groessen verwendet:

### Directionality

```text
D_up = Anzahl positiver Preisveraenderungen / Anzahl aller Veraenderungen
```

Beispiel:

```text
+ + - + + +

D_up = 5 / 6 = 0.83
```

Ein Ausgangswert zum Testen waere z. B.:

```text
D_up >= 0.70 bis 0.75
```

Fuer Short entsprechend `D_down`.

### Mindeststeigung

Auf die gewichteten Sample-Preise wird eine lineare oder robuste Regression angewendet.

```text
P(i) = a + b*i
```

Ein Aufwaertstrend benoetigt:

```text
b >= b_min
```

Ein Abwaertstrend:

```text
b <= -b_min
```

Die Mindeststeigung sollte vorzugsweise an die lokale Volatilitaet angepasst werden.

### Path Efficiency

      Efficiency = abs(P_end - P_start) / Sum(abs(delta P_i))

Interpretation:

      nahe 1.0 -> gerichteter, sauberer Pfad
      nahe 0.0 -> viel Zickzack bei wenig Nettofortschritt

Ein Startwert zum Testen koennte etwa `0.5` sein.

### Mindestbewegung

Zusaetzlich sollte die gesamte Bewegung wirtschaftlich relevant sein.
Die Schwelle sollte nicht zwingend statisch sein, sondern kann volatilitaetsadjustiert werden.


Zustandswechsel als Bullseye
------------------------------

Fuer jedes Sample `t` werden zwei Fenster betrachtet:

```text
Past Window        t        Future Window
<------------->    |    <---------------->
```

Beispiel fuer einen ersten Versuch:

```text
Sampling:       12 s
Past Window:    5 Samples = 60 s
Future Window:  8 Samples = 96 s
```

Fuer beide Fenster werden Directionality, Steigung, Efficiency und Gesamtbewegung berechnet.

Ein `START_UP` liegt vor, wenn:

```text
Future = starker Aufwaertstrend
AND
Past war noch kein starker Aufwaertstrend
```

Ein `START_DOWN` entsprechend:

```text
Future = starker Abwaertstrend
AND
Past war noch kein starker Abwaertstrend
```

Es muss davor nicht zwingend perfekt seitwaerts gegangen sein. Auch beispielsweise ein schwacher Gegentrend kann in einen neuen starken Trend uebergehen.

Modell B: Triple Barrier
---------------------------

Das Triple-Barrier-Modell beantwortet unabhaengig vom Bullseye:

> Bietet ein Long- oder Short-Einstieg genau jetzt ein ausreichend gutes Chance-Risiko-Profil?

Das Modell laeuft ebenfalls alle 12 Sekunden.

Auch dieses Modell kann als 3-Klassen-Klassifikator formuliert werden:

      0 = kein profitabler/attraktiver Trade
      1 = Long profitabel
      2 = Short profitabel

Long und Short koennen unter der gewaehlten symmetrischen Stop-Geometrie nicht gleichzeitig erfolgreich sein.

Triple-Barrier-Geometrie
----------------------------

Das Risiko pro Trade wird ueber eine symmetrische Stop-Distanz begrenzt.

Beispiel:

      Long Target       +10 Ticks
      Short Stop         +4 Ticks

      Entry               0

      Long Stop          -4 Ticks
      Short Target      -10 Ticks

Damit gilt:

      CRV = Target / Stop = 10 / 4 = 2.5

Bevor das Short-Target bei -10 erreicht werden kann, wurde der Long-Stop bei -4 bereits getroffen.
Umgekehrt wird der Short-Stop bei +4 getroffen, bevor das Long-Target +10 erreicht.
Damit sind die Outcome-Klassen eindeutig.

Zusaetzlich existiert eine Time Barrier, beispielsweise 120 oder 180 Sekunden.


Gewinnchance beim Triple-Barrier-Modell
------------------------------------------

Die Gewinnchance wird **nicht** als kontinuierliches Trainingslabel vorgegeben.

Historisch ist das Ergebnis diskret:

      Long erfolgreich
      Short erfolgreich
      kein attraktiver Trade / Timeout / Stop

Das trainierte Klassifikationsmodell liefert trotzdem kontinuierliche Wahrscheinlichkeiten:

      P(unprofitabel)     = 0.18
      P(Long profitabel)  = 0.74
      P(Short profitabel) = 0.08

Die `0.74` kann nach sauberer Probability Calibration als geschaetzte Wahrscheinlichkeit des definierten Long-Outcomes interpretiert werden.

Wichtig: `predict_proba()` eines Boosting-Modells ist nicht automatisch perfekt kalibriert.
Die Kalibrierung muss auf zeitlich getrennten Walk-forward-Daten validiert werden, z. B. mit:

 - Reliability Diagram
 - Brier Score
 - Log Loss
 - Platt Scaling
 - Isotonic Regression


CRV und Break-even-Wahrscheinlichkeit
--------------------------------------

Bei einem Brutto-CRV von 2.5 gilt ohne Kosten und Timeout-Effekte:

      p_break_even = 1 / (1 + 2.5)
                   = 28.6 %

Eine Strategie mit hohem CRV benoetigt deshalb nicht zwingend eine Trefferquote von ueber 50 %.
Gebuehren, Spread und Slippage muessen jedoch in der Barrier-Geometrie beziehungsweise der EV-Berechnung beruecksichtigt werden.
Entscheidend ist das **Netto-CRV**.


Warum beide Modelle parallel laufen
--------------------------------------

Bullseye und Triple Barrier beantworten komplementaere Fragen.

Bullseye:

> Beginnt gerade etwas Neues?

Triple Barrier:

> Lohnt sich ein Trade jetzt?

Deshalb darf ein Trade nicht davon abhaengen, dass zwingend beide Modelle dieselbe Art Signal liefern.

Beispiele:

| Bullseye  | Triple Barrier | Interpretation |
|-----------|----------------|----------------|
| Long hoch | Long hoch      | Idealer frueher Long-Entry |
| niedrig   | Long hoch      | Trend laeuft bereits, Long kann weiterhin attraktiv sein |
| Long hoch | niedrig        | moeglicher Trendstart, aber CRV/Outcome unattraktiv, warten |
| niedrig   | niedrig        | kein Trade |

Der besonders wichtige Fall ist:

      Bullseye: kein neuer Trendstart
      Triple Barrier: Long attraktiv

Das bedeutet:

> Der optimale Trendstart wurde eventuell verpasst, aber der laufende Trend bietet noch immer einen wirtschaftlich attraktiven Einstieg.


Decision Engine
------------------

Zunaechst sollte kein drittes ML-Metamodell notwendig sein.
Die Decision Engine kann transparente Regeln verwenden und spaeter walk-forward optimiert werden.

Beispiel:

Bullseye:

      P(start_up) = 0.82

Triple Barrier:

      P(long_profitabel) = 0.75

=> starker frueher Long-Kandidat

Oder:

```text
Bullseye:
P(no_start) = 0.89

Triple Barrier:
P(long_profitabel) = 0.77

=> moeglicher Continuation Entry
```

Die exakten Schwellen werden nicht anhand von Accuracy optimiert, sondern anhand wirtschaftlicher Out-of-Sample-Ergebnisse.

---

# 12. Modelltyp

Fuer die erste Version bietet sich an, **beide Targets mit demselben Modelltyp** zu trainieren, z. B. XGBoost.

```text
X(t)
 |
 +--> XGBoost #1: Bullseye
 |
 +--> XGBoost #2: Triple Barrier
```

Vorteile:

- identische Datenbasis
- identische technische Infrastruktur
- Unterschiede sind primaer auf die Targets zurueckzufuehren
- sehr gute Eignung fuer tabellarische Features
- schnelle Inferenz
- SHAP-Analyse moeglich

LightGBM und CatBoost bleiben sinnvolle Challenger.

Spaeter kann fuer das Bullseye-Modell insbesondere ein TCN getestet werden, falls die explizite zeitliche Sequenz gegenueber den Rolling Features einen messbaren Walk-forward-Vorteil liefert.

---

# 13. Walk-forward-Validierung

Randomisierte Train/Test-Splits sind fuer dieses System ungeeignet.

Stattdessen:

```text
Train        Validate       Test
Jan-Apr      Mai            Juni

      Train             Validate       Test
      Feb-Mai           Juni           Juli

             usw.
```

Wichtig sind Purging und gegebenenfalls Embargo an den Split-Grenzen, da die Targets absichtlich zukuenftige Daten verwenden.

---

# 14. Relevante Erfolgsmetriken

Nicht primaer Accuracy optimieren.

## Bullseye

- Precision von `START_UP` / `START_DOWN`
- Zeit zwischen erkanntem Bullseye und spaeterem Trend
- MFE nach Bullseye
- False-Ignition-Rate
- Anteil der Signale, bei denen bereits ein Trend lief
- Stabilitaet ueber verschiedene Marktregime

## Triple Barrier

- Kalibrierung der vorhergesagten Wahrscheinlichkeiten
- Profit-Target-vor-Stop-Haeufigkeit
- erwarteter Netto-Wert pro Signal
- CRV nach Kosten und Slippage
- Long-/Short-Stabilitaet
- Signalzahl pro Handelstag

## Gesamtsystem

- Netto-EV nach Gebuehren und Slippage
- Profit Factor
- Maximum Drawdown
- durchschnittlicher Gewinn/Verlust
- Trefferquote im Zusammenhang mit CRV
- Anteil frueher Entries vs. Continuation Entries
- Robustheit ueber Monate, Tageszeiten und Volatilitaetsregime

---

# 15. Position Management

Nach dem Einstieg soll der Bot einen profitablen Trend moeglichst lange ausnutzen.

Grundidee:

- initiales Risiko klar begrenzen
- Stop-Loss niemals wieder aufweiten
- bei zunehmendem Gewinn Stop nachziehen
- bei nachlassender Trendstaerke aggressiver absichern
- wenn der Trend erneut staerker wird, Stop nicht wieder aufweiten, aber weniger aggressiv weiter nachziehen

Damit wird der Triple-Barrier-Target nicht automatisch zum tatsaechlichen Live-Exit. Triple Barrier bewertet die **Entry-Opportunity**. Das Position Management darf einen starken Trend erheblich laenger laufen lassen als die urspruengliche Profit-Barriere.


Aktueller Gesamtentwurf
---------------------------

```text
             Databento MBP-1 + Trades
                       |
                       v
              12-s Aggregation
                       |
            gemeinsame Features X(t)
                       |
          +------------+------------+
          |                         |
          v                         v
   Bullseye XGBoost          Triple-Barrier XGBoost
          |                         |
  0 no trend start          0 no attractive trade
  1 start up                1 profitable long
  2 start down              2 profitable short
          |                         |
          |                  calibrated probabilities
          |                         |
          +------------+------------+
                       |
                       v
                Decision Engine
                       |
          +------------+------------+
          |            |            |
         LONG         WAIT         SHORT
          |                         |
          +------------+------------+
                       |
                       v
              Position Management
                       |
                       v
                Tradovate API
```

Kernerkenntnisse
------------------

1. **Bullseye** und **Triple Barrier** duerfen nicht vermischt werden.
2. Beide Modelle verwenden **denselben aktuellen Feature-Vektor**, lernen aber unterschiedliche Targets.
3. Bullseye ist ein **Trendstart-/Change-Point-Problem**.
4. Das Bullseye-Target hat genau drei Klassen: `kein Trendstart`, `Start nach oben`, `Start nach unten`.
5. Fuer die Bullseye-Labelerzeugung darf und soll sowohl Vergangenheit als auch Zukunft betrachtet werden.
6. Ein einfacher und transparenter Bullseye-Algorithmus kann auf gewichteten 12-s-Preisen basieren.
7. Ein Trend wird ueber **Directionality + Mindeststeigung + Path Efficiency + Mindestbewegung** definiert.
8. Bullseye ist der **frueheste valide Zustandswechsel** in einen neuen Trend, nicht irgendein Punkt innerhalb des bereits laufenden Trends.
9. Triple Barrier bewertet dagegen **kontinuierlich alle 12 Sekunden**, ob ein Long- oder Short-Entry das verlangte CRV bietet.
10. Das Triple-Barrier-Target bleibt diskret; die kontinuierliche Gewinnchance kommt aus den **kalibrierten Klassenwahrscheinlichkeiten** des Modells.
11. Durch symmetrische Stop-Distanzen und ein Ziel mit CRV >= 2.5 koennen Long- und Short-Erfolg fuer denselben Startpunkt nicht gleichzeitig eintreten.
12. Ein niedriger Bullseye-Score verbietet keinen Trade. Triple Barrier kann einen profitablen **Continuation Entry** erkennen.
13. Nach einem Entry ist das Position Management eine eigene Aufgabe und soll profitable Trends laenger laufen lassen koennen als die Entry-Profit-Barriere.
14. Der wichtigste Qualitaetsnachweis ist nicht In-Sample-Accuracy, sondern **Walk-forward-Netto-EV nach realistischen Kosten und Slippage**.
