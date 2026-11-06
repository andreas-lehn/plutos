#
# tradoclient.py
#

import os
import asyncio
import httpx
import websockets
import json
from datetime import datetime
import logging

# Holt genau den Logger, den Uvicorn für die Konsolen-Ausgabe nutzt
logger = logging.getLogger("uvicorn.error")

# Festgelegte Endpunkte (Demo)
DEMO_URL = "https://demo.tradovateapi.com/v1"
DEMO_WSS = "wss://demo.tradovateapi.com/v1/websocket"
LIVE_URL = "https://live.tradovateapi.com/v1"
LIVE_WSS = "wss://md.tradovateapi.com/v1/websocket"

class Portfolio:
    def __init__(self):
        self.account_id = None
        self.account_spec = None
        self.cash_balance = 0.0
        
        # Bidirektionales Mapping: Symbol <-> contractId
        self.symbol_to_id = {}
        self.id_to_symbol = {}
        
        # Aktive Markt-Zustände (Keys sind immer die numerischen contractIds)
        self.positions = {}       # Format: { contractId: { "net_pos": int, "avg_price": float } }
        self.working_orders = {}   # Format: { orderId: { "contract_id": int, "action": str, "qty": int, "price": float } }

    @classmethod
    def from_sync_data(cls, sync_d_payload):
        """
        Factory-Methode: Erstellt ein komplett initialisiertes Portfolio-Objekt
        aus dem 'd'-Key der Tradovate user/syncrequest Antwort.
        """
        portfolio = cls()

        # 1. SCHRITT: Mapping-Tabellen (contracts) aufbauen
        # Das müssen wir zuerst tun, damit wir bei Positionen/Orders Symbole auflösen könnten
        contracts = sync_d_payload.get("contracts", [])
        for contract in contracts:
            c_id = contract.get("id")
            symbol = contract.get("name")  # z.B. "MNQZ6"
            if c_id and symbol:
                portfolio.symbol_to_id[symbol] = c_id
                portfolio.id_to_symbol[c_id] = symbol

        # 2. SCHRITT: Kontodaten extrahieren (accounts)
        accounts = sync_d_payload.get("accounts", [])
        if accounts:
            # Wir nehmen das primäre Konto (meistens das erste im Array)
            main_account = accounts[0]
            portfolio.account_id = main_account.get("id")
            portfolio.account_spec = main_account.get("name")
            
        # Optional: Cash Balance auslesen (cashBalances)
        cash_balances = sync_d_payload.get("cashBalances", [])
        if cash_balances:
            # Tradovate listet hier oft Werte pro Währung auf, wir nehmen die erste
            portfolio.cash_balance = cash_balances[0].get("amount", 0.0)

        # 3. SCHRITT: Nur OFFENE Positionen filtern (positions)
        positions = sync_d_payload.get("positions", [])
        for pos in positions:
            net_pos = pos.get("netPos", 0)
            c_id = pos.get("contractId")
            portfolio.positions[c_id] = {
                "net_pos": net_pos,
            }

        # 4. SCHRITT: Nur AKTIVE Orders filtern (orders)
        orders = sync_d_payload.get("orders", [])

        for order in orders:
            status = order.get("ordStatus")
            
            # Wir ignorieren "Filled", "Cancelled", "Rejected" aus der Historie
            if status in ["Working", "PendingNew"]:
                order_id = order.get("id")
                portfolio.working_orders[order_id] = {
                    "contract_id": order.get("contractId"),
                    "status": status,
                    "action": order.get("action"),  # "Buy" oder "Sell"
                }

        return portfolio

    # Hilfsmethoden für die spätere Bot-Logik
    def get_symbol_by_id(self, contract_id):
        return self.id_to_symbol.get(contract_id, f"UNKNOWN_{contract_id}")

    def get_id_by_symbol(self, symbol):
        return self.symbol_to_id.get(symbol)

    def on_order(self, event, order):
        """ order event received """
        status = order.get("ordStatus")
        order_id = order.get("id")
        self.working_orders[order_id] = {
            "contract_id": order.get("contractId"),
            "status": status,
            "action": order.get("action"),  # "Buy" oder "Sell"
        }

    def on_position(self, event, entity):
        c_id = entity.get('contractId')
        net_pos = entity.get('netPos')
        self.positions[c_id] = {
            "net_pos": net_pos,
        }

    def on_cash_balance(self, event, entity):
        if entity.get("accountId") == self.account_id:
            self.cash_balance = entity.get("amount")

    def on_props(self, etype, event, entity):
        """
        Wird aufgerufen, wenn der Server von sich aus eine Änderung schickt.
        """
        if etype == "order":
            self.on_order(event, entity)
        elif etype == "position":
            self.on_position(event, entity)
        elif etype == "cashBalance":
            self.on_cash_balance(event, entity)


    def __repr__(self):
        """ Entwickler-Ansicht: Zeigt den internen Zustand kompakt beim Debuggen."""
        return f"Portfolio(account='{self.account_spec}', positions_count={len(self.positions)}, working_orders_count={len(self.working_orders)})"

    def __str__(self):
        """ Standard-String-Ausgabe: Liefert eine kurze, prägnante Zusammenfassung."""
        pos_summary = ", ".join([f"{self.get_symbol_by_id(cid)}: {data['net_pos']}" for cid, data in self.positions.items()])
        return f"Account: {self.account_spec} | Balance: {self.cash_balance}$ | Positions: [{pos_summary or 'None'}]"

    def display(self):

        """
        Gibt den kompletten aktuellen Zustand des Portfolios hochformatiert aus.
        Ersetzt das unübersichtliche Loggen im WebSocket-Handler.
        """
        print(f"\nAccount {self.account_spec} ({self.account_id}) {self.cash_balance:.2f} USD\n")
        # 1. Positionen ausgeben
        print(f"  {'contract id':>12}  symbol  {'qty':>6}")
        for c_id, data in self.positions.items():
            symbol = self.get_symbol_by_id(c_id)
            pos_str = f"+{data['net_pos']}" if data['net_pos'] > 0 else str(data['net_pos'])
            print(f"  {c_id:>12}  {symbol:>6}  {pos_str:>6}")

        # 2. Arbeitende Orders ausgeben
        print()
        print(f"  {'order id':>12}  symbol  {'action':>6}  {'status':>10}")
        for o_id, data in self.working_orders.items():
            symbol = self.get_symbol_by_id(data['contract_id'])
            print(f"  {o_id:>12}  {symbol:>6}  {data['action']:>6}  {data['status']:>10}")  
        print()


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
        self.expitation_time = None
        self.ws = None
        self._request_id = 0
        self.portfolio = None
        self._listen_task = None
        self._pending_requests = {}
        self.connection_authorized = False

    # Als neue Methode in die Klasse einfügen:
    async def send_command(self, endpoint, body=""):
        """
        Zusatzfunktion, die das Tradovate-WSS-Format generiert,
        die Request-ID automatisch erhöht und die Nachricht absendet.
        """
        if not self.ws:
            raise ConnectionError("WebSocket not connected.")

        # Format: endpoint\nreq_id\nquery\nbody
        self._request_id += 1
        message = f"{endpoint}\n{self._request_id}\n\n{body}"
        await self.ws.send(message)
        
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_requests[self._request_id] = future
        return future


    async def on_response(self, request_id, status, data):
        """
        Wird aufgerufen, wenn der Server direkt auf eine unserer Anfragen antwortet.
        """

        future = self._pending_requests.pop(request_id)
        if status == 200:
            future.set_result(data)
            if request_id == 1:
                self.connection_authorized = True
        else:
            future.set_exception(ValueError(f"{request_id} failed {status}: {data}"))


    async def authorize(self):
        """ Autorizes open WebSocket connection """
        if not self.access_token:
            raise ValueError("no access token available")
        return await self.send_command("authorize", self.access_token)


    async def user_sync(self):
        """
        Fordert den vollständigen Konto- und Positions-Sync von Tradovate an.
        Die Daten fließen danach automatisch in die Hintergrund-Schleife.
        """
        return await self.send_command(
            "user/syncrequest", 
            '{ "entityTypes": [ "account", "contract", "order", "position", "cashBalance" ] }'
        )


    async def place_order(self, order_type: str, action: str, qty: int, price: float = None, stop_price: float = None):
        order = (
            f'"accountId":{self.portfolio.account_id},'
            f'"action":"{action}",'
            f'"symbol":"MNQZ6",'
            f'"orderType":"{order_type}",'
            f'"orderQty":{qty},'
            f'"isAutomated": true,'
            f'"timeInForce":"Day"'
        )
        if price:
            order += f',"price":{price}'
        if stop_price:
            order += f',"stopPrice":{stop_price}'

        command = await self.send_command('order/placeorder', '{' + order + '}')
        return (await command)['orderId']


    async def cancel_order(self, order_id: int):
        body = f'"orderId": {order_id}'
        return await self.send_command("order/cancelorder", '{' + body + '}')
    

    async def modify_order(self, order_id: int, order_type: str, action: str, qty: int, price: float = None, stop_price: float = None):
        order = (
            f'"orderId":{order_id},'
            f'"action":"{action}",'
            f'"symbol":"MNQZ6",'
            f'"orderType":"{order_type}",'
            f'"orderQty":{qty},'
            f'"isAutomated": true,'
            f'"timeInForce":"Day"'
        )
        if price:
            order += f',"price":{price}'
        if stop_price:
            order += f',"stopPrice":{stop_price}'
        return await self.send_command('order/modifyorder', '{' + order + '}')


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
            data = response.json()
            self.access_token = data.get("accessToken")
            self.expitation_time = datetime.fromisoformat(data.get("expirationTime"))
            logger.info("Tradovate access token received.")

        # 2. WebSocket-Verbindung herstellen
        self.ws = await websockets.connect(self.wss_url)
        logger.info("Tradovate web socket connected.")

        # Verbindung authorisieren
        await (await self.authorize())
        logger.info("Tradovate web socket successfully authorized.")
        
        # user sychronisieren
        sync_request = await self.user_sync()
        self.portfolio = Portfolio.from_sync_data(await sync_request)
        logger.info(f"Connected to Tradovate account {self.portfolio.account_spec}({self.portfolio.account_id})")

    
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
                    logger.info("Tradovate access token invalidated (HTTP logout)")
            except Exception as e:
                logger.error(f"error during HTTP logout: Tradovate access token not invalidated): {e}")
            finally:
                self.access_token = None

        # 2. Den WebSocket schließen
        if self.ws:
            await self.ws.close()
            logger.info("Tradovate web socket closed.")


    async def listen_loop(self):
        """
        Der reine Router: Erkennt den Typ (Response oder Event) 
        und leitet die Daten sofort an die zuständige Methode weiter.
        """
        try:
            logger.info("Tradovate web socket listen loop is running...")
            while not self.ws:
                await asyncio.sleep(0.1)

            logger.info("Tradovate web socket is opened. Receiving messages...")
            async for message in self.ws:
                if message == "h":
                    await self.ws.send('[]')
                elif message == "o":
                    logger.info('Recieved Tradovate web socket connection open message')
                elif message.startswith("a"):
                    raw_data = json.loads(message[1:])
                    for item in raw_data:
                        # Pfad 1: Es ist eine Antwort auf ein Command (i ist vorhanden)
                        if "i" in item:
                            await self.on_response(
                                request_id=item.get("i"),
                                status=item.get("s"),
                                data=item.get("d", {})
                            )
                        
                        # Pfad 2: Es ist ein spontanes Live-Event (e ist vorhanden)
                        elif "e" in item:
                            event=item.get("e")
                            data=item.get("d", {})
                            if event == "props":
                                self.portfolio.on_props(data.get("entityType"), data.get("eventType"), data.get("entity"))
                            elif event == "shutdown":
                                logger.warning('Tradovate web socket shutdown message reveived:', data.get('reasonCode'), data.get('reason'))
                            elif event == "md":
                                pass
                            elif event == "clock":
                                pass
                elif message.startswith("c"):
                    closing_frame = json.load(message[1:])
                    logger.warning('Tradovate web socket closing frame received:', closing_frame)

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Tradovate web socket closed. Listener loop terminated.")
        except asyncio.CancelledError:
            logger.info('Tradovate web sockert listen loop cancelled.')


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

