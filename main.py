import asyncio
import logging
import random
from fastapi import FastAPI, Request

# Logging konfigurieren (wichtig für render.com Live-Logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("plutos")

app = FastAPI(
    title="Plotos trading bot",
    description="AI supported hight performance sculping bot for Nasdaq Futures (NQ/MNQ).",
    version="1.0.0")

# Globale Variable zur Steuerung der Hintergrund-Schleife
bot_running = False

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
