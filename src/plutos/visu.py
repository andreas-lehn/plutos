import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import io
import click

@click.command()
@click.argument('chart_file', type=click.File('r', encoding='utf-8'), help="chart file")
@click.option('-p', '--profile-file', type=click.File('r', encoding='utf-8'), help="file with volume profile")
@click.option('-s', '--start', type=int, default=0, help="start offset (sec) of candle in charts file")
@click.option('-n', '--num-candles', type=int, help="number of candles to be drawn into chart")
def show(chart_file: io.TextIOWrapper, profile_file: io.TextIOWrapper, start:int, num_candles: int): 
    """ show chart diagram """

    df_sticks = pd.read_csv(chart_file)
    if num_candles:
        df_sticks = df_sticks.iloc[start:start + num_candles]
    else:
        df_sticks = df_sticks.iloc[start:]

    df_sticks['open'] = df_sticks['open'] / 4
    df_sticks['low'] = df_sticks['low'] / 4
    df_sticks['average'] = df_sticks['average'] / 4
    df_sticks['high'] = df_sticks['high'] / 4
    df_sticks['close'] = df_sticks['close'] / 4
    df_sticks['Date'] = pd.to_datetime(df_sticks['timestamp']//10**9, unit='s')
    df_sticks.set_index('Date', inplace=True)
    df_sticks.sort_index(inplace=True)
    df_sticks.rename(columns={
                        'open': 'Open',
                        'low': 'Low',
                        'high': 'High',
                        'close': 'Close',
                        'volume': 'Volume',
                    }, inplace=True)

    n_sticks = len(df_sticks)
    markersize  = max(2.0, 600.0 / n_sticks)
    markerwidth = max(0.5, 30.0 / n_sticks)

    additional_plots = []
    if 'average' in df_sticks.columns:
        additional_plots.append(mpf.make_addplot(df_sticks['average'], type='scatter', color='grey', marker='o', markersize=markersize, panel=0))

    if 'contracts' in df_sticks.columns:
        additional_plots.append(mpf.make_addplot(df_sticks['contracts'], type='bar', width=0.5, panel=2))
        df_sticks["long"]  = np.where(df_sticks["contracts"] > 0, df_sticks["Low"] - 2, np.nan)
        if df_sticks["long"].notna().any():
            additional_plots.append(mpf.make_addplot(df_sticks["long"].values, type="scatter", marker="^", color="white", edgecolors="black", linewidths=0.5, markersize=4*markersize, panel=0))

        df_sticks["short"] = np.where(df_sticks["contracts"] < 0, df_sticks["High"] + 2, np.nan)
        if df_sticks["short"].notna().any():
            additional_plots.append(mpf.make_addplot(df_sticks["short"], type="scatter", marker="v", color="black", edgecolors="black", linewidths=0.5, markersize=4*markersize, panel=0))

    if 'prediction' in df_sticks.columns:
        additional_plots.append(mpf.make_addplot(df_sticks['prediction'], width=0.5, panel=3))

    for average in ['ema_fast', 'ema_slow']:
        if average in df_sticks.columns:
            df_sticks[average] = df_sticks[average] / 4
            additional_plots.append(mpf.make_addplot(df_sticks[average], width=0.6, panel=0))

    # 3. Candlestick-Basisplot erstellen und Achsen abfangen
    fig, axlist = mpf.plot(
        df_sticks, 
        type='candle', 
        #title=chart_file,
        volume=True,
        volume_panel=1,
        panel_ratios=(5,1),
        addplot=additional_plots,
        datetime_format='%H:%M:%S', # Zeigt Stunden:Minuten auf der X-Achse
        returnfig=True,
        figsize=(16, 9),
    )

    ax_main = axlist[0]  # Oberer Hauptplot (Kerzen)
    ax_overlay = ax_main.twiny()
    ax_overlay.get_xaxis().set_visible(False)

    # 2. ZWEITE CSV: Volumen-Profil (Volumen pro Preis) laden
    if profile_file:
        df_prof = pd.read_csv(profile_file)
        df_prof['price'] = df_prof['price'] / 4
        max_vol_wert = df_prof['volume'].max()


        # 4. BREITE DER HORIZONTALEN BALKEN SKALIEREN
        # Wir ermitteln die zeitliche Breite des Charts, damit die Balken nicht zu lang werden
        x_min, x_max = ax_main.get_xlim()
        chart_breite = x_max - x_min
        offset_ratio = abs(x_min) /chart_breite
        max_vol_limit = max_vol_wert * 10 # Balken nehmen maximal 25% der Chartbreite ein
        offset = 0 # -(max_vol_limit * offset_ratio) / 2
        ax_overlay.set_xlim(offset, max_vol_limit)

        # 5. DIE HORIZONTALEN BALKEN AUS DER ZWEITEN CSV EINZEICHNEN
        # Wir bestimmen die Höhe eines einzelnen Balkens dynamisch aus den Preisabständen
        if len(df_prof) > 1:
            balken_hoehe = (df_prof['price'].iloc[1] - df_prof['price'].iloc[0]) # * 0.8
        else:
            balken_hoehe = 0.5

        ax_overlay.barh(
            y=df_prof['price'],             # Y-Position: Die Preise aus der zweiten CSV
            width=df_prof['volume'],       # X-Länge: Das skalierte Volumen
            height=balken_hoehe,            # Dicke der Balken
            color='#1f77b4',
            alpha=0.5,                     # Transparent, damit die Kerzen sichtcandle bleiben
            align='center',
        )
        ax_overlay.plot(df_prof['smooth_volume'], df_prof['price'], color='#1f77b4', linewidth=1)

        # ==========================================
        # 4.5 PEAK DETECTION & S/R-LINIEN EINZEICHNEN
        # ==========================================

        # 1. Mathematische Peaks (HVNs) auf der geglätteten Kurve finden
        # distance=5 verhindert, dass Linien zu nah beieinanderliegen
        # prominence filtert das Rauschen (nur Peaks, die mind. 5% des Max-Volumens herausragen)
        smoothed_volumes = df_prof['smooth_volume']
        prices = df_prof['price']

        min_prominence = smoothed_volumes.max() * 0.05
        peaks, _ = find_peaks(smoothed_volumes, distance=5, prominence=min_prominence)

        # Die exakten Preise der Peaks extrahieren
        sr_levels = prices[peaks]

        # 2. Die Linien direkt in das Candlestick-Diagramm (ax_candles) zeichnen
        for level in sr_levels:
            # axhline zieht eine Linie quer über die gesamte Breite der Kerzen-Achse
            ax_main.axhline(
                y=level, 
                color='#1f77b4',
                linestyle='--',           # Gestrichelte Linie
                linewidth=1,            # Dezente Linienstärke
                alpha=0.5,
            )
            
    # Den fertig modifizierten Chart anzeigen
    plt.show()

if __name__ == "__main__":
    show()
