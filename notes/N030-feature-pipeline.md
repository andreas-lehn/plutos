Mehrstufige Marktdatenaggregation auf Basis von Databento MBP-1
==================================================================================


Architekturüberblick
------------------------

In automatisierten Handels- und Analysesystemen entsteht oft ein Missverhältnis zwischen
der Frequenz der eintreffenden Börsendaten und der Taktung der Entscheidungsmodelle

* **High-Frequency-Ebene:** Die Matching-Engine liefert über Databento bis zu Tausende Updates pro Sekunde (Ticks).
* **Entscheidungsebene:** Handelsmodelle, Machine-Learning-Pipelines oder Risikosysteme agieren in diskreten Zeiteinheiten
  (z. B. alle 12 Sekunden, 1 Minute oder 5 Minuten).

Ein simples Subsampling (d. h. das bloße Abfragen des aktuellen Buchstands am Intervallende) ignoriert die Orderbuchdynamik innerhalb des Intervalls.
Die Lösung ist eine **zweistufige Aggregationspipeline**:

```
[ Databento MBP-1 Rohdatenstrom ]
               │  (Sub-Millisekunden, Event-Driven)
               ▼
┌─────────────────────────────────────────┐
│     Stufe 1: Primär-Aggregator          │
│  - Inkrementelle Berechnung in O(1)     │
│  - Nanosekundengenaue Zeitgewichtung    │
└─────────────────────────────────────────┘
               │
               ▼  (Diskreter 1-Hz-Stream)
┌─────────────────────────────────────────┐
│   Standardisiertes 1-Sekunden-Sample    │
│  - Microprice-OHLC                      │
│  - TWAP & TW-Imbalance                  │
│  - Cumulative OFI & Trade-Flow          │
└─────────────────────────────────────────┘
         │                       │
         ▼ (Puffer: 12 Samples)  ▼ (Puffer: 60 Samples)
┌──────────────────┐   ┌──────────────────┐
│ Stufe 2a: 12s    │   │ Stufe 2b: 1min   │
│ Handelsentscheid.│   │ Regime-Filter    │
└──────────────────┘   └──────────────────┘
```


Aufbau der Databento-Nachrichten (`mbp-1`)
-----------------------------------------------

Im Databento Binary Encoding (DBN) besteht jeder Datensatz aus einem standardisierten 16-Byte Header, gefolgt vom Nachrichtenkörper.
Das Schema `mbp-1` (Market By Price – Level 1) stellt ein vollwertiges **Superset** des reinen `trades`-Schemas dar:
Es enthält alle ausgeführten Trades und ergänzt diese um den synchronen Zustand des Top-of-Book-Orderbuchs (Best Bid & Best Ask).

### Der DBN-Record-Header (`RecordHeader`)

Jede Nachricht beginnt mit folgendem 16-Byte-Block:

| Feldname | Datentyp | Größe | Beschreibung |
| :--- | :--- | :--- | :--- |
| `length` | `uint8_t` | 1 Byte | Gesamtlänge des Records in 4-Byte-Wörtern. |
| `rtype` | `uint8_t` | 1 Byte | Record-Typ. Für `mbp-1` gilt `rtype = 1` (bei reinem `trades` gilt `rtype = 0`). |
| `publisher_id` | `uint16_t` | 2 Bytes | Eindeutige Kennung der Datenquelle / Börse. |
| `instrument_id` | `uint32_t` | 4 Bytes | Eindeutige numerische Wertpapier-ID. |
| `ts_event` | `uint64_t` | 8 Bytes | Zeitstempel des Ereignisses von der Matching-Engine (in Nanosekunden seit Unix-Epoche). |

### Der MBP-1 Nachrichtenkörper (`Mbp1Msg`)

Direkt nach dem Header folgen die Event-Metadaten sowie das L1-Orderbuch-Array:

