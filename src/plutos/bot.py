import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import tradoclient

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Plutos Bot",
    description="High performance trading bot for Nasdaq Futures (NQ/MNQ).",
    version="1.0.0",
)

trado_connection = tradoclient.Connection(True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    trado_task = asyncio.create_task(trado_connection.listen_loop())
    await trado_connection.connect()

    yield

    await trado_connection.disconnect()
    trado_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "status": "online", 
        "message": "Plutos bot is running..."
    }

@app.get("/account")
async def account_info():
    return (
        '{'
            f'"accountName":{trado_connection.portfolio.account_spec},'
            f'"accountId":{trado_connection.portfolio.account_id},'
            f'"balance":{trado_connection.portfolio.cash_balance}'
        '}')
