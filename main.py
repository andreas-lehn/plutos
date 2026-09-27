import asyncio
import logging
import random
from fastapi import FastAPI, Request
import httpx
import os

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Plutos bot",
    description="AI supported high performance sculping bot for Nasdaq Futures (NQ/MNQ).",
    version="1.0.0")

# Globale Variable zur Steuerung der Hintergrund-Schleife
bot_running = False

# Die App zieht sich die Daten direkt aus der aktiven Conda-Umgebung bzw. Render-Umgebung
TRADOVATE_URL = "https://tradovateapi.com"
TRADOVATE_USER = os.getenv("TRADOVATE_USER")
TRADOVATE_PASS = os.getenv("TRADOVATE_PASS")
TRADOVATE_APP_KEY = os.getenv("TRADOVATE_APP_KEY")

# Sicherheitsprüfung beim Start des Bots, ob alle wichtigen Umgebungsvariablen gesetzt sind
if not TRADOVATE_USER:
    logger.error("TRADOVATE_USER not set!")
if not TRADOVATE_PASS:
    logger.error("TRADOVATE_PASS not set!")
if not TRADOVATE_APP_KEY:
    logger.error("TRADOVATE_APP_KEY not set!")

# Globale Variable, um das Token für andere Funktionen bereitzuhalten
token_store = {
    "access_token": None,
    "expiration": None
}

async def get_tradovate_token() -> bool:
    """ Holt sich ein frisches OAuth-Token von Tradovate """
    url = f"{TRADOVATE_URL}/auth/accesstokenrequest"
    payload = {
        "name": TRADOVATE_USER,
        "password": TRADOVATE_PASS,
        "appId": TRADOVATE_APP_KEY,
        "appVersion": "1.0.0"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                token_store["access_token"] = data.get("accessToken")
                logger.info("🔐 TRADOVATE: Login erfolgreich! Access Token empfangen.")
                return True
            else:
                logger.error(f"❌ TRADOVATE: Login fehlgeschlagen. Status: {response.status_code}, Info: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ TRADOVATE: Fehler bei Verbindung zu Tradovate: {e}")
        return False

# --- MINIMALE PLATZHALTER-LOGIK ---

def mock_ki_prediction() -> float:
    """Simuliert die KI-Vorhersage (Wert zwischen -1.0 und +1.0)"""
    return round(random.uniform(-1.0, 1.0), 2)

def execute_algorithmic_logic(ki_signal: float):
    """Klassische algorithmische Logik mit fixen Schwellenwerten"""
    THRESHOLD = 0.75 
    
    if ki_signal >= THRESHOLD:
        logger.info(f"🚀 ALGO-LOGIK: Signal ({ki_signal}) >= {THRESHOLD}. Sende BUY Bracket-Order!")
    elif ki_signal <= -THRESHOLD:
        logger.info(f"💥 ALGO-LOGIK: Signal ({ki_signal}) <= -{THRESHOLD}. Sende SELL Bracket-Order!")
    else:
        logger.info(f"⏳ ALGO-LOGIK: Signal ({ki_signal}) neutral. Kein Trade.")

# --- BACKGROUND TASK (Das 10-Sekunden Herzstück) ---

async def trading_loop():
    """Diese Schleife läuft asynchron im Hintergrund."""
    global bot_running
    logger.info("Schleife gestartet. Warte auf den nächsten 10-Sekunden-Takt...")
    
    while bot_running:
        try:
            logger.info("🔄 10-Sekunden-Fenster geschlossen. Verarbeite Takt...")
            
            # KI berechnet Signal
            ki_signal = mock_ki_prediction()
            logger.info(f"🧠 KI-Vorhersage: {ki_signal}")
            
            # Algorithmus entscheidet
            execute_algorithmic_logic(ki_signal)
            
        except Exception as e:
            logger.error(f"Fehler in der Trading-Schleife: {e}")
            
        # Exakt 10 Sekunden warten
        await asyncio.sleep(10)

# --- FASTAPI ENDPOINTS ---

@app.on_event("startup")
async def startup_event():
    """Wird aufgerufen, sobald FastAPI startet."""
    global bot_running
    bot_running = True
    asyncio.create_task(trading_loop())
    logger.info("✅ Bot initialisiert und Hintergrund-Task läuft.")

@app.on_event("shutdown")
async def shutdown_event():
    """Wird aufgerufen, wenn der Server gestoppt wird."""
    global bot_running
    bot_running = False
    logger.info("🛑 Bot wird heruntergefahren...")

@app.get("/")
def read_root(request: Request):
    """Gibt die zentralen Metadaten der FastAPI-App dynamisch zurück."""
    # Holt sich die App-Instanz aus dem Request
    app = request.app 
    
    return {
        "name": app.title,
        "description": app.description,
        "version": app.version
    }

@app.get("/health")
def health_check():
    """Wichtig für das Deployment auf render.com"""
    return {"status": "healthy", "bot_running": bot_running}
