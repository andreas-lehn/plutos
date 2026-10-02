# Tradovate API

import asyncio
import json
import aiohttp
import websockets
import os
import requests
from datetime import datetime, timedelta

# Festgelegte Endpunkte (Demo)
DEMO_URL = "https://demo.tradovateapi.com/v1"
LIVE_URL = "https://live.tradovateapi.com/v1"
WS_URL = "wss://md.tradovateapi.com/v1/websocket"

async def get_access_token(name = None, password = None, sec = None, cid = None, app_id = "plutos_bot", url = DEMO_URL):
    """Authenticate by REST-API and retrieve the access token."""
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
    }
    response = requests.post(f"{url}/auth/accesstokenrequest", json=payload)
    if response.status_code == 200:
        data = response.json()
        if "accessToken" in data:
            return data["accessToken"]
    raise Exception(f"authentication failed: {response.text}")


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
        rollover_thursday = third_friday - timedelta(days=8)  # 8 Tage zurück, um den Donnerstag vor dem 3. Freitag zu erhalten
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
    
    return f"{symbol.upper()}{contract_code}{contract_year}"

class TradovateAPI:
    def __init__(self, username, password, app_id, app_version, is_demo=True):
        self.username = username
        self.password = password
        self.app_id = app_id
        self.app_version = app_version
        
        # Basis-URLs für Demo- oder Live-Umgebung
        if is_demo:
            self.rest_url = "https://tradovateapi.com"
        else:
            self.rest_url = "https://tradovateapi.com"
        self.ws_url = "wss://://tradovateapi.com"
            
        self.token = None
        self.websocket = None
        self._request_id = 1  # Tradovate verlangt eine fortlaufende ID pro WS-Anfrage

    async def authenticate(self):
        """Authentifiziert den Client über REST und speichert das Access-Token."""
        url = f"{self.rest_url}/auth/namecredentialsauthentication"
        payload = {
            "name": self.username,
            "password": self.password,
            "appId": self.app_id,
            "appVersion": self.app_version
        }
        
        print("[*] Authentifiziere bei Tradovate...")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("accessToken")
                    print("[+] Authentifizierung erfolgreich. Token erhalten.")
                    return True
                else:
                    error_text = await response.text()
                    raise Exception(f"Authentifizierung fehlgeschlagen: {response.status} - {error_text}")

    async def connect_websocket(self):
        """Herstellt die WebSocket-Verbindung und autorisiert diese mit dem Token."""
        if not self.token:
            raise Exception("Bitte zuerst am() aufrufen, um ein Token zu generieren.")
            
        print(f"[*] Verbinde mit WebSocket: {self.ws_url}")
        self.websocket = await websockets.connect(self.ws_url)
        
        # Tradovate (SockJS) schickt direkt nach dem Verbindungsaufbau ein "o" (Open-Frame)
        initial_frame = await self.websocket.recv()
        if initial_frame == 'o':
            print("[+] WebSocket-Kanal geöffnet (SockJS 'o' empfangen).")
            
        # Autorisierung über den WebSocket-Kanal senden
        await self.send_ws_request("authorize", self.token)

    async def send_ws_request(self, endpoint, body=None):
        """Hilfsmethode, um Anfragen im von Tradovate erwarteten SockJS-Format zu senden."""
        # Tradovate erwartet: "URL\nReqID\n[QueryArgs]\nBody"
        req_id = self._request_id
        self._request_id += 1
        
        formatted_body = json.dumps(body) if body else ""
        payload = f"{endpoint}\n{req_id}\n\n{formatted_body}"
        
        # SockJS verlangt, dass die Nachricht als JSON-String-Array verpackt ist
        wrapped_payload = json.dumps([payload])
        await self.websocket.send(wrapped_payload)

    async def listen(self, callback_func):
        """
        Lauscht auf dem WebSocket und gibt bereinigte Daten an eine 
        Callback-Funktion weiter. Behandelt auch das Tradovate-Heartbeat ('h').
        """
        print("[*] Starte WebSocket-Zuhörer...")
        try:
            async for raw_message in self.websocket:
                # 1. Heartbeats abfangen (Tradovate schickt regelmäßig 'h')
                if raw_message == 'h':
                    # SockJS benötigt keine Antwort auf ein 'h', es dient nur als Lebenszeichen
                    continue
                
                # 2. Daten-Frames beginnen bei SockJS mit 'a' (z.B. a["..."])
                if raw_message.startswith('a'):
                    # Das 'a' abschneiden und das enthaltene JSON-Array parsen
                    inner_data_json = raw_message[1:]
                    frames = json.loads(inner_data_json)
                    
                    for frame in frames:
                        # Eventuelle Zeilenumbrüche von Tradovate bereinigen
                        cleaned_frame = frame.strip()
                        if not cleaned_frame:
                            continue
                        
                        # Übergabe der Rohdaten an Ihre benutzerdefinierte Funktion
                        await callback_func(cleaned_frame)
                        
        except websockets.exceptions.ConnectionClosed:
            print("[-] Verbindung vom Tradovate-Server geschlossen (EOF/Close Frame).")
