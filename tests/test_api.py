
"""API tests for the ChronosMatch FastAPI application."""

from itertools import count

import pytest
from fastapi.testclient import TestClient

from chronosmatch import api
from chronosmatch.matching_engine import MatchingEngine


@pytest.fixture
def client():
    """Give each test a fresh engine and simulator state."""
    api.engine = MatchingEngine()
    api.order_ids = count(1)
    api.timestamps = count(1)
    api.simulator_task = None
    api.simulator_orders_generated = 0

    with TestClient(api.app) as test_client:
        yield test_client

        # Avoid leaving the simulator running after a test.
        if api.simulator_task is not None:
            if not api.simulator_task.done():
                test_client.post("/simulator/stop")


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_orderbook_initially_empty(client):
    response = client.get("/orderbook")

    assert response.status_code == 200
    data = response.json()
    assert data["best_bid"] is None
    assert data["best_ask"] is None


def test_trades_initially_empty(client):
    response = client.get("/trades")

    assert response.status_code == 200
    assert response.json() == []


def test_submit_valid_buy_order(client):
    response = client.post(
        "/orders",
        json={"side": "BUY", "price": 100, "quantity": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order"]["side"] == "BUY"
    assert data["order"]["price"] == 100
    assert data["order"]["quantity"] == 10


def test_matching_orders_create_trade(client):
    sell_response = client.post(
        "/orders",
        json={"side": "SELL", "price": 100, "quantity": 10},
    )
    assert sell_response.status_code == 200

    buy_response = client.post(
        "/orders",
        json={"side": "BUY", "price": 100, "quantity": 10},
    )
    assert buy_response.status_code == 200

    data = buy_response.json()
    assert len(data["trades"]) == 1
    assert data["trades"][0]["price"] == 100
    assert data["trades"][0]["quantity"] == 10

    trades_response = client.get("/trades")
    assert trades_response.status_code == 200
    assert len(trades_response.json()) == 1


@pytest.mark.parametrize(
    "order",
    [
        {"side": "BUY", "price": 0, "quantity": 10},
        {"side": "SELL", "price": 100, "quantity": 0},
        {"side": "INVALID", "price": 100, "quantity": 10},
        {"side": "BUY", "price": -1, "quantity": 10},
    ],
)
def test_invalid_orders_are_rejected(client, order):
    response = client.post("/orders", json=order)

    assert response.status_code == 422


def test_simulator_initial_status(client):
    response = client.get("/simulator/status")

    assert response.status_code == 200
    assert response.json()["running"] is False
    assert response.json()["generated"] == 0


def test_simulator_can_start_and_stop(client):
    start_response = client.post("/simulator/start")

    assert start_response.status_code == 200
    assert start_response.json()["status"] in {
        "running",
        "already_running",
    }

    status_response = client.get("/simulator/status")
    assert status_response.status_code == 200
    assert status_response.json()["running"] is True

    stop_response = client.post("/simulator/stop")

    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"

    final_status = client.get("/simulator/status").json()
    assert final_status["running"] is False