| Kategorie | Feldname | Datentyp | Beschreibung |
| :--- | :--- | :--- | :--- |
| **Event-Info** | `action` | `char` | Auslösende Aktion: `'T'` (Trade), `'A'` (Add), `'C'` (Cancel), `'M'` (Modify), `'R'` (Reset). |
| | `side` | `char` | Aggressor-Seite bei Trades bzw. Buchseite bei Quotes: `'B'` (Bid) oder `'A'` (Ask). |
| | `price` | `int64_t` | Ausführungspreis bei Trades (skaliert mit $10^{-9}$ zur Fixkomma-Darstellung). |
| | `size` | `uint32_t` | Ausgeführtes Trade-Volumen. |
| | `flags` | `uint8_t` | Bitmaske für System-Flags (z. B. Paket-Ende). |
| | `ts_in_delta` | `int32_t` | Latenzoffset in Nanosekunden zwischen Capture-Server und Börsen-Matching-Engine. |
| | `sequence` | `uint32_t` | Fortlaufende Sequenznummer der Börse. |
| **L1-Orderbuch** | `bid_px_00` | `int64_t` | Aktueller Best Bid Preis (skaliert mit $10^{-9}$). |
| | `ask_px_00` | `int64_t` | Aktueller Best Ask Preis (skaliert mit $10^{-9}$). |
| | `bid_sz_00` | `uint32_t` | Akkumulierte Stückzahl / Liquidität auf Best Bid. |
| | `ask_sz_00` | `uint32_t` | Akkumulierte Stückzahl / Liquidität auf Best Ask. |
| | `bid_ct_00` | `uint32_t` | Anzahl individueller Limit-Orders auf Best Bid. |
| | `ask_ct_00` | `uint32_t` | Anzahl individueller Limit-Orders auf Best Ask. |


Definition & Semantik des 1-Sekunden-Samples
-------------------------------------------------

Das 1-Sekunden-Sample bündelt die hochfrequenten Ticks einer Kalendersekunde in ein kompaktes, fixes Datenobjekt.
Das Sample enthält folgende Kennzahlen:

1. **Microprice-OHLC (`open`, `high`, `low`, `close`):**
   * *Bedeutung:* Der volumengewichtete Mikropreis berücksichtigt die Liquiditätsverteilung zwischen Bid und Ask. Er bildet den "fairen" Preis realistischer ab als der einfache Midprice. Die OHLC-Spanne quantifiziert die Intrasekunden-Volatilität.
2. **Zeitgewichteter Mikropreis (`twap_micro`):**
   * *Bedeutung:* Glättet kurzzeitige Spikes heraus, die nur für wenige Mikrosekunden bestanden haben.
3. **Zeitgewichtete Imbalance (`twap_imbalance`):**
   * *Bedeutung:* Liefert das durchschnittliche Kräfteverhältnis im Top-of-Book. Ein positiver Wert signalisiert anhaltenden Liquiditätsüberhang auf der Kaufseite.
4. **Kumulierte Order Flow Imbalance (`cumulative_ofi`):**
   * *Bedeutung:* Erfasst die Netto-Veränderung des Orderbuchs (Hinzufügen, Stornieren, Ausführen) zwischen Ticks. OFI ist ein starker Prädiktor für unmittelbaren Preisdruck.
5. **Trade-Volumen & Netto-Trade-Imbalance (`trade_volume`, `trade_imbalance_vol`):**
   * *Bedeutung:* Trennt passive Liquiditätsänderungen von aktiven Marktaufträgen. Ein positives `trade_imbalance_vol` zeigt an, dass Marktteilnehmer aggressiv in den Ask hineingekauft haben.
6. **Tick-Rate (`tick_count`):**
   * *Bedeutung:* Dient als Indikator für Marktaktivität und algorithmische Dichte (HFT-Partizipation).


Berechnung der 1-Sekunden-Features aus Databento-Records
-------------------------------------------------------------

Um Tausende Ticks pro Sekunde latenzfrei zu verarbeiten,
erfolgt die Berechnung im Primär-Aggregator **strikt inkrementell in** $O(1)$ ohne dynamische Speicherallokation.

### Grundlegende Momentan-Metriken (pro Tick $k$)

