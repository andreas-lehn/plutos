import time
from tqdm import tqdm

total_ticks = 50000  # Wir wissen, wir erwarten 50.000 Ticks
block_size = 4096    # Tradovate schickt Daten in 4096er-Blöcken

# Erstellt den Balken manuell mit einer Beschreibung
with tqdm(total=total_ticks, desc="Lade MNQ Ticks", unit="ticks") as pbar:
    current_ticks = 0
    while current_ticks < total_ticks:
        time.sleep(0.3)  # Simuliert die Wartezeit auf den API-Block
        
        # Aktualisiert den Balken um die Anzahl der neu geladenen Ticks
        pbar.update(block_size)
        current_ticks += block_size

print("[+] Download abgeschlossen!")
