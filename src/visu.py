import pandas as pd
import mplfinance as mpf

# 1. CSV-Datei einlesen
# 'parse_dates=True' und 'index_col=0' sorgen dafür, dass die erste Spalte (Date) als Zeit-Index geladen wird
df = pd.DataFrame()
try:
    df = pd.read_csv('trading_data.csv', parse_dates=True, index_col=0)
except FileNotFoundError:
    # Nur zur Demonstration, falls die Datei noch nicht existiert, erstellen wir Dummy-Daten:
    dates = pd.date_range(start="2026-10-02 09:00:00", periods=6, freq="5min")
    data = {
        'Open':  [19050.00, 19062.25, 19055.50, 19040.00, 19048.25, 19060.00],
        'High':  [19068.50, 19070.00, 19058.00, 19052.50, 19064.00, 19075.50],
        'Low':   [19045.00, 19052.00, 19035.25, 19038.00, 19045.00, 19058.25],
        'Close': [19062.25, 19055.50, 19040.00, 19048.25, 19060.00, 19072.50],
        'SMA_20': [19045.50, 19048.25, 19047.00, 19046.50, 19049.00, 19053.50],
        'SMA_50': [19030.00, 19032.50, 19034.00, 19035.50, 19038.00, 19041.25],
        'SMA_200':[19010.25, 19011.00, 19011.50, 19012.00, 19012.25, 19013.00]
    }
    df = pd.DataFrame(data, index=dates)

# 2. Die drei gleitenden Durchschnitte als Overlays definieren
additional_plots = [
    # SMA_20 wird hier als blaue Punkte ('scatter') mit Kreisen ('o') dargestellt:
    mpf.make_addplot(df['SMA_20'], type='scatter', marker='o', color='black', markersize=15),
    
    # Die anderen beiden Durchschnitte bleiben normale Linien:
    mpf.make_addplot(df['SMA_50'], color='orange', width=1.5, linestyle='--'),
    mpf.make_addplot(df['SMA_200'], color='purple', width=2.0, linestyle='--')
]

# 3. Das Candlestick-Chart zusammen mit den Linien zeichnen

# Eigenen Stil basierend auf 'charles' erstellen und Gitter erzwingen

# 'base_style' wurde zu 'base_mpf_style' korrigiert
custom_style = mpf.make_mpf_style(
    base_mpf_style='charles', 
    gridaxis='both', 
    gridstyle='--'
)

# Das Candlestick-Chart zusammen mit den Linien zeichnen
mpf.plot(
    df, 
    type='candle', 
    style=custom_style,        # Hier nutzen wir Ihren korrigierten Stil
    addplot=additional_plots,  
    title='MNQ Chart mit 3 gleitenden Durchschnitten',
    ylabel='Preis (USD)',
    volume=False
)
