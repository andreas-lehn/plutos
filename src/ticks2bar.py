import os
import pandas as pd


def build_volume_bar(df: pd.DataFrame, volume: int) -> pd.DataFrame:
    """create bar with fixed volume"""

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
    return volumen_kerzen[spalten_reihenfolge]


def build_time_bar(df: pd.DataFrame, seconds: int) -> pd.DataFrame:
    """create bar with fixed period of time"""

    # Hilfsspalte für den gewichteten Preis erstellen (für den VWAP)
    df["preis_mal_volumen"] = df["price"] * df["size"]

    # Für resample() muss der Zeitstempel der Index des DataFrames sein
    df["timestamp_dt"] = pd.to_datetime(df["ts_event"], unit='ns')
    df = df.set_index("timestamp_dt")

    # Zeitbasiertes Resampling
    # 's' steht für Sekunden. label='left' sorgt dafür, dass der Startzeitpunkt als Timestamp genutzt wird.
    zeit_str = f"{seconds}s"
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

    zeit_kerzen["timestamp"] = zeit_kerzen['timestamp_dt'].astype("int64") // 10**6

    # Gewichteten Durchschnitt (VWAP) berechnen
    zeit_kerzen["average"] = (zeit_kerzen["summe_preis_volumen"] / zeit_kerzen["volume"])

    # Temporäre Spalten entfernen und finale Reihenfolge festlegen
    zeit_kerzen = zeit_kerzen.drop(columns=['timestamp_dt', 'summe_preis_volumen'])
    spalten_reihenfolge = [
        "timestamp",
        "open",
        "low",
        "average",
        "high",
        "close",
        "volume",
    ]
    return zeit_kerzen[spalten_reihenfolge]


def build_tick_bar(df: pd.DataFrame, size: int) -> pd.DataFrame:
    """create bar with a fixed number of trades"""
    pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="create bar")
    parser.add_argument("files", nargs="+", help="files with databento ticks")
    parser.add_argument("-t", "--type", choices=['volume', 'time', 'tick'], required=True, help="type of bar")
    parser.add_argument("-s", "--size", type=int, required=True, help="size of bar (volume, seconds, trades)")
    parser.add_argument("-v", "--verbose", action="store_true", help="activate verbose mode")
    args = parser.parse_args()

    for file in args.files:
        if args.verbose:
            print(f'{parser.prog}: converting file {file}')
        
        df = pd.read_csv(file)
        if args.type == 'volume':
            bars = build_volume_bar(df, args.size)
            post_fix = 'v'
        if args.type == 'time':
            bars = build_time_bar(df, args.size)
            post_fix = 's'
        if args.type == 'tick':
            bars = build_tick_bar(df, args.size)
            post_fix = 't'

        base_name = file.removesuffix('.csv').removesuffix('_ticks')
        out_file = f"{base_name}_{args.size}{post_fix}.csv"
        
        bars.to_csv(out_file, index=False)
        if args.verbose:
            print(bars)
            print(f'{parser.prog}: {len(bars)} bars written to {out_file}')
