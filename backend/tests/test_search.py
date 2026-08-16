"""Tests del módulo de búsqueda social (FASE 10).

`/search/users`, `/search/books`, `/search/posts`: ranking, filtros de
visibilidad (no devuelve privados), normalización de tildes y límites.
"""

import uuid as _uuid

from tests.conftest import random_email, valid_password


async def _register(client, username: str, *, display_name: str | None = None) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Search User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    login = await client.post(
        "/auth/login", json={"email": payload["email"], "password": valid_password()}
    )
    token = login.json()["access_token"]
    if display_name:
        me = await client.patch(
            "/profiles/me", json={"display_name": display_name}, headers=_h(token)
        )
        assert me.status_code == 200, me.text
    return token


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_book_db(session_factory, **overrides) -> int:
    from app.models import Book

    suffix = _uuid.uuid4().hex[:8]
    data = dict(
        title=f"Cien años de soledad {suffix}",
        author=f"Gabriel García Márquez {suffix}",
        language="es",
        normal_title=f"cien anos de soledad {suffix}",
        normal_author=f"gabriel garcia marquez {suffix}",
        page_count=400,
    )
    data.update(overrides)
    async with session_factory() as session:
        book = Book(**data)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book.id


async def test_search_users_by_username_and_ranking(client):
    token_a = await _register(client, "maria_dev")
    await _register(client, "anamar")
    await _register(client, "mar_extra")

    resp = await client.get("/search/users?q=mar", headers=_h(token_a))
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 3
    usernames = [u["username"] for u in users]
    assert "maria_dev" in usernames
    assert "anamar" in usernames
    assert "mar_extra" in usernames
    assert usernames.index("maria_dev") < usernames.index("anamar")


async def test_search_users_tildes_normalization(client):
    token = await _register(client, "jose_lector")
    await _register(client, "otro_usuario", display_name="José García")
    await _register(client, "tercero")

    resp = await client.get("/search/users?q=jose", headers=_h(token))
    assert resp.status_code == 200
    matches = {u["username"] for u in resp.json()}
    assert "jose_lector" in matches
    assert "otro_usuario" in matches  # display_name con tilde vía unaccent

    resp = await client.get("/search/users?q=josé", headers=_h(token))
    assert resp.status_code == 200
    matches = {u["username"] for u in resp.json()}
    assert "otro_usuario" in matches


async def test_search_users_private_profile_hidden(client):
    token_priv = await _register(client, "privperfil", display_name="Solo Amigos")
    await _register(client, "normalito")

    privacy = await client.patch(
        "/profiles/me/privacy",
        json={"profile_visibility": "PRIVATE"},
        headers=_h(token_priv),
    )
    assert privacy.status_code == 200, privacy.text

    anon = await client.get("/search/users?q=privperfil")
    assert anon.status_code == 200
    assert all(u["username"] != "privperfil" for u in anon.json())

    other = await _register(client, "curioso")
    resp = await client.get("/search/users?q=privperfil", headers=_h(other))
    assert resp.status_code == 200
    assert all(u["username"] != "privperfil" for u in resp.json())

    own = await client.get("/search/users?q=privperfil", headers=_h(token_priv))
    assert own.status_code == 200
    assert any(u["username"] == "privperfil" for u in own.json())


async def test_search_users_block_anonymous(client):
    token = await _register(client, "anonfobi")
    await client.patch(
        "/profiles/me/privacy", json={"block_anonymous": True}, headers=_h(token)
    )

    anon = await client.get("/search/users?q=anonfobi")
    assert anon.status_code == 200
    assert all(u["username"] != "anonfobi" for u in anon.json())

    viewer = await _register(client, "laconstru")
    resp = await client.get("/search/users?q=anonfobi", headers=_h(viewer))
    assert resp.status_code == 200
    assert any(u["username"] == "anonfobi" for u in resp.json())


async def test_search_users_blocked_relation_hidden(client):
    token_a = await _register(client, "bloqueado2")
    token_b = await _register(client, "otromas2")

    block = await client.post("/users/bloqueado2/block", headers=_h(token_b))
    assert block.status_code in (200, 204), block.text

    resp = await client.get("/search/users?q=bloqueado2", headers=_h(token_b))
    assert resp.status_code == 200
    assert all(u["username"] != "bloqueado2" for u in resp.json())

    resp = await client.get("/search/users?q=otromas2", headers=_h(token_a))
    assert resp.status_code == 200
    assert all(u["username"] != "otromas2" for u in resp.json())


async def _create_book_db(session_factory, **overrides) -> int:
    from app.models import Book

    suffix = _uuid.uuid4().hex[:8]
    data = dict(
        title=f"Cien años de soledad {suffix}",
        author=f"Gabriel García Márquez {suffix}",
        language="es",
        normal_title=f"cien anos de soledad {suffix}",
        normal_author=f"gabriel garcia marquez {suffix}",
        page_count=400,
    )
    data.update(overrides)
    async with session_factory() as session:
        book = Book(**data)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book.id


