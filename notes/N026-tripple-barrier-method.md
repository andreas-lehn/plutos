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

## Evaluierung der Performance

Um die reale Performance deines Trading-Modells zu ermitteln, darfst du dich nicht auf Standard-Metriken der Informatik verlassen.
Eine hohe „Accuracy“ (Genauigkeit) nützt dir gar nichts, wenn das Modell in den falschen Momenten verliert.
Die Performance-Ermittlung erfolgt in zwei Stufen:
Erst die statistische Qualität des Modells (Klassifikation) und danach die finanzielle Qualität (Simulierter Backtest).


### Stufe 1: Die statistische Qualität (Classification Report)

Du nutzt die Vorhersagen deines Modells auf dem unberührten Test-Set (Tag 6)
und erstellst eine sogenannte Confusion Matrix sowie einen Classification Report.
Für deinen Bot sind hierbei zwei Metriken für die Klassen Long (2) und Short (0) lebenswichtig:

#### Precision (Präzision) – Deine Erfolgsquote:

Wenn das Modell ein Signal gibt, wie oft liegt es richtig?
Da du ein Chance-Risiko-Verhältnis (CRV) von z. B. 2:1 eingebaut hast,
reicht hier oft eine Precision von > 45 %, um profitabel zu sein.

#### Recall (Sensitivität) – Deine Signalhäufigkeit:

Wie viel Prozent aller tatsächlichen Ausbrüche erkennt das Modell?
Im Trading ist ein niedriger Recall (z. B. 10 %) völlig okay.
Es bedeutet nur, dass der Bot wählerisch ist und seltene, aber sichere Trades sucht.


    from sklearn.metrics import classification_report, confusion_matrix

    # y_test = Wahre Labels (0, 1, 2)
    # y_pred = Die Vorhersagen deines Modells (0, 1, 2)
    print(classification_report(y_test, y_pred, target_names=['Short', 'Neutral', 'Long']))


### Stufe 2: Die finanzielle Qualität (Der Mini-Backtester)

Die wichtigste Wahrheit liefert dir nur die simulierte Equity-Kurve (dein Kontoverlauf).
Du simulierst im Code exakt das, was dein Bot am Test-Tag getan hätte:
Bei einem Signal kaufst/verkaufst du und prüfst, ob der Kurs zuerst dein TP oder dein SL erreicht.


## Kennzahlen

Die 3 ultimativen Trading-Kennzahlen für dein Walk-Forward-Training

Wenn du deinen 4-1-1 Rhythmus über mehrere Wochen hinweg rollierend testest,
addierst du die finanziellen Ergebnisse aller Testtage auf und berechnest diese drei Metriken:

 1. Profit Factor (Leistungsfaktor):
    \(\text{Profit\ Factor}=\frac{\text{Summe\ aller\ Gewinntrades}}{\text{Summe\ aller\ Verlusttrades}}\)
    Ein Wert über 1.0 bedeutet, dass der Bot profitabel ist.
    Gute ML-Systeme im Intraday-Bereich liegen oft zwischen 1.2 und 1.6.
 2. Maximum Drawdown (Maximaler Verlustschmerz): 
    Was war der größte zwischenzeitliche Rückgang deines simulierten Kapitals von einem Höchstpunkt zu einem Tiefpunkt?
    Das zeigt dir, ob dein Konto die Strategie überlebt.
 3. Sharpe Ratio (Risikobereinigte Rendite):
    Setzt deinen Gewinn in Relation zu den Schwankungen deiner Equity-Kurve.
    Beim tageweisen Walk-Forward-Trading willst du eine Sharpe Ratio von > 1.5 sehen.

## Übergang von statistischer Vorhersage zu Execution-Stragegy

Das ist der klassische Übergang von der statistischen Vorhersage zur Execution-Strategie!

Du hast vollkommen recht:
Raw-Klassifikationen von Machine-Learning-Modellen geben dir Wahrscheinlichkeiten, 
z. B. [Short: 0.25, Neutral: 0.40, Long: 0.35], aber keine Handelsbefehle.
Um aus diesen drei Wahrscheinlichkeiten harte Kauf- oder Verkaufssignale zu generieren,
nutzt man in der Praxis primär zwei bewährte Ansätze.


### Ansatz 1: Der feste Konfidenz-Schwellenwert (Confidence Threshold)

Die simpelste und robusteste Methode:
Du nimmst die Wahrscheinlichkeit der Klasse und prüfst, ob sie eine von dir definierte Alpha-Schwelle überschreitet.
Da die Klasse Neutral sehr oft dominiert, reicht der Standard-Ansatz _nimm das Maximum_ nicht aus.
Du suchst nach außergewöhnlich hoher Sicherheit für einen Ausbruch.

Logik: Da die Summe aller drei Wahrscheinlichkeiten immer 1.0 (100 %) ergibt,
ist alles über 0.33 theoretisch bereits die Mehrheit.
Für ein echtes Signal forderst du aber einen Sicherheitsaufschlag.

