
"""FastAPI endpoints for ChronosMatch."""

from itertools import count
import asyncio

from .market_simulator import MarketSimulator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .matching_engine import MatchingEngine
from .models import Order, OrderSide

app = FastAPI(title="ChronosMatch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

engine = MatchingEngine()
order_ids = count(1)
timestamps = count(1)

simulator = MarketSimulator()
simulator_task: asyncio.Task | None = None
simulator_orders_generated = 0


class OrderRequest(BaseModel):
    order_id: str | None = None
    side: OrderSide
    price: int = Field(gt=0)
    quantity: int = Field(gt=0)


def order_to_dict(order: Order) -> dict:
    return {
        "order_id": order.order_id,
        "side": order.side.value,
        "price": order.price,
        "quantity": order.quantity,
        "remaining_quantity": order.remaining_quantity,
        "timestamp": order.timestamp,
    }


def trade_to_dict(trade) -> dict:
    return {
        "trade_id": trade.trade_id,
        "buy_order_id": trade.buy_order_id,
        "sell_order_id": trade.sell_order_id,
        "price": trade.price,
        "quantity": trade.quantity,
        "timestamp": trade.timestamp,
    }


@app.get("/")
def root():
    return {"name": "ChronosMatch API", "docs": "/docs", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/orderbook")
def get_orderbook():
    book = engine.order_book
    bids = [
        order_to_dict(o) for o in book._bids
        if o.remaining_quantity is not None and o.remaining_quantity > 0
    ]
    asks = [
        order_to_dict(o) for o in book._asks
        if o.remaining_quantity is not None and o.remaining_quantity > 0
    ]
    best_bid = book.get_best_bid()
    best_ask = book.get_best_ask()

    return {
        "bids": bids,
        "asks": asks,
        "best_bid": best_bid.price if best_bid else None,
        "best_ask": best_ask.price if best_ask else None,
    }


@app.get("/trades")
def get_trades():
    return [trade_to_dict(t) for t in engine.trades]


@app.post("/orders")
def submit_order(request: OrderRequest):
    order_id = request.order_id or f"WEB-{next(order_ids)}"

    try:
        order = Order(
            order_id=order_id,
            side=request.side,
            price=request.price,
            quantity=request.quantity,
            timestamp=next(timestamps),
        )
        trades = engine.submit_order(order)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "order": order_to_dict(order),
        "trades": [trade_to_dict(t) for t in trades],
        "orderbook": get_orderbook(),
    }
async def _run_simulator():
    global simulator_orders_generated

    async for order in simulator.generate_orders(
        count=None,
        yield_every=1,
    ):
        engine.submit_order(order)
        simulator_orders_generated += 1

        # Keep the simulation readable and responsive.
        await asyncio.sleep(0.5)


@app.post("/simulator/start")
async def start_simulator():
    global simulator_task

    if simulator_task is not None and not simulator_task.done():
        return {"status": "already_running"}

    simulator_task = asyncio.create_task(_run_simulator())
    return {"status": "running"}


@app.post("/simulator/stop")
async def stop_simulator():
    global simulator_task

    if simulator_task is not None and not simulator_task.done():
        simulator_task.cancel()

        try:
            await simulator_task
        except asyncio.CancelledError:
            pass

    simulator_task = None
    return {"status": "stopped"}


@app.get("/simulator/status")
async def get_simulator_status():
    running = simulator_task is not None and not simulator_task.done()

    return {
        "running": running,
        "generated": simulator_orders_generated,
    }