#!/bin/env python
#
# converts databento tick data to bars
#

import argparse
import glob
import os
import pandas as pd


def erzeuge_zeit_kerzen(csv_pfad, sekunden_pro_kerze):
    if not os.path.exists(csv_pfad):
        print(f"Fehler: Die Datei '{csv_pfad}' wurde nicht gefunden.")
        return

    print(f"Lese Datei ein: {csv_pfad}...")
    df = pd.read_csv(csv_pfad)

    # ISO8601-Format explizit angeben
    df["ts_event"] = pd.to_datetime(df["ts_event"], format="ISO8601")

    print(
        f"Berechne Zeit-Kerzen mit einer Größe von {sekunden_pro_kerze} Sekunden..."
    )

    # Hilfsspalte für den gewichteten Preis erstellen (für den VWAP)
    df["preis_mal_volumen"] = df["price"] * df["size"]

    # Für resample() muss der Zeitstempel der Index des DataFrames sein
    df = df.set_index("ts_event")

    # Zeitbasiertes Resampling (OHLCV + Summen für VWAP)
    # 's' steht für Sekunden. label='left' sorgt dafür, dass der Startzeitpunkt als Timestamp genutzt wird.
    zeit_str = f"{sekunden_pro_kerze}s"
    zeit_kerzen = (
        df.resample(zeit_str, label="left")
        .agg(
            open=("price", "first"),
            high=("price", "max"),
            low=("price", "min"),
            close=("price", "last"),
            volume=("size", "sum"),
            summe_preis_volumen=("preis_mal_volumen", "sum"),
        )
        .dropna(
            subset=["open"]
        )
        .reset_index()
    )  # dropna entfernt Zeitintervalle, in denen kein Trade stattfand

    # Absolut zeitzonensichere Berechnung der Millisekunden seit 00:00 Uhr
    zeiten = zeit_kerzen["ts_event"].dt
    zeit_kerzen["timestamp"] = (
        (zeiten.hour * 3600000)
        + (zeiten.minute * 60000)
        + (zeiten.second * 1000)
        + (zeiten.microsecond // 1000)
    ).astype("int64")

    # Gesichteten Durchschnitt (VWAP) berechnen
    zeit_kerzen["average"] = (
        zeit_kerzen["summe_preis_volumen"] / zeit_kerzen["volume"]
    )

    # Temporäre Spalten entfernen und finale Reihenfolge festlegen
    spalten_reihenfolge = [
        "timestamp",
        "open",
        "low",
        "average",
        "high",
        "close",
        "volume",
    ]
    zeit_kerzen = zeit_kerzen[spalten_reihenfolge]

    # Namenskonvention anwenden (_ticks.csv durch _sNNN.csv ersetzen)
    if "_ticks.csv" in csv_pfad:
        ausgabe_pfad = csv_pfad.replace(
            "_ticks.csv", f"_s{sekunden_pro_kerze}.csv"
        )
    else:
        basisname, _ = os.path.splitext(csv_pfad)
        ausgabe_pfad = f"{basisname}_s{sekunden_pro_kerze}.csv"

    # Datei speichern
    zeit_kerzen.to_csv(ausgabe_pfad, index=False)
    print(zeit_kerzen)
    print(f"Erfolgreich fertiggestellt! Gespeichert unter: {ausgabe_pfad}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Erzeugt zeit-basierte Kerzen (OHLCV + VWAP) aus mehreren Databento CSV-Dateien."
    )

    # Erlaubt die Übergabe von beliebig vielen Dateien direkt als Positionsargumente
    parser.add_argument(
        "files",
        nargs="+",
        help="Pfad(e) zu den Databento CSV-Dateien (Unterstützt Wildcards wie *_ticks.csv)",
    )
    parser.add_argument(
        "-s",
        "--seconds",
        type=int,
        required=True,
        help="Gewünschte Sekunden pro Kerze (z.B. 5 oder 60)",
    )

    args = parser.parse_args()

    # Alle übergebenen Argumente/Wildcards auflösen
    aufgeloeste_dateien = []
    for muster in args.files:
        dateien = glob.glob(muster)
        if dateien:
            aufgeloeste_dateien.extend(dateien)
        else:
            aufgeloeste_dateien.append(muster)

    aufgeloeste_dateien = sorted(list(set(aufgeloeste_dateien)))

    print(f"Es wurden {len(aufgeloeste_dateien)} Datei(en) gefunden.")

    # Schleife über alle Dateien
    for datei_pfad in aufgeloeste_dateien:
        erzeuge_zeit_kerzen(datei_pfad, args.seconds)
