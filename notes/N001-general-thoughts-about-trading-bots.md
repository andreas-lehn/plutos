General thoughts about a trading bot
======================================

* Tradovate as broker and real time data supplier
* Data used: contracts and order book
* Trading of Micro-Nasdaq-Futures (MNQ)



Kursbewegung
-------------

Eine Kursbewegen von 25 Punkten zu erwischen, ist ausreichend, um damit Gewinn zu machen:
Das entsprichte mein Nasdaq-Future einem Gewinn von $50.

0,5 Punkte (2 Ticks) sind ausreichend, um die Kosten für einen Trade zu decken.


Verhersage-Intervall
----------------------

Das Vorhersagemodell macht eine Vorhersage auf den Kurs in den nächsten Sekunden oder wenigen Minuten.
In der Literatur findet man 3, 5 oder 15 min.
Der Nasdaq-Future ist sehr volatil.
Deshalb ist das max. vermutlich 3 min. 
Aber auch kürzere Zeiträumen: 1 min oder gar 30 s könten sinnvoll sein.


Prognosegenauigkeit
---------------------

Das Vorhersagemodell läuft mindestens in Sekunden-Takt.
Es sagt Kurse im Vorhersageintervall voraus, das wenige Minuten lang ist.
Das Bedeutet auch, dass es alle paar Minuten seine Vorhersagegenauigkeit bestimmen kann.
Die Vorhersagegenauikeit des Vorhersagemodells kann verwendet werden, 
um die Entscheidung zu treffen, ob überhaupt gehandelt wird.


Reinforcement-Learning
------------------------

Der Nasdaq Future Markt ist sehr volatil und produziert Unmengen an Daten.
Für historische Zeiträume sind deshalb die Rohdaten,
die Tradovate liefert, nicht verfügbar.
Ein Lernen auf historischen Daten kann daher nur bedingt erfolgreich sind.
Das Modell soll deshalb online lernen auf den Rohdaten des Brokers.

Das hat viele Vorteile:
 * Keine Rohdaten und Simulationen erforderlich
 * Es passt sich langfristigen Trends in der Änderung des Kaufverhaltens an.

Insbesonder letzter Punkt ist wichtig, da durch die fortschreitende Automatisierung immer mehr Bots entstehen werden,
die das aktuelle Kaufverhalten analysieren und diese ausnutzen werden.
Dadurch werden Strategieen, die bisher erfolgreich waren, ihren Erfolg einbüsen.
