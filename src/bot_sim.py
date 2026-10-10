# simulation of the bot based on databento ticks file

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from typing import List, Dict
import logging
from marketdata import SampleBuilder
import databento as db

# Logger initialisieren
logger = logging.getLogger("uvicorn.error")  # Nutzt den Uvicorn-Fehlerlogger für konsistente Ausgabe

# Globale Datenspeicher und Kommunikations-Queue
sample_queue: asyncio.Queue = asyncio.Queue(10)
sample_list: List = []


async def on_sample(sample: Dict):
    logger.info(f"sample {sample['timestamp']} written to queue")
    await sample_queue.put(sample)


async def databento_task():
    import os

    FILE_PATH = os.getenv("PLUTOS_SIM_TRADES_FILE", "databento_trades.dbn")
    logger.info(f"Databento Task gestartet... Lese Datei: {FILE_PATH}")

    if not os.path.exists(FILE_PATH):
        raise BaseException(f"FEHLER: Datei '{FILE_PATH}' wurde nicht gefunden!")

    builder = SampleBuilder()    
    trades = db.DBNStore.from_file(FILE_PATH)
    for record in trades:
        sample = builder.on_trade(record)
        if sample is not None:
            await sample_queue.put(sample)
    if builder.is_sample_available:
        await sample_queue.put(builder.get_sample())


async def queue_consumer_task():
    """Holt die aggregierten Samples aus der Queue und speichert sie in der Liste."""
    logger.info("Queue Consumer Task gestartet...")
    while True:
        # Wartet blockierungsfrei, bis Daten in der Queue verfügbar sind
        sample = await sample_queue.get()
        sample_list.append(sample)
        sample_queue.task_done()


# --- DER NEUE LIFESPAN HANDLER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup-Logik: Hintergrund-Tasks beim Starten der API registrieren
    databento_job = asyncio.create_task(databento_task())
    consumer_job = asyncio.create_task(queue_consumer_task())

    # 0.5 Sekunden warten, damit die Tasks kurz anlaufen können
    await asyncio.sleep(0.5)
    
    # Status prüfen
    if databento_job.done():
        logger.error(f"Databento Task ist bereits beendet! Ergebnis/Fehler: {databento_job.exception()}")
    if consumer_job.done():
        logger.error(f"Consumer Task ist bereits beendet! Ergebnis/Fehler: {consumer_job.exception()}")

    yield  # Hier läuft die FastAPI App und nimmt HTTP-Requests entgegen
    
    # 2. Shutdown-Logik: Tasks sauber beenden, wenn die App gestoppt wird
    databento_job.cancel()
    consumer_job.cancel()
    print("Hintergrund-Tasks sauber beendet.")

# App-Instanz wird direkt mit dem Lifespan-Manager verknüpft
app = FastAPI(lifespan=lifespan)

# --- ENDPUNKTE ---

@app.get("/count")
async def get_count():
    """Liefert die Anzahl der aktuell verarbeiteten Sekunden-Samples."""
    return {"count": len(sample_list)}

@app.get("/sample/{n}")
async def get_sample(n: int):
    """Liefert das n-te Sample aus der Liste (0-basiert)."""
    if n < 0 or n >= len(sample_list):
        raise HTTPException(
            status_code=404, 
            detail=f"Sample am Index {n} nicht gefunden. Aktuelle Länge ist {len(sample_list)}."
        )
    return sample_list[n]

