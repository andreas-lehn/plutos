import json
import requests
import websocket

REST_URL = "https://live.tradovateapi.com/v1/auth/accesstokenrequest"
WSS_URL  = "wss://md.tradovateapi.com/v1/websocket"

#websocket.enableTrace(True)

request_id = 1

# 1. TOKEN FRISCH ABRUFEN
print(f"Hole frischen Access Token von der REST API: {REST_URL}")
login_payload = {
    "name": "alehn",
    "password": "Zywmyz-4fegve-fiscat",
    "appId": "plutos_bot",
    "appVersion": "1.0.0",
    "deviceId": "plutos_machine",
    "cid": 17380,
    "sec": "fecc35d8-0822-4108-8825-f91aa4f7657b"
}

response = requests.post(f"{REST_URL}", json=login_payload)

if response.status_code != 200:
    print(f"REST Login fehlgeschlagen! Status: {response.status_code}, Antwort: {response.text}")
    exit()

data = response.json()
ACCESS_TOKEN = data["accessToken"]
MD_ACCESS_TOKEN = data["mdAccessToken"]

# 2. WEBSOCKET LOGIK
def on_open(ws):
    print(f"Verbindung zu Tradovate {WSS_URL} geöffnet.")

def on_message(ws, message):
    global request_id
    print(f"Server-Nachricht: {message}")
    
    # SockJS Open-Frame
    if message == 'o':
        auth_frame = f"authorize\n{request_id}\n\n{MD_ACCESS_TOKEN}" 
        print("Sende frisch geholte Autorisierung...")
        ws.send(auth_frame.encode('utf-8'))
        request_id += 1
        
    # Server sendet Heartbeat -> Wir müssen nicht zwingend antworten, 
    # aber es zeigt, dass die Verbindung noch offen ist.
    elif message == 'h':
        pass 

    # Wenn eine Antwort kommt
    elif message.startswith('a'):
        # Schneidet das 'a' ab und lädt die Liste der Server-Antworten
        data_list = json.loads(message[1:])
        
        for item in data_list:
            # Prüfen, ob es die Antwort auf unsere Autorisierung ist
            if "s" in item and item["s"] == 200 and item["i"] == 1:
                print("Autorisierung erfolgreich! Fordere jetzt Chartdaten an...")
                
                chart_request_id = 2  # Eindeutige ID für diesen Chart-Request
                
                chart_params = {
                    "symbol": "MNQZ6",  # Micro E-mini Nasdaq (Dezember 2026)
                    "chartDescription": {
                        "underlyingType": "MinuteBar",  # Minuten-Kerzen
                        "elementSize": 1,               # 1-Minuten-Intervall
                        "elementSizeUnit": "UnderlyingUnits",
                        "withHistogram": False
                    },
                    "timeRange": {
                        # Zeitraum für gestern (01. Oktober 2026)
                        "asFarAsTimestamp": "2026-10-01T00:00:00.000Z",
                        "asCloseAsTimestamp": "2026-10-01T23:59:59.000Z"
                    }
                }
                
                # SockJS-Frame zusammensetzen
                #chart_frame = f"md/getChart\n{chart_request_id}\n\n{json.dumps(chart_params)}"
                
                # Wir bauen den String manuell zusammen – ohne f-String-Gefahr
                body_json = json.dumps(chart_params)
                chart_frame = f"md/getChart\n{chart_request_id}\n\n{body_json}"
    
                # Absenden
                message_to_send = json.dumps([chart_frame])
                print(f"Sende Chart-Anfrage: {message_to_send}")
                ws.send(message_to_send)
                print("Chart-Anfrage wurde abgesendet.")

def on_error(ws, error):
    print(f"Fehler: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"!!! VERBINDUNG GESCHLOSSEN !!!")
    print(f"Status Code: {close_status_code}")
    print(f"Grund vom Server: {close_msg}")

print(f"Versuche WebSocket-Verbindung mit URL: '{WSS_URL}'")

# Starte den WebSocket
ws = websocket.WebSocketApp(WSS_URL,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

ws.run_forever()
