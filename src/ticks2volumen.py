import os
import pandas as pd


def build_volume_bar(csv_pfad, volumen_pro_kerze):
    df = pd.read_csv(csv_pfad)

    # ISO8601-Format explizit angeben
    df["ts_event"] = pd.to_datetime(df["ts_event"], format="ISO8601")
    df["preis_mal_volumen"] = df["price"] * df["size"]
    df["kumuliertes_volumen"] = df["size"].cumsum()
    df["kerzen_id"] = df["kumuliertes_volumen"] // volumen_pro_kerze

    # OHLCV + Summe des gewichteten Preises aggregieren
    volumen_kerzen = (
        df.groupby("kerzen_id")
        .agg(
            timestamp=("ts_event", "first"),
            open=("price", "first"),
            high=("price", "max"),
            low=("price", "min"),
            close=("price", "last"),
            volume=("size", "sum"),
            summe_preis_volumen=("preis_mal_volumen", "sum"),
        )
        .reset_index(drop=True)
    )

    zeiten = volumen_kerzen["timestamp"].dt
    volumen_kerzen["timestamp"] = (
        (zeiten.hour * 3600000)
        + (zeiten.minute * 60000)
        + (zeiten.second * 1000)
        + (zeiten.microsecond // 1000)
    ).astype("int64")

    # Gesichteten Durchschnitt (VWAP) berechnen
    volumen_kerzen["vwap"] = (
        volumen_kerzen["summe_preis_volumen"] / volumen_kerzen["volume"]
    )

    # Gesichteten Durchschnitt (VWAP) berechnen
    volumen_kerzen["average"] = volumen_kerzen["summe_preis_volumen"] / volumen_kerzen["volume"]
    volumen_kerzen = volumen_kerzen.drop(columns=["summe_preis_volumen"])

    # Spaltenreihenfolge für ein sauberes Format definieren
    spalten_reihenfolge = [
        "timestamp",
        "open",
        "low",
        "average",
        "high",
        "close",
        "volume"
    ]
    volumen_kerzen = volumen_kerzen[spalten_reihenfolge]

    # Namenskonvention anwenden (_ticks.csv durch _vnnn.csv ersetzen)
    if "_ticks.csv" in csv_pfad:
        ausgabe_pfad = csv_pfad.replace("_ticks.csv", f"_v{volumen_pro_kerze}.csv")
    else:
        basisname, _ = os.path.splitext(csv_pfad)
        ausgabe_pfad = f"{basisname}_v{volumen_pro_kerze}.csv"

    # Datei speichern
    volumen_kerzen.to_csv(ausgabe_pfad, index=False)
    print(volumen_kerzen)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Erzeugt volumen-optimierte Kerzen (OHLCV + VWAP) mit Millisekunden seit Mitternacht.")
    parser.add_argument("files", nargs="+", help="Pfad zur Databento CSV-Datei (z.B. NMQZ6_2026-10-01_ticks.csv)")
    parser.add_argument("-v", "--volume", type=int, default=500, help="Gewünschtes Volumen pro Kerze (z.B. 100 oder 500)")
    args = parser.parse_args()

    for file in args.files:
        print(f'{parser.prog}: converting file {file}')
        build_volume_bar(file, args.volume)