Regel:
 * Gehe LONG, wenn P(Long) > 0.45 (oder 0.50, je nach gewünschter Strenge).
 * Gehe SHORT, wenn P(Short) > 0.45.
 * In allen anderen Fällen: Tu nichts (NEUTRAL).

### Ansatz 2: Das Signal-Delta (Wahrscheinlichkeits-Spread)

Dieser Ansatz schaut nicht auf die absolute Höhe, sondern auf das Verhältnis zwischen der Long- und Short-Wahrscheinlichkeit.
Er eignet sich besonders gut, wenn der Markt in eine volatile Phase übergeht und die Klasse Neutral plötzlich sehr klein vorhergesagt wird,
weil die KI weiß, dass eine heftige Bewegung kommt, sich aber bei der Richtung noch minimal unsicher ist.

Die Formel:
    \(\text{Signal\ Delta}=P(\text{Long})-P(\text{Short})\)

Regel:
 * Gehe LONG, wenn Signal Delta > 0.15 UND P(Neutral) < 0.50.
 * Gehe SHORT, wenn Signal Delta < -0.15 UND P(Neutral) < 0.50.

### Wichtiger Optimierungs-Tipp: Die ROC-Kurve nutzen

Wie findest du den perfekten Schwellenwert (ob 0.40, 0.45 oder 0.55)?
Das ermittelst du während deiner Evaluierungs-Phase (Tag 5):
 * Wenn du den Schwellenwert sehr hoch ansetzt (z. B. 0.55), filterst du fast alle Fehlsignale heraus (hohe Precision).
   Dein Bot tradet dann aber vielleicht nur noch einmal am Tag.
 * Wenn du den Schwellenwert niedriger ansetzt (z. B. 0.38), bekommst du sehr viele Trades (hoher Recall),
   fängst dir aber auch mehr Verlust-Trades ein.

Im quantitativen Handel lässt man den Backtester über das Eval-Set laufen und testet Schwellenwerte in 2-%-Schritten durch,
um das Maximum beim Profit Factor zu finden.

Was zeigt die ROC-Kurve?

Die ROC-Kurve ist ein Diagramm, das dir zeigt,
wie gut dein Modell echte Signale (Long/Short) von Rauschen (Neutral) trennen kann,
während du den Schwellenwert (Threshold) von 0 % bis 100 % verschiebst.
Sie spannt sich zwischen zwei Achsen auf:
 1. Y-Achse: Die Richtig-Positiv-Rate (True Positive Rate / Recall): 
    Welchen Prozentsatz der echten Ausbrüche erwischt dein Bot? (Das willst du maximieren).
 2. X-Achse: Die Falsch-Positiv-Rate (False Positive Rate):
    Bei wie viel Prozent der Seitwärtsphasen schlägt dein Bot fälschlicherweise Alarm und kauft? (Das willst du minimieren).

Der perfekte Punkt für deinen Trading-Bot

Wenn du eine ROC-Kurve zeichnest, entsteht meistens eine Kurve, die sich nach links oben wölbt.
 * Die Diagonale (Zufall): Eine gerade Linie von links unten nach rechts oben bedeutet: Dein Modell ist so gut wie Münzwurf.
 * Die Wölbung nach links oben: Je steiler die Kurve nach links oben steigt, desto besser ist dein Modell.
   Ein Punkt auf dieser Kurve entspricht exakt einem bestimmten Schwellenwert (z. B. threshold=0.45).

Die wichtigste Kennzahl: Der AUC-Wert

In der Praxis schaut man sich oft nicht die ganze Kurve an,
sondern den AUC (Area Under the Curve) – also die Fläche unter dieser Kurve.
 * Anhand des AUC-Werts auf deinem Eval-Set (Tag 5) siehst du sofort,
   ob dein 4-Tage-Training überhaupt ein Alpha (einen Vorteil) gefunden hat,
   bevor du den Bot auf das Test-Set loslässt:

       AUC-Wert	Bedeutung für deinen MNQ-Bot
           0.50	Reiner Zufall. Das Modell hat keinerlei Muster im Orderbuch gelernt.
    0.55 – 0.65	Der Realitätsbereich im Trading. Ein kleiner, aber mathematisch profitabler Vorteil (Edge), wenn das CRV stimmt.
    0.70 – 0.85	Exzellente Trennschärfe. (Sehr selten bei so kurzen Rastern wie 10 Sekunden).
         > 0.90	Warnung (Data Leakage)! Wenn deine KI im Trading so gut abschneidet,
                hast du mit 99%iger Wahrscheinlichkeit versehentlich Daten aus der Zukunft in deine Features gefüttert.

