from datetime import datetime, timedelta
import json
import time
import pandas as pd
import websocket
import tradovate
import asyncio

# --- GLOBALE STATUSVARIABLEN ---
access_token = None
all_ticks = []
ticks_downloaded = 0
current_closest_timestamp = None
request_id = 2
ws_client = None


def request_tick_packet(ws, closest_timestamp):
    """Fordert ein Paket von Ticks an."""
    global request_id
    request_id += 1
    
    chart_params = {
        "symbol": symbol,
        "chartStyle": "Tick",
        "elementSize": 1,
        "underlyingType": "Tick",
        "timeRange": {
            "closestTimestamp": closest_timestamp,
            "asMuchAsElements": 4096
        }
    }
    message = f"md/getChart\n{request_id}\n\n{json.dumps(chart_params)}"
    ws.send(message)


def on_message(ws, message):
    global all_ticks, ticks_downloaded, current_closest_timestamp
    
    if message == 'o':
        print("🟢 WebSocket geöffnet. Sende Autorisierung...")
        ws.send(f'["authorize\n1\n\n{access_token}"]')
        
    elif message == 'h':
        pass
        
    elif message.startswith('a'):
        data_list = json.loads(message[1:])
        for item in data_list:
            if item.get("i") == 1:
                if item.get("s") == 200:
                    print(f"🔒 Autorisierung erfolgreich! Starte Download rückwärts ab {end_dt}...")
                    request_tick_packet(ws, closest_timestamp=END_MS)
                else:
                    print(f"❌ Autorisierungsfehler: {item}")
                    ws.close()
            
            elif item.get("i") == request_id:
                chart_data = item.get("d", {})
                bars = chart_data.get("bars", [])
                
                if not bars:
                    print("🏁 Keine weiteren Ticks für diesen Zeitraum vorhanden.")
                    ws.close()
                    return
                
                # Nur Ticks im gewünschten Tages-Zeitfenster behalten
                valid_bars = [b for b in bars if START_MS <= b.get("t") <= END_MS]
                
                if valid_bars:
                    all_ticks.extend(valid_bars)
                    ticks_downloaded += len(valid_bars)
                    print(f"📥 {len(valid_bars)} Ticks für diesen Tag im Paket gefunden. (Gesamt für den Tag: {ticks_downloaded})")
                
                oldest_tick_ms = bars[0].get("t")
                
                if oldest_tick_ms < START_MS:
                    print("🎉 Alle Ticks innerhalb des definierten Tagesfensters geladen!")
                    ws.close()
                else:
                    time.sleep(0.5)  # Rate-Limit-Schutz
                    request_tick_packet(ws, closest_timestamp=oldest_tick_ms)


def on_close(ws, close_status_code, close_msg):
    print("!!! VERBINDUNG GESCHLOSSEN !!!")
    print(f"Status Code: {close_status_code}")
    print(f"Grund vom Server: {close_msg}")

    """Bereitet die Daten auf und speichert sie als tagesbasierte CSV-Datei."""
    if not all_ticks:
        raise("no ticks available to save")
        
    df = pd.DataFrame(all_ticks)
    df.rename(columns={
        't': 'timestamp',
        'o': 'price',
        'v': 'volume',
        'bidVolume': 'bid_volume',
        'offerVolume': 'offer_volume'
    }, inplace=True, errors='ignore')
    
    # Chronologische Sortierung sicherstellen
    if 'timestamp' in df.columns:
        df.sort_values(by='timestamp', ascending=True, inplace=True)
        df['datetime_utc'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df.to_csv(f"{symbol}_{args.date}.csv", index=False)

async def download_ticks_for_day(symbol, target_date):
    global access_token

    end_date = target_date + timedelta(days=1) - timedelta(seconds=1)
    START_MS = int(target_date.timestamp() * 1000)
    END_MS = int(end_date.timestamp() * 1000)
    
    symbol = tradovate.get_active_symbol(symbol, target_date)
    print(f"{parser.prog}: downloading ticks for {symbol}: {target_date} .. {end_date}")
        
    access_token = await tradovate.get_access_token(app_id="plutos_bot")
    print(f"🔑 Access Token erhalten: {access_token}")

    ws_client = websocket.WebSocketApp(
        tradovate.DEMO_WSS,
        on_message=on_message,
        on_close=on_close
    )
    
    print(f"Starte WebSocket-Verbindung für {symbol} am {target_date.date()}...")
    ws_client.run_forever()

# --- START ---
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Tradovate API - Automatischer MNQ Tages-Tick-Downloader")
    parser.add_argument("--date", required=True, help="Ziel-Datum im Format YYYY-MM-DD (z.B. 2026-09-28)")
    parser.add_argument("--symbol", default="MNQ", help="Symbol for download (Standard: MNQ)")
    args = parser.parse_args()

    try:
        asyncio.run(download_ticks_for_day(args.symbol, datetime.strptime(args.date, "%Y-%m-%d")))

    except KeyboardInterrupt:
        print(f"{parser.prog}: aborted by user. No data saved.", file=sys.stderr)
    except Exception as e:
        print(f"{parser.prog}: error: {e}", file=sys.stderr)
