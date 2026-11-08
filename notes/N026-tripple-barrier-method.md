Tripple barrier method
==========================

Zusammen kopiert von Meta-AI:

Die Triple-Barrier-Methode (eingeführt von Marcos López de Prado) ist der Goldstandard im Machine Learning für Trading.
Sie löst das größte Problem klassischer Kennzeichnungen:
Im echten Trading wartest du fast nie starr genau 10 Sekunden, um eine Position zu schließen.
Du hast Ziele und Risiko-Limits.
Die Methode legt um jedes deiner 10-Sekunden-Samples drei virtuelle Barrieren in die Zukunft.
Die Barriere, die der Kurs als Erste berührt, bestimmt das Label (die Klasse) für dein Modell.

    Preis ^
          |          ________________________ Obere Barriere (Take-Profit) -> Label: Long
          |         /  
          |        /   <-- Kursverlauf trifft die obere Schranke zuerst
          |  ----*--------------------------- Aktueller Kurs bei Start (t=0)
          |       \
          |        \_________________________ Untere Barriere (Stop-Loss)  -> Label: Neutral (oder Short)
          |
          +----------------------------------|--> Zeit
                                        t = 60s (Vertikale Barriere) -> Label: 0

Die Logik muss für Long und Short seperate ausgeführt werden.
Die unterschiedliche Dynamik von steigenden zu fallenden Kursen,
kann mit unterschiedlichen Schwellen für long und short ausgeglichen werden.


## Das mathematische Risiko-Rendite-Verhältnis (CRV)

Im professionellen Trading möchtest du im Durchschnitt mehr gewinnen, als du verlierst.
 * Wenn dein Profit-Target (obere Barriere) doppelt so weit entfernt ist wie dein Stop-Loss (untere Barriere),
   hast du ein Chance-Risiko-Verhältnis (CRV) von 2:1.
 * Der Vorteil für dein ML-Modell: Wenn dein Modell später eine Genauigkeit (Win-Rate) von nur 40 % erreicht,
   ist dein Bot unter dem Strich trotzdem hochprofitabel, weil die Gewinntrades doppelt so groß sind wie die Verlusttrades.


## Asymmetrie von Kauf- und Verkaufsphasen (Marktdynamik)

Märkte bewegen sich nach oben anders als nach unten.
Das Sprichwort heißt: *The market takes the stairs up, but the elevator down*
(Der Markt nimmt die Treppe nach oben, aber den Fahrstuhl nach unten).

Wenn du deine Daten labelst, musst du entscheiden, für welche Richtung du das Sample gerade auswertest:
 * Wenn du ein KAUF-Signal (Long) suchst:
     * Obere Barriere = Dein Gewinnziel (Take-Profit)
	 * Untere Barriere = Dein Risiko-Limit (Stop-Loss)
 * Wenn du ein VERKAUF-Signal (Short) suchst:
	 * Untere Barriere = Dein Gewinnziel (Take-Profit), weil du von fallenden Kursen profitierst!
	 * Obere Barriere = Dein Risiko-Limit (Stop-Loss)

Weil fallende Bewegungen beim MNQ oft viel schneller und explosiver ablaufen als steigende Bewegungen,
nutzen quantitative Trader für Short-Signale häufig andere Barrieren-Abstände
(z. B. engere Stops oder größere Targets) als für Long-Signale.


## Ein wichtiger mathematischer Sonderfall

Es gibt ein einziges Szenario in deiner Logik, das du im Code explizit abfangen musst,
damit das Labeling wasserdicht ist: Das *Gleichzeitigkeits-Problem*!

