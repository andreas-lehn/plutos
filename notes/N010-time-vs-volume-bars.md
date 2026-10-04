Von zeitlichen zu volumenbasierten Kerzen
===========================================

Bisher haben wir den Trader mit 1-Minuten-Kerzen und geschätztem gewichteten Durchschnitt betrieben.
Da wir nun Tick-Daten von Databento erhalten haben, können wir auf volumenbasiert Kerzen umsteigen.
Offen ist, wie viel Volumen wir in die Kerze packen.
500 Trades sind sehr verbreitet.
Aber ist das ein gutes Maß?

Um uns dieser Frage zu nähern schauen wir uns den 1.10. an
und vergleichen verschiedene Volumina mit den 1-Minuten Kerzen als Referenz:

    time   total_profit  trades  win_rate  profit_factor  max_profit  min_profit
     60s        1180.25     182  0.543956       4.898431        73.0      -29.25

    volume total_profit  trades  win_rate  profit_factor  max_profit  min_profit
       100      5787.50    5002  0.499200       2.677536        27.0       -9.00
       250      3935.50    1995  0.521805       3.062361       35.50       -9.75
       500      2857.00    1002  0.519960       3.204901       63.00      -14.25   
      1000      1915.00     487  0.519507       3.222867       68.75      -17.75
      2500      1584.50     194  0.567010       4.986164       67.25      -15.25
      5000       903.75      99  0.555556       3.527972       96.00      -29.00

Es zeigt sich wieder das bereits bekannte Phänomen:
Viele kleine Trades erzeugen einen hohen Gewinn,
führen aber zu einer geringen win_rate und niedrigem profit_factor.
Dennoch: 5787.50 Punkte Gewinn bei 5002 Trades ist beeindruckend.

Interessant ist die Zeile mit den 2500er Kerzen:
Ein stattlicher Gewinn von 1584 bei 194 Trades.
Das ist ein deutlich höhere Gewinn als bei der 1-Minuten-Kerze (1180.25)
bei einer vergleichbaren Anzahl von Trades (194/182).
Win_rate von 56.7% und ein profit_factor von 4.99 ist excelent!

Ein Tag in 1-Minutenkerzen aufgeteilt führt zu 1380 Samples.
Bei den Volumen-Kerzen kann man das nicht genau sagen,
weil das ja vom Handelsvolumen abhängig ist.
Am 1.10. waren es etwa 3.7 Mio Trades. Daraus erben sich folgende Sample-Anzahlen:

    volume  samples
       100    37369
       250    14952
       500     7477
      1000     3738
      2500     1492
      5000      748

Wie man sieht, ist die Anzahl der Samples bei einem Volumen von 2500 sehr nahe dran an den 1-Minutenkerzen.
Um auf 1380 Samples zu kommen, hätte es an diesem Tag Volumenkerzen mit einem Volumen von 2707 gebraucht.

Wenn die Sample-Zahle höher sind, dann bedeutet das auch mehr samples pro Zeiteinheit.
Da wir die Filterkonstante im Trader nicht verändert haben,
aber implizit T kleiner geworden ist, filtern wir weniger.
Die Frage, die sich daraus ergbit:
Können wir durch eine stärkere Filterung bessere Ergebnisse erzielen?

Beginnen wir mit dem 100er Volumen und verstärken die Filterung (Filterkonstante wird kleiner)

    filter total_profit  trades  win_rate  profit_factor  max_profit  min_profit
      0.50      5787.50    5002      0.50           2.68       27.00       -9.00
      0.25      2553.50    2689      0.47           2.24       19.00       -7.50
      0.10       474.00    1113      0.42           1.43       17.75       -7.50

Die Trades gehen runter bei einer Filterung. 
Aber auch die win_rate und der profit_factor und damit total_profit.
Ohne das jetzt näher angeschaut zu haben,
ist der Verdacht, dass die Einstiegssignal zu spät generiert werden
und dann in den meisten Fällen der Zug schon lange abgefahren ist.

Aber vielleicht ist das 100er Volumen einfach zu klein.
Schauen wir uns das 1000er Volumen an:

    filter total_profit  trades  win_rate  profit_factor  max_profit  min_profit
       0.5      1915.00     487      0.52           3.22       68.75      -17.75 
       0.4      1449.00     387      0.53           3.13       68.75      -20.25 
       0.3      1195.00     290      0.55           3.35       47.00      -19.00 
       0.2       813.25     212      0.52           2.96       59.25      -14.25 
       0.1       217.00     111      0.42           2.02       33.00      -13.00 

Eine Filerung mit Faktor 0.3 kann eine Verbesserung erzielen.
Aber mit einem Gesamtgewinn von 1195.00 Punkten bei 290 Trades
ist das schlechter - weil mehr Trades - als die 1-Minutenkerze.

Zu guter letzt noch die vielversprechende 2000er Kerze:

    filter total_profit  trades  win_rate  profit_factor  max_profit  min_profit
       0.5      1600.00     232      0.57           4.16       71.25      -18.75
       0.4      1328.50     204      0.60           3.97       60.25      -18.75 
       0.3       726.00     161      0.55           2.72       60.25      -20.75 

Und die 2500er Kerze:

    filter total_profit  trades  win_rate  profit_factor  max_profit  min_profit
       0.5      1584.50     194      0.57           4.99       67.25      -15.25
       0.4      1319.75     167      0.59           4.84       67.25      -20.00 
       0.3       344.50     126      0.46           1.81       42.00      -25.00 

Aus dieser Untersuchung heraus zwei Kandidaten:

    volumen  filter  total_profit  trades  win_rate  profit_factor
       2500     0.4       1319.75     167      0.59           4.84
       2000     0.4       1328.50     204      0.60           3.97

Diese Kandidaten schlagen die 1-Minutenkerze deutlich:

       time  filter  total_profit  trades  win_rate  profit_factor
        60s     0.5       1180.25     182      0.54           4.89

Für die beiden obigen Kandidaten muss als nächstes eine breiter Datenbasis herangezogen werden,
um die Ergebnisse zu stüten.


Fazit
------

Volumenkerzen haben das Potential, die Ergebnisse zu verbessern.
Allerdings nicht dramatisch.


Offene Punkte
--------------

 * Warum ist ausgerechnet die 1-Minutenkerze so gut?
   Ist der zeitliche Faktor doch relevanter als gedacht?
 * Die Dynamik des Marktes schwankt sehr in Abhängigkeit von der Tageszeit.
   Gibt es für die unterschiedlichen Phasen Einstellungen, die zur jeweiligen Phase besser passen?
 * Wieso ist die zeitliche Filterung so schlecht?
   Die ursprüngliche Erwartung:
   Volumen-basiert Kerzen mit geringem Volumen und zeitlicher Filerung schlagen zeitbasierte Kerzen mit viel Volumen,
   hat sich nicht bestätigt.
 * Da die zeitliche Filterung so schlecht ist, gibt das einen Hinweis daruaf,
   wie wichtig ein kurze Latenz ist: von der Börse zum Bot und wieder zurück.
   Vor allen in dynamischen Tageszeiten.
 