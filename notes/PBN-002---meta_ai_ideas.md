Was Meta AI zum Trading Bot sagt
==================================

 * Vorhersage der Richtung, nicht des Preises
 * Nehmen, was der Orderflow hergibt:
     * Preis in Kerzen der letzen 20 Schätzintervalle (20 x 1 min Kerzen bei 1 min Vorausschau)
     * Kaufvolumen/Verkaufvolumen
     * Microstruktur: Abstand zum VWAP, RSI(14), Distand zum Tagestief/-hoch
     * Zeit: Minute seit Open
 * Das ergibt ca. 50 - 100 Zahlen pro Schätzung
 * LSTM ist ungeeignet, weil zu langsam und overfitted
 * Besser: 1D CNN. Kann schnell berechnet werden.
 * Ein gutes Modell schafft 53-56% Precision auf Long/Short.
 * 54% reicht, wenn Gewinn größer als Verlust
 * bei 10 sec sind Kerzen nutzlos
 * Nur noch das Orderbook ist relevant (Orderbuch Daten sind teuer)
 * Latenz ist kritisch, kann zum Tod führen
 * Rauschen ist sehr dominant
 * Bei 1 min sind Retail-Trader die Gegner. Sie sind leicht zu schlagen.
 * Bei 10 sec sind HFT die Gegner: Haifischbecken
 * Regel bei den Prop: _Trade den Timeframe, wo deine Konkurrenz am dümmsten ist."
 * 1 - 15 min: Konkurrenz ist menschlich, langsam, ängstlich
 * Deshalb: 10 sec Daten nutzen, um 1 min Vorhersage zu verbessern
 * Sweep spot für Solo-KI-Trader: 15 bis 30 sec Features für 60 sec Prediction
 * Statt zeitlichen Kerzen sind Volumen-orientierte Kerzen besser: Ein Kerze für 500 Kontrakte
 * Um die Retail-Trader zu schlagen, braucht es kein Orderbuch
 * Algo für Online Training:
     * PPO: Stabil, verzeiht Fehler, Standard für Trading, lernt langsam aber crasht nicht
     * DQN mit Replay Buffer: Schneller, aber gefährlich online, weil er alte Marktphasen auswendig lernt
 * Fazit: PPO ist der richtige Algo
 * Weil sich der Markt verändert: Rolling Window + Forget
     * Replay Buffer darf nur 3 Tage enthalten
     * Alle 24h Learning Rate auf 50% reduzieren
 * Kontinuierlicher Ausgabewert von -1.0 bis +1.0 ist ein geiler Gedanke!
 * Das ist dann kein RL mehr sondern Continuous Control
 * Letzer Layer wird Tanh und nicht Softmax.
 * Zu definieren ist, was "stark" heißt. Ein Bespiel: 0.8 entspricht 5 Punkten
 * Damit ist dann kein PPO mehr nötig. Supervised Learning ist das richtige.
 * Architekturvorschlag:
    * Input: 20 x 30 sec Bars
    * 1D-CNN 32 Filter
    * LSTM 64 (optimal, für Gedächtnis)
    * Dense 32, ReLU
    * Dense 1, tanh
    * Loss = MSE
 