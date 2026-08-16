"""Tests del feed v1 (FASE 5)."""

from tests.conftest import random_email, valid_password


async def _register(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Feed User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    login = await client.post(
        "/auth/login", json={"email": payload["email"], "password": valid_password()}
    )
    return login.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _feed(client, token: str, **params) -> dict:
    resp = await client.get("/feed", params=params, headers=_h(token))
    assert resp.status_code == 200
    return resp.json()


async def test_feed_requires_auth(client):
    resp = await client.get("/feed")
    assert resp.status_code == 401


async def test_feed_empty_for_new_user(client):
    token = await _register(client, "feeduser1")
    data = await _feed(client, token)
    assert data["items"] == []
    assert data["next"] is None


async def test_feed_includes_own_activity(client):
    token_a = await _register(client, "feeduser2")
    token_b = await _register(client, "feeduser3")

    # A sigue a B: genera una actividad FOLLOWED de A.
    await client.post("/users/feeduser3/follow", headers=_h(token_a))

    data = await _feed(client, token_a)
    assert len(data["items"]) == 1
    assert data["items"][0]["verb"] == "FOLLOWED"
    assert data["items"][0]["actor"]["username"] == "feeduser2"


async def test_feed_includes_followed_activity(client):
    token_a = await _register(client, "feeduser4")
    token_b = await _register(client, "feeduser5")
    token_c = await _register(client, "feeduser6")

    # A sigue a B; B sigue a C (actividad de B).
    await client.post("/users/feeduser5/follow", headers=_h(token_a))
    await client.post("/users/feeduser6/follow", headers=_h(token_b))

    data = await _feed(client, token_a)
    actors = {i["actor"]["username"] for i in data["items"]}
    # La propia de A + la de B.
    assert actors == {"feeduser4", "feeduser5"}
    assert len(data["items"]) == 2


async def test_feed_excludes_non_followed(client):
    token_a = await _register(client, "feeduser7")
    token_b = await _register(client, "feeduser8")
    token_c = await _register(client, "feeduser9")

    # B y C no se siguen entre sí; A no sigue a ninguno.
    await client.post("/users/feeduser9/follow", headers=_h(token_b))
    await client.post("/users/feeduser8/follow", headers=_h(token_c))

    data = await _feed(client, token_a)
    assert data["items"] == []


async def test_feed_excludes_muted(client):
    token_a = await _register(client, "feeduser10")
    token_b = await _register(client, "feeduser11")
    token_c = await _register(client, "feeduser12")

    # A sigue a B; B genera actividad. A silencia a B.
    await client.post("/users/feeduser11/follow", headers=_h(token_a))
    await client.post("/users/feeduser12/follow", headers=_h(token_b))
    await client.post("/users/feeduser11/mute", headers=_h(token_a))

    data = await _feed(client, token_a)
    actors = {i["actor"]["username"] for i in data["items"]}
    # Solo la propia de A (la de B queda excluida por el mute).
    assert actors == {"feeduser10"}


async def test_feed_excludes_private_activity(client):
    token_a = await _register(client, "feeduser13")
    token_b = await _register(client, "feeduser14")
    token_c = await _register(client, "feeduser15")

    # B pone su actividad en PRIVATE y genera actividad (B sigue a C).
    await client.patch(
        "/profiles/me/privacy", json={"activity_visibility": "PRIVATE"},
        headers=_h(token_b),
    )
    await client.post("/users/feeduser15/follow", headers=_h(token_b))
    # A sigue a B y genera su propia actividad.
    await client.post("/users/feeduser14/follow", headers=_h(token_a))

    data = await _feed(client, token_a)
    actors = {i["actor"]["username"] for i in data["items"]}
    # La PRIVATE de B no aparece; sí la propia de A.
    assert actors == {"feeduser13"}


async def test_feed_excludes_blocked(client):
    token_a = await _register(client, "feeduser16")
    token_b = await _register(client, "feeduser17")
    token_c = await _register(client, "feeduser18")

    # A sigue a B; B genera actividad. A bloquea a B (borra el follow).
    await client.post("/users/feeduser17/follow", headers=_h(token_a))
    await client.post("/users/feeduser18/follow", headers=_h(token_b))
    await client.post("/users/feeduser17/block", headers=_h(token_a))

    data = await _feed(client, token_a)
    actors = {i["actor"]["username"] for i in data["items"]}
    assert actors == {"feeduser16"}


async def test_feed_followers_visibility(client):
    token_a = await _register(client, "feeduser19")
    token_b = await _register(client, "feeduser20")
    token_c = await _register(client, "feeduser21")

    # B pone su actividad en FOLLOWERS y genera actividad.
    await client.patch(
        "/profiles/me/privacy", json={"activity_visibility": "FOLLOWERS"},
        headers=_h(token_b),
    )
    await client.post("/users/feeduser21/follow", headers=_h(token_b))
    # A sigue a B (es follower de B).
    await client.post("/users/feeduser20/follow", headers=_h(token_a))

    data = await _feed(client, token_a)
    actors = {i["actor"]["username"] for i in data["items"]}
    # A es follower de B: la actividad FOLLOWERS de B sí entra en su feed.
    assert actors == {"feeduser19", "feeduser20"}


async def test_feed_cursor_pagination(client):
    token_a = await _register(client, "feeduser22")
    # A sigue a 3 usuarios y cada uno genera una actividad.
    for i in range(23, 26):
        other = await _register(client, f"feeduser{i}")
        await client.post(f"/users/feeduser{i}/follow", headers=_h(token_a))
        await client.post("/users/feeduser22/follow", headers=_h(other))

    data = await _feed(client, token_a, limit=2)
    assert len(data["items"]) == 2
    assert data["next"] is not None

    data2 = await _feed(client, token_a, limit=2, cursor=data["next"])
    assert len(data2["items"]) >= 1
    ids = {i["id"] for i in data["items"] + data2["items"]}
    # Sin duplicados entre páginas y en total las 4 (3 seguidos + 1 propia).
    assert len(ids) == 4
