"""Tests del módulo lists & collaborators (FASE 7)."""

import uuid as _uuid

from tests.conftest import random_email, valid_password


async def _register_and_token(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Lists User",
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
        title=f"Libro de listas {suffix}",
        author=f"Autor Listas {suffix}",
        language="es",
        normal_title=f"libro de listas {suffix}",
        normal_author=f"autor listas {suffix}",
        page_count=250,
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


async def _create_list(client, token: str, *, title: str = "Mi lista", **extra) -> dict:
    payload = {"title": title}
    payload.update(extra)
    resp = await client.post("/lists", json=payload, headers=_h(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _user_id(session_factory, username: str) -> str:
    from app.auth.models import User
    from sqlmodel import select

    async with session_factory() as session:
        stmt = select(User).where(User.username == username)
        user = (await session.exec(stmt)).first()
        return str(user.id)


async def test_create_list_requires_auth(client):
    resp = await client.post("/lists", json={"title": "Mi lista"})
    assert resp.status_code == 401


async def test_create_and_get_list(client):
    token = await _register_and_token(client, "listuser1")
    data = await _create_list(client, token, title="Favoritos", description="Cosas buenas")
    assert data["title"] == "Favoritos"
    assert data["slug"]
    assert data["owner"]["username"] == "listuser1"
    assert data["is_owner"] is True
    assert data["can_edit"] is True
    assert data["visibility"] == "PUBLIC"

    resp = await client.get(f"/lists/{data['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Favoritos"


async def test_list_not_found(client):
    token = await _register_and_token(client, "listuser2")
    resp = await client.get(f"/lists/{_uuid.uuid4()}", headers=_h(token))
    assert resp.status_code == 404
    assert resp.json()["error"] == "list_not_found"


async def test_slug_unique_per_owner(client):
    token = await _register_and_token(client, "listuser3")
    await _create_list(client, token, title="Ciencia ficción")
    data = await _create_list(client, token, title="Ciencia ficción")
    assert data["slug"].startswith("ciencia-ficcion")
    assert data["slug"] != "ciencia-ficcion"


async def test_update_list_only_owner(client):
    token_a = await _register_and_token(client, "listuser4")
    token_b = await _register_and_token(client, "listuser5")
    lst = await _create_list(client, token_a)

    resp = await client.patch(
        f"/lists/{lst['id']}", json={"title": "Editado"}, headers=_h(token_b)
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "list_forbidden"

    resp = await client.patch(
        f"/lists/{lst['id']}", json={"title": "Editado"}, headers=_h(token_a)
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Editado"


async def test_delete_list_soft_delete_and_recreate_same_slug(client):
    token = await _register_and_token(client, "listuser6")
    lst = await _create_list(client, token, title="Relectura")
    original_slug = lst["slug"]

    resp = await client.delete(f"/lists/{lst['id']}", headers=_h(token))
    assert resp.status_code == 204

    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token))
    assert resp.status_code == 404

    # Re-crear con el mismo título recupera el slug (soft delete lo libera).
    lst2 = await _create_list(client, token, title="Relectura")
    assert lst2["slug"] == original_slug

    # Los items de la lista borrada siguen en BD (CASCADE solo al borrar duro).
    resp = await client.get("/lists", headers=_h(token))
    assert [l["title"] for l in resp.json()["items"]] == ["Relectura"]


async def test_list_visibility_followers(client):
    token_a = await _register_and_token(client, "listuser7")
    token_b = await _register_and_token(client, "listuser8")
    token_c = await _register_and_token(client, "listuser9")

    lst = await _create_list(client, token_a, visibility="FOLLOWERS")

    # B no sigue a A: no ve la lista FOLLOWERS.
    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token_b))
    assert resp.status_code == 403
    assert resp.json()["error"] == "list_private"

    # C sigue a A: sí la ve.
    await client.post("/users/listuser7/follow", headers=_h(token_c))
    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token_c))
    assert resp.status_code == 200

    # El owner siempre la ve.
    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token_a))
    assert resp.status_code == 200


async def test_blocked_viewer_cannot_see_list(client):
    token_a = await _register_and_token(client, "listuser10")
    token_b = await _register_and_token(client, "listuser11")
    lst = await _create_list(client, token_a)

    await client.post("/users/listuser10/block", headers=_h(token_b))
    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token_b))
    assert resp.status_code == 404

    resp = await client.get("/users/listuser10/lists", headers=_h(token_b))
    assert len(resp.json()["items"]) == 0