Für jeden eintreffenden Record $k$ mit Zeitstempel $t_k = \text{ts\_event}_k$ werden berechnet:

1. **Volumengewichteter Mikropreis:**
   $$\text{Microprice}_k = \frac{\text{bid\_px\_00}_k \cdot \text{ask\_sz\_00}_k + \text{ask\_px\_00}_k \cdot \text{bid\_sz\_00}_k}{\text{bid\_sz\_00}_k + \text{ask\_sz\_00}_k}$$

2. **Top-of-Book Imbalance:**
   $$\text{Imbalance}_k = \frac{\text{bid\_sz\_00}_k - \text{ask\_sz\_00}_k}{\text{bid\_sz\_00}_k + \text{ask\_sz\_00}_k}$$

### Inkrementelle Zeitgewichtung (TWAP)

Ein Wert ist für die Dauer $\Delta t_k = t_k - t_{k-1}$ zwischen zwei aufeinanderfolgenden Ticks gültig. Der Aggregator summiert kontinuierlich Flächeninhalte auf:

$$\text{Area}_{\text{micro}} \mathrel{+}= \text{Microprice}_{k-1} \cdot \Delta t_k$$
$$\text{Area}_{\text{imbalance}} \mathrel{+}= \text{Imbalance}_{k-1} \cdot \Delta t_k$$
$$\Delta t_{\text{total}} \mathrel{+}= \Delta t_k$$

Am Ende des Sekundenintervalls ($T_{\text{end}}$) wird der letzte Zustand bis zur Sekundengrenze aufintegriert:

$$\text{twap\_micro} = \frac{\text{Area}_{\text{micro}}}{\Delta t_{\text{total}}}, \quad \text{twap\_imbalance} = \frac{\text{Area}_{\text{imbalance}}}{\Delta t_{\text{total}}}$$

*Wichtig:* Der Zustand am Ende von Sekunde $S$ dient als Startwert für Sekunde $S+1$, sodass keine Informationslücken entstehen.

### Order Flow Imbalance (OFI)

Zwischen dem aktuellen Buchzustand $k$ und dem Vorzustand $k-1$ berechnet sich der OFI-Beitrag $e_k$:

$$e_k = I^B_k - I^A_k$$

Wobei für die Bid-Seite gilt:
$$I^B_k = \begin{cases} \text{bid\_sz}_k & \text{falls } \text{bid\_px}_k > \text{bid\_px}_{k-1} \\ \text{bid\_sz}_k - \text{bid\_sz}_{k-1} & \text{falls } \text{bid\_px}_k = \text{bid\_px}_{k-1} \\ -\text{bid\_sz}_{k-1} & \text{falls } \text{bid\_px}_k < \text{bid\_px}_{k-1} \end{cases}$$

Und für die Ask-Seite:
$$I^A_k = \begin{cases} -\text{ask\_sz}_k & \text{falls } \text{ask\_px}_k > \text{ask\_px}_{k-1} \\ \text{ask\_sz}_k - \text{ask\_sz}_{k-1} & \text{falls } \text{ask\_px}_k = \text{ask\_px}_{k-1} \\ \text{ask\_sz}_{k-1} & \text{falls } \text{ask\_px}_k < \text{ask\_px}_{k-1} \end{cases}$$

Die Summe aller $e_k$ innerhalb der Sekunde ergibt `cumulative_ofi`.

### Trade-Event-Handling

Wird ein Record mit `action == 'T'` empfangen:
* `trade_volume += size`
* Falls `side == 'B'`: `trade_imbalance_vol += size` (Käufer-initiiert)
* Falls `side == 'A'`: `trade_imbalance_vol -= size` (Verkäufer-initiiert)


Sekundäre Aggregation: 1s-Samples $\rightarrow$ 12s / 1min
--------------------------------------------------------------

Da alle 1-Sekunden-Samples über exakt dasselbe Zeitintervall ($1{,}000{,}000{,}000\text{ ns}$) gemessen wurden,
vereinfachen sich die Rechenoperationen auf Stufe 2 erheblich.

