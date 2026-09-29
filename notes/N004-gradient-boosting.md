Gradient Boosting
===================

Von Google KI-Modus:

Um Gradient Boosting (wie LightGBM, XGBoost oder CatBoost) für eine Vorhersage auf Basis von Order Flow (Auftragsfluss im Orderbuch) einzusetzen,
musst du die kontinuierlichen, hochfrequenten Marktdaten in eine strukturierte Tabellenform (Features und Targets) übersetzen.
Da Order-Flow-Daten eine Zeitreihe darstellen,
ist das wichtigste Kriterium das sogenannte Feature Engineering
(das Erstellen aussagekräftiger Merkmale).

Hier ist der Schritt-für-Schritt-Leitfaden, wie du das Projekt aufbaust:

Das Ziel definieren (Die Target-Variable Y)
--------------------------------------------

Bevor du Daten sammelst, musst du festlegen, was das Modell vorhersagen soll.
Beliebte Ansätze im Order Flow sind:

* Preisrichtung: Steigt oder fällt der Preis im nächsten Zeitfenster
  (z.B. in den nächsten 10 Sekunden oder nach den nächsten 50 Trades)? -> Klassifikation
* Preisänderung: Um wie viele Ticks bewegt sich der Mid-Price
  (Mittelwert aus bestem Ask und Bid)? -> Regression
* Volatilität/Spread: Weitet sich der Spread in Kürze aus? -> Regression/Klassifikation


Feature Engineering: Aus Order Flow Daten Merkmale machen
-----------------------------------------------------------

Gradient Boosting kann nicht direkt mit rohen Event-Daten (wie "Order platziert", "Order storniert") umgehen.
Du musst die Daten aggregieren – entweder in Zeit-Fenstern (z. B. alle 500ms) oder Volumen-/Tick-Bars (z. B. nach jeweils 100 Trades).

Erstelle aus diesen Fenstern folgende Features:

## Ungleichgewicht im Orderbuch (Imbalance)

* Volume Imbalance: Das Verhältnis von Kauf- zu Verkaufsaufträgen auf den besten Preisstufen (L1, L2, L3).

    $$\text{Imbalance} = \frac{\text{Bid Size} - \text{Ask Size}}{\text{Bid Size} + \text{Ask Size}}$$ 

* Order Book Slope: Wie steil fällt das Volumen ab, wenn man tiefer in das Orderbuch schaut (Markttiefe)?

## Aggressive Marktteilnehmer (Trades)

* Delta (Order Flow Delta): Die Differenz zwischen dem Volumen,
  das zum Ask-Preis (Käufer-initiiert) und zum Bid-Preis (Verkäufer-initiiert) ausgeführt wurde.
  Ein stark positives Delta zeigt aggressiven Kaufdruck.
* CVD (Cumulative Volume Delta): Die fortlaufende Summe des Deltas über den Tag.
* Trade Size Distribution: Verhältnis von institutionellen (großen) Orders zu Retail- (kleinen) Orders.

## Stornierungen und Spoofing

Cancellation Rate: Wie schnell werden Limit-Orders im Vergleich zu ausgeführten Orders gelöscht
Hohe Stornierungsraten auf einer Seite deuten oft auf Fake-Liquidity (Spoofing) hin.

## Historische Lags (Verzögerungen)

Da Gradient Boosting keine eingebaute Zeitkomponente hat (wie z. B. ein LSTM-Netzwerk),
musst du die Vergangenheit als Spalten abbilden.
Erstelle Spalten für: Delta_t-1, Delta_t-2, Imbalance_t-1, etc.


Besonderheiten beim Training mit Gradient Boosting
----------------------------------------------------

Beim Training von LightGBM oder XGBoost auf Finanzdaten musst du zwingend zwei fundamentale Fehler vermeiden:
Data Leakage (Datenlecks) und falsche Validierung.

## Zeitreihen-Validierung (Time-Series Split)

Nutze niemals eine klassische, zufällige K-Fold-Kreuzvalidierung!
Wenn du zufällige Zeilen zum Testen herausgreifst,
lernt das Modell die Zukunft und sagt die Vergangenheit voraus.

* Lösung: Nutze einen Rolling Window oder Purged Group Time Series Split.
  Trainiere auf den Monaten 1–3, teste auf Monat 4. Trainiere auf 1–4, teste auf Monat 5.

