Untersuchung der slope_threshold
==================================

slope_threshold ist ein parameter des KentBeckTraders.
Steigung (slopes) unterhalb diese Parameter werden wie 0.0 behandelt.
Der Parameter ist dafür da,
um kleine Schwankungen um den Nullpunkt zu eliminieren.
Dadurch werden weniger Kaufsignale generiert.

Die Untersuchung basiert auf den Daten von Yahoo Finanze in der Zeit von 2026-09-08 - 2026-10-02.
Bei den Daten handelt es dich um OLHCV-Kerzen im 1 Minutentakt.
Die folgende Tabelle zeigt den Einfluss des Parameter:

threshold  total_profit  number_of_trades  win_rate  profit_factor
  0.00000      15179.50              3376      0.53           4.10
  0.00001      15179.50              3376      0.53           4.10  
  0.0001       15185.25              3377      0.53           4.10
  0.0005       15189.75              3375      0.53           4.10  
  0.001        15196.75              3374      0.53           4.11
  0.005        15131.50              3367      0.52           4.08
  0.01         15094.75              3366      0.52           4.08
  0.1          14892.25              3277      0.52           3.84
  1.0          12880.00              2303      0.56           4.43
  2.0          10159.75              1469      0.59           6.44 
  5.0           3723.00               393      0.57          11.51
 10.0.           954.00                64      0.42          11.92


Betrachtet man den Gesamtgewinn, dann ist ein slope_threshold von 0.001 offenbar der sweep spot.
Alle anderen Wert erzielen ein geringeres Gesamtergebnis.

Überraschend ist, dass die Einstellung von 0.0001 sogar zu einem Trade mehr führt,
als kein Threshold. 
Da des Gesamtergebnis besser ist, war das wohl ein profitable Trade.

Mit der Einstellung von 0.001 werden 2 (bzw. 3) Trades weniger gemacht,
als mit kleineren Einstellung.
Es werden offenbar unprofitable Trades weggelassen.

Erhöht man den Threshold deutlich,
so kann man auch erkennen, dass die Anzahl der Trades deutlich abnimmt.
Bei 1.0 sind es schon 1/3 weniger Trades.
Bei 5.0 nur noch 1/10.
Dadurch sinkt jedoch auch der Gesamtgewinn deutlich ab.

Je höher der Wert, desto Wert, desto größer wird fast immer auch die win_rate und der profit_factor.
Die win_rate hat bei 2.0 ihr Maximum mit 0.59.
Der Profit_factor steigt bis auf fast 12 bei einem Threshold von 10.

Für Day-Trader sind die Kennzahlen win_rate und profit_factor das Maß der Dinge.
Es überrascht jedoch, dass sehr hohe Werte bei diesen Kennzahlen zu einem deutlich geringern Gewinn führen.
Vielleicht sind diese Kennzahlen gar nicht so entscheidend?
