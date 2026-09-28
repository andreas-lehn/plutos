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

# --- FASTAPI ENDPOINTS ---

@app.on_event("startup")
async def startup_event():
    """Wird aufgerufen, sobald FastAPI startet."""
    logger.info("Bot startup...")

@app.on_event("shutdown")
async def shutdown_event():
    """Wird aufgerufen, wenn der Server gestoppt wird."""
    logger.info("Bot shutting down...")

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
