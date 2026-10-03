Zeitliche Filterung des KentBeckTraders
=========================================

Der KentBeckTrader filtert die Mittelwerte der Kerzen und Steigung der Mittelwerte.
Dabei handelt es sich um eine in der Regelungstechnik üblichen PT1-Filterung.
Die typischerweise im Finanzwesen eingesetzt Filterung mit gleitenden Durchschnitten nicht gewählt.
Grund ist die einfachere und schnellere Berechenbar- und Einstellbarkeit des PT1-Filters.

In der nachfolgenden Tabelle wird der Einfluss des Parameters auf das Trading-Ergebnis dargestellt.

param  total_profit  number_of_trades  win_rate  profit_factor  
  1.00     19073.75              4802      0.50           3.44
  0.95     18388.75              4673      0.50           3.51
  0.75     17863.25              4187      0.50           3.80  
  0.60     16571.25              3790      0.51           3.89 
  0.50     15196.75              3374      0.53           4.11
  0.40     13051.75              2823      0.53           3.88
  0.25      6086.00              1852      0.47           2.77    
  0.10      1204.25               708      0.41           1.75  

Hinweis: Ein Parameterwert von 1.0 entspricht keiner Filterung.

Die win_rate hat bei Wert von 0.4 bis 0.5 ihren Höchstwert.
Der profit_factor ist bei 0.5 am höchste.
Auf Basis dieser Kennzahlen scheint ein Wert von 0.5 für optimal.

Allerdings zeigt auch diese Untersuchung,
dass der Gesamtgewinn ansteigt, wenn die Anzahl der Trades zunimmt.
Da die win_rate nur nimmt nur leicht.
Aber wegen des kleiner profit_factor sind deutlich mehr Trades für die Gesamtgewinn erforderlich.
