Trading Strategy
=======================

Die Zusammenfassung der Tick-Daten zu Volumenkerzen ist die erste Filterung,
die druchgeführt wird.
Der Parameter dieser Filterung ist das Volumen der Kerze.
Je Grüßer das Volument, desto stärker die Filterung.

Über die Volumen-Filterung kann eine zeitliche Filterung gelegt werden.
In der Finanzwelt sind diese Filter fast immer gleitende Durchschnitte.
Im Gegensatz dazu verwendet der Regelungstechniker eine PT1-Filterung.
Der große Vorteil der PT1-Filterung ist, dass die rekursiv ist:
Die gefilterten Werte können direkt aus dem aktuellen und gefilterten wert ausgerechnet werden.
Es müssern keine historischen Werte gespeichert werden.

Da der gleitende Durchschnitt sehr gut mit einer PT1-Filterung angenähert werden können
und es sowieso nicht so genau auf die Filterung ankommt,
werden wir dem regelungstechnischen Ansatz folgen und ein PT1-Filterung durchführen.
Dafür ist dann eine einzige konstante nötig, die Filterkonstante c.

Die folgenden Werte werden zeitlich gefiltert:
 1. Gewichteter Durchschnitt
 2. Tiefstwerte
 3. Höchstwerte

Die gefilterten Tiefs/Hochs werden die Stopp-Loss Kurse.
Die werden während des Trads kontinuierlich nachgeführt und führen so zu einem Ausstieg.
Früher oder Später.

Die Prognose für den zukünftigen Durchschnittswert wird aus der Steigung des gleitenden Durchschnitt der gewichteten Mittelwerte errechnet.

Der Abstand des Schlusskurse der aktuellen Kerze zum Stopp-Loss-Kurs ist ein Maß für das Risiko eine Trades.
Die Steigung des gewichteten Durchschnitts ist ein Maß für die Chance eine Trades.
Der Quotient der beiden bestimmt das Chance/Risiko-Verhältnis.
Ist diese Verhältnis gut (größer als ein Schwellwert), dann ist das ein Einstiegssignal.

Diese Strategie ist sehr simple und leicht umzusetzen.
Dieses Verfahren ist vermutlich das einfachst denkbare Verfahren, das möglicherweise funktionieren kann.
Nach der Lehre von Kent Beck sollte man deshalb damit beginnen.
Ich nenne ihn deshalb `KentBeckTrader`.

Der `KentBeckTrader` wird dann die Basis sein, an der sich Verbesserungen messen lassen müssen.

Der KentBeckTrader ist parametrisierbar. 
Folgende Parameter gibt es:
 * Volumen V der Volument Bar
 * Zeitkonstante k für die zeitliche Filterung
 * Schwelle für das Chance/Risikok-Verhältnis
 * Maximaler Verlust pro Trade

Der Maximale Verlust pro Trade hängt nicht direkt mit der Trading-Strategy zusammen.
Die Parameter kommt aus dem Risikomanagement.
Durch ihn wird festgelegt, wieviel Kontrakte bei Trade eingegangen werden.