async def test_list_user_lists(client):
    token_a = await _register_and_token(client, "listuser12")
    await _create_list(client, token_a, title="Lista uno")
    await _create_list(client, token_a, title="Lista dos")

    resp = await client.get("/users/listuser12/lists")
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert titles == {"Lista uno", "Lista dos"}

    # Mis listas (auth) devuelven lo mismo.
    resp = await client.get("/lists", headers=_h(token_a))
    assert len(resp.json()["items"]) == 2


async def test_add_and_remove_item(client, session_factory):
    token_a = await _register_and_token(client, "listuser13")
    token_b = await _register_and_token(client, "listuser14")
    lst = await _create_list(client, token_a)
    book_id = await _create_book(session_factory)

    resp = await client.post(
        f"/lists/{lst['id']}/items",
        json={"book_id": book_id, "note": "Muy bueno"},
        headers=_h(token_b),
    )
    assert resp.status_code == 403  # solo owner/EDITOR

    resp = await client.post(
        f"/lists/{lst['id']}/items",
        json={"book_id": book_id, "note": "Muy bueno"},
        headers=_h(token_a),
    )
    assert resp.status_code == 201
    item = resp.json()
    assert item["book"]["id"] == book_id
    assert item["note"] == "Muy bueno"
    assert item["position"] == 0

    # item único por (list, book): duplicado da 409.
    resp = await client.post(
        f"/lists/{lst['id']}/items",
        json={"book_id": book_id},
        headers=_h(token_a),
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "list_item_already_exists"

    resp = await client.get(f"/lists/{lst['id']}/items")
    assert len(resp.json()["items"]) == 1

    resp = await client.delete(f"/lists/{lst['id']}/items/{book_id}", headers=_h(token_a))
    assert resp.status_code == 204
    resp = await client.get(f"/lists/{lst['id']}/items")
    assert len(resp.json()["items"]) == 0


async def test_add_item_unknown_book(client, session_factory):
    token = await _register_and_token(client, "listuser15")
    lst = await _create_list(client, token)
    resp = await client.post(
        f"/lists/{lst['id']}/items", json={"book_id": 99999999}, headers=_h(token)
    )
    assert resp.status_code == 404


async def test_collaborator_editor_can_manage_items(client, session_factory):
    token_a = await _register_and_token(client, "listuser16")
    token_b = await _register_and_token(client, "listuser17")
    lst = await _create_list(client, token_a)
    book_id = await _create_book(session_factory)
    user_b = await _user_id(session_factory, "listuser17")

    resp = await client.post(
        f"/lists/{lst['id']}/collaborators",
        json={"user_id": user_b, "role": "EDITOR"},
        headers=_h(token_a),
    )
    assert resp.status_code == 201
    collabs = resp.json()["collaborators"]
    assert len(collabs) == 1
    assert collabs[0]["user"]["username"] == "listuser17"
    assert collabs[0]["role"] == "EDITOR"
    assert collabs[0]["can_add_books"] is True

    # El EDITOR ve la lista y puede añadir items.
    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json()["is_collaborator"] is True
    assert resp.json()["can_edit"] is True

    resp = await client.post(
        f"/lists/{lst['id']}/items", json={"book_id": book_id}, headers=_h(token_b)
    )
    assert resp.status_code == 201

    # No puede editar la lista (solo owner).
    resp = await client.patch(
        f"/lists/{lst['id']}", json={"title": "No"}, headers=_h(token_b)
    )
    assert resp.status_code == 403


async def test_collaborator_viewer_cannot_add(client, session_factory):
    token_a = await _register_and_token(client, "listuser18")
    token_b = await _register_and_token(client, "listuser19")
    lst = await _create_list(client, token_a)
    book_id = await _create_book(session_factory)
    user_b = await _user_id(session_factory, "listuser19")

    await client.post(
        f"/lists/{lst['id']}/collaborators",
        json={"user_id": user_b, "role": "VIEWER"},
        headers=_h(token_a),
    )

    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token_b))
    assert resp.json()["can_edit"] is False

    resp = await client.post(
        f"/lists/{lst['id']}/items", json={"book_id": book_id}, headers=_h(token_b)
    )
    assert resp.status_code == 403