async def test_search_books_tildes_and_fields(client, session_factory):
    token = await _register(client, "buscarlib")
    marker = "kt" + _uuid.uuid4().hex[:6]
    await _create_book_db(
        session_factory,
        title=f"Cien años de soledad {marker}",
        author=f"Gabriel García Márquez {marker}",
        normal_title=f"cien anos de soledad {marker}",
        normal_author=f"gabriel garcia marquez {marker}",
    )
    await _create_book_db(
        session_factory,
        title=f"El coronel no tiene quien le escriba {marker}",
        normal_title=f"el coronel no tiene quien le escriba {marker}",
    )

    # "cien anos" (sin tilde) debe emparejar "Cien años" (normalización).
    resp = await client.get(
        "/search/books",
        params={"q": f"cien anos de soledad {marker}"},
        headers=_h(token),
    )
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert "soledad" in books[0]["title"]
    assert books[0]["page_count"] == 400

    # Búsqueda por autor (normalizado).
    resp = await client.get(
        "/search/books",
        params={"q": f"gabriel garcia marquez {marker}"},
        headers=_h(token),
    )
    assert resp.status_code == 200
    authors = resp.json()
    assert len(authors) == 1
    assert "Gabriel" in authors[0]["author"]


async def test_search_posts_visibility(client, session_factory):
    token_pub = await _register(client, "pubposte")
    token_follow = await _register(client, "seguidorx")
    token_other = await _register(client, "tiootro")

    public = await client.post(
        "/posts",
        json={"body": "Me encanta la física cuántica", "visibility": "PUBLIC"},
        headers=_h(token_pub),
    )
    followers = await client.post(
        "/posts",
        json={"body": "La física cuántica y el multiverso", "visibility": "FOLLOWERS"},
        headers=_h(token_pub),
    )
    private = await client.post(
        "/posts",
        json={"body": "Física cuántica en privado", "visibility": "PRIVATE"},
        headers=_h(token_pub),
    )
    assert public.status_code == 201, public.text
    assert followers.status_code == 201
    assert private.status_code == 201

    await client.post("/users/pubposte/follow", headers=_h(token_follow))

    anon = await client.get("/search/posts?q=fisica")
    assert anon.status_code == 200
    anon_titles = {p["id"] for p in anon.json()}
    assert public.json()["id"] in anon_titles
    assert followers.json()["id"] not in anon_titles
    assert private.json()["id"] not in anon_titles

    other = await client.get("/search/posts?q=fisica", headers=_h(token_other))
    assert other.status_code == 200
    other_ids = {p["id"] for p in other.json()}
    assert public.json()["id"] in other_ids
    assert followers.json()["id"] not in other_ids

    follow_resp = await client.get(
        "/search/posts?q=fisica", headers=_h(token_follow)
    )
    assert follow_resp.status_code == 200
    follow_ids = {p["id"] for p in follow_resp.json()}
    assert public.json()["id"] in follow_ids
    assert followers.json()["id"] in follow_ids
    assert private.json()["id"] not in follow_ids

    author = await client.get("/search/posts?q=fisica", headers=_h(token_pub))
    assert author.status_code == 200
    author_ids = {p["id"] for p in author.json()}
    assert private.json()["id"] in author_ids


async def test_search_posts_muted_author_excluded(client):
    token_a = await _register(client, "mutedwriter")
    token_b = await _register(client, "mutedreader")

    await client.post(
        "/posts", json={"body": "Contenido silenciado único"}, headers=_h(token_a)
    )
    mute = await client.post("/users/mutedwriter/mute", headers=_h(token_b))
    assert mute.status_code in (200, 204), mute.text

    resp = await client.get(
        "/search/posts?q=silenciado", headers=_h(token_b)
    )
    assert resp.status_code == 200
    assert all("silenciado" not in p["body"] for p in resp.json())


async def test_search_limit(client):
    token = await _register(client, "limituser")
    for i in range(5):
        await client.post(
            "/posts", json={"body": f"publicación especial número {i}"}, headers=_h(token)
        )

    resp = await client.get("/search/posts?q=publicacion&limit=2", headers=_h(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.get("/search/posts?q=publicacion&limit=0", headers=_h(token))
    assert resp.status_code == 422
    resp = await client.get("/search/posts?q=publicacion&limit=200", headers=_h(token))
    assert resp.status_code == 422


async def test_search_empty_query_validation(client):
    token = await _register(client, "validaok")
    resp = await client.get("/search/users?q=", headers=_h(token))
    assert resp.status_code == 422