Day trading approach
=======================

NMQ als Basis
---------------

Das Day-Trading soll auf dem Nasdaq-100 Future stattfinden.
Für diese Future gibt es 4 Größen:

 1. Standard/Großer Nasdaq-100 Future (NDX): Multiplicator: 20 USD
 2. E-mini Nasdaq-100 Future: Multiplicator 20$, in 1/5 handelbar, 0.25 Mindesttick
 3. Mirco E-mini Nasday-100 Future: wie E-mini aber Multiplikator 2$
 4. E-nano/Nano Future: Noch kleiner als Micro, aber Broker spezifisch

Unser Ziel ist es, den Retail-Broker zu schlagen.
Die institutionellen Profi-Broker werden wir nicht schlagen können.
Die meisten Retail-Broker tummeln sich im Mirco E-mini Nasdaq-100 Future.
Deshalb und wegen seiner sehr guten Liquidität ist dieser Future der Future unserer Wahl.


Echtzeidaten und Orderflow
---------------------------

Um den Retail-Broker zu schlagen, brauchen wir die beste Information,
die wir bekommen können.
Wir brauchen deshalb sehr genaue Kursdaten mit dem jeweiligen Handelsvolumen pro Kurs
und auch das Orderbuch.
Diese Daten füttern wir dann in ein KI-Modell, um von diesem eine Prognose zu erhalten.
Auf Basis dieser Prognose machen wir dann unsere Trading-Entscheidung abhängig.


Volumen-basiert statt Zeit-basiert
------------------------------------

Die KI-kann nicht auf den Rohdaten der Börse arbeiten.
Dafür sind das viel zu viele Daten bzw. die uns zur Verfügung stehenden Rechenleistung reicht dafür nicht aus.
Vielleich machen das die professionellen Trader so.
Das ist dann ihr Vorteil ggü. uns.
Deshalb können wir sie nicht schlagen.

Um die Datenmenge handhabbar für die KI zu machen, braucht es 2 Dinge:

 * Aggregation der Daten
 * Ermittlung von Kennzahlen auf den aggregierten Zahlen

Die typische Methode für die Aggregation von (Kurs-)Daten ist die Kerze (Bar).
Sie fasst alle Trades eines festen Zeitabschnitts zusammen.
Die Zeitabschnitte können dabei von Sekunden, über Minuten, Stunden, Tagen bis Wochen und Monate reichen.
Typischerweise beinhaltet eine Kerze folgende Daten:
 * Anfangs-/Endezeit
 * Eröffnungskurs, niedrigster Kurs, höchster Kurs, Schlusskurs
 * Handelsvolumen
 * Manchmal: Handelsvolumen pro Kurs (Histogramm)

Für die Kursentwicklung sind die tatsächlich ausgeführten Trades entscheidend.
Die Anzahl der Trades unterscheidet sich pro Zeiteinheit innerhalb eines Tages sehr stark.
Bei einer Zeit-basierten Vorgehensweise verstärkt das das ohnehin schon sehr große Rauschen.
Deshalb ist ein Volumen-basiert Ansatz wesentlich besser, als ein Zeit-basierter.
Daraus resultiert eine Volumentkerze (volume bar).

Die Volumenbars können aus den einzeln Ticks errechnet werden.
Dadurch wird es möglich, den Volumenbar wesentliche bessere Kennzahlen als die oben genannten hinzuzufügen.


Prognose-Modell
-----------------

Das Prognose-Modell wird ein Gradient-Booster-Modell sein.
Modelle dieser Art sind sehr schnell zu trainieren und sie können sehr gut mich vielen historischen Daten umgehen.

Diese Prognose-Modell wird auf den Volumenkerzen der letzen Monate trainiert.
Für die Prognose erhält es dann die aktuelle Volumenkerze und sagt auf dieser Basis voraus,
was in den nächsten beiden Volumeneinheiten passieren wird.
Das Prognose-Fenster ist also doppelt so lange wie die Kerze.

Hindergrund: Auf Basis der Prognose treffen wir eine Kauf- oder Verkaufentscheidung.
Während unser Trade läuft erhalten wir kontinuierlich weitere Prognosen.
Mit diese Prognosen können wir dann unseren laufenden Deal justieren.
Deshalb muss das Prognose-Intervall mindesten zwei Volumentkerzen lang sein.
Länger braucht es aber auch nicht sein, weil die die Prognose umso ungenauer wird,
je weiter sie in die Zukunft reicht.

Die Prognose besteht aus der oberen und unteren Schranke des Kurse für die nächsten beiden Volumeneinheiten,
relative zum Schlusskurs der aktuellen Kerze.

Beispiel für eine Schlusskurs der aktuellen Kerze bei 30.000 Punkten:

 * Unter Schranke: 0.01%
 * Obere Schranke: 0.05%

Ein solche Prognose bedeutet dann,
dass sich der Kurs in den nächsten beiden Volumeneinheiten zwischen
29970 und 30150 Punkten bewegen wird.
Daraus kann man schließen, Long zu gehen.

Während man dann Long ist, erhält man in der Mitte des Prognoseintervall eine neue Prognose.
Auf Basis dieser Prognose kann man dann entscheiden, wie man mit der aktuellen Order umgeht.
Kaufen, aufstocken, Stop-Loss nachziehen,...
