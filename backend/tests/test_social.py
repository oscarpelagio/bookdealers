"""Tests del módulo social / social graph (FASE 4)."""

import uuid as _uuid

from tests.conftest import random_email, valid_password


async def _register(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Social User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    login = await client.post(
        "/auth/login", json={"email": payload["email"], "password": valid_password()}
    )
    return login.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_follow_unfollow_and_is_following(client):
    token_a = await _register(client, "socuser1")
    token_b = await _register(client, "socuser2")

    resp = await client.post("/users/socuser2/follow", headers=_h(token_a))
    assert resp.status_code == 201
    assert resp.json()["followee"]["username"] == "socuser2"

    resp = await client.get("/users/socuser2/is-following", headers=_h(token_a))
    assert resp.json()["is_following"] is True

    resp = await client.get("/users/socuser1/is-following", headers=_h(token_b))
    assert resp.json()["is_following"] is False

    resp = await client.delete("/users/socuser2/follow", headers=_h(token_a))
    assert resp.status_code == 204

    resp = await client.get("/users/socuser2/is-following", headers=_h(token_a))
    assert resp.json()["is_following"] is False


async def test_follow_unique_and_idempotent(client):
    token_a = await _register(client, "socuser3")
    token_b = await _register(client, "socuser4")

    await client.post("/users/socuser4/follow", headers=_h(token_a))
    resp = await client.post("/users/socuser4/follow", headers=_h(token_a))
    assert resp.status_code == 201  # idempotente, no duplica

    resp = await client.get("/users/socuser4/followers", headers=_h(token_b))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


async def test_cannot_follow_self(client):
    token = await _register(client, "socuser5")
    resp = await client.post("/users/socuser5/follow", headers=_h(token))
    assert resp.status_code == 400
    assert resp.json()["error"] == "cannot_follow_self"


async def test_followers_and_following_lists(client):
    token_b = await _register(client, "socuser6")
    token_c = await _register(client, "socuser7")
    token_a = await _register(client, "socuser8")

    await client.post("/users/socuser8/follow", headers=_h(token_b))
    await client.post("/users/socuser8/follow", headers=_h(token_c))

    resp = await client.get("/users/socuser8/followers", headers=_h(token_a))
    assert len(resp.json()["items"]) == 2
    usernames = {i["username"] for i in resp.json()["items"]}
    assert usernames == {"socuser6", "socuser7"}

    resp = await client.get("/users/socuser6/following", headers=_h(token_b))
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["username"] == "socuser8"


async def test_followers_pagination(client):
    token_a = await _register(client, "socuser9")
    for i in range(10, 13):
        token = await _register(client, f"socfollower{i}")
        await client.post("/users/socuser9/follow", headers=_h(token))

    resp = await client.get("/users/socuser9/followers?limit=1", headers=_h(token_a))
    assert len(resp.json()["items"]) == 1
    assert resp.json()["next"] is not None

    resp2 = await client.get(
        f"/users/socuser9/followers?limit=1&cursor={resp.json()['next']}",
        headers=_h(token_a),
    )
    assert len(resp2.json()["items"]) == 1
    assert resp2.json()["items"][0]["id"] != resp.json()["items"][0]["id"]


async def test_block_deletes_follows_both_ways_and_hides_content(client):
    token_a = await _register(client, "socuser13")
    token_b = await _register(client, "socuser14")

    await client.post("/users/socuser14/follow", headers=_h(token_a))
    await client.post("/users/socuser13/follow", headers=_h(token_b))

    resp = await client.post("/users/socuser14/block", headers=_h(token_a))
    assert resp.status_code == 204

    # Los follows a dos sentidos se borraron.
    resp = await client.get("/users/socuser13/following", headers=_h(token_a))
    assert len(resp.json()["items"]) == 0
    resp = await client.get("/users/socuser14/followers", headers=_h(token_b))
    assert len(resp.json()["items"]) == 0

    # La actividad de A deja de ser visible para B (block oculta contenido).
    resp = await client.get("/users/socuser13/activity", headers=_h(token_b))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0

    # Ya no se pueden seguir (block en cualquier dirección).
    resp = await client.post("/users/socuser13/follow", headers=_h(token_b))
    assert resp.status_code == 403
    assert resp.json()["error"] == "cannot_follow_blocked"

    resp = await client.post("/users/socuser14/follow", headers=_h(token_a))
    assert resp.status_code == 403


async def test_block_idempotent_and_unblock(client):
    token_a = await _register(client, "socuser15")
    token_b = await _register(client, "socuser16")

    await client.post("/users/socuser16/block", headers=_h(token_a))
    resp = await client.post("/users/socuser16/block", headers=_h(token_a))
    assert resp.status_code == 204  # idempotente

    await client.delete("/users/socuser16/block", headers=_h(token_a))
    resp = await client.post("/users/socuser15/follow", headers=_h(token_b))
    assert resp.status_code == 201  # tras desbloquear se puede seguir


async def test_cannot_block_self(client):
    token = await _register(client, "socuser17")
    resp = await client.post("/users/socuser17/block", headers=_h(token))
    assert resp.status_code == 400
    assert resp.json()["error"] == "cannot_block_self"


async def test_mute_and_unmute(client):
    token_a = await _register(client, "socuser18")
    token_b = await _register(client, "socuser19")

    resp = await client.post("/users/socuser19/mute", headers=_h(token_a))
    assert resp.status_code == 204
    resp = await client.post("/users/socuser19/mute", headers=_h(token_a))
    assert resp.status_code == 204

    # El mute no borra follows ni afecta listados.
    await client.post("/users/socuser18/follow", headers=_h(token_b))
    resp = await client.get("/users/socuser18/followers", headers=_h(token_a))
    assert len(resp.json()["items"]) == 1

    resp = await client.delete("/users/socuser19/mute", headers=_h(token_a))
    assert resp.status_code == 204


async def test_cannot_mute_self(client):
    token = await _register(client, "socuser20")
    resp = await client.post("/users/socuser20/mute", headers=_h(token))
    assert resp.status_code == 400


async def test_report_created(client):
    token = await _register(client, "socuser21")
    target_id = str(_uuid.uuid4())
    resp = await client.post(
        "/reports",
        json={
            "target_type": "REVIEW",
            "target_id": target_id,
            "reason": "Contenido inapropiado",
            "details": "Incluye spoilers sin avisar.",
        },
        headers=_h(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["target_type"] == "REVIEW"
    assert data["target_id"] == target_id
    assert data["status"] == "OPEN"
    assert data["reason"] == "Contenido inapropiado"

    # target_id debe ser UUID válido
    resp = await client.post(
        "/reports",
        json={"target_type": "USER", "target_id": "not-a-uuid", "reason": "x"},
        headers=_h(token),
    )
    assert resp.status_code == 422

    # reason obligatoria
    resp = await client.post(
        "/reports",
        json={"target_type": "USER", "target_id": target_id, "reason": ""},
        headers=_h(token),
    )
    assert resp.status_code == 422


async def test_follow_creates_public_activity(client):
    token_a = await _register(client, "socuser22")
    token_b = await _register(client, "socuser23")

    await client.post("/users/socuser23/follow", headers=_h(token_a))

    resp = await client.get("/users/socuser22/activity", headers=_h(token_a))
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["verb"] == "FOLLOWED"
    assert items[0]["target_type"] == "USER"
    assert items[0]["target_id"]
    assert items[0]["visibility"] == "PUBLIC"

    # Anónimo también lo ve (público).
    resp = await client.get("/users/socuser22/activity")
    assert len(resp.json()["items"]) == 1

    # Un tercero autenticado también.
    token_c = await _register(client, "socuser24")
    resp = await client.get("/users/socuser22/activity", headers=_h(token_c))
    assert len(resp.json()["items"]) == 1


async def test_activity_visibility_followers_only(client):
    token_a = await _register(client, "socuser25")
    token_b = await _register(client, "socuser26")
    token_c = await _register(client, "socuser27")
    token_d = await _register(client, "socuser28")

    resp = await client.patch(
        "/profiles/me/privacy",
        json={"activity_visibility": "FOLLOWERS"},
        headers=_h(token_a),
    )
    assert resp.status_code == 200

    # A sigue a B: genera una actividad FOLLOWED con visibilidad FOLLOWERS.
    await client.post("/users/socuser26/follow", headers=_h(token_a))
    # C sigue a A para ser follower.
    await client.post("/users/socuser25/follow", headers=_h(token_c))

    # C (follower de A) sí ve la actividad.
    resp = await client.get("/users/socuser25/activity", headers=_h(token_c))
    assert len(resp.json()["items"]) == 1

    # D (no follower) no ve nada.
    resp = await client.get("/users/socuser25/activity", headers=_h(token_d))
    assert len(resp.json()["items"]) == 0

    # Anónimo no ve nada.
    resp = await client.get("/users/socuser25/activity")
    assert len(resp.json()["items"]) == 0

    # El autor siempre ve todo.
    resp = await client.get("/users/socuser25/activity", headers=_h(token_a))
    assert len(resp.json()["items"]) == 1


async def test_activity_visibility_private(client):
    token_a = await _register(client, "socuser29")
    token_b = await _register(client, "socuser30")

    await client.patch(
        "/profiles/me/privacy",
        json={"activity_visibility": "PRIVATE"},
        headers=_h(token_a),
    )
    await client.post("/users/socuser30/follow", headers=_h(token_a))

    resp = await client.get("/users/socuser29/activity", headers=_h(token_b))
    assert len(resp.json()["items"]) == 0
    resp = await client.get("/users/socuser29/activity")
    assert len(resp.json()["items"]) == 0
    resp = await client.get("/users/socuser29/activity", headers=_h(token_a))
    assert len(resp.json()["items"]) == 1


async def test_activity_append_only_after_unfollow(client):
    token_a = await _register(client, "socuser31")
    token_b = await _register(client, "socuser32")
    token_c = await _register(client, "socuser33")

    await client.post("/users/socuser32/follow", headers=_h(token_a))
    await client.post("/users/socuser33/follow", headers=_h(token_a))
    await client.delete("/users/socuser32/follow", headers=_h(token_a))

    # La actividad es append-only: las entradas FOLLOWED siguen estando.
    resp = await client.get("/users/socuser31/activity", headers=_h(token_a))
    assert len(resp.json()["items"]) == 2


async def test_activity_pagination(client):
    token_a = await _register(client, "socuser34")
    for i in range(35, 38):
        token = await _register(client, f"socuser{i}")
        await client.post(f"/users/socuser{i}/follow", headers=_h(token_a))

    resp = await client.get("/users/socuser34/activity?limit=1", headers=_h(token_a))
    assert len(resp.json()["items"]) == 1
    assert resp.json()["next"] is not None

    resp2 = await client.get(
        f"/users/socuser34/activity?limit=1&cursor={resp.json()['next']}",
        headers=_h(token_a),
    )
    assert len(resp2.json()["items"]) == 1
    ids = {resp.json()["items"][0]["id"], resp2.json()["items"][0]["id"]}
    assert len(ids) == 2


async def test_block_hides_activity_for_viewer(client):
    token_a = await _register(client, "socuser38")
    token_b = await _register(client, "socuser39")

    await client.post("/users/socuser39/follow", headers=_h(token_a))
    await client.post("/users/socuser38/block", headers=_h(token_b))

    # B bloqueó a A: la actividad de A no es visible para B.
    resp = await client.get("/users/socuser38/activity", headers=_h(token_b))
    assert len(resp.json()["items"]) == 0
    # A (autor) sigue viendo su propia actividad.
    resp = await client.get("/users/socuser38/activity", headers=_h(token_a))
    assert len(resp.json()["items"]) == 1


async def test_follows_not_allowed(client):
    token_a = await _register(client, "socuser40")
    token_b = await _register(client, "socuser41")

    await client.patch(
        "/profiles/me/privacy", json={"allow_follows": False}, headers=_h(token_b)
    )
    resp = await client.post("/users/socuser41/follow", headers=_h(token_a))
    assert resp.status_code == 403
    assert resp.json()["error"] == "follows_not_allowed"


async def test_profile_reflects_follow(client):
    token_a = await _register(client, "socuser42")
    token_b = await _register(client, "socuser43")

    await client.post("/users/socuser43/follow", headers=_h(token_a))
    resp = await client.get("/profiles/socuser43", headers=_h(token_a))
    assert resp.status_code == 200
    assert resp.json()["is_following"] is True
