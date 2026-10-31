#
# tradoclient.py
#

import os
import asyncio
import httpx
import websockets
import json

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
            
            # Wichtig: Tradovate schickt auch geschlossene Positionen (netPos == 0) im Sync mit!
            if c_id and net_pos != 0:
                # TRADOVATE PRICE-HUNTING: Suche nach dem echten Einstiegspreis
                # 1. Versuch: Der Standard-Einstiegspreis
                price = pos.get("avgPrice")
                # 2. Versuch: Falls avgPrice 0/None ist, nimm prevAvgPrice (häufig bei Overnight-Positions)
                if not price or float(price) == 0.0:
                    price = pos.get("prevAvgPrice")

                portfolio.positions[c_id] = {
                    "net_pos": net_pos,
                    "avg_price": price if price else 0.0
                }

        # 4. SCHRITT: Nur AKTIVE Orders filtern (orders)
        orders = sync_d_payload.get("orders", [])
        for order in orders:
            status = order.get("orderStatus")
            
            # Wir ignorieren "Filled", "Cancelled", "Rejected" aus der Historie
            if status in ["Working", "PendingNew"]:
                order_id = order.get("id")
                portfolio.working_orders[order_id] = {
                    "contract_id": order.get("contractId"),
                    "action": order.get("action"),  # "Buy" oder "Sell"
                    "qty": order.get("qty"),
                    "price": order.get("price")
                }

        return portfolio

    # Hilfsmethoden für die spätere Bot-Logik
    def get_symbol_by_id(self, contract_id):
        return self.id_to_symbol.get(contract_id, f"UNKNOWN_{contract_id}")

    def get_id_by_symbol(self, symbol):
        return self.symbol_to_id.get(symbol)

    def __repr__(self):
        """Entwickler-Ansicht: Zeigt den internen Zustand kompakt beim Debuggen."""
        return f"Portfolio(account='{self.account_spec}', positions_count={len(self.positions)}, working_orders_count={len(self.working_orders)})"

    def __str__(self):
        """Standard-String-Ausgabe: Liefert eine kurze, prägnante Zusammenfassung."""
        pos_summary = ", ".join([f"{self.get_symbol_by_id(cid)}: {data['net_pos']}" for cid, data in self.positions.items()])
        return f"Account: {self.account_spec} | Balance: {self.cash_balance}$ | Positions: [{pos_summary or 'None'}]"

    def display(self):
        """
        Gibt den kompletten aktuellen Zustand des Portfolios hochformatiert aus.
        Ersetzt das unübersichtliche Loggen im WebSocket-Handler.
        """
        print(f"\nAccount {self.account_spec} ({self.account_id}) {self.cash_balance:.2f} USD\n")
        # 1. Positionen ausgeben
        print(f"  {'contract id':>12}  symbol  {'qty':>6}  {'Ø price':>10}")
        for c_id, data in self.positions.items():
            symbol = self.get_symbol_by_id(c_id)
            # Ein Pluszeichen für Long-Positionen hinzufügen
            pos_str = f"+{data['net_pos']}" if data['net_pos'] > 0 else str(data['net_pos'])
            print(f"  {c_id:>12}  {symbol:>6}  {pos_str:>6}  {data['avg_price']:>10.2f}")
        # 2. Arbeitende Orders ausgeben
        print()
        print(f"  {'order id':>12}  symbol  {'action':>6}  {'qty':>6}  {'limit':>10}")
        for o_id, data in self.working_orders.items():
            symbol = self.get_symbol_by_id(data['contract_id'])
            price_str = f"{data['price']:.2f}" if data['price'] is not None else "Market"
            print(f"  {o_id:>12}  {symbol:>6}  {data['action']:>6}  {data['qty']:>6} | {price_str:>10}")  
        print()


# 1. Die neue Account-Klasse ganz oben in der Datei definieren:
class Account:
    def __init__(self, connection, id, name):
        """
        Repräsentiert dein Handelskonto im RAM.
        Hält eine saubere Referenz zurück zur übergeordneten Connection.
        """
        self.connection = connection
        self.id = id
        self.name = name
        self.balance = 0.0
        self.positions = {}  # Symbol -> Position (bauen wir im nächsten Schritt)

    @classmethod
    def from_responce(cls, connection, data):
        return cls(connection, data.get('id'), data.get('name'))
    
    def __repr__(self):
        return f"<Account(name='{self.name}', id={self.id}, balance={self.balance}USD)>"
    
