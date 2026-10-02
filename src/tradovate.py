# Tradovate API

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
