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
    return {
        "accountName": trado_connection.portfolio.account_spec,
        "accountId": trado_connection.portfolio.account_id,
        "balance": trado_connection.portfolio.cash_balance,
    }

@app.get("/orders")
async def get_orders():
    orders = []
    for key, values in trado_connection.portfolio.working_orders.items():
        values['order_id'] = key
        values['symbol'] = trado_connection.portfolio.get_symbol_by_id(values['contract_id'])
        orders.append(values)
    return orders

@app.get("/positions")
async def get_positions():
    positions = []
    for key, values in trado_connection.portfolio.positions.items():
        values['contract_id'] = key
        values['symbol'] = trado_connection.portfolio.get_symbol_by_id(key)
        positions.append(values)
    return positions

# Daten-Modell für das Platzieren einer Order
class OrderPayload(BaseModel):
    action: str  # "Buy" oder "Sell"
    qty: int
    price: float

@app.post("/place/order")
async def place_order(order: OrderPayload):
    try:
        order_type = 'Limit' if order.price != 0.0 else 'Market'
        order_id = await trado_connection.place_order(order_type, order.action, order.qty, price=order.price)
        return {"status": "success", "orderId": order_id}
        
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Tradovate API timeout")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/place/stop")
async def place_stop(order: OrderPayload):
    try:
        order_id = await trado_connection.place_order('Stop', order.action, order.qty, stop_price=order.price)
        return {"status": "success", "orderId": order_id}
        
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Tradovate API timeout")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/cancel/order")
async def cancel_order(order_id: int):
    try:
        response = await trado_connection.cancel_order(order_id)
        return {"status": "success", "response": await response}
        
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Tradovate API timeout")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/modify/stop")
async def modify_stop(order_id: int, order: OrderPayload):
    try:
        response = await trado_connection.modify_order(order_id, 'Stop', order.action, order.qty, stop_price=order.price)
        return {"status": "success", "response": await response}
        
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Tradovate API timeout")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

