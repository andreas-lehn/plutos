Who to beat?
============
 
 Wie bereits vor ein paar Wochen realisiert, muss der Bot nicht die Instiotutionen, sondern die retailer schlagen.
 Klar, gewinnt man in beiden Fällen, die Chance, eine Institution zu schlagen, kommt so häufig vor wie ein Sechser im Lotto.  

 Nun stellt sich natürlich die Frage, was die größten Fehler/Verluste der _Retailtrader_ sind und wie man diese ausnutzen kann.
 Das schlechteste was einem Retailer passieren kann ist der Fehlschlag eines Ausbruchs, wenn er auf diesen spekuliert.
 Man spricht in diesem Falle von _trapped Buyern/Sellern_.
 Das Szenario ist simpel: Der Markt akkumuliert, handelt eine Order über/unter der Akkumulation an, Trader steigen ein.
 Findet der Markt allerdings keine weiteren Marketorders, welche den Preis weiter aus der Akkumulation schieben,
 so kommt der Preis sehr schnell wieder zurück zum fairen Wert der Sammelphase.
 Durch die generelle Akzeptanz in diesem Preisbereich ist es nicht unwahrscheinlich,
 dass dieser nochmals durchhandelt wird oder gar in die Gegenrichtung ausbricht.
 Zusätzlich stehen alle Positionen, welche auf einen direkten Ausbruch spekuliert haben, im Minus.
 Das Auflösen, sowie das Erreichen einer SL-Order,
 stellt nichts anderes als eine Market-Order entgegen der ursprünglich geplanten Richtung dar. 

 Man spricht hier von einem Fehlausbruch oder **Fake**.
 Das **tükische** an dieser Situation?
 Die **Marktdynamik** eines _Ausbruchs_ und eines _Fakes_ sind visuell identisch!  
 Nur wer die Daten tiefer betrachtet kann es vorher erkennen.
 Reaktionszeit spielt hierbei natürlich auch eine Rolle. 


 Konzept Dolos
-------------- 

Dolos ist in der griechischen Mythologie die Personifikation der Täuschung, des Hinterhalts und der List.
Die Namensgebung erscheint nun schlüssig.  
Wer sich am Markt, als Händler, durchsetzen will, muss die Konkurrenz schlagen, sie _überlisten_
und darf sich nicht selbst _täuschen_ lassen.
Wer erkennt, wo sich andere _täuschen_, schlägt die breite Masse und wird nicht selbst getäuscht.

Eine konkrete Umsetztung dieses Konzepts muss noch erarbeitet werden.
Der zugrunde liegende Gedanke kann durchaus ein funktionierendes System erzeugen.


Eigener Algorithmus oder zweite Facette?
-----------------------------------------

Es ist mir nicht klar ob Dolos ein eigener Algorithmus oder die zweite Persönlichkeit des Plutos werden sollte.  
Kurzgesagt, ob er alleinstehend existieren oder in Plutos integriert werden sollte,
da sich die Ansätze doch grundlegend unterscheiden. 

Während Plutos sich auf die Vortsetzung eines Trends fokussiert,
möchte Dolos den Fehlschlag eines Ausbruchs aus einer Akkumulation finden.
Damit einher geht auch gegen den eigentlichen Trend zu handeln.
Trades des Dolos sind dafür auch deutlich kleiner, so groß wie die Akkumulation eben war/ist.  

Plutos möchte nicht durch _Rangephasen_ gebremst werden.
Dolos möchte den kurzfristig entstehenden Trendbruch finden und in eine Range zurückkehren.
Durch die Addition der Kontrakte können keine Gegenpositionen eröffnet werden.
Die Konzepte können also nicht paralell auf demselben Konto ausgeführt werden.  
Für eine Implementierung müsste der Bot also erkennen, ober er bereits in einem _Trend Trade_ ist,
wie das aktuelle Umfeld aussieht und **früh genung** erkennen ober der Ausbruch echt oder unecht ist,
um dann seine _"Persönlichkeit"_ zu wählen. 


Erwartungen, Wünsche und Schwierigkeiten
----------------------------------------

 * Der Bot hat insgesamt einen besseren Überblick über die gesamte Stituation, er kenn nun mehr Szenarien.
 * Die Anzahl der Trades bleibt gleich oder verringert sich gar.  
   Entweder stoppt Dolos einen Einstieg durch das Konzept Plustos aufgrund gemischter Signale  
   oder der Bot entscheidet sich für einen Einstieg über Dolos statt Plutos.
 * Die *WinRate* erhöht sich spürbar!
   Durch die kleinen Stopps des Plutos führt ein Fehlausbruch unmittelbar zu einen Verlust.  
   Verlust des Plutos werden vermieden oder gar zu Gewinnen über das Konzept Dolos.
   Es könnte also ein Absicherungsalgo werden.
 * Genaue Deklaration der Rahmenbedingungen:  
    - Wann ist eine Range eine Range?  
    - Wie kann sich ein Fehlausbruch äußern bzw. welche Äußerungen sind relevater als andere?  
    - TP und SL Setzungen  
    - Kann ein TP bei einem Dolos-Einstieg und anhaltender Plutosbestätigung vergrößert werden?  
    - Mit welchem Gewinnfaktor ist zu rechnen?  
    - Wie erkennt man, über welches Konzept der Bot eingestiegen ist?