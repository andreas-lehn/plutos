import argparse
import sys
from datetime import datetime, timedelta
import json
import os
import time
import uuid
import pandas as pd
import requests
import websocket

# Festgelegte Endpunkte (Demo)
BASE_URL = "https://demo.tradovateapi.com/v1"
WS_URL = "wss://md.tradovateapi.com/v1/websocket"

# --- GLOBALE STATUSVARIABLEN ---
access_token = None
all_ticks = []
ticks_downloaded = 0
current_closest_timestamp = None
request_id = 2
ws_client = None


def get_third_friday(year, month):
    """Ermittelt den 3. Freitag eines bestimmten Monats und Jahres."""
    # Start am 1. des Monats
    first_day = datetime(year, month, 1)
    # Wochentag des 1. Tages (0 = Montag, 4 = Freitag, 6 = Sonntag)
    first_weekday = first_day.weekday()
    
    # Tage bis zum ersten Freitag berechnen
    days_to_first_friday = (4 - first_weekday) % 7
    first_friday = first_day + timedelta(days=days_to_first_friday)
    
    # Der 3. Freitag ist 2 Wochen nach dem ersten Freitag
    third_friday = first_friday + timedelta(weeks=2)
    return third_friday


def get_active_symbol(symbol, target_date):
    """
    Ermittelt automatisch das aktive Kontraktsymbol für ein gegebenes Datum.
    Rollover findet am Donnerstag vor dem 3. Freitag im März, Juni, September und Dezember statt.
    """
    year = target_date.year
    year_suffix = str(year)[-1]  # Die letzte Ziffer des Jahres (z.B. '6' für 2026)
    
    # Definition der Kontraktmonate und deren Kürzel
    months_map = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
    
    # Wir bestimmen die Rollover-Termine für das aktuelle Jahr
    rollovers = {}
    for m in [3, 6, 9, 12]:
        third_friday = get_third_friday(year, m)
        # Rollover-Donnerstag ist 1 Tag vor dem 3. Freitag
        rollover_thursday = third_friday - timedelta(days=1)
        rollovers[m] = rollover_thursday
        
    # Bestimme, in welchem Quartalsfenster wir uns befinden
    # Wenn das Datum VOR dem März-Rollover liegt -> März-Kontrakt (H)
    if target_date < rollovers[3]:
        contract_code = 'H'
        contract_year = year_suffix
    # Zwischen März-Rollover und Juni-Rollover -> Juni-Kontrakt (M)
    elif target_date < rollovers[6]:
        contract_code = 'M'
        contract_year = year_suffix
    # Zwischen Juni-Rollover und September-Rollover -> September-Kontrakt (U)
    elif target_date < rollovers[9]:
        contract_code = 'U'
        contract_year = year_suffix
    # Zwischen September-Rollover und Dezember-Rollover -> Dezember-Kontrakt (Z)
    elif target_date < rollovers[12]:
        contract_code = 'Z'
        contract_year = year_suffix
    # Nach dem Dezember-Rollover -> März-Kontrakt des NÄCHSTEN Jahres (H)
    else:
        contract_code = 'H'
        contract_year = str(year + 1)[-1]
    
    return f"{symbol.upper()}{contract_code}{contract_year}", rollovers


def get_access_token(name = None, password = None, sec = None, cid = None, app_id = "plutos_bot"):
    """Authentifiziert sich über die REST-API und holt das Access-Token."""
    if (name is None):
        name = os.getenv("TRADOVATE_NAME")
        if name is None:
            raise Exception("TRADOVATE_NAME environment variable is not set.")
    if (password is None):
        password = os.getenv("TRADOVATE_PASSWORD")
        if password is None:
            raise Exception("TRADOVATE_PASSWORD environment variable is not set.")
    if (sec is None):
        sec = os.getenv("TRADOVATE_SEC")
        if sec is None:
            raise Exception("TRADOVATE_SEC environment variable is not set.")
    if (cid is None):
        cid = os.getenv("TRADOVATE_CID")
        if cid is None:
            raise Exception("TRADOVATE_CID environment variable is not set.")
    payload = {
        "name": name,
        "password": password,
        "appId": app_id,
        "appVersion": "1.0",
        "cid": cid,
        "sec": sec,
        "deviceId": str(uuid.uuid4())
    }
    response = requests.post(f"{BASE_URL}/auth/accesstokenrequest", json=payload)
    if response.status_code == 200:
        data = response.json()
        if "accessToken" in data:
            return data["accessToken"]
    raise Exception(f"authentication failed: {response.text}")


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
        ws.send(f"authorize\n1\n\n{access_token}")
        
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


# --- START ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tradovate API - Automatischer MNQ Tages-Tick-Downloader")
    parser.add_argument("--date", required=True, help="Ziel-Datum im Format YYYY-MM-DD (z.B. 2026-09-28)")
    parser.add_argument("--symbol", default="MNQ", help="Symbol for download (Standard: MNQ)")
    args = parser.parse_args()

    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
        
        symbol = get_active_symbol(args.symbol, target_date)
        
        start_dt = target_date
        end_date = target_date + timedelta(days=1) - timedelta(seconds=1)
        
        START_MS = int(target_date.timestamp() * 1000)
        END_MS = int(end_date.timestamp() * 1000)
        
        print(f"{parser.prog}: downloading ticks for {symbol}: {target_date} .. {end_date}")
        
        access_token = get_access_token(app_id=parser.prog)
        
        ws_client = websocket.WebSocketApp(
            WS_URL,
            on_message=on_message,
            on_close=on_close
        )
        ws_client.run_forever()
        
    except KeyboardInterrupt:
        print(f"{parser.prog}: aborted by user. No data saved.", file=sys.stderr)
    except Exception as e:
        print(f"{parser.prog}: error: {e}", file=sys.stderr)