In der Praxis hilft dir die ROC-Analyse auf Tag 5 also dabei,
den Schwellenwert zu finden, bei dem du die Falsch-Positiv-Rate (die teuren Fehlsignale) drastisch senkst,
während du noch genug echte Trades (True Positive Rate) mitnimmst.

### Berechnung des AUC Werts

Da du ein Drei-Klassen-Modell (0: Short, 1: Neutral, 2: Long) hast,
unterscheidet sich die Berechnung leicht von einem klassischen binären (Ja/Nein) Modell.
Bei mehreren Klassen berechnet man den AUC-Wert typischerweise nach dem One-vs-Rest (OvR) Prinzip.
Das bedeutet: Das Modell bewertet jede Klasse einzeln so, als wäre sie die Zielklasse gegen alle anderen.
Hier ist das präzise Python-Skript unter Verwendung von scikit-learn,
das du am Evaluierungstag (Tag 5) aufrufst, um deinen exakten AUC-Wert zu ermitteln.

    import numpy as np
    from sklearn.metrics import roc_auc_score

    def calculate_multiclass_auc(y_true, y_prob_predictions):
        """
        Berechnet den AUC-Wert für ein Drei-Klassen-Setup (OvR).
        
        y_true: Die wahren Labels aus deinem Datensatz, z.B. Array [0, 1, 2, 1, 0, ...]
        y_prob_predictions: Die vom Modell vorhergesagten Wahrscheinlichkeiten für ALLE Klassen.
                            Das ist eine Matrix der Form (n_samples, 3), 
                            die du über model.predict_proba() erhältst.
        """
        
        # 'macro' berechnet den AUC für jede Klasse einzeln und nimmt dann den ungewichteten Durchschnitt.
        # Perfekt, da uns die Performance von Long und Short gleichermaßen interessiert!
        auc_macro = roc_auc_score(
            y_true, 
            y_prob_predictions, 
            multi_class='ovr', 
            average='macro'
        )
        
        # Optional: Wir können uns auch den AUC-Wert für jede Klasse einzeln anzeigen lassen,
        # um zu sehen, ob das Modell Short-Signale besser vorhersagen kann als Long-Signale.
        auc_per_class = roc_auc_score(
            y_true, 
            y_prob_predictions, 
            multi_class='ovr', 
            average=None
        )
        
        print(f"=== AUC PERFORMANCE ANALYSIS ===")
        print(f"Gesamt-AUC (Macro): {auc_macro:.4f}")
        print(f" -> AUC Klasse 0 (Short)  : {auc_per_class[0]:.4f}")
        print(f" -> AUC Klasse 1 (Neutral): {auc_per_class[1]:.4f}")
        print(f" -> AUC Klasse 2 (Long)   : {auc_per_class[2]:.4f}")
        
        return auc_macro

    # --- ANWENDUNGS-BEISPIEL FÜR DEIN LIGHTGBM MODELL ---
    # (Wird am Ende von Tag 5 ausgeführt)

    # 1. Hole die Wahrscheinlichkeiten für das Eval-Set
    # Das Ergebnis ist ein Array wie: [[0.1, 0.7, 0.2], [0.5, 0.4, 0.1], ...]
    y_eval_probabilities = model.predict(X_eval) # Bei nativem lgb.train() gibt predict() direkt Wahrscheinlichkeiten aus

    # 2. Berechne den Wert
    eval_auc = calculate_multiclass_auc(y_eval, y_eval_probabilities)


### Wie du das Ergebnis für deinen Bot nutzt

Sobald du dieses Skript auf dein Eval-Set anwendest, nutzt du den Wert für eine Qualitäts-Weiche in deiner Pipeline:

 * Die Alpha-Schranke: Setze im Code eine Mindest-Schwelle (z. B. eval_auc > 0.52).
 * Die Konsequenz:
   Wenn der Gesamt-AUC an Tag 5 unter 0.52 fällt, bedeutet das,
   dass das Modell für den darauffolgenden Testtag (oder im Live-Betrieb für den nächsten Tag) keinen statistischen Vorteil gefunden hat.
 * Das Verhalten deines Bots:
   In diesem Fall sollte die Pipeline das Modell für den Folgetag verwerfen und den Bot automatisch auf "Flat / Neutral" stellen.
   Es ist im Trading oft profitabler, an einem unberechenbaren Tag gar nicht am Markt teilzunehmen, als mit einem blinden Modell zu agieren.


## Anhang: Nutze relative Abstände statt absoluten Abständen

Momentan funktioniert mein Modell sehr gut, weil sich der Nasdaq für die aktuellen Testdaten in einem engen Kurs-Korridor befindet.
Deshalb kommt es nicht zum tragen, ob als Abstand die absolute Differenz oder die prozentual verwendet wird.
Sobald der Nasdaq sich aber eine größere Spannweite umfasst, kommt der Unterschied zum tragen.
Deshalb muss bereits jetzt der relative Abstand verwendet werden,
damit die gelernte Werte auf die Zukunft übertragbar sind.
