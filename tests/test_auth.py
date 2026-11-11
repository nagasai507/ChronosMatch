from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chronosmatch import auth, auth_routes


@pytest.fixture
def client():
    """Create an isolated test application for authentication."""

    app = FastAPI()
    app.include_router(auth_routes.router)

    with TestClient(app) as test_client:
        yield test_client


def test_user_registration(client, monkeypatch):
    user = SimpleNamespace(
        id=1,
        username="ramya",
        email="ramya@example.com",
    )

    monkeypatch.setattr(
        auth_routes,
        "get_user_by_email",
        lambda email: None,
    )
    monkeypatch.setattr(
        auth_routes,
        "hash_password",
        lambda password: "hashed_password",
    )
    monkeypatch.setattr(
        auth_routes,
        "create_user",
        lambda **kwargs: user,
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "ramya",
            "email": "ramya@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "ramya@example.com"


def test_duplicate_email_registration(client, monkeypatch):
    existing_user = SimpleNamespace(id=1)

    monkeypatch.setattr(
        auth_routes,
        "get_user_by_email",
        lambda email: existing_user,
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "ramya",
            "email": "ramya@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 409


def test_successful_login(client, monkeypatch):
    user = SimpleNamespace(
        id=1,
        username="ramya",
        email="ramya@example.com",
        password_hash="hashed_password",
    )

    monkeypatch.setattr(
        auth_routes,
        "get_user_by_email",
        lambda email: user,
    )
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda plain, hashed: True,
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "ramya@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_incorrect_login_password(client, monkeypatch):
    user = SimpleNamespace(
        id=1,
        email="ramya@example.com",
        password_hash="hashed_password",
    )

    monkeypatch.setattr(
        auth_routes,
        "get_user_by_email",
        lambda email: user,
    )
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda plain, hashed: False,
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "ramya@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401


def test_valid_token_profile(client, monkeypatch):
    user = SimpleNamespace(
        id=1,
        username="ramya",
        email="ramya@example.com",
    )

    monkeypatch.setattr(
        auth_routes,
        "get_user_by_email",
        lambda email: user,
    )

    token = auth.create_access_token(
        {"sub": "ramya@example.com"}
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "ramya"


def test_invalid_token_rejected(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_expired_token_rejected(client):
    token = auth.create_access_token(
        {"sub": "ramya@example.com"},
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401