Fixed-Windows Bullseye
==========================

Fixed-Windows Labeling (auch bekannt als Fixed-Time Horizon Method)
gehört im Financial Machine Learning zu den Standardverfahren,
um Kursdaten für KI-gestützte Intraday-Trading-Bots zu klassifizieren.
Der Begriff _Bullseye_ bezieht sich in diesem Kontext auf ein präzise definiertes _Zielgebiet_ (einen Volatilitätskorridor),
das ein Kurs innerhalb eines festen Zeitfensters erreichen muss,
um als valides Signal (z. B. ein hochprofitabler Ausbruch) gewertet zu werden.

Im Gegensatz zum klassischen _Tripple-Barrier-Labeling_
(das dynamisch auf variable Zeitpunkte reagiert)
oder dem simplen _Horizon-Return-Labeling_ (das starr nur den Endpreis misst),
zielt das Bullseye-Verfahren darauf ab, 
hochpräzise Eintrittsfenster mit exzelentem Risiko-Ertrags-Verhältnis (CRV) als Volltreffen (_Bullseye_) zu markieren.

Mit diesem Verfahren lässt sich sehr gut die Frage beantworten:

_Befinden wir uns jetzt gerade am exakten Startpunkt (dem Zündfunken) für ein explosive Bewegung,
die sich in den nächsten Minuten Bahn brechen wird?_


Momentum Ignition
--------------------

Mit diesem Verfahren können wir unsere Strategie ändern:
Wir erkennen nicht mehr den Trend, sondern den Start einens Trends (_Momentum Ignition_).
Das ist ein bisschen ein Zwischending von Yesterdays-Weather und Turning-Point:

 * Mit Yesterdays-Wether wollten wir den Trend erkennen, waren dann aber oft zu spät dran.
 * Mit Turning-Point wollten wir die Trendumkehr erkennen, lagen aber oft falsch.

Für die Erkennung des _Zündfunkens_ schauen wir etwas in die Zukunft.
Wir wollen nicht die länge des Trends oder die Preisspanne vorhersagen.
Das ist viel zu unsicher.
Stattdessen wollen wir einen guten Einstieg erwischen.
Wir werden nicht gleich wieder ausgestoppt und es besteht die Chance auf eine große Veränderung.
Sind wir dann mal drin, übernimmt unser regelbasierten Ansatz das managen der Position
und zieht den Stop-Loss intelligent nach oder steigt zu einem guten Zeitpunkt aus,
lässt aber den Gewinn möglichst lange laufen.

Das Verfahren
----------------

Für das Bullseye-Verfahren definieren wir zunächst ein festes Vorhersagefenster (Fixed-Window).
In unserem Fall, da wir auf 15-20 min Trends spekulieren,
sind das 3 - 5 min.

Für jede Kerzen in diesem Zeitfenster (10x36s oder 24x12s?) berechnen wir zwei Kennzahlen:

 1. **Maximum Favorable Excursion (MFE)**:
    Der maximale Gewinn, den man in den nächsten n Kerzen hätte erzielen könnnen.
 2. **Maximum Adverse Excursion (MAE)**:
    Der maximale Buchverlust (_Drawdown_), den man in dieser Zeit hätte ertragen müssen.

Für das Labeling werden dann folgende Kriterien festgelegt:

 * **Profit-Target**: z.B. 0.15% oder 42 Ticks
 * **Risk-Tolerance**: z.B. 0.05% oder 14 Ticks

Das kann jeweils für Long und Short anders aussehen,
um der unterschiedlichen Dynamik der Auf-/Abwärtsbewegung Rechnung zu tragen.
Long/Short ergibt sich dann, wenn folgende Bedingung erfüllt ist:

    MFE > Profit-Target and MAE < Risk-Tolerance


12s Kerzen
------------

Für das schnelle Erkennen von Einstiegsmöglichkeiten scheint eine 12s Kerze
statt der bisherigen 36s Kerze ratsam:

 * 12s ist lange genug, um die Unruhe der HFTs herauszufiltern.
 * Wir sind deutlich schneller/früher bei der Bewegung dabei,
   was unser Potential erheblich erhöht
 * Unserer Rechenleistung reicht locker für ein 12s Raster aus.


Vor- und Rückshau
------------------

Mit den 12s Kerzen schauen wir dann 24 Kerzen (4.8 min) in die Zukunft,
um das Target zu berechnen.

Für die Rückschau sind mehrere Ebenen (_Multi-Scale Look-Back) sinnvoll:

 1. **Mikro-State**: 1-2 min (9 Kerzen) für die Erkennung der aktuellen Dynamik
 2. **Trend-Etablierung**: 12-15 min für den aktuellen Trend
 3. **Macro-Anker**: 30-60 min als generellen Komposs, wo die Reise gerade hingeht.