async def test_collaborator_viewer_can_add_if_can_add_books(client, session_factory):
    token_a = await _register_and_token(client, "listuser20")
    token_b = await _register_and_token(client, "listuser21")
    lst = await _create_list(client, token_a)
    book_id = await _create_book(session_factory)
    user_b = await _user_id(session_factory, "listuser21")

    await client.post(
        f"/lists/{lst['id']}/collaborators",
        json={"user_id": user_b, "role": "VIEWER", "can_add_books": True},
        headers=_h(token_a),
    )

    resp = await client.post(
        f"/lists/{lst['id']}/items", json={"book_id": book_id}, headers=_h(token_b)
    )
    assert resp.status_code == 201


async def test_collaborators_owner_only(client, session_factory):
    token_a = await _register_and_token(client, "listuser22")
    token_b = await _register_and_token(client, "listuser23")
    lst = await _create_list(client, token_a)
    user_a = await _user_id(session_factory, "listuser22")

    # No owner no puede invitar.
    resp = await client.post(
        f"/lists/{lst['id']}/collaborators",
        json={"user_id": user_a, "role": "VIEWER"},
        headers=_h(token_b),
    )
    assert resp.status_code == 403

    # No auto-invitación del owner.
    resp = await client.post(
        f"/lists/{lst['id']}/collaborators",
        json={"user_id": user_a, "role": "VIEWER"},
        headers=_h(token_a),
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "cannot_collaborate_self"


async def test_collaborator_update_and_remove(client, session_factory):
    token_a = await _register_and_token(client, "listuser24")
    token_b = await _register_and_token(client, "listuser25")
    lst = await _create_list(client, token_a)
    user_b = await _user_id(session_factory, "listuser25")

    await client.post(
        f"/lists/{lst['id']}/collaborators",
        json={"user_id": user_b, "role": "VIEWER"},
        headers=_h(token_a),
    )

    # Duplicado da 409.
    resp = await client.post(
        f"/lists/{lst['id']}/collaborators",
        json={"user_id": user_b, "role": "EDITOR"},
        headers=_h(token_a),
    )
    assert resp.status_code == 409

    resp = await client.patch(
        f"/lists/{lst['id']}/collaborators/{user_b}",
        json={"role": "EDITOR"},
        headers=_h(token_a),
    )
    assert resp.status_code == 200
    collab = next(
        c for c in resp.json()["collaborators"] if c["user"]["id"] == user_b
    )
    assert collab["role"] == "EDITOR"

    resp = await client.delete(
        f"/lists/{lst['id']}/collaborators/{user_b}", headers=_h(token_a)
    )
    assert resp.status_code == 204

    # Tras quitarlo, el VIEWER/EDITOR ya no ve la lista PRIVATE.
    await client.patch(
        f"/lists/{lst['id']}", json={"visibility": "PRIVATE"}, headers=_h(token_a)
    )
    resp = await client.get(f"/lists/{lst['id']}", headers=_h(token_b))
    assert resp.status_code == 403


async def test_list_creates_activity(client):
    token_a = await _register_and_token(client, "listuser26")
    token_b = await _register_and_token(client, "listuser27")

    await _create_list(client, token_a, title="Top novelas")
    await client.post("/users/listuser26/follow", headers=_h(token_b))

    resp = await client.get("/feed", headers=_h(token_b))
    items = [i for i in resp.json()["items"] if i["verb"] == "LIST_CREATED"]
    assert len(items) == 1
    assert items[0]["target_type"] == "LIST"
    assert items[0]["actor"]["username"] == "listuser26"

    # En la actividad de perfil del autor también.
    resp = await client.get("/users/listuser26/activity", headers=_h(token_a))
    assert any(i["verb"] == "LIST_CREATED" for i in resp.json()["items"])


async def test_list_pagination(client):
    token = await _register_and_token(client, "listuser28")
    for i in range(3):
        await _create_list(client, token, title=f"Lista {i}")

    resp = await client.get("/lists?limit=2", headers=_h(token))
    assert len(resp.json()["items"]) == 2
    assert resp.json()["next"] is not None

    resp2 = await client.get(
        f"/lists?limit=2&cursor={resp.json()['next']}", headers=_h(token)
    )
    assert len(resp2.json()["items"]) == 1
    ids = {l["id"] for l in resp.json()["items"] + resp2.json()["items"]}
    assert len(ids) == 3