Was passiert, wenn innerhalb derselben 10-Sekunden-Kerze (oder innerhalb der nächsten 6 Samples) der Markt so extrem wild schwankt,
dass sowohl dein Long-Target als auch dein Short-Target im selben Zeitraum erreicht werden?
Für diesen Fall gibt es in der Quant-Praxis eine klare Priorisierungsregel:
 1. Die First-Touch-Regel (Empfehlung):
    Du musst prüfen, welches Target zeitlich zuerst (also in welcher Millisekunde oder in welchem der zukünftigen 6 Samples zuerst berührt wurde.
    Wenn in Sample +2 das Short-Limit gerissen wird und erst in Sample +4 das Long-Limit, gewinnt das Short-Limit.
 2. Die Verlust-Zuerst-Regel (Konservativ): Wenn beide Limits innerhalb desselben zukünftigen 10s-Samples berührt werden
    (weil der Markt in diesen 10 Sekunden massiv hoch und runter schoss), labelst du das Sample sicherheitshalber als Neutral. 
    Im Live-Trading weißt du nämlich nie, ob dich der Markt erst unglücklich ausgestoppt hätte, bevor er ins Ziel läuft.

## Klassenungleichgewicht

Das Klassenungleichgewicht (Class Imbalance) ist eine der größten Hürden beim Machine Learning im Trading.
Da Finanzmärkte die meiste Zeit in einer Seitwärtsphase verbringen oder leichtes Rauschen zeigen,
wird deine Zielklasse 1 (Neutral) massiv dominieren – oft macht sie 70 % bis 90 % deines gesamten Datasets aus.

Das Problem: Die _faule_ KI

Wenn dein Dataset zu 85 % aus der Klasse Neutral, zu 7 % aus Long und zu 8 % aus Short besteht,
lernt dein Gradient Boosting Modell folgendes:
_Wenn ich einfach immer 'Neutral' vorhersage, habe ich eine sensationelle Genauigkeit (Accuracy) von 85 %!_

Das Modell erzielt auf dem Papier tolle Metriken, ist für deinen Trading-Bot aber völlig nutzlos, da er niemals ein Signal generiert.
Hier sind die drei effektivsten Strategien,
wie du dieses Ungleichgewicht bei Tree-basierten Modellen (XGBoost, LightGBM, CatBoost) im Griff hast:


### Die richtige Verlustfunktion & Klassengewichtung (Empfehlung)

Anstatt die Daten künstlich zu verändern, sagst du dem Algorithmus während des Trainings,
dass Fehler bei den seltenen Klassen (Long und Short) viel teurer bestraft werden müssen als Fehler bei der Klasse Neutral.
Bei LightGBM oder XGBoost kannst du dafür direkt die Klassengewichte (Class Weights) berechnen und übergeben.

    from sklearn.utils.class_weight import compute_class_weight
    import numpy as np
    import lightgbm as lgb

    # y_train enthält deine Labels (0, 1, 2)
    classes = np.unique(y_train)

    # Berechne die Gewichte automatisch basierend auf der Häufigkeit
    # Seltene Klassen erhalten ein hohes Gewicht, häufige ein niedriges
    weights = compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
    class_weights_dict = dict(zip(classes, weights))

    print(f"Berechnete Gewichte: {class_weights_dict}")
    # Beispiel-Ausgabe: {0: 4.2, 1: 0.4, 2: 3.9} -> Fehler bei Short(0) wiegen 10x schwerer als bei Neutral(1)!

    # Beim Trainieren des LightGBM Classifiers übergibst du das einfach:
    model = lgb.LGBMClassifier(
        objective='multiclass',
        num_class=3,
        class_weight=class_weights_dict, # Hier greift die Magie
        random_state=42
    )
    model.fit(X_train, y_train)


### Downsampling der _Neutral_-Klasse

Da die 10-Sekunden-Kerzen extrem viele Datenpunkte erzeugen, hast du meistens ohnehin mehr als genug Daten.
Anstatt komplexe Synthese-Methoden (wie SMOTE) zu nutzen, die bei Zeitreihen oft zu Overfitting führen,
nutzt man im Trading eher Random Under-Sampling der Mehrheitsklasse.
 * **Logik:** Du behältst alle deine Long (2) und Short (0) Samples.
   Aus den riesigen Mengen an Neutral (1) Samples wirfst du zufällig so viele weg,
   bis das Verhältnis z. B. 1:1:1 oder zumindest 1:2:1 beträgt.
 * **Vorteil:** Das Training geht drastisch schneller und das Modell fokussiert sich viel stärker auf die echten Ausbruchsmuster.


### Die Metriken-Falle: Nutze niemals _Accuracy_!

Wenn du dein Modell evaluierst, darfst du dich niemals auf die klassische Genauigkeit (Accuracy) verlassen.
Nutze stattdessen den F1-Score (Macro) oder die Precision und Recall für jede Klasse einzeln.
Für deinen Trading-Bot ist die wichtigste Kennzahl die Precision für Long (2) und Short (0):
 * **Precision (Präzision):** _Wenn das Modell sagt 'Kaufen (2)', wie oft lag es dann tatsächlich richtig?_
 * Wenn deine Long-Precision bei 55 % oder 60 % liegt, ist das beim hochgehebelten MNQ-Future
   (unter Berücksichtigung deines Chance-Risk-Verhältnisses von z.B. 2:1) eine absolute Gelddruckmaschine,
   selbst wenn das Modell 80 % der eigentlichen Marktbewegungen verpasst (niedriger Recall).

## Anhang: Nutze relative Abstände statt absoluten Abständen

Momentan funktioniert mein Modell sehr gut, weil sich der Nasdaq für die aktuellen Testdaten in einem engen Kurs-Korridor befindet.
Deshalb kommt es nicht zum tragen, ob als Abstand die absolute Differenz oder die prozentual verwendet wird.
Sobald der Nasdaq sich aber eine größere Spannweite umfasst, kommt der Unterschied zum tragen.
Deshalb muss bereits jetzt der relative Abstand verwendet werden,
damit die gelernte Werte auf die Zukunft übertragbar sind.