class Position:
    def __init__(self, account, symbol, qty, entry_price):
        """
        Repräsentiert einen aktiven Trade im RAM.
        Hält eine saubere Referenz nach oben zum Account.
        """
        self.account = account
        self.symbol = symbol
        self.qty = qty
        self.entry_price = entry_price
        self.stop_loss = None  # Wird später gekoppelt

    @classmethod
    def from_sync_data(cls, pos_data, contracts_map, account):
        """Factory-Methode für den initialen User-Sync."""
        contract_id = pos_data.get("contractId")
        contract_info = contracts_map.get(contract_id, {})
        
        symbol = pos_data.get("symbol") or contract_info.get("symbol", f"ID-{contract_id}")
        qty = pos_data.get("netPos", 0)
        entry_price = (
            pos_data.get("netPrice") or 
            pos_data.get("prevPrice") or 
            pos_data.get("openPrice") or 
            0.0
        )
        return cls(account, symbol, qty, entry_price)

    @classmethod
    def from_live_event(cls, entity_data, account):
        """Factory-Methode für spontane Live-Events über den WebSocket."""
        symbol = entity_data.get("symbol")
        qty = entity_data.get("netPos", 0)
        entry_price = entity_data.get("prevPrice") or entity_data.get("openPrice") or 0.0
        return cls(account, symbol, qty, entry_price)


    @property
    def is_flat(self):
        return self.qty == 0

    def __repr__(self):
        richtung = "LONG" if self.is_long else "SHORT"
        return f"<Position({richtung} {abs(self.qty)}x {self.symbol} @ {self.entry_price})>"


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
        self.portfolio = None

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


    async def user_sync(self):
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
        print("Listener läuft.")

    
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

    # Vergiss nicht, ganz oben in deiner Datei 'import json' hinzuzufügen!

    async def on_response(self, request_id, status, data):
        """
        Wird aufgerufen, wenn der Server direkt auf eine unserer Anfragen antwortet.
        """
        if status != 200:
            print(f"[ERROR] Anfrage {request_id} fehlgeschlagen mit Status {status}: {data}")
            return
        
        if request_id == 1:
            print("Subsciption successful -> sync...")
            await self.user_sync()
            
        if request_id == 2:
            print("Sync request successful -> extract state information")
            self.portfolio = Portfolio.from_sync_data(data)
            self.portfolio.display()
            # Konten extrahieren
            #for acc in data.get("accounts", []):
            #    account = Account.from_responce(self, acc)
            #    self.accounts[account.id] = account

            #for bal_data in data.get("cashBalances", []):
            #    acc_id = bal_data.get("accountId")
            #    self.accounts[acc_id].balance = bal_data.get("amount", 0.0)
            
            # 3. Temporäre Kontrakt-Übersetzungskarte bauen
            #contracts_map = {}
            #for contract in data.get("contracts", []):
            #    contracts_map[contract.get("id")] = {"symbol": contract.get("name")}
            
            # 4. Offene Positionen über die Factory erstellen und einhängen
            #for pos_data in data.get("positions", []):
            #    acc_id = pos_data.get("accountId")
            #    if pos_data.get("netPos", 0) != 0 and acc_id in self.accounts:
            #        account = self.accounts[acc_id]
            #        pos = Position.from_sync_data(pos_data, contracts_map, account)
            #        account.positions[pos.symbol] = pos


    async def on_event(self, event_type, data):
        """
        Wird aufgerufen, wenn der Server von sich aus eine Änderung schickt.
        """
        if event_type == "props":
            entity_type = data.get("entityType")
            entity = data.get("entity", {})
            acc_id = entity.get("accountId")
            if not acc_id:
                return

            account = self.accounts[acc_id]
            if not account:
                return

            # 1. Kontostand-Änderung im Live-Betrieb
            if entity_type == "cashBal":
                account.balance = entity.get("amount", 0.0)
                print(f"[LIVE-UPDATE] Kontostand für {account.name} geändert: {account.balance} USD")
                
            # 2. Positions-Änderung im Live-Betrieb
            elif entity_type == "position":
                symbol = entity.get("symbol")
                net_pos = entity.get("netPos", 0)
                if symbol not in account.positions:
                    account.positions[symbol] = Position.from_live_event(entity, account)
                else:
                    # Bestehende Position im RAM updaten
                    pos = account.positions[symbol]
                    pos.qty = net_pos
                    pos.entry_price = entity.get("prevPrice") or entity.get("openPrice") or pos.entry_price

            self.print_portfolio()


    async def _listen_loop(self):
        """
        Der reine Router: Erkennt den Typ (Response oder Event) 
        und leitet die Daten sofort an die zuständige Methode weiter.
        """
        try:
            async for message in self.ws:
                if not message:
                    continue

                if message == "h":
                    continue

                print(message[:80])

                if message == "o":
                    print("socket opened -> authorize ...")
                    await self.authorize()
                    continue

                if message.startswith("a"):
                    raw_data = json.loads(message[1:])
                    if not isinstance(raw_data, list):
                        raw_data = [ raw_data ]

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
                            await self.on_event(
                                event_type=item.get("e"),
                                data=item.get("d", {})
                            )
                                    
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket-Verbindung geschlossen. Hörer beendet.")
        except Exception as e:
            print(f"Fehler in der Router-Schleife: {e}")


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
        async with Connection(demo=True) as conn:
            # Endlosschleife, die den Bot am Leben hält
            while True:
                # Wir schlafen jeweils 1 Sekunde, um die CPU nicht zu belasten.
                # Der Listener läuft im Hintergrund völlig unabhängig davon weiter!
                await asyncio.sleep(0.2)
                
    except asyncio.CancelledError:
        # Wird ausgelöst, wenn der Task sauber beendet wird
        print("\nLive-Monitor wird heruntergefahren...")
    except KeyboardInterrupt:
        # Fängt das Ctrl+C ab
        print("\nBot manuell durch Benutzer gestoppt.")


if __name__ == "__main__":
    # Startet die offizielle asynchrone Engine für das Skript
    asyncio.run(main())