### Aggregationsregeln für ein Zeitfenster aus $N$ Samples

Gegeben sei eine Liste von $N$ aufeinanderfolgenden 1-Sekunden-Samples $S_1, S_2, \dots, S_N$ (z. B. $N = 12$ für 12 Sekunden, $N = 60$ für 1 Minute):

| Ziel-Feature | Aggregationsmethode | Mathematische Vorschrift |
| :--- | :--- | :--- |
| **Open** | Erster Wert | $\text{Open} = S_1.\text{open\_micro}$ |
| **High** | Maximalwert | $\text{High} = \max_{i=1 \dots N}(S_i.\text{high\_micro})$ |
| **Low** | Minimalwert | $\text{Low} = \min_{i=1 \dots N}(S_i.\text{low\_micro})$ |
| **Close** | Letzter Wert | $\text{Close} = S_N.\text{close\_micro}$ |
| **TWAP Microprice** | Arithmetisches Mittel | $\overline{\text{TWAP}}_{\text{micro}} = \frac{1}{N} \sum_{i=1}^N S_i.\text{twap\_micro}$ |
| **TWAP Imbalance** | Arithmetisches Mittel | $\overline{\text{TWAP}}_{\text{imb}} = \frac{1}{N} \sum_{i=1}^N S_i.\text{twap\_imbalance}$ |
| **Cumulative OFI** | Summe | $\text{OFI}_{\text{total}} = \sum_{i=1}^N S_i.\text{cumulative\_ofi}$ |
| **Trade Volume** | Summe | $\text{Vol}_{\text{total}} = \sum_{i=1}^N S_i.\text{trade\_volume}$ |
| **Net Trade Flow** | Summe | $\text{NetTradeFlow} = \sum_{i=1}^N S_i.\text{trade\_imbalance\_vol}$ |
| **Tick Count** | Summe | $\text{Ticks}_{\text{total}} = \sum_{i=1}^N S_i.\text{tick\_count}$ |

*Hinweis zur Zeitgewichtung auf Stufe 2:*
Da jedes Basiselement $S_i$ exakt eine Sekunde repräsentiert, entspricht das arithmetische Mittel der TWAPs exakt dem globalen,
zeitgewichteten Integral über den gesamten $N$-Sekunden-Zeitraum.


Referenzimplementierung (Python)
-------------------------------------

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class BookSample1S:
    timestamp_s: int
    open_micro: float
    high_micro: float
    low_micro: float
    close_micro: float
    twap_micro: float
    twap_imbalance: float
    cumulative_ofi: float
    trade_volume: int
    trade_imbalance_vol: int
    tick_count: int

class PrimaryOneSecondAggregator:
    """Stufe 1: Verarbeitet HFT-Databento-Records zu 1-Sekunden-Samples."""
    def __init__(self):
        self.current_sec: Optional[int] = None
        self._reset_bucket()
        self.prev_bid_px = None
        self.prev_bid_sz = None
        self.prev_ask_px = None
        self.prev_ask_sz = None

    def _reset_bucket(self):
        self.open_m = self.high_m = self.low_m = self.close_m = None
        self.area_micro = 0.0
        self.area_imbalance = 0.0
        self.duration_ns = 0
        self.last_ts_ns = None
        self.last_micro = None
        self.last_imbalance = None
        self.cumulative_ofi = 0.0
        self.trade_volume = 0
        self.trade_imbalance_vol = 0
        self.tick_count = 0

    def process_tick(self, record) -> Optional[BookSample1S]:
        ts_ns = record.ts_event
        sec = ts_ns // 1_000_000_000
        completed_sample = None

        if self.current_sec is not None and sec > self.current_sec:
            completed_sample = self._finalize_bucket(self.current_sec, ts_ns)
            last_m, last_imb = self.last_micro, self.last_imbalance
            self._reset_bucket()
            self.last_micro, self.last_imbalance = last_m, last_imb
            self.last_ts_ns = ts_ns

        self.current_sec = sec

        # Microprice & Imbalance
        denom = record.bid_sz_00 + record.ask_sz
