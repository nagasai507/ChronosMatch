
"""FastAPI endpoints for ChronosMatch API."""

import asyncio
from itertools import count
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .market_simulator import MarketSimulator
from .matching_engine import MatchingEngine
from .models import Order, OrderSide


app = FastAPI(title="ChronosMatchAPI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

engine = MatchingEngine()
order_ids = count(1)
timestamps = count(1)

simulator = MarketSimulator()
simulator_task: asyncio.Task | None = None
simulator_orders_generated = 0

# Metrics for orders submitted through the API.
orders_processed = 0
total_matching_latency_seconds = 0.0
api_total_trades = 0
api_executed_quantity = 0


class OrderRequest(BaseModel):
    order_id: str | None = None
    side: str
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
    return {
        "name": "ChronosMatch API",
        "docs": "/docs",
        "status": "ok",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/orderbook")
def get_orderbook():
    book = engine.order_book

    bids = [
        order_to_dict(order)
        for order in book._bids
        if order.remaining_quantity is not None
        and order.remaining_quantity > 0
    ]

    asks = [
        order_to_dict(order)
        for order in book._asks
        if order.remaining_quantity is not None
        and order.remaining_quantity > 0
    ]

    best_bid = book.get_best_bid()
    best_ask = book.get_best_ask()

    return {
        "bids": bids,
        "asks": asks,
        "best_bid": (
            order_to_dict(best_bid) if best_bid else None
        ),
        "best_ask": (
            order_to_dict(best_ask) if best_ask else None
        ),
    }


@app.get("/trades")
def get_trades():
    return [trade_to_dict(trade) for trade in engine.trades]


@app.get("/metrics")
def get_metrics():
    """Return metrics for API-submitted orders only."""

    average_latency_ms = (
        total_matching_latency_seconds / orders_processed * 1000
        if orders_processed
        else 0.0
    )

    matching_operations_per_second = (
        orders_processed / total_matching_latency_seconds
        if total_matching_latency_seconds > 0
        else 0.0
    )

    return {
        "orders_processed": orders_processed,
        "total_trades": api_total_trades,
        "executed_quantity": api_executed_quantity,
        "average_matching_latency_ms": average_latency_ms,
        "matching_operations_per_second": (
            matching_operations_per_second
        ),
    }


@app.post("/orders")
def submit_order(request: OrderRequest):
    global orders_processed
    global total_matching_latency_seconds
    global api_total_trades
    global api_executed_quantity

    # Reject explicitly supplied empty or whitespace-only IDs.
    if request.order_id is not None and not request.order_id.strip():
        raise HTTPException(
            status_code=400,
            detail="order_id must not be empty",
        )

    # Generate an ID only when the client does not provide one.
    order_id = (
        request.order_id
        if request.order_id is not None
        else f"WEB-{next(order_ids)}"
    )

    try:
        order = Order(
            order_id=order_id,
            side=OrderSide(request.side.upper()),
            price=request.price,
            quantity=request.quantity,
            timestamp=next(timestamps),
        )

        started_at = perf_counter()
        trades = engine.submit_order(order)
        elapsed = perf_counter() - started_at

        orders_processed += 1
        total_matching_latency_seconds += elapsed

        api_total_trades += len(trades)
        api_executed_quantity += sum(
            trade.quantity for trade in trades
        )

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "order": order_to_dict(order),
        "trades": [trade_to_dict(trade) for trade in trades],
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
    running = (
        simulator_task is not None and not simulator_task.done()
    )

    return {
        "running": running,
        "generated": simulator_orders_generated,
    }
