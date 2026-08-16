"""Tests del flux de login."""

import jwt as pyjwt

from app.core.config import settings
from tests.conftest import random_email, valid_password


async def _register_user(client, email: str | None = None) -> dict:
    payload = {
        "email": email or random_email(),
        "username": "loginuser",
        "password": valid_password(),
        "full_name": "Login User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    return payload


async def test_login_success(client):
    payload = await _register_user(client)
    resp = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": valid_password()},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]

    decoded = pyjwt.decode(
        data["access_token"],
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert decoded["roles"] == ["USER"]
    assert decoded["type"] == "access"


async def test_login_wrong_password_is_generic(client):
    payload = await _register_user(client)
    resp = await client.post(
        "/auth/login", json={"email": payload["email"], "password": "Wrong!Pass1"}
    )
    assert resp.status_code == 401
    assert "Invalid email or password." in resp.json()["message"]


async def test_login_unknown_email_is_generic(client):
    resp = await client.post(
        "/auth/login", json={"email": random_email(), "password": valid_password()}
    )
    assert resp.status_code == 401
    # Mismo mensaje que el caso "password incorrecta" (no hay enumeración).
    assert resp.json()["message"] == "Invalid email or password."


async def test_login_rejects_invalid_format(client):
    resp = await client.post(
        "/auth/login", json={"email": "not-an-email", "password": "x"}
    )
    assert resp.status_code == 422


async def test_login_normalizes_email(client):
    payload = await _register_user(client)
    resp = await client.post(
        "/auth/login",
        json={"email": payload["email"].upper(), "password": valid_password()},
    )
    assert resp.status_code == 200


async def test_login_locks_account_after_max_attempts(client):
    payload = await _register_user(client)
    for _ in range(settings.login_max_attempts):
        resp = await client.post(
            "/auth/login",
            json={"email": payload["email"], "password": "Wrong!Pass1"},
        )
        assert resp.status_code == 401

    # El usuario queda bloqueado: siguiente intento → 429.
    resp = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": valid_password()},
    )
    assert resp.status_code == 429
