Volumen bar sizes
=====================

In dieser note möchte ich mich mit der größe von Volumenbars auseinander setzen.
Folgende Größen sind 100, 150, 300, 600, 1200, 1800, 2400.
Die Größen werden an jeweils 5 Tagen für den MNQZ6 simuliert.

Für die Simulation verwenden wir Tage mit unterschiedlichem Handelsvolumen.
Dabei handelt es sich um 5 verschieden Wochentage mit stark unterschiedlichem Handelsvolumen.
Die Tage und ihr Handelsvolumen sind:

    Tag       Datum  Tagevolumen 
     Di  15.09.2026    1.615.400
     Fr  18.09.2026    1.926.200
     Mi  23.09.2026    2.242.000
     Mo  28.09.2026    2.889.700
     Do  01.10.2026    3.725.700
     
Wie man sieht, steigt das Handelsvolumen über die Zeit an.
Das liegt vielleicht daran, dass am 14.09.2026 der roll-over Tag von MNQU6 auf MNQZ6 war.

Di, 2026-09-14
---------------

    size  total_profit  trades  win_rate  profit_factor  max_profit  min_profit
     100       2025.25    1340  0.504478       2.819632       29.75       -8.25
     150       1877.75     916  0.515284       3.014213       52.00      -10.50
     300       1246.00     464  0.512931       2.968404       43.50      -11.75
     600        698.25     231  0.493506       2.507285       41.00      -14.25
    1200        517.25     107  0.514019       2.712748       51.75      -15.25
    1800        482.75      66  0.500000       3.561008      135.00      -31.75
    2400        502.25      45  0.555556       4.555752      146.50      -21.50

Fr, 2026-09-18
---------------

    size  total_profit  trades  win_rate  profit_factor  max_profit  min_profit
     100       1465.25    2653  0.447041       1.901831       18.25       -6.00
     150       1475.75    1740  0.482759       2.254623       24.50       -5.50
     300       1279.00     897  0.496098       2.720821       25.25       -8.25
     600        876.50     455  0.503297       2.667142       28.50       -9.25
    1200        605.25     224  0.459821       2.645819       43.75      -10.00
    1800        481.75     144  0.493056       2.637213       47.75      -13.75
    2400        617.75     102  0.617647       4.504965       46.75      -11.75

Mi, 2026-09-23
---------------

    size  total_profit  trades  win_rate  profit_factor  max_profit  min_profit
     100       2410.00    3019  0.477642       2.292918       17.00       -6.25
     150       2180.75    2004  0.500000       2.642750       17.75       -6.50
     300       1523.25    1023  0.484848       2.539414       25.00       -8.25
     600       1189.00     507  0.497041       3.007598       36.50      -11.50
    1200        831.50     268  0.492537       2.752371       33.50      -14.00
    1800        440.25     171  0.456140       2.052600       38.50      -13.75
    2400        699.25     131  0.503817       3.294504       46.75      -20.75

Mo, 2026-09-28
--------------

    size  total_profit  trades  win_rate  profit_factor  max_profit  min_profit
     100       3996.00    3953  0.483177       2.437022       74.75       -8.75
     150       3759.75    2661  0.488538       2.796560       50.00       -9.25
     300       2542.50    1358  0.505155       2.749527       37.50      -12.00
     600       1963.50     715  0.499301       2.836334       34.75      -13.00
    1200       1073.75     356  0.494382       2.341768       44.50      -20.25
    1800       1056.50     233  0.506438       3.088977       71.75      -15.25
    2400        775.25     165  0.503030       2.749013       63.75      -26.75

Do, 2026-10-01
--------------

    size  total_profit  trades  win_rate  profit_factor  max_profit  min_profit
     100       5784.00    5006  0.498602       2.715684       25.50       -7.50
     150       4687.75    3379  0.501628       2.755712       28.25       -9.75
     300       3440.50    1681  0.511005       2.915113       42.00      -14.50
     600       2526.25     839  0.523242       3.096473       67.00      -18.75
    1200       1890.00     405  0.530864       3.539469       64.50      -16.75
    1800       1761.75     259  0.583012       4.606448       57.50      -19.75
    2400       1679.00     200  0.635000       4.981031       61.00      -18.25


Beobachtungen
--------------

Es zeigt sich wieder dasselbe Bild wie in vorherigen Untersuchungen:
Je kleiner die größe der Kerze, desto größer wird der Gesamtgewinn.
Trotz einer relative niedrigen win_rate und profit_factor macht die Anzahl der Trades den Unterschied.

Dafür zeigen die großen Kerzen vor allem beim handelsstarken Donnerstag ist Stärke
in Bezug auf win_rate und profit_factor.
Aber das Gesamtergebnis ist dennoch enttäuschend:
1679.00 Punkten für die 2400er Kerze im Vergleich zu
5784.00 Punkten für die 100er Kerze am volumeneichen Donnerstag spricht Bände.

Betrachtet man den Anstieg der Trades im Vergleich zur Verbesserung des Gewinns,
dann sieht man, dass die Trades überproportional ansteigen.

Der Handelstag hat 1380 Minuten.
Wenn die Anzahl der Trades diesen Wert übersteigt,
dann handeln wir mehrmals in der Minute.
Betrachtet man dann noch das unterschiedliche Handelsvolumen über den Tag verteilt,
dann kommen wir in den Sekundenbereich.
Das passt nicht zu einem schmalbrüstigen Python-Bot betrieben auf einer freien Web-Seite.

Vor diesem Hintergrund scheiden kleinere Größen als 300 aus.
300 ist bereits grenzwertig. 
Hier muss die Praxis zeigen, ob das tauglich ist.
Eine große von 600 (oder auch 500) sollte gut machbar sein.


Gewinn pro Trade
------------------

Auch wenn es keine offizielle Kennzahl ist, dann möchte ich gerne ausrechen,
wieviel Gewinn pro Trade die verschieden Größen erreichen.
Wir summieren dazu einfach alles auf und teilen den Gesamtgewinn durch die Anzahl der Trades:

    size total_profit  trades  profit/trade
     100     15680.50   15971          0.98
     150     13981.75   10700          1.31
     300     10031.25    5423          1.85
     600      7253.50    2747          2.64
    1200      4917.75    1360          3.62
    1800      4223.00     873          4,84
    2400      4273.50     643          6,65


Fazit
-------

Eventuell entscheidet die Leistungsfähigkeit der Infrastruktur darüber,
wieviel Trades pro Minute durchgeführt werden können
und damit indirekt über den Gesamtgewinn.
Vielleicht ist das der Grund,
weshalb professionelle Day-Trader ihre riesigen Rechner direkt im Gebäude der CME stehen haben...
