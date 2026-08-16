"""Tests del módulo posts & engagement (FASE 6)."""

import uuid as _uuid

from tests.conftest import random_email, valid_password


async def _register_and_token(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Posts User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    login = await client.post(
        "/auth/login", json={"email": payload["email"], "password": valid_password()}
    )
    return login.json()["access_token"]


async def _create_book(session_factory, **overrides) -> int:
    from app.models import Book

    suffix = _uuid.uuid4().hex[:8]
    data = dict(
        title=f"Libro de posts {suffix}",
        author=f"Autor Posts {suffix}",
        language="es",
        normal_title=f"libro de posts {suffix}",
        normal_author=f"autor posts {suffix}",
        page_count=200,
    )
    data.update(overrides)
    async with session_factory() as session:
        book = Book(**data)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book.id


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_post(client, token: str, *, body: str = "Hola, mundo!", **extra) -> dict:
    payload = {"body": body}
    payload.update(extra)
    resp = await client.post("/posts", json=payload, headers=_h(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _mention_rows(session_factory, content_type: str, content_id: str):
    from app.posts.models import Mention

    async with session_factory() as session:
        from sqlmodel import select

        stmt = select(Mention).where(
            Mention.content_type == content_type, Mention.content_id == content_id
        )
        return (await session.exec(stmt)).all()


async def test_create_post_requires_auth(client):
    resp = await client.post("/posts", json={"body": "Hola"})
    assert resp.status_code == 401


async def test_create_and_get_post(client):
    token = await _register_and_token(client, "postuser1")
    data = await _create_post(
        client,
        token,
        body="Mi primera publicación",
        media=[{"media_type": "IMAGE", "url": "https://img.example.com/1.jpg", "position": 0}],
    )
    assert data["author"]["username"] == "postuser1"
    assert data["body"] == "Mi primera publicación"
    assert data["type"] == "TEXT"
    assert data["visibility"] == "PUBLIC"
    assert len(data["media"]) == 1
    assert data["media"][0]["media_type"] == "IMAGE"

    resp = await client.get(f"/posts/{data['id']}")
    assert resp.status_code == 200
    assert resp.json()["body"] == "Mi primera publicación"


async def test_post_not_found(client):
    token = await _register_and_token(client, "postuser2")
    resp = await client.get(f"/posts/{_uuid.uuid4()}", headers=_h(token))
    assert resp.status_code == 404
    assert resp.json()["error"] == "post_not_found"


async def test_book_share_requires_book(client):
    token = await _register_and_token(client, "postuser3")
    resp = await client.post(
        "/posts",
        json={"type": "BOOK_SHARE", "body": "Comparto libro"},
        headers=_h(token),
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "book_share_requires_book"


async def test_book_share_with_book_and_unknown_book(client, session_factory):
    token = await _register_and_token(client, "postuser4")
    book_id = await _create_book(session_factory)

    data = await _create_post(
        client, token, type="BOOK_SHARE", body="Comparto libro", book_id=book_id
    )
    assert data["book"]["id"] == book_id
    assert data["book"]["title"]

    resp = await client.post(
        "/posts",
        json={"type": "BOOK_SHARE", "body": "x", "book_id": 99999999},
        headers=_h(token),
    )
    assert resp.status_code == 404


async def test_update_post_author_only(client):
    token_a = await _register_and_token(client, "postuser5")
    token_b = await _register_and_token(client, "postuser6")
    post = await _create_post(client, token_a, body="Original")

    resp = await client.patch(
        f"/posts/{post['id']}", json={"body": "Editado"}, headers=_h(token_b)
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "post_forbidden"

    resp = await client.patch(
        f"/posts/{post['id']}", json={"body": "Editado"}, headers=_h(token_a)
    )
    assert resp.status_code == 200
    assert resp.json()["body"] == "Editado"


async def test_delete_post_soft_delete(client):
    token = await _register_and_token(client, "postuser7")
    post = await _create_post(client, token)

    resp = await client.delete(f"/posts/{post['id']}", headers=_h(token))
    assert resp.status_code == 204

    resp = await client.get(f"/posts/{post['id']}", headers=_h(token))
    assert resp.status_code == 404

    # La actividad POST (append-only) sobrevive al soft delete.
    resp = await client.get("/users/postuser7/activity", headers=_h(token))
    assert any(item["verb"] == "POST" for item in resp.json()["items"])


async def test_list_user_posts_visibility_followers(client):
    token_a = await _register_and_token(client, "postuser8")
    token_b = await _register_and_token(client, "postuser9")
    token_c = await _register_and_token(client, "postuser10")

    post = await _create_post(
        client, token_a, body="Solo seguidores", visibility="FOLLOWERS"
    )

    # B (no sigue a A) no ve el post FOLLOWERS.
    resp = await client.get("/users/postuser8/posts", headers=_h(token_b))
    assert len(resp.json()["items"]) == 0

    # C (sigue a A) sí lo ve.
    await client.post("/users/postuser8/follow", headers=_h(token_c))
    resp = await client.get("/users/postuser8/posts", headers=_h(token_c))
    assert [p["id"] for p in resp.json()["items"]] == [post["id"]]

    # A (autor) siempre ve sus posts.
    resp = await client.get("/users/postuser8/posts", headers=_h(token_a))
    assert [p["id"] for p in resp.json()["items"]] == [post["id"]]


async def test_blocked_viewer_cannot_see_post(client):
    token_a = await _register_and_token(client, "postuser11")
    token_b = await _register_and_token(client, "postuser12")
    post = await _create_post(client, token_a)

    await client.post("/users/postuser11/block", headers=_h(token_b))
    resp = await client.get(f"/posts/{post['id']}", headers=_h(token_b))
    assert resp.status_code == 404

    resp = await client.get("/users/postuser11/posts", headers=_h(token_b))
    assert len(resp.json()["items"]) == 0


async def test_private_post_only_author(client):
    token_a = await _register_and_token(client, "postuser13")
    token_b = await _register_and_token(client, "postuser14")
    post = await _create_post(client, token_a, visibility="PRIVATE")

    resp = await client.get(f"/posts/{post['id']}", headers=_h(token_b))
    assert resp.status_code == 403
    assert resp.json()["error"] == "post_private"

    resp = await client.get(f"/posts/{post['id']}", headers=_h(token_a))
    assert resp.status_code == 200


async def test_comment_create_and_list_chronological(client):
    token_a = await _register_and_token(client, "postuser15")
    token_b = await _register_and_token(client, "postuser16")
    post = await _create_post(client, token_a)

    resp = await client.post(
        f"/posts/{post['id']}/comments",
        json={"body": "Primer comentario"},
        headers=_h(token_b),
    )
    assert resp.status_code == 201
    comment = resp.json()
    assert comment["author"]["username"] == "postuser16"

    resp = await client.post(
        f"/posts/{post['id']}/comments",
        json={"body": "Respuesta", "parent_id": comment["id"]},
        headers=_h(token_b),
    )
    assert resp.status_code == 201
    reply = resp.json()
    assert reply["parent_id"] == comment["id"]

    resp = await client.get(f"/posts/{post['id']}/comments")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["id"] == comment["id"]  # orden cronológico
    assert items[1]["id"] == reply["id"]


async def test_comment_nesting_one_level_only(client):
    token = await _register_and_token(client, "postuser17")
    post = await _create_post(client, token)

    resp = await client.post(
        f"/posts/{post['id']}/comments", json={"body": "raíz"}, headers=_h(token)
    )
    root = resp.json()
    resp = await client.post(
        f"/posts/{post['id']}/comments",
        json={"body": "respuesta", "parent_id": root["id"]},
        headers=_h(token),
    )
    reply = resp.json()

    # Un comentario hijo no puede ser padre: anidado máximo 1 nivel.
    resp = await client.post(
        f"/posts/{post['id']}/comments",
        json={"body": "nieto", "parent_id": reply["id"]},
        headers=_h(token),
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "nested_comments_not_allowed"


async def test_comment_delete_by_author_or_post_author(client):
    token_a = await _register_and_token(client, "postuser18")
    token_b = await _register_and_token(client, "postuser19")
    token_c = await _register_and_token(client, "postuser20")
    post = await _create_post(client, token_a)

    resp = await client.post(
        f"/posts/{post['id']}/comments", json={"body": "c"}, headers=_h(token_b)
    )
    comment = resp.json()

    # Un tercero no puede borrarlo.
    resp = await client.delete(
        f"/posts/{post['id']}/comments/{comment['id']}", headers=_h(token_c)
    )
    assert resp.status_code == 403

    # El autor del comentario sí.
    resp = await client.delete(
        f"/posts/{post['id']}/comments/{comment['id']}", headers=_h(token_b)
    )
    assert resp.status_code == 204

    resp = await client.get(f"/posts/{post['id']}/comments")
    assert len(resp.json()["items"]) == 0


async def test_like_post_idempotent_and_count(client):
    token_a = await _register_and_token(client, "postuser21")
    token_b = await _register_and_token(client, "postuser22")
    post = await _create_post(client, token_a)

    resp = await client.post(f"/posts/{post['id']}/like", headers=_h(token_b))
    assert resp.status_code == 201
    resp = await client.post(f"/posts/{post['id']}/like", headers=_h(token_b))
    assert resp.status_code == 201  # idempotente

    detail = await client.get(f"/posts/{post['id']}", headers=_h(token_b))
    assert detail.json()["like_count"] == 1
    assert detail.json()["is_liked"] is True

    resp = await client.delete(f"/posts/{post['id']}/like", headers=_h(token_b))
    assert resp.status_code == 204
    detail = await client.get(f"/posts/{post['id']}", headers=_h(token_a))
    assert detail.json()["like_count"] == 0


async def test_like_comment(client):
    token_a = await _register_and_token(client, "postuser23")
    token_b = await _register_and_token(client, "postuser24")
    post = await _create_post(client, token_a)
    resp = await client.post(
        f"/posts/{post['id']}/comments", json={"body": "c"}, headers=_h(token_b)
    )
    comment = resp.json()

    resp = await client.post(f"/comments/{comment['id']}/like", headers=_h(token_a))
    assert resp.status_code == 201

    resp = await client.get(f"/posts/{post['id']}/comments", headers=_h(token_a))
    item = next(i for i in resp.json()["items"] if i["id"] == comment["id"])
    assert item["like_count"] == 1
    assert item["is_liked"] is True

    resp = await client.delete(f"/comments/{comment['id']}/like", headers=_h(token_a))
    assert resp.status_code == 204


async def test_mentions_created_and_self_skipped(client, session_factory):
    token_a = await _register_and_token(client, "postuser25")
    token_b = await _register_and_token(client, "postuser26")

    post = await _create_post(
        client, token_a, body="Hola @postuser26, mira este post y @postuser25"
    )
    rows = await _mention_rows(session_factory, "POST", post["id"])
    mentioned = {str(r.mentioned_user_id) for r in rows}
    # @postuser26 se menciona; @postuser25 (autor) se salta.
    assert len(rows) == 1

    async with session_factory() as session:
        from app.auth.models import User
        from sqlmodel import select

        stmt = select(User).where(User.username == "postuser26")
        user_b = (await session.exec(stmt)).first()
    assert str(user_b.id) in mentioned


async def test_comment_mentions(client, session_factory):
    token_a = await _register_and_token(client, "postuser27")
    token_b = await _register_and_token(client, "postuser28")
    post = await _create_post(client, token_a)

    resp = await client.post(
        f"/posts/{post['id']}/comments",
        json={"body": "@postuser28 te menciono"},
        headers=_h(token_a),
    )
    comment = resp.json()
    rows = await _mention_rows(session_factory, "COMMENT", comment["id"])
    assert len(rows) == 1


async def test_mentions_updated_on_edit(client, session_factory):
    token = await _register_and_token(client, "postuser29")
    token_b = await _register_and_token(client, "postuser30")
    post = await _create_post(client, token, body="Sin menciones")

    resp = await client.patch(
        f"/posts/{post['id']}",
        json={"body": "Ahora sí @postuser30"},
        headers=_h(token),
    )
    assert resp.status_code == 200
    rows = await _mention_rows(session_factory, "POST", post["id"])
    assert len(rows) == 1


async def test_post_activity_in_feed(client):
    token_a = await _register_and_token(client, "postuser31")
    token_b = await _register_and_token(client, "postuser32")

    post = await _create_post(client, token_a, body="Post que sale en el feed")
    await client.post("/users/postuser31/follow", headers=_h(token_b))

    resp = await client.get("/feed", headers=_h(token_b))
    items = resp.json()["items"]
    post_items = [i for i in items if i["verb"] == "POST"]
    assert len(post_items) == 1
    assert post_items[0]["object_id"] == post["id"]
    assert post_items[0]["actor"]["username"] == "postuser31"

    # La actividad del autor también aparece en su propio perfil.
    resp = await client.get("/users/postuser31/activity", headers=_h(token_a))
    assert any(i["verb"] == "POST" for i in resp.json()["items"])


async def test_post_pagination(client):
    token = await _register_and_token(client, "postuser33")
    for i in range(3):
        await _create_post(client, token, body=f"post número {i}")

    resp = await client.get("/users/postuser33/posts?limit=2", headers=_h(token))
    assert len(resp.json()["items"]) == 2
    assert resp.json()["next"] is not None

    resp2 = await client.get(
        f"/users/postuser33/posts?limit=2&cursor={resp.json()['next']}",
        headers=_h(token),
    )
    assert len(resp2.json()["items"]) == 1
    ids = {p["id"] for p in resp.json()["items"] + resp2.json()["items"]}
    assert len(ids) == 3
