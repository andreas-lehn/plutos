Gradient Boosting Data Sets
================================

Jeder Tag stelt eine Einheit dar,
die wir fürs Training oder die Evaluierung der Gradient Boosting Modells verwenden können.
Ingesamt brauchen wir drei verschiedene Mengen an Datensätze für unterschiedliche Zwecke:

 1. Trainingsdaten: Mit diesen Daten wir das Modell trainiert.
 2. Evaluierungsdaten: Auf diesen Daten stellt der Algo fest, ob sich das Lernergebnis noch verbesssert.
    Damit verhindern wir ein Overfitting
 3. Testdaten: Mit diesen Daten überprüfen wir dei Performance des Modells

Um die unterschiedlichen Wochentage in den Datensätzen korrekt abzubilden,
wird ein 6-Tage-Zyklus angewandt.
Innerhalb jedes 6-Tageszyklus werden die einzelnen Tage wie folgt verwendet:

 1. Training
 2. Training
 3. Evaluierung
 4. Training
 5. Training
 6. Test


Damit erreichen wir ein gutes Verhältnis von Trainingsdaten, Eval- und Testdaten.
Außerdem ist sichergestellt, dass die Wochentage mit der Zeit gleichmäßig verteilt
in den einzelnen Datensätzen vorkommen.

Der feste Zyklus hat den großen Vorteil, dass wir anhand des Datums ermitteln können,
zu welcher Kategorie der Datensatz gehört.
Nehmen wir an, wir starten mit unseren Daten am Mo. 07.09.2026.
Dann gehört dieser Montag zu den Trainingsdaten.
Der Mittwoch dieser Woche, also der 09.09.2026 ist ein Evaluierungstag.
Der Montag der darauffolgenden Woche ein Testtag.

Ein Algorithmus, der zu einem Datum die entsprechende Kategorie ausgibt,
ist in `datasetcategory.py` implementiert.
