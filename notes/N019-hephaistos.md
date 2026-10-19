Hephaistos
===============

Nach der antiken Mythologie war es der griechische Gott
[Hephaistos](https://de.wikipedia.org/wiki/Hephaistos),
der die ersten Maschinen mit Intelligenz schuf.
Darunter waren zwei goldene Dienerinnen und
[Talos](https://de.wikipedia.org/wiki/Talos_(Riese)),
der Bronzeriese, der Kreat bewacht.

Hephaistos ist damit die Gottheit,
die am ehesten mit Robotern und künstlicher Intelligenz in Verbindung steht.
Wir bennenen deshalb unseren KI-Trader nach ihm.


Gradient Boosting
---------------------

[https://en.wikipedia.org/wiki/Gradient_boosting](https://en.wikipedia.org/wiki/Gradient_boosting)
ist das KI-Verfahren, das wir anwenden werden.
Wir werden _supervised learning_ mit den historischen Daten praktizieren.

Jetzt stellt sich die grundsätzliche Frage, 
was sind die Eingangsdaten und was ist der Prognosewert.
Mit den Erfahrungen von Yesterdays Weather ist der Vorschlag für den Prognosewert:

    Das Delta des gewichteten Durchschnitts 3 Kerzen in der Zukunft

Drei Kerzen Vorausschau ist nicht besonders lang,
aber lang genug, um darauf reagieren zu können.
Der Einstieg erfolgt irgenwann in der darauffolgenden Kerze.
Dann bleiben noch 2 Kerzen, um ein entsprechende Bewegung zu erhalten.

Um die Vorhersage durchführen zu können, braucht es Eingangsgrößen.
Bei den Eingangswerten sind absolute Werte zu vermeiden.
Die KI soll ja nicht lernen, dass es bei 30123.25 Punkten fällt.
Das wäre kontraproduktiv.


Eingangsdaten
---------------

Folgende Eingangsdaten sind Kandidaten:

 * Die aktuellen Kerzendaten: Low, High, Close relativ zum Durchschnitt, Close relativ zu Open, Range, Volume
 * Abstand zu den gleitenden Durchschnitt EMA9 und EMA50
 * Daten zur Vergangenheit: Average relativ zur vorausgehenden Kerze und relativ zu 9 Kerzen zurück (für Preisentwicklung)
 * Steigung von EMA9 und EMA50
 * Abstände zu Volumenhochs/-tiefs, Gradient des Volumens am aktuellen Punkt

Diese Daten werden dann mit jeder neuen Kerze ermittelt und dem trainierten Netzt vorgesetzt,
dass daraus dann den Kurs in drei Kerzen voraussagt.
Auf Basis dieser Information kann dann algorithmisch ein Einstiegssignal generiert werden.


Nächste Schritte
------------------

Aufgrund der Erfahrung mit der Optimierung von Yesterdays Weather
möchte ich sehr schnell beginnen, Hephaistos ins Leben zu rufen.
Mich interessiert brennend,
wie er bei den Einstiegssignalen im Vergleich zu Yesterdays Weather abschneidet.


Dolos
---------

Dolos könnte ganz ähnlich umgesetzt werden:
Idealerweise arbeitet Dolos auf denselben Eingangswerten wie Hephaistos.
Nur sein Modell wird nicht auf Verhersage des nächsten Kurses trainiert,
sondern auf die Wahrscheinlichkeit einer Trendumkehr bzw. Fake-Ausbruchs.
