"""Tests del flux de logout."""

from tests.conftest import random_email, valid_password


async def _login_with_device(client, device_id: str) -> dict:
    suffix = "".join(ch for ch in device_id if ch.isalnum())[-8:]
    payload = {
        "email": random_email(),
        "username": f"logoutuser{suffix}",
        "password": valid_password(),
    }
    await client.post("/auth/register", json=payload)
    login = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": valid_password(), "device_id": device_id},
    )
    assert login.status_code == 200
    return login.json()


async def test_logout_revokes_single_refresh_token(client):
    tokens = await _login_with_device(client, "device-a")
    resp = await client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200

    refresh = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401


async def test_logout_everywhere_revokes_all_sessions(client):
    # Dos sesiones del MISMO usuario (mismo email, dos device_id).
    email = random_email()
    payload = {"email": email, "username": "logoutmulti", "password": valid_password()}
    await client.post("/auth/register", json=payload)

    first_login = await client.post(
        "/auth/login",
        json={"email": email, "password": valid_password(), "device_id": "device-a"},
    )
    second_login = await client.post(
        "/auth/login",
        json={"email": email, "password": valid_password(), "device_id": "device-b"},
    )
    assert first_login.status_code == 200
    assert second_login.status_code == 200
    first = first_login.json()
    second = second_login.json()

    logout = await client.post(
        "/auth/logout",
        json={"refresh_token": first["refresh_token"], "logout_everywhere": True},
    )
    assert logout.status_code == 200

    assert (
        await client.post(
            "/auth/refresh", json={"refresh_token": first["refresh_token"]}
        )
    ).status_code == 401
    assert (
        await client.post(
            "/auth/refresh", json={"refresh_token": second["refresh_token"]}
        )
    ).status_code == 401


async def test_logout_is_idempotent(client):
    tokens = await _login_with_device(client, "device-a")
    first = await client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    second = await client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert first.status_code == 200
    assert second.status_code == 200
