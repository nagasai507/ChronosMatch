
"""FastAPI endpoints for ChronosMatch API."""

import asyncio
from contextlib import asynccontextmanager
from itertools import count
from time import perf_counter

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .market_simulator import MarketSimulator
from .matching_engine import MatchingEngine
from .models import Order, OrderSide
from .repositories import save_order, save_trades
from .auth_routes import router as auth_router
from .database import create_tables
from .websocket_manager import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="ChronosMatchAPI",
    version="0.1.0",
    lifespan=lifespan,
)

manager = ConnectionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Register authentication endpoints.
app.include_router(auth_router)

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


def capture_resting_orders() -> dict[str, Order]:
    """Capture existing orders before matching changes them."""

    book = engine.order_book

    return {
        order.order_id: order
        for order in list(book._bids) + list(book._asks)
    }


def persist_submission(
    order: Order,
    trades: list,
    resting_orders_before: dict[str, Order],
) -> None:
    """Persist an incoming order, affected resting orders, and trades."""

    save_order(order)

    affected_order_ids = set()

    for trade in trades:
        affected_order_ids.add(trade.buy_order_id)
        affected_order_ids.add(trade.sell_order_id)

    affected_order_ids.discard(order.order_id)

    for affected_id in affected_order_ids:
        resting_order = resting_orders_before.get(affected_id)

        if resting_order is not None:
            save_order(resting_order)

    save_trades(trades)


async def broadcast_market_update(
    order: Order,
    trades: list,
) -> None:
    """Broadcast order, order-book, and trade updates."""

    await manager.broadcast({
        "event": "order_submitted",
        "data": order_to_dict(order),
    })

    await manager.broadcast({
        "event": "order_book_update",
        "data": get_orderbook(),
    })

    if trades:
        await manager.broadcast({
            "event": "trade_executed",
            "data": [
                trade_to_dict(trade)
                for trade in trades
            ],
        })


@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    """Provide real-time market data to connected clients."""

    await manager.connect(websocket)

    try:
        await websocket.send_json({
            "event": "market_snapshot",
            "data": {
                "orderbook": get_orderbook(),
                "trades": get_trades(),
            },
        })

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)


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
    return [
        trade_to_dict(trade)
        for trade in engine.trades
    ]


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
async def submit_order(request: OrderRequest):
    global orders_processed
    global total_matching_latency_seconds
    global api_total_trades
    global api_executed_quantity

    if request.order_id is not None and not request.order_id.strip():
        raise HTTPException(
            status_code=400,
            detail="order_id must not be empty",
        )

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

        resting_orders_before = capture_resting_orders()

        started_at = perf_counter()
        trades = engine.submit_order(order)
        elapsed = perf_counter() - started_at

        persist_submission(
            order,
            trades,
            resting_orders_before,
        )

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

    # Broadcast only after successful persistence.
    await broadcast_market_update(order, trades)

    order_data = order_to_dict(order)
    trade_data = [
        trade_to_dict(trade)
        for trade in trades
    ]

    return {
        "order": order_data,
        "trades": trade_data,
        "orderbook": get_orderbook(),
    }


async def _run_simulator():
    global simulator_orders_generated

    async for order in simulator.generate_orders(
        count=None,
        yield_every=1,
    ):
        resting_orders_before = capture_resting_orders()

        trades = engine.submit_order(order)

        persist_submission(
            order,
            trades,
            resting_orders_before,
        )

        simulator_orders_generated += 1

        await broadcast_market_update(order, trades)

        await asyncio.sleep(0.5)


@app.post("/simulator/start")
async def start_simulator():
    global simulator_task

    if simulator_task is not None and not simulator_task.done():
        return {"status": "already_running"}

    simulator_task = asyncio.create_task(_run_simulator())

    await manager.broadcast({
        "event": "market_status",
        "data": {"status": "running"},
    })

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

    await manager.broadcast({
        "event": "market_status",
        "data": {"status": "stopped"},
    })

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
