import time

def day_offset(offset_ms: int) -> int:
    """Ermittelt den offset des Tages in Millisekunden und gibt die Anzahl der Millisekunden seit Mitternacht zurück."""
    return offset_ms % 86400000  # 86400000 ms = 24 Stunden

def offset_to_time_string(offset_ms: int) -> str:
    # 1. Bruchteile berechnen
    ms = offset_ms % 1000
    
    total_seconds = offset_ms // 1000
    seconds = total_seconds % 60
    
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    
    hours = total_minutes // 60
    
    # 2. String mit führenden Nullen formatieren
    # :02d = 2-stellig Integer, :03d = 3-stellig Integer
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"

def update_inplace(offset_ms: int, price: float):
    time_str = offset_to_time_string(offset_ms)
    print(f"Letzter Tick: {time_str} -> Aktueller Preis: {price:.2f}", end="\r", flush=True)


if __name__ == "__main__":
    # Testfälle
    test_offsets = [0, 1234, 60000, 3600000, 3661000, 86399999]
    
    for offset in test_offsets:
        print(f"Offset: {offset:8d} ms -> Time String: {offset_to_time_string(offset)}")   

    # Simulation von 3 schnellen Ticks
    ticks = [13179750, 13180120, 13180890]
    prices = [4250.75, 4251.00, 4250.50]
    for offset, price in zip(ticks, prices):
        update_inplace(offset, price)
        time.sleep(0.9) 
    print() # Finale Leerzeile nach dem Ende des Streams
