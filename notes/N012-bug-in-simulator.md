Was zu schön ist um wahr zu sein...
========================================

Der Kent-Beck-Trader hat trotz seine Einfachheit ganze hervorragende Ergebnisse geliefert.
Leider waren diese sehr guten Ergebnisse auf eine fehlerhafte Simulation zurück zu führen.
Dazu muss man ein bisschen verstehen, wie die Simulation funktioniert:

 * Der Trader sieht immer nur neue Kerzen kommen.
 * Auf Basis der akutellen und - falls nötig - bereits erhaltenen Kerzen trifft der Trader sein Kauf-/Verkaufs-Entscheidung.
 * Der Kauf erfolgt aber erst im nächsten Zyklus: In einem der Trades der nächsten Kerze ist auch unserer enthalten.
 * Aufgabe der Simulation ist es nun, den Kauf-/Verkaufspreis zu ermitteln:
   Sie nimmt den Open-Kurs der nächsten Kerze mit einem Penalty von einem Tick (0.25 Punkte)

Der Fehler in der Simulation war, dass nicht die nächste Kerze zur Ermittlung des Kurses genommen wurde,
sondern die aktuelle, auf der auch der Trader sein Kauf-/Verkaufsentscheidung getroffen hatte.
Damit war die Steigerung die Kursveränderung, die zur Entscheidung geführt hat, bereits im Trade eingeschlossen.
Es war so, als könnte der Trader eine Kerze in die Zukunft sehen:

Er trifft seine Entscheidung am Ende der Kerze und kauft-/verkauft dann zum Preis vom Anfang der Kerze.
Dieser entscheidende - aber in der Praxis unmögliche - Vorausschau führt zu diesen phenomenal guten Ergebnissen
In der folgenden Tabelle werden die Auswirkungen beispielhaft für 300er Volumenkerzen am 01.10.2026 gezeigt:

               total_profit  trades  win_rate  p_factor  max_profit  min_profit
    korrekt          278.50     308      0.36      1.44       46.50      -15.00 
    fehlerhaft       889.75     326      0.51      2.77       55.50      -13.00 

Für kleiner Kerzen wird wird die Diskrepanz noch viel größer:
Bei kleineren Kerzen haben wir viel mehr Trades gesehen als bei längerem.
Der Vorteil kommt bei jedem Trade zum tragen.
Deshalb waren viele Trades so profitabel mit der fehlerhaften Simulation.


Die Moral von der Geschichte...
---------------------------------

Eine Glaskugel, mit der man die Entwicklung der ersten Kerze verhersehen könnte,
würde zu unermesslichem Reichtum führen.

Spaß bei Seite: Die Erkenntnis zeigt, wie wichtig die richtige erste Prognose ist.
Liegt man hier richtig, wird es schnell profitabel.
