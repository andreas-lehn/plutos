#
# tradoclient.py
#

import os
import asyncio
import httpx
import websockets

# Festgelegte Endpunkte (Demo)
DEMO_URL = "https://demo.tradovateapi.com/v1"
DEMO_WSS = "wss://demo.tradovateapi.com/v1/websocket"
LIVE_URL = "https://live.tradovateapi.com/v1"
LIVE_WSS = "wss://md.tradovateapi.com/v1/websocket"


# tradoclient.py
import os
import asyncio
import httpx
import websockets

class Connection:
    def __init__(self, demo=True):
        """
        Initialisiert die Verbindungskomponente.
        Zugangsdaten kommen aus den Umgebungsvariablen.
        """
        self.username = os.getenv("TRADOVATE_NAME")
        self.password = os.getenv("TRADOVATE_PASSWORD")
        self.client_secret = os.getenv("TRADOVATE_SEC")
        cid_env = os.getenv("TRADOVATE_CID")
        self.client_id = int(cid_env) if cid_env else None
        
        if missing := [v for v in ["TRADOVATE_NAME", "TRADOVATE_PASSWORD", "TRADOVATE_SEC", "TRADOVATE_CID"] if not os.getenv(v)]:
            raise ValueError(f"Fehlende Umgebungsvariablen: {', '.join(missing)}")
        
        # Endpunkte für HTTP und WSS trennen
        if demo:
            self.http_base = DEMO_URL
            self.wss_url = DEMO_WSS
        else:
            self.http_base = LIVE_URL
            self.wss_url = LIVE_WSS
            
        self.access_token = None
        self.ws = None
        self._request_id = 0

    # Als neue Methode in die Klasse einfügen:
    async def _send_command(self, endpoint, body=""):
        """
        Zusatzfunktion, die das Tradovate-WSS-Format generiert,
        die Request-ID automatisch erhöht und die Nachricht absendet.
        """
        if not self.ws:
            raise ConnectionError("WebSocket not connected.")
            
        self._request_id += 1
        
        # Format: endpoint\nreq_id\nquery\nbody
        message = f"{endpoint}\n{self._request_id}\n\n{body}"
        
        await self.ws.send(message)
        return self._request_id

    async def authorize(self):
        """ Autorizes open WebSocket connection """

        if not self.access_token:
            raise ValueError("no access token available")
        
        await self._send_command("authorize", self.access_token)


    async def sync_user(self):
        """
        Fordert den vollständigen Konto- und Positions-Sync von Tradovate an.
        Die Daten fließen danach automatisch in die Hintergrund-Schleife.
        """
        print("Fordere User-Synchronisation an...")
        # Endpunkt: user/syncrequest, Body: {}
        await self._send_command("user/syncrequest", "{}")


    async def connect(self):
        """
        connect to tradovate: get access token via HTTP and open WebSocket.
        """
        # 1. Token abholen via HTTP (Asynchron mit httpx)
        async with httpx.AsyncClient() as client:
            url = f"{self.http_base}/auth/accesstokenrequest"
            payload = {
                "name": self.username,
                "password": self.password,
                "appId": "PlutosBot",
                "appVersion": "1.0",
                "cid": self.client_id,
                "sec": self.client_secret,
                "deviceId": "PlutosServer"
            }
            
            response = await client.post(url, json=payload)
            response.raise_for_status()
            self.access_token = response.json().get("accessToken")
            print("HTTP-Login erfolgreich. Token erhalten.")

        # 2. WebSocket-Verbindung herstellen
        self.ws = await websockets.connect(self.wss_url)
        print("WebSocket-Verbindung erfolgreich geöffnet.")
        asyncio.create_task(self._listen_loop())
        await self.authorize()
            
        # Kurz 100ms warten, damit die Autorisierung beim Server durch ist
        await asyncio.sleep(0.1)
        # User-Sync anfordern
        await self.sync_user()

    
    async def disconnect(self):
        """
        Loggt den Token über HTTP aus und schließt den WebSocket.
        """
        # 1. Den Access Token serverseitig ungültig machen
        if self.access_token:
            try:
                async with httpx.AsyncClient() as client:
                    url = f"{self.http_base}/auth/logout"
                    headers = {
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                    # Tradovate erwartet eine leere POST-Anfrage zum Ausloggen
                    await client.post(url, headers=headers, json={})
                    print("Access Token erfolgreich bei Tradovate entwertet (HTTP Logout).")
            except Exception as e:
                print(f"Fehler beim HTTP-Logout (Token konnte nicht entwertet werden): {e}")
            finally:
                self.access_token = None

        # 2. Den WebSocket schließen
        if self.ws:
            await self.ws.close()
            print("WebSocket-Verbindung sauber geschlossen.")

    async def _listen_loop(self):
        """
        Lauscht im Hintergrund permanent auf eingehende WebSocket-Nachrichten.
        """
        try:
            # Solange der WebSocket geöffnet ist, liefert uns diese Schleife jede Nachricht
            async for message in self.ws:
                # Heartbeats ("h") von Tradovate ignorieren, um die Konsole sauber zu halten
                if message == "h":
                    continue
                    
                print(f"\n[WSS-Inbound]: {message}")
                
                # Hier werden wir später die Nachrichten parsen und an die Positionen verteilen
                
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket-Hintergrundschleife beendet (Verbindung geschlossen).")
        except Exception as e:
            print(f"Fehler in der WebSocket-Hintergrundschleife: {e}")

    async def __aenter__(self):
        """
        Ermöglicht die Nutzung von 'async with tradoclient.Connection() as c:'.
        Baut automatisch die Verbindung auf.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Sorgt dafür, dass beim Verlassen des Blocks (oder bei Fehlern)
        automatisch disconnect() aufgerufen wird.
        """
        await self.disconnect()
        return False  # Lässt eventuelle Exceptions im Block normal durchfliegen

    @property
    def connection_state(self):
        return self.ws.state.name if self.ws else "NONE"
    
    @property
    def mode(self):
        return 'demo' if 'demo' in self.http_base else 'live'
    
    def __repr__(self):
        """
        Eindeutige String-Repräsentation für den Debugger.
        Gibt Aufschluss über den Modus und den aktuellen Verbindungsstatus.
        """
        return (
            f"<{self.__class__.__name__}(mode='{self.mode}', "
            f"connection_state={self.connection_state}, "
            f"url={self.http_base})>"
        )