Train: [■ ■ ■] Test: [▨]
Train: [■ ■ ■ ■] Test: [▨]

## Umgang mit Overfitting (Überanpassung)

Order-Flow-Daten sind extrem verrauscht (Noise).
Gradient Boosting neigt dazu, das Rauschen auswendig zu lernen.

* Gegenmaßnahmen in LightGBM:
* Halte max_depth flach (z.B. 3 bis 6).
   * Setze learning_rate niedrig (z.B. 0.01 bis 0.05).
   * Nutze Regularisierung: lambda_l1 und lambda_l2.
   * Nutze early_stopping_rounds, um das Training zu stoppen, sobald die Performance auf den Testdaten schlechter wird.


Ein kompaktes Python-Beispiel (Konzept)
------------------------------------------

Hier ist ein stark vereinfachtes Beispiel, wie der Code mit lightgbm aufgebaut ist:

    import lightgbm as lgbimport pandas as pdimport numpy as np

    # 1. Daten laden (Beispiel-Struktur nach dem Feature Engineering)
    # Spalten: bid_ask_imbalance, order_flow_delta, cvd, target_next_price_move
    data = pd.read_csv("order_flow_features.csv")
    
    # Zeitliche Sortierung ist essenziell
    data = data.sort_values('timestamp')

    # 2. Split in Train und Test (chronologisch, z.B. 80/20 Split)

    split_idx = int(len(data) * 0.8)train_df = data.iloc[:split_idx]
    test_df = data.iloc[split_idx:]
    features = ['bid_ask_imbalance', 'order_flow_delta', 'cvd', 'delta_lag_1']target = 'target_next_price_move' # 1 für Preis steigt, 0 für fällt
    X_train, y_train = train_df[features], train_df[target]X_test, y_test = test_df[features], test_df[target]

    # 3. LightGBM Datensätze erstellen

    train_data = lgb.Dataset(X_train, label=y_train)test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    # 4. Parameter definieren (auf Rauschunterdrückung optimiert)

    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'boosting_type': 'gbdt',
        'learning_rate': 0.03,
        'max_depth': 4,
        'num_leaves': 15,
        'lambda_l2': 5.0, # Regularisierung gegen Noise
        'verbose': -1
    }

    # 5. Modell trainieren mit Early Stopping

    callbacks = [lgb.early_stopping(stopping_rounds=50)]model = lgb.train(
        params,
        train_data,
        num_boost_round=1000,
        valid_sets=[test_data],
        callbacks=callbacks
    )

    # 6. Feature Wichtigkeit analysieren
    # Zeigt dir, welche Order-Flow-Metriken die meiste Vorhersagekraft haben

    importance = model.feature_importance(importance_type='gain')for f, imp in zip(features, importance):
        print(f"Feature: {f} -> Importance: {imp:.2f}")

## Warum ist LightGBM dafür besonders gut geeignet?

Order Flow Vorhersagen finden oft im Millisekundenbereich statt. Während Deep Learning (z. B. LSTMs) sehr lange für Berechnungen braucht, ist ein einmal trainiertes LightGBM-Modell im Live-Betrieb extrem schnell (Sub-Millisekunden-Bereich) bei der Auswertung eines neuen Datenpunktes. Zudem kann es hervorragend mit nicht-linearen Beziehungen im Orderbuch (z. B. plötzlichen Liquiditäts-Entzug) umgehen.


Datenhaltung
---------------

Gradient Boosting bzw. LightGBM arbeitet auf Tabellen.
Um diese Tabellen programmatisch zu erstellen, nutzt man `pandas'.
Das ist Excel in Python.

Beim Nachtraining wird immer der ganze Tag genutz.
Zur Laufzeit des Bots müssen also alles Daten aufgesammelt werden,
die dann später initial in die Tabelle geschrieben werden.
Die Tabellen kann man dann in CSV-Dateien schreiben oder
die eleganter Methode mit Parquet-Datein wählen.
Beides kann Pandas out of the box.

Eine weiter alternative wäre eine SQLite Datenbank.
Mir ist nämlich noch nicht klar, wie ich die problematik des Datei-Downloads löse.
Evtl. muss ich doch speicherplatz bei Render.com dazu kaufen.
Oder ich kann das Modell regelmäßig down-loaden und ins git pushen.

Oder ich lasse den Bot das neue Modell ins git-Repo pushen.
Das ist vielleicht der beste Ansatz, weil ich dann zurück rollen kann.
