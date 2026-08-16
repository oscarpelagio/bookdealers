"""Tests del módulo profiles (FASE 1)."""

from tests.conftest import random_email, valid_password


async def _register_and_token(client, username: str, email: str | None = None) -> str:
    """Registra un usuario y devuelve su access token."""
    payload = {
        "email": email or random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Test User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    login = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": valid_password()},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


async def test_me_creates_profile_automatically(client):
    token = await _register_and_token(client, "alice")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/profiles/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["preferences"]["default_review_visibility"] == "PUBLIC"
    assert data["privacy"]["profile_visibility"] == "PUBLIC"
    assert data["joined_at"]


async def test_me_requires_auth(client):
    resp = await client.get("/profiles/me")
    assert resp.status_code == 401


async def test_update_own_profile(client):
    token = await _register_and_token(client, "bob")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.patch(
        "/profiles/me",
        json={"display_name": "Bob Book", "bio": "Lector voraz", "location": "Barcelona"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Bob Book"
    assert data["bio"] == "Lector voraz"
    assert data["location"] == "Barcelona"


async def test_public_profile_anonymous(client):
    token = await _register_and_token(client, "carol")
    resp = await client.get("/profiles/carol")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "carol"
    assert data["is_following"] is False


async def test_public_profile_not_found(client):
    resp = await client.get("/profiles/ghost-user")
    assert resp.status_code == 404


async def test_private_profile_forbidden_for_others(client):
    token_a = await _register_and_token(client, "dana")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    # Dana pone su perfil en privado
    resp = await client.patch(
        "/profiles/me/privacy",
        json={"profile_visibility": "PRIVATE"},
        headers=headers_a,
    )
    assert resp.status_code == 200

    # Otro usuario autenticado no puede verlo
    token_b = await _register_and_token(client, "eve")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    resp = await client.get("/profiles/dana", headers=headers_b)
    assert resp.status_code == 403
    assert resp.json()["error"] == "profile_private"

    # Ni anónimo
    resp = await client.get("/profiles/dana")
    assert resp.status_code == 403

    # La autora sí
    resp = await client.get("/profiles/me", headers=headers_a)
    assert resp.status_code == 200


async def test_update_privacy(client):
    token = await _register_and_token(client, "frank")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.patch(
        "/profiles/me/privacy",
        json={"library_visibility": "FOLLOWERS", "block_anonymous": True},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["library_visibility"] == "FOLLOWERS"
    assert data["block_anonymous"] is True
    assert data["profile_visibility"] == "PUBLIC"


async def test_update_preferences(client):
    token = await _register_and_token(client, "grace")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.patch(
        "/profiles/me/preferences",
        json={
            "language": "es",
            "default_review_visibility": "FOLLOWERS",
            "content_languages": ["es", "ca"],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "es"
    assert data["default_review_visibility"] == "FOLLOWERS"
    assert data["content_languages"] == ["es", "ca"]


async def test_goal_upsert_and_delete(client):
    token = await _register_and_token(client, "heidi")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.put(
        "/profiles/me/goals/2026", json={"year": 2026, "books_goal": 20}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["books_goal"] == 20

    # Upsert parcial no pisa el campo previo
    resp = await client.put(
        "/profiles/me/goals/2026", json={"year": 2026, "pages_goal": 500}, headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["books_goal"] == 20
    assert data["pages_goal"] == 500

    # GET devuelve el mismo objetivo (único por año)
    resp = await client.get("/profiles/me/goals/2026", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["books_goal"] == 20

    resp = await client.delete("/profiles/me/goals/2026", headers=headers)
    assert resp.status_code == 204

    resp = await client.get("/profiles/me/goals/2026", headers=headers)
    assert resp.status_code == 200
    assert resp.json() is None


async def test_goal_invalid_year(client):
    token = await _register_and_token(client, "ivan")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put(
        "/profiles/me/goals/1999", json={"year": 1999, "books_goal": 5}, headers=headers
    )
    assert resp.status_code == 422
