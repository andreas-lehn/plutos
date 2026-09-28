Plutos concepts and ideas
==========================

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


Recherche über Whatsapp KI
----------------------------

 * Vorhersage der Richtung, nicht des Preises
 * Nehmen, was der Orderflow hergibt:
     * Preis in Kerzen der letzen 20 Schätzintervalle (20 x 1 min Kerzen bei 1 min Vorausschau)
     * Kaufvolumen/Verkaufvolumen
     * Microstruktur: Abstand zum VWAP, RSI(14), Distand zum Tagestief/-hoch
     * Zeit: Minute seit Open
 * Das ergibt ca. 50 - 100 Zahlen pro Schätzung
 * LSTM ist ungeeignet, weil zu langsam und overfitted
 * Besser: 1D CNN. Kann schnell berechnet werden.
 * Ein gutes Modell schafft 53-56% Precision auf Long/Short.
 * 54% reicht, wenn Gewinn größer als Verlust
 * bei 10 sec sind Kerzen nutzlos
 * Nur noch das Orderbook ist relevant (Orderbuch Daten sind teuer)
 * Latenz ist kritisch, kann zum Tod führen
 * Rauschen ist sehr dominant
 * Bei 1 min sind Retail-Trader die Gegner. Sie sind leicht zu schlagen.
 * Bei 10 sec sind HFT die Gegner: Haifischbecken
 * Regel bei den Prop: _Trade den Timeframe, wo deine Konkurrenz am dümmsten ist."
 * 1 - 15 min: Konkurrenz ist menschlich, langsam, ängstlich
 * Deshalb: 10 sec Daten nutzen, um 1 min Vorhersage zu verbessern
 * Sweep spot für Solo-KI-Trader: 15 bis 30 sec Features für 60 sec Prediction
 * Statt zeitlichen Kerzen sind Volumen-orientierte Kerzen besser: Ein Kerze für 500 Kontrakte
 * Um die Retail-Trader zu schlagen, braucht es kein Orderbuch
 * Algo für Online Training:
     * PPO: Stabil, verzeiht Fehler, Standard für Trading, lernt langsam aber crasht nicht
     * DQN mit Replay Buffer: Schneller, aber gefährlich online, weil er alte Marktphasen auswendig lernt
 * Fazit: PPO ist der richtige Algo
 * Weil sich der Markt verändert: Rolling Window + Forget
     * Replay Buffer darf nur 3 Tage enthalten
     * Alle 24h Learning Rate auf 50% reduzieren
 * Kontinuierlicher Ausgabewert von -1.0 bis +1.0 ist ein geiler Gedanke!
 * Das ist dann kein RL mehr sondern Continuous Control
 * Letzer Layer wird Tanh und nicht Softmax.
 * Zu definieren ist, was "stark" heißt. Ein Bespiel: 0.8 entspricht 5 Punkten
 * Damit ist dann kein PPO mehr nötig. Supervised Learning ist das richtige.
 * Architekturvorschlag:
    * Input: 20 x 30 sec Bars
    * 1D-CNN 32 Filter
    * LSTM 64 (optimal, für Gedächtnis)
    * Dense 32, ReLU
    * Dense 1, tanh
    * Loss = MSE
 