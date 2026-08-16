"""Tests del módulo shelves (FASE 2)."""

from tests.conftest import random_email, valid_password


async def _register_and_token(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Shelf User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    login = await client.post(
        "/auth/login", json={"email": payload["email"], "password": valid_password()}
    )
    return login.json()["access_token"]


async def _create_book(session_factory, **overrides) -> int:
    from app.models import Book
    import uuid as _uuid

    suffix = _uuid.uuid4().hex[:8]
    data = dict(
        title=f"Cien años de soledad {suffix}",
        author=f"Gabriel García Márquez {suffix}",
        language="es",
        normal_title=f"cien anos de soledad {suffix}",
        normal_author=f"gabriel garcia marquez {suffix}",
        page_count=471,
    )
    data.update(overrides)
    async with session_factory() as session:
        book = Book(**data)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book.id


async def _get_status_shelf_id(client, token, slug: str) -> str:
    resp = await client.get("/shelves", headers=_h(token))
    shelves = resp.json()
    return next(s["id"] for s in shelves if s["slug"] == slug)


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_default_status_shelves_seeded(client):
    token = await _register_and_token(client, "shelfuser1")
    resp = await client.get("/shelves", headers=_h(token))
    assert resp.status_code == 200
    slugs = [s["slug"] for s in resp.json()]
    assert {"to-read", "currently-reading", "read"} <= set(slugs)
    statuses = [s for s in resp.json() if s["kind"] == "STATUS"]
    assert len(statuses) == 3


async def test_create_custom_shelf(client):
    token = await _register_and_token(client, "shelfuser2")
    resp = await client.post(
        "/shelves", json={"name": "Favoritos", "description": "Mis favoritos"}, headers=_h(token)
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "CUSTOM"
    assert data["slug"] == "favoritos"
    assert data["book_count"] == 0


async def test_duplicate_shelf_name_gets_unique_slug(client):
    token = await _register_and_token(client, "shelfuser3")
    first = await client.post("/shelves", json={"name": "Favoritos"}, headers=_h(token))
    assert first.status_code == 201
    assert first.json()["slug"] == "favoritos"
    second = await client.post("/shelves", json={"name": "Favoritos"}, headers=_h(token))
    assert second.status_code == 201
    assert second.json()["slug"] == "favoritos-2"


async def test_cannot_modify_status_shelf(client):
    token = await _register_and_token(client, "shelfuser4")
    sid = await _get_status_shelf_id(client, token, "to-read")
    resp = await client.patch(f"/shelves/{sid}", json={"name": "Mis Lecturas"}, headers=_h(token))
    assert resp.status_code == 400
    assert resp.json()["error"] == "cannot_modify_status_shelf"


async def test_cannot_delete_status_shelf(client):
    token = await _register_and_token(client, "shelfuser5")
    sid = await _get_status_shelf_id(client, token, "read")
    resp = await client.delete(f"/shelves/{sid}", headers=_h(token))
    assert resp.status_code == 400
    assert resp.json()["error"] == "shelf_not_custom"


async def test_custom_shelf_add_list_remove(client, session_factory):
    token = await _register_and_token(client, "shelfuser6")
    book_id = await _create_book(session_factory)
    shelf_resp = await client.post("/shelves", json={"name": "Pendientes"}, headers=_h(token))
    shelf_id = shelf_resp.json()["id"]

    resp = await client.put(
        f"/shelves/{shelf_id}/books/{book_id}", headers=_h(token)
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == book_id

    resp = await client.get(f"/shelves/{shelf_id}/books", headers=_h(token))
    assert len(resp.json()) == 1

    await client.delete(f"/shelves/{shelf_id}/books/{book_id}", headers=_h(token))
    resp = await client.get(f"/shelves/{shelf_id}/books", headers=_h(token))
    assert resp.json() == []


async def test_cannot_add_book_to_status_shelf(client, session_factory):
    token = await _register_and_token(client, "shelfuser7")
    book_id = await _create_book(session_factory)
    sid = await _get_status_shelf_id(client, token, "currently-reading")
    resp = await client.put(f"/shelves/{sid}/books/{book_id}", headers=_h(token))
    assert resp.status_code == 400
    assert resp.json()["error"] == "shelf_not_custom"


async def test_user_book_status_dates(client, session_factory):
    token = await _register_and_token(client, "shelfuser8")
    book_id = await _create_book(session_factory)

    resp = await client.patch(
        f"/library/me/{book_id}", json={"status": "READING"}, headers=_h(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "READING"
    assert data["started_at"] is not None
    assert data["finished_at"] is None

    resp = await client.patch(
        f"/library/me/{book_id}", json={"status": "READ"}, headers=_h(token)
    )
    data = resp.json()
    assert data["status"] == "READ"
    assert data["started_at"] is not None
    assert data["finished_at"] is not None


async def test_status_required_when_creating(client, session_factory):
    token = await _register_and_token(client, "shelfuser9")
    book_id = await _create_book(session_factory)
    resp = await client.patch(f"/library/me/{book_id}", json={}, headers=_h(token))
    assert resp.status_code == 422


async def test_library_filter_by_status(client, session_factory):
    token = await _register_and_token(client, "shelfuser10")
    b1 = await _create_book(session_factory)
    b2 = await _create_book(session_factory, title="Otro libro", normal_title="otro libro")
    await client.patch(f"/library/me/{b1}", json={"status": "READING"}, headers=_h(token))
    await client.patch(f"/library/me/{b2}", json={"status": "READ"}, headers=_h(token))

    resp = await client.get("/library/me?status=READING", headers=_h(token))
    assert [u["book_id"] for u in resp.json()] == [b1]

    resp = await client.get("/library/me", headers=_h(token))
    assert len(resp.json()) == 2


async def test_progress_update_and_history(client, session_factory):
    token = await _register_and_token(client, "shelfuser11")
    book_id = await _create_book(session_factory)
    await client.patch(f"/library/me/{book_id}", json={"status": "READING"}, headers=_h(token))

    resp = await client.patch(
        f"/library/me/{book_id}/progress", json={"page": 50}, headers=_h(token)
    )
    assert resp.status_code == 200
    assert resp.json()["current_page"] == 50

    resp = await client.get(f"/library/me/{book_id}/progress", headers=_h(token))
    assert len(resp.json()) == 1

    # Página por encima del page_count del libro
    resp = await client.patch(
        f"/library/me/{book_id}/progress", json={"page": 472}, headers=_h(token)
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "progress_exceeds_book"

    # Sin page ni percent
    resp = await client.patch(f"/library/me/{book_id}/progress", json={}, headers=_h(token))
    assert resp.status_code == 422


async def test_delete_user_book(client, session_factory):
    token = await _register_and_token(client, "shelfuser12")
    book_id = await _create_book(session_factory)
    await client.patch(f"/library/me/{book_id}", json={"status": "WANT_TO_READ"}, headers=_h(token))
    resp = await client.delete(f"/library/me/{book_id}", headers=_h(token))
    assert resp.status_code == 204
    resp = await client.get("/library/me", headers=_h(token))
    assert resp.json() == []


async def test_public_library_visibility(client, session_factory):
    token_a = await _register_and_token(client, "pubuser1")
    book_id = await _create_book(session_factory)
    await client.patch(f"/library/me/{book_id}", json={"status": "READ"}, headers=_h(token_a))

    # Pública por defecto → visible para otro usuario
    token_b = await _register_and_token(client, "pubuser2")
    resp = await client.get("/library/pubuser1", headers=_h(token_b))
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Ponerla privada → 403 para otros
    await client.patch("/profiles/me/privacy", json={"library_visibility": "PRIVATE"}, headers=_h(token_a))
    resp = await client.get("/library/pubuser1", headers=_h(token_b))
    assert resp.status_code == 403
    assert resp.json()["error"] == "library_private"

    # El propio usuario sigue viendo su librería
    resp = await client.get("/library/me", headers=_h(token_a))
    assert resp.status_code == 200