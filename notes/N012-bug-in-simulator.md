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
In der folgenden Tabelle werden die Auswirkungen beispielhaft für 300er Volumenkerze am 01.10.2026 gezeigt:

               total_profit  trades  win_rate  p_factor  max_profit  min_profit
    korrekt          278.50     308      0.36      1.44       46.50      -15.00 
    fehlerhaft       889.75     326      0.51      2.77       55.50      -13.00 

Für kleiner Kerzen wird wird die Diskrepanz noch viel größer:
Bei kleineren Kerzen haben wir viel mehr Trades gesehen als bei längerem.
Der Vorteil kommt bei jedem Trade zum tragen.
Deshalb waren viele Trades so profitabel mit der fehlerhaften Simulation.

'Fehlerfreie' Simulation
--------------------------

In file://N011-volume-bar-sizes.md untersuchten wir die Auswirkungen unterschiedliche großer Volumenkerzen.
Dafür verwendeten wir die Daten von 5 ausgewählen Tagen.
In der folgenden Tabellen sieht man die zusammengefassten Werte dieser Tage,
wie sie mit einer korrigierten Simulation errechnet wurden:

    volume  total_profit  trades  win_rate  p_factor  max_profit  min_profit
       100       -225.50   14508      0.31      0.96       66.25      -10.25
       150        783.50    9684      0.32      1.06       44.25      -10.50
       300        715.25    4926      0.35      1.07       34.75      -14.50
       600        545.00    2485      0.32      1.08       56.00      -16.25
      1200        518.25    1227      0.33      1.15       44.50      -20.50
      1800        734.00     783      0.33      1.28      132.00      -23.00
      2400       1151.25     587      0.37      1.62      129.00      -22.50

Leider ist jetzt nichts mehr übrige von den hohen win_rates und den phänomenalen profit_factors.
Aber dennoch sind für große Volumenkerzen beachtliche Gewinne entstanden.
Ironie des Schicksals: Jetzt sind die großen Kerzen besser als die kleinen.
Zumindest mit diesem Trading-Algorithmus.

Das Ganze nun auch noch für die Zeitkerzen:

      time  total_profit  trades  win_rate  p_factor  max_profit  min_profit
       15s         86.25    3617      0.28      1.00       67.75      -25.00
       30s       1390.75    1773      0.31      1.36      132.75      -32.00
       60s        353.25     911      0.38      1.16      127.00      -33.00

Überraschenderweise erzielt Kent-Beck mit 30s-Kerzen die besten Ergebnisse:
Immerhin 1390.75 in 5 Tagen.
Hier die genau Austellung der einzelnen Tage:

      date  total_profit  trades  win_rate  p_factor  max_profit  min_profit
    14.09.        460.00     347      0.34      1.71      132.75      -13.50
    18.09.         56.75     352      0.31      1.09       40.50      -11.25
    23.09.        126.75     359      0.28      1.21       35.50      -13.50
    28.09.        330.25     376      0.32      1.36       62.25      -15.50
    01.10.        417.00     339      0.34      1.44       65.50      -32.00

Sind Zeitkerzen doch besser geeignet als Volumenkerzen?


Die Moral von der Geschichte...
---------------------------------

Eine Glaskugel, mit der man die Entwicklung der ersten Kerze verhersehen könnte,
würde zu unermesslichem Reichtum führen.

Spaß bei Seite: Die Erkenntnis zeigt, wie wichtig die richtige erste Prognose ist.
Liegt man hier richtig, wird es schnell profitabel.
