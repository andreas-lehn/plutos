Yesterdays weather
=====================

Die Anekdote
--------------

Als man begann, die Wettervorhersage mit dem Computer zu machen,
entwicklete man dafür Modell, um das Wetter verherzusagen.
Dazu war auch viel Forschung erforderlich.
Irgendwann waren die Forscher sehr glücklich,
weil sie ein Verhersagegenauigkeit von 75% erreichten.

75% Vorhersagegenauigkeit klingt auf den erste Blick sehr gut:
In 3 von 4 Fällen richtig.
Bei der Börse im Intraday-Trading versucht man 55%-60% zu erreichen,
wobei 60% sehr gut ist.

Allerdings sieht die Vorhersage-Wahrscheinlichkeit nicht mehr so gut aus,
wenn man eine andere Prognose-Methode wählt: Yesterdays-Weather.
Die Methode hat eine Vorhersage-Wahrscheinlichkeit von 80%
und geht wie folgt:

Morgen wir das Wetter so, wie es heute ist!

Mit dieser einfachen Methode landet man zu 80% einen Treffer.
Jeder andere Modell, das weniger als 80% schafft, ist damit schlecht.


Übertragung auf die Börse
---------------------------

Für die Vorhersage der Böresenkurse werden ebenfalls komplizierte Modelle entwicklet.
Auch wir haben vor, eine KI zu trainieren, in der Hoffnung, damit gute Ergebenisse zu erzielen.
Yesterdays Weather übertragen auf die Börsenkurse bedeutet,
dass sich die Kurse so weiterentwickeln werden, wie sie es in der Vergangenheit getan haben.

The trend is your friend!

In dieser Ausssage kommt das genau zum Ausdruck:
Wenn die Börse einmal steigt, wird sie weitersteigen.
Auch wegen dem selbstverstärkenden Effekt, dass mehr Leute kaufen.

Niemals in ein fallendes Messer greifen!

Das ist dasselbe für fallende Kurse. 
Wegbleiben, wenn es fällt, weil es wird wahrscheinlich weiter fallen.

Es besteht also ein große Wahrscheinlichkeit,
dass Yesterdays Weather auch für die Börse ein gute Prognosemöglichkeit darstellt.


Lineare Extrapolation
-------------------------

Linear Extrapolation ist die algorithmische Varianten von Yesterdays Weather für Börsenkurse.
Im folgenden möchte ich ein Verfahren erläutern.

Ausgangsbasis sind Volumentkerzen, wie in N005 beschrieben.
Jede Volumentkerze hat einen gewichteten Mittelwert und eine Volatilität.
Das ist der gewichtete Mittelwert ist der ausschlaggebende Kurs.
Technische gesehen er eine Filterung auf vielen Messungen.

Über linare Interpolation leget man eine gerade durch die gewichteten Mittelwert der letzen drei kerzen.
Dann errechnet man mit dieser gerade den gewichteten Mittel Wert der übernächsten Kerze
(zwei Kerzen Prognose).

Mit dem durchschnitt der Volatilität der letzen beiden Kerzen bestimmt man den niedrigsten und höchsten Kurs der Kerze.
Jetzt hat man ein Prognose-Intervall, das man zum Traden verwenden kann.


Einstiegssignal
-------------------

Mit dem Prognose-Intervall und dem letzte Schlusskurs kann man Einstiegssignale generieren.
Dazu errechnet welche Position der letzte Schlusspunkt zwischen Hoch und Tief der Prognose einnimmt.
Das ergibt typischerweise einen Wert zwischen 0.0 und 1.0.
 
 * 0.0: Schlusskurs ist beim Tief
 * 0.5: Schlusskurs liegt genau zwischen Hoch und Tief
 * 1.0: Schlusskurs ist am Hoch

 * Long gehen: Wert < 0.3
 * Short gehen: Wert > 0.7

Mit dem darauf folgenden Prognose-Intervall kann man entscheiden ob man drin bleibt oder raus geht:

 * Drin bleiben: Wert < 0.5 (bei Long), Wert > 0.5 (bei Short)
 * Sonst raus


Erfolgskontrolle
------------------

In einer Simulation kann die Strategie sehr einfach überprüfen.
Für die Richtigkeit des Einstiegsignal kann man sich die Differenz zwischen dem Anfangskurs der nächste und dem Endkurs der übernächsten Kerze anschauen.

Für das Ausstiegssignal kann man sich was ähnliches überlegen.
Aber zunächste wäre mal wichtig korrekte Einstiegsignale zu ermitteln
und mit dem Algo zu prüfen.
