from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_register_success(client: TestClient, user_payload: dict[str, str]) -> None:
    response = client.post("/auth/register", json=user_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == user_payload["email"]
    assert body["role"] == "user"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email(client: TestClient, user_payload: dict[str, str]) -> None:
    client.post("/auth/register", json=user_payload)

    response = client.post("/auth/register", json={**user_payload, "phone": "9123456789"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Registration failed: this email is already registered"


def test_login_success(client: TestClient, user_payload: dict[str, str]) -> None:
    client.post("/auth/register", json=user_payload)

    response = client.post(
        "/auth/login", json={"email": user_payload["email"], "password": user_payload["password"]}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.json()["email"] == user_payload["email"]


def test_login_wrong_password(client: TestClient, user_payload: dict[str, str]) -> None:
    client.post("/auth/register", json=user_payload)

    response = client.post("/auth/login", json={"email": user_payload["email"], "password": "not-the-password"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Login failed: email or password is incorrect"


def test_protected_route_without_token(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required: missing bearer token in the Authorization header"


def test_protected_route_with_expired_token(
    client: TestClient,
    user_payload: dict[str, str],
    login: Callable[[str, str], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client.post("/auth/register", json=user_payload)
    monkeypatch.setattr(settings, "jwt_expire_minutes", -1)
    expired_headers = login(user_payload["email"], user_payload["password"])

    response = client.get("/auth/me", headers=expired_headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication failed: token has expired, please log in again"
