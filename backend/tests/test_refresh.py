"""Tests del flux de refresh (rotació + protecció replay)."""

from tests.conftest import random_email, valid_password


async def _login(client, device_id: str | None = None) -> dict:
    payload = {
        "email": random_email(),
        "username": "refreshuser",
        "password": valid_password(),
    }
    await client.post("/auth/register", json=payload)
    login = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": valid_password(), "device_id": device_id},
    )
    assert login.status_code == 200
    return login.json()


async def test_refresh_rotates_token(client):
    tokens = await _login(client)
    resp = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"] != tokens["refresh_token"]


async def test_refresh_with_same_token_is_rejected(client):
    tokens = await _login(client)

    first = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert first.status_code == 200
    second_tokens = first.json()

    # Reutilizar un token ya rotado → detección de replay → toda la familia revocada.
    replay = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401
    assert replay.json()["error"] == "token_revoked"

    # El token rotado también queda invalidado (se revocó la familia completa).
    family_revoked = await client.post(
        "/auth/refresh", json={"refresh_token": second_tokens["refresh_token"]}
    )
    assert family_revoked.status_code == 401


async def test_refresh_with_invalid_token(client):
    resp = await client.post("/auth/refresh", json={"refresh_token": "garbage-token"})
    assert resp.status_code == 401


async def test_refresh_after_logout_is_rejected(client):
    tokens = await _login(client)
    logout = await client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout.status_code == 200

    resp = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 401
