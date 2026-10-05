import os
import pandas as pd


def build_volume_bar(csv_file, volume):
    df = pd.read_csv(csv_file)

    #df["ts_event"] = pd.to_datetime(df["ts_event"], format="ISO8601")
    df["preis_mal_volumen"] = df["price"] * df["size"]
    df["kumuliertes_volumen"] = df["size"].cumsum()
    df["kerzen_id"] = df["kumuliertes_volumen"] // volume

    # OHLCV + Summe des gewichteten Preises aggregieren
    volumen_kerzen = (
        df.groupby("kerzen_id")
        .agg(
            ts_event=("ts_event", "first"),
            open=("price", "first"),
            high=("price", "max"),
            low=("price", "min"),
            close=("price", "last"),
            volume=("size", "sum"),
            summe_preis_volumen=("preis_mal_volumen", "sum"),
        )
        .reset_index(drop=True)
    )

    volumen_kerzen["timestamp"] = volumen_kerzen['ts_event'] // 1_000_000
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
    if "_ticks.csv" in csv_file:
        out_file = csv_file.replace("_ticks.csv", f"_{volume}v.csv")
    else:
        basisname, _ = os.path.splitext(csv_file)
        out_file = f"{basisname}_v{volume}.csv"

    volumen_kerzen.to_csv(out_file, index=False)
    print(volumen_kerzen)


def build_bar(csv_file: str, seconds: int) -> None:
    pass


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="create bar")
    parser.add_argument("files", nargs="+", help="files with databento ticks")
    parser.add_argument("-v", "--volume", type=int, help="volume of volume bar")
    parser.add_argument("-s", "--seconds", type=int, help="duration of time based bar")
    args = parser.parse_args()

    if args.volume is None and args.seconds is None:
        print(f'{parser.prog}: error: --volume or --seconds must be set', file=sys.stderr)
        exit(1)
    if args.volume is not None and args.seconds is not None:
        print(f'{parser.prog}: warning: both --volume and --seconds are set. ignoring --seconds', file=sys.stderr)

    for file in args.files:
        print(f'{parser.prog}: converting file {file}')
        if args.volume is not None:
            build_volume_bar(file, args.volume)
        if args.seconds is not None:
            build_bar(file, args.seconds)