async def main():
    print("Starte den reaktiven Tradovate-Live-Monitor...")
    print("Beenden mit STRG+C (Ctrl+C)\n")
    
    try:
        conn = Connection(demo=True)
        listen_task = asyncio.create_task(conn.listen_loop())
        async with conn:
            conn.portfolio.display()
            for order_id in conn.portfolio.working_orders:
                await conn.cancel_order(order_id)
            
            buy_id = await conn.place_order('Market', 'Buy', 1)
            print(f"buy order = {buy_id}")

            sell_id = await conn.place_order('Market', 'Sell', 1)
            print(f"sell order = {sell_id}")

            stop_id = await conn.place_order('Stop', 'Sell', 1, stop_price=25000.0)
            print(f"stop_id = {stop_id}")
            await conn.modify_order(stop_id, 'Stop', 'Sell', 1, stop_price=26000.0)

            await asyncio.sleep(1.0)

            await conn.cancel_order(stop_id)

            # Endlosschleife, die den Bot am Leben hält
            while True:
                # Wir schlafen jeweils 1 Sekunde, um die CPU nicht zu belasten.
                # Der Listener läuft im Hintergrund völlig unabhängig davon weiter!
                conn.portfolio.display()
                await asyncio.sleep(1.0)
        
        listen_task.cancel()        
                
    except asyncio.CancelledError:
        # Wird ausgelöst, wenn der Task sauber beendet wird
        print("\nLive-Monitor wird heruntergefahren...")
    except KeyboardInterrupt:
        # Fängt das Ctrl+C ab
        print("\nBot manuell durch Benutzer gestoppt.")


if __name__ == "__main__":
    # Startet die offizielle asynchrone Engine für das Skript
    asyncio.run(main())
