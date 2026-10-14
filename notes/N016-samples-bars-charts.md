Samples, Bars, Charts,...
===============================

An der CME kommen an Stoßzeiten bis zu 100 Trades pro Sekunde zustande.
Der Preis für einen einzelnen Trade ist dabei wenig aussagekräftig:
Die Preis schwanken im Mikrosekunden-Bereich hin und her.

Betrachtet man die Kursentwicklung an der CME regelungstechnisch,
das ist das _Kurssignal_ ein sehr verrauschtes Signal.
Deshalb hat Plutos das Konzept des Samples:

Ein Sample fasst alles Trades innerhalb von einer Sekunde zu einer Einheit zusammen.
Eine Sekunde ist das kürzeste Zeitintervall, mit dem Plutos arbeitet.
Das Sample stellt eine Abtastung des Signals dar.
Die vielen Trades innerhalb des Samples sind mit vielen Messungen zu vergleichen,
die man dafür macht, die Genauigkeit des Messergebnisses zu verbessern.

Aus Sicht von Plutos hat das Sample keine zeitliche Ausdehnung.
Plutos tut so, als seien alle Käufe innerhalb eines Samples zur selben Zeit passiert.
Der Kurs des Samples (die Messung) entspricht dem gewichteten Durchschnitt aller Trades.
Deshalb reicht es aus, dem Sample einen Zeitstempel auf Sekundenbasis zu geben.
(Im Gegensatz zum Sample hat der Trade einen Zeitstemple auf Nano-Sekunden-Basis.)

Zeitliche Ausdehnung entsteht erst durch die Kerze (Bar).
Eine Kerze fasst viele Samples zu einer größeren Einheit zusammen.
Dadurch hat sie eine Dauer von n Sekunden.

Da konzeptionell das Sample keine zeitliche Ausdehnung hat,
macht für ein Sample ein Öffnung- und Schlusskurs keinen Sinn.
Diese Kurse wären aufgrund des verrauschten Signals willkürliche Messungen.
Bei der Kerze sieht das anders aus:
Die hat Samples als Basis, die eine einigermaßen zuverlässige Aussage
über den aktuellen Kurs machen.

Deshalb hat eine Kerze einen Öffnungs- und Schlusskurs.
Der Öffnungskurs entspricht dem Kurs des ersten Sample.
Der Schlusskurs entspricht dem Kurs des letzten Samples.

Ein Chart ist eine Zusammenfassung von Kerzen,
also Objekten mit einer zeitlichen Ausdehnung.
Das unterscheidet das Chart von der Kerze:
Die Kerze besteht aus Elementen ohne Dauer
während das Chart Elemente mit einer Dauer enthält.

Vermutlich ist Chart kein guter Begriff für diese Objekt.
Ein Chart verbindet man eher mit einem Diagramm.
Aber bisher ist noch kein besser Begriff aufgetaucht...

Ab jetzt wird es rekursiv:
Ein Chart könnte wieder Charts enthalten.
Letztendlich sieht ein Chart von außen betrachtet wie eine Bar aus:
Ein Chart hat einen Öffnung- und Schlusskurs, ebenso wie alle anderen Kurse
und ein Kursprofil.

Ein Sample ist - wenn man es genau betrachtet - nichts anderes als ein Volumenprofil.
Sowohl Kerze als auch Chart führen intern ein eigenes Volumenprofil
Hierfür verwenden sie das Sample.
