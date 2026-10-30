
from itertools import count

import pytest
from fastapi.testclient import TestClient

from chronosmatch import api


@pytest.fixture
def client():
    """Create a test client with isolated API state."""
    api.engine = api.MatchingEngine()
    api.order_ids = count(1)
    api.timestamps = count(1)

    api.simulator_task = None
    api.simulator_orders_generated = 0

    # Reset API metrics for each test.
    api.orders_processed = 0
    api.total_matching_latency_seconds = 0.0
    api.api_total_trades = 0
    api.api_executed_quantity = 0

    with TestClient(api.app) as test_client:
        yield test_client


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "ChronosMatch API"
    assert data["docs"] == "/docs"
    assert data["status"] == "ok"


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_orderbook_initially_empty(client):
    response = client.get("/orderbook")

    assert response.status_code == 200
    data = response.json()

    assert data["bids"] == []
    assert data["asks"] == []
    assert data["best_bid"] is None
    assert data["best_ask"] is None


def test_submit_sell_order(client):
    response = client.post(
        "/orders",
        json={
            "side": "SELL",
            "price": 100,
            "quantity": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["order"]["side"] == "SELL"
    assert data["order"]["price"] == 100
    assert data["order"]["quantity"] == 10
    assert data["trades"] == []


def test_submit_buy_order(client):
    response = client.post(
        "/orders",
        json={
            "side": "BUY",
            "price": 100,
            "quantity": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["order"]["side"] == "BUY"
    assert data["order"]["price"] == 100
    assert data["order"]["quantity"] == 10
    assert data["trades"] == []


def test_matching_orders_create_trade(client):
    sell_response = client.post(
        "/orders",
        json={
            "side": "SELL",
            "price": 100,
            "quantity": 10,
        },
    )
    assert sell_response.status_code == 200

    buy_response = client.post(
        "/orders",
        json={
            "side": "BUY",
            "price": 100,
            "quantity": 4,
        },
    )
    assert buy_response.status_code == 200

    trades = buy_response.json()["trades"]

    assert len(trades) == 1
    assert trades[0]["price"] == 100
    assert trades[0]["quantity"] == 4


def test_get_trades(client):
    client.post(
        "/orders",
        json={
            "side": "SELL",
            "price": 100,
            "quantity": 10,
        },
    )
    client.post(
        "/orders",
        json={
            "side": "BUY",
            "price": 100,
            "quantity": 4,
        },
    )

    response = client.get("/trades")

    assert response.status_code == 200
    trades = response.json()

    assert len(trades) == 1
    assert trades[0]["quantity"] == 4


def test_invalid_order_side(client):
    response = client.post(
        "/orders",
        json={
            "side": "INVALID",
            "price": 100,
            "quantity": 10,
        },
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        {"side": "BUY", "price": 0, "quantity": 10},
        {"side": "BUY", "price": 100, "quantity": 0},
        {"side": "BUY", "price": -1, "quantity": 10},
        {"side": "BUY", "price": 100, "quantity": -1},
    ],
)
def test_invalid_price_or_quantity(client, payload):
    response = client.post("/orders", json=payload)

    assert response.status_code == 422


def test_custom_order_id(client):
    response = client.post(
        "/orders",
        json={
            "order_id": "CUSTOM-123",
            "side": "BUY",
            "price": 100,
            "quantity": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["order"]["order_id"] == "CUSTOM-123"


def test_simulator_status_initially_stopped(client):
    response = client.get("/simulator/status")

    assert response.status_code == 200
    data = response.json()

    assert data["running"] is False
    assert data["generated"] == 0


def test_simulator_can_start_and_stop(client):
    start_response = client.post("/simulator/start")

    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"

    stop_response = client.post("/simulator/stop")

    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"

    final_status = client.get("/simulator/status").json()
    assert final_status["running"] is False


def test_metrics_initially_zero(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.json()

    assert data["orders_processed"] == 0
    assert data["total_trades"] == 0
    assert data["executed_quantity"] == 0
    assert data["average_matching_latency_ms"] == 0.0
    assert data["matching_operations_per_second"] == 0.0


def test_metrics_update_after_matching_orders(client):
    sell_response = client.post(
        "/orders",
        json={
            "side": "SELL",
            "price": 100,
            "quantity": 10,
        },
    )
    assert sell_response.status_code == 200

    buy_response = client.post(
        "/orders",
        json={
            "side": "BUY",
            "price": 100,
            "quantity": 4,
        },
    )
    assert buy_response.status_code == 200

    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.json()

    assert data["orders_processed"] == 2
    assert data["total_trades"] == 1
    assert data["executed_quantity"] == 4
    assert data["average_matching_latency_ms"] >= 0
    assert data["matching_operations_per_second"] >= 0


def test_simulator_trades_do_not_affect_api_metrics(client):
    """Simulator orders should not increment API-specific metrics."""
    api.engine.submit_order(
        api.Order(
            order_id="SIM-TEST-1",
            side=api.OrderSide.SELL,
            price=100,
            quantity=10,
            timestamp=1,
        )
    )
    api.engine.submit_order(
        api.Order(
            order_id="SIM-TEST-2",
            side=api.OrderSide.BUY,
            price=100,
            quantity=5,
            timestamp=2,
        )
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.json()

    assert data["orders_processed"] == 0
    assert data["total_trades"] == 0
    assert data["executed_quantity"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"side": "BUY", "price": 100},
        {"side": "BUY", "quantity": 5},
        {"price": 100, "quantity": 5},
    ],
)
def test_missing_required_order_fields(client, payload):
    response = client.post("/orders", json=payload)

    assert response.status_code == 422


def test_malformed_order_json(client):
    response = client.post(
        "/orders",
        content="{invalid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("order_id", ["", "   "])
def test_blank_custom_order_id(client, order_id):
    response = client.post(
        "/orders",
        json={
            "order_id": order_id,
            "side": "BUY",
            "price": 100,
            "quantity": 5,
        },
    )

    assert response.status_code == 400


def test_repeated_simulator_start_and_stop(client):
    first_start = client.post("/simulator/start")
    second_start = client.post("/simulator/start")

    assert first_start.status_code == 200
    assert second_start.status_code == 200
    assert second_start.json()["status"] in (
        "running",
        "already_running",
    )

    first_stop = client.post("/simulator/stop")
    second_stop = client.post("/simulator/stop")

    assert first_stop.status_code == 200
    assert second_stop.status_code == 200
    assert second_stop.json()["status"] == "stopped"

    assert client.get("/simulator/status").json()["running"] is False
