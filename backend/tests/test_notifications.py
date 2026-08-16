"""Tests del módulo notifications (FASE 8)."""

import uuid as _uuid

from tests.conftest import random_email, valid_password


async def _register_and_token(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Notif User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    login = await client.post(
        "/auth/login", json={"email": payload["email"], "password": valid_password()}
    )
    return login.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_book(session_factory, **overrides) -> int:
    from app.models import Book

    suffix = _uuid.uuid4().hex[:8]
    data = dict(
        title=f"Libro notif {suffix}",
        author=f"Autor Notif {suffix}",
        language="es",
        normal_title=f"libro notif {suffix}",
        normal_author=f"autor notif {suffix}",
        page_count=300,
    )
    data.update(overrides)
    async with session_factory() as session:
        book = Book(**data)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book.id


async def test_notifications_requires_auth(client):
    resp = await client.get("/notifications")
    assert resp.status_code == 401


async def test_follow_creates_notification_to_followee(client):
    token_a = await _register_and_token(client, "notifuser1")
    token_b = await _register_and_token(client, "notifuser2")

    resp = await client.post("/users/notifuser2/follow", headers=_h(token_a))
    assert resp.status_code == 201

    # El seguido (B) recibe la notificación; el seguidor (A) no.
    resp = await client.get("/notifications", headers=_h(token_b))
    data = resp.json()
    assert data["unread_count"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["type"] == "FOLLOW"
    assert item["actor"]["username"] == "notifuser1"
    assert item["read"] is False

    resp = await client.get("/notifications", headers=_h(token_a))
    assert resp.json()["items"] == []


async def test_muted_actor_suppresses_notification(client):
    token_a = await _register_and_token(client, "notifuser2a")
    token_b = await _register_and_token(client, "notifuser2b")

    # A mutea a B.
    resp = await client.post("/users/notifuser2b/mute", headers=_h(token_a))
    assert resp.status_code == 204

    # B sigue a A: A (destinataria) tiene muteado al actor → sin notificación.
    resp = await client.post("/users/notifuser2a/follow", headers=_h(token_b))
    assert resp.status_code == 201

    resp = await client.get("/notifications", headers=_h(token_a))
    assert resp.json()["items"] == []
    assert resp.json()["unread_count"] == 0


async def test_blocked_actor_suppresses_notification(client):
    token_a = await _register_and_token(client, "notifuser2c")
    token_b = await _register_and_token(client, "notifuser2d")

    # A bloquea a B.
    resp = await client.post("/users/notifuser2d/block", headers=_h(token_a))
    assert resp.status_code == 204

    resp = await client.get("/notifications", headers=_h(token_a))
    assert resp.json()["items"] == []


async def test_mark_read_and_mark_all(client):
    token_a = await _register_and_token(client, "notifuser3")
    token_b = await _register_and_token(client, "notifuser4")
    token_c = await _register_and_token(client, "notifuser5")

    await client.post("/users/notifuser4/follow", headers=_h(token_a))
    await client.post("/users/notifuser4/follow", headers=_h(token_c))

    # Marcar una.
    resp = await client.get("/notifications", headers=_h(token_b))
    first_id = resp.json()["items"][0]["id"]
    resp = await client.patch(
        f"/notifications/{first_id}/read", headers=_h(token_b)
    )
    assert resp.status_code == 200
    assert resp.json()["read"] is True

    resp = await client.get("/notifications", headers=_h(token_b))
    assert resp.json()["unread_count"] == 1
    by_id = {n["id"]: n for n in resp.json()["items"]}
    assert by_id[first_id]["read"] is True

    # Marcar todas.
    resp = await client.post("/notifications/read", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json()["read"] == 1
    resp = await client.get("/notifications", headers=_h(token_b))
    assert resp.json()["unread_count"] == 0


async def test_cannot_mark_others_notification(client):
    token_a = await _register_and_token(client, "notifuser6")
    token_b = await _register_and_token(client, "notifuser7")
    token_c = await _register_and_token(client, "notifuser8")

    await client.post("/users/notifuser7/follow", headers=_h(token_a))
    resp = await client.get("/notifications", headers=_h(token_b))
    notif_id = resp.json()["items"][0]["id"]

    # C no es el destinatario: 404 (no se filtra existencia).
    resp = await client.patch(f"/notifications/{notif_id}/read", headers=_h(token_c))
    assert resp.status_code == 404


async def test_post_mention_notifies_mentioned(client, session_factory):
    token_a = await _register_and_token(client, "notifuser9")
    token_b = await _register_and_token(client, "notifuser10")

    resp = await client.post(
        "/posts", json={"body": "@notifuser10 te menciono"}, headers=_h(token_a)
    )
    assert resp.status_code == 201
    post_id = resp.json()["id"]

    resp = await client.get("/notifications", headers=_h(token_b))
    data = resp.json()
    assert data["unread_count"] == 1
    item = data["items"][0]
    assert item["type"] == "MENTION"
    assert item["actor"]["username"] == "notifuser9"
    assert item["object_id"] == post_id


async def test_comment_notifies_post_author(client):
    token_a = await _register_and_token(client, "notifuser11")
    token_b = await _register_and_token(client, "notifuser12")
    token_c = await _register_and_token(client, "notifuser13")

    resp = await client.post("/posts", json={"body": "mi post"}, headers=_h(token_a))
    post_id = resp.json()["id"]

    # Comenta un tercero → el autor del post recibe notificación.
    await client.post(
        f"/posts/{post_id}/comments", json={"body": "comentario"}, headers=_h(token_b)
    )
    resp = await client.get("/notifications", headers=_h(token_a))
    data = resp.json()
    assert data["unread_count"] == 1
    assert data["items"][0]["type"] == "COMMENT"
    assert data["items"][0]["actor"]["username"] == "notifuser12"

    # Comenta el propio autor → sin notificación.
    await client.post(
        f"/posts/{post_id}/comments", json={"body": "yo mismo"}, headers=_h(token_a)
    )
    resp = await client.get("/notifications", headers=_h(token_a))
    assert resp.json()["unread_count"] == 1


async def test_post_like_notifies_author_and_self_like_skipped(client):
    token_a = await _register_and_token(client, "notifuser14")
    token_b = await _register_and_token(client, "notifuser15")

    resp = await client.post("/posts", json={"body": "mi post"}, headers=_h(token_a))
    post_id = resp.json()["id"]

    # Self-like: no notificación.
    await client.post(f"/posts/{post_id}/like", headers=_h(token_a))
    resp = await client.get("/notifications", headers=_h(token_a))
    assert resp.json()["items"] == []

    # Like de otro → notificación al autor.
    await client.post(f"/posts/{post_id}/like", headers=_h(token_b))
    resp = await client.get("/notifications", headers=_h(token_a))
    data = resp.json()
    assert data["unread_count"] == 1
    assert data["items"][0]["type"] == "POST_LIKE"
    assert data["items"][0]["object_type"] == "POST"


async def test_review_like_notifies_review_author(client, session_factory):
    token_a = await _register_and_token(client, "notifuser16")
    token_b = await _register_and_token(client, "notifuser17")
    book_id = await _create_book(session_factory)

    # A añade el libro y escribe una review.
    await client.patch(f"/library/me/{book_id}", json={"status": "READ"}, headers=_h(token_a))
    resp = await client.post(
        f"/reviews/{book_id}",
        json={"score": 4, "body": "Muy buena"},
        headers=_h(token_a),
    )
    assert resp.status_code == 201
    review_id = resp.json()["id"]

    # B da like a la review → A recibe notificación.
    resp = await client.post(f"/reviews/{review_id}/like", headers=_h(token_b))
    assert resp.status_code == 201

    resp = await client.get("/notifications", headers=_h(token_a))
    data = resp.json()
    assert data["unread_count"] == 1
    assert data["items"][0]["type"] == "REVIEW_LIKE"
    assert data["items"][0]["object_id"] == review_id


async def test_settings_in_app_master_off_disables_notifications(client):
    token_a = await _register_and_token(client, "notifuser18")
    token_b = await _register_and_token(client, "notifuser19")

    # B apaga todas las notificaciones in-app.
    resp = await client.patch(
        "/notifications/settings",
        json={"in_app_master": False},
        headers=_h(token_b),
    )
    assert resp.status_code == 200
    assert resp.json()["in_app_master"] is False

    await client.post("/users/notifuser19/follow", headers=_h(token_a))
    resp = await client.get("/notifications", headers=_h(token_b))
    assert resp.json()["items"] == []
    assert resp.json()["unread_count"] == 0


async def test_settings_exception_disables_specific_type(client):
    token_a = await _register_and_token(client, "notifuser20")
    token_b = await _register_and_token(client, "notifuser21")

    # B desactiva solo FOLLOW.
    resp = await client.patch(
        "/notifications/settings",
        json={"exceptions": {"FOLLOW": {"in_app": False, "email": False}}},
        headers=_h(token_b),
    )
    assert resp.status_code == 200
    assert resp.json()["exceptions"]["FOLLOW"] == {"in_app": False, "email": False}

    await client.post("/users/notifuser21/follow", headers=_h(token_a))
    resp = await client.get("/notifications", headers=_h(token_b))
    assert resp.json()["items"] == []

    # Otros tipos (p. ej. MENTION) siguen activos.
    await client.post(
        "/posts", json={"body": "@notifuser21 hola"}, headers=_h(token_a)
    )
    resp = await client.get("/notifications", headers=_h(token_b))
    assert resp.json()["unread_count"] == 1
    assert resp.json()["items"][0]["type"] == "MENTION"


async def test_settings_validation(client):
    token = await _register_and_token(client, "notifuser22")

    # Tipo desconocido.
    resp = await client.patch(
        "/notifications/settings",
        json={"exceptions": {"NOPE": {"in_app": False}}},
        headers=_h(token),
    )
    assert resp.status_code == 422

    # Valor no booleano.
    resp = await client.patch(
        "/notifications/settings",
        json={"exceptions": {"FOLLOW": {"in_app": "si"}}},
        headers=_h(token),
    )
    assert resp.status_code == 422

    # Normalización: rellena email con False.
    resp = await client.patch(
        "/notifications/settings",
        json={"exceptions": {"FOLLOW": {"in_app": True}}},
        headers=_h(token),
    )
    assert resp.status_code == 200
    assert resp.json()["exceptions"]["FOLLOW"] == {"in_app": True, "email": False}


async def test_settings_get_creates_defaults(client):
    token = await _register_and_token(client, "notifuser23")
    resp = await client.get("/notifications/settings", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["in_app_master"] is True
    assert data["email_digest_enabled"] is False
    assert data["exceptions"] == {}


async def test_notifications_pagination(client):
    token_a = await _register_and_token(client, "notifuser24")
    for i in range(25, 28):
        other = await _register_and_token(client, f"notifuser{i}")
        await client.post("/users/notifuser24/follow", headers=_h(other))

    resp = await client.get("/notifications?limit=2", headers=_h(token_a))
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["next"] is not None
    assert data["unread_count"] == 3

    resp2 = await client.get(
        f"/notifications?limit=2&cursor={data['next']}", headers=_h(token_a)
    )
    assert len(resp2.json()["items"]) == 1
    ids = {n["id"] for n in data["items"] + resp2.json()["items"]}
    assert len(ids) == 3


async def test_actor_anonymous_when_deleted(client, session_factory):
    token_a = await _register_and_token(client, "notifuser28")
    token_b = await _register_and_token(client, "notifuser29")

    await client.post("/users/notifuser29/follow", headers=_h(token_a))
    resp = await client.get("/notifications", headers=_h(token_b))
    assert resp.json()["items"][0]["actor"]["username"] == "notifuser28"

    # Se borra el actor (hard delete directo): la notificación queda anónima.
    from app.auth.models import User
    from sqlmodel import select

    async with session_factory() as session:
        stmt = select(User).where(User.username == "notifuser28")
        user_a = (await session.exec(stmt)).first()
        await session.delete(user_a)
        await session.commit()

    resp = await client.get("/notifications", headers=_h(token_b))
    data = resp.json()
    assert data["items"][0]["actor"] is None
    # El mensaje genérico sobrevive al borrado del actor.
    assert data["items"][0]["message"]
