"""Tests del módulo reviews (FASE 3)."""

import uuid as _uuid

from tests.conftest import random_email, valid_password


async def _register_and_token(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Review User",
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
        title=f"La casa de los espíritus {suffix}",
        author=f"Isabel Allende {suffix}",
        language="es",
        normal_title=f"la casa de los espiritus {suffix}",
        normal_author=f"isabel allende {suffix}",
        page_count=433,
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


async def _add_to_library(client, token: str, book_id: int) -> None:
    resp = await client.patch(
        f"/library/me/{book_id}", json={"status": "READ"}, headers=_h(token)
    )
    assert resp.status_code == 200


async def _get_book(session_factory, book_id: int):
    from app.models import Book

    async with session_factory() as session:
        return await session.get(Book, book_id)


async def _create_review(
    client, token: str, book_id: int, *, score: int = 4, title: str = "Gran novela",
    body: str = "Me encantó.", spoiler: bool = False, language: str = "es",
) -> dict:
    resp = await client.post(
        f"/reviews/{book_id}",
        json={
            "score": score,
            "title": title,
            "body": body,
            "spoiler": spoiler,
            "language": language,
        },
        headers=_h(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_requires_user_book(client, session_factory):
    token = await _register_and_token(client, "reviewuser1")
    book_id = await _create_book(session_factory)
    resp = await client.post(
        f"/reviews/{book_id}",
        json={"score": 4, "body": "Sin libro en librería"},
        headers=_h(token),
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "user_book_required"


async def test_create_review_success(client, session_factory):
    token = await _register_and_token(client, "reviewuser2")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token, book_id)

    data = await _create_review(client, token, book_id, score=4)
    assert data["score"] == 4
    assert data["title"] == "Gran novela"
    assert data["body"] == "Me encantó."
    assert data["book"]["id"] == book_id
    assert data["author"]["username"] == "reviewuser2"

    book = await _get_book(session_factory, book_id)
    assert book.rating_count == 1
    assert float(book.rating_avg) == 4.0
    assert book.review_count == 1


async def test_duplicate_active_review_conflict(client, session_factory):
    token = await _register_and_token(client, "reviewuser3")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token, book_id)
    await _create_review(client, token, book_id)

    resp = await client.post(
        f"/reviews/{book_id}", json={"score": 3}, headers=_h(token)
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "review_already_exists"


async def test_review_after_soft_delete(client, session_factory):
    token = await _register_and_token(client, "reviewuser4")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token, book_id)
    review = await _create_review(client, token, book_id, score=5)
    review_id = review["id"]

    resp = await client.delete(f"/reviews/{book_id}", headers=_h(token))
    assert resp.status_code == 204

    # El rating sobrevive al borrado de la review
    book = await _get_book(session_factory, book_id)
    assert book.rating_count == 1
    assert book.review_count == 0

    # La review ya no es visible públicamente
    resp = await client.get(f"/reviews/{review_id}")
    assert resp.status_code == 404

    # Mi review devuelve null
    resp = await client.get(f"/reviews/{book_id}", headers=_h(token))
    assert resp.status_code == 200
    assert resp.json() is None

    # Re-review permitido tras soft delete
    resp = await client.post(
        f"/reviews/{book_id}", json={"score": 2, "body": "Segunda opinión"},
        headers=_h(token),
    )
    assert resp.status_code == 201


async def test_rating_bounds(client, session_factory):
    token = await _register_and_token(client, "reviewuser5")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token, book_id)

    resp = await client.post(f"/reviews/{book_id}", json={"score": 0}, headers=_h(token))
    assert resp.status_code == 422

    resp = await client.post(f"/reviews/{book_id}", json={"score": 6}, headers=_h(token))
    assert resp.status_code == 422

    resp = await client.post(f"/reviews/{book_id}", json={}, headers=_h(token))
    assert resp.status_code == 422


async def test_update_review(client, session_factory):
    token = await _register_and_token(client, "reviewuser6")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token, book_id)
    await _create_review(client, token, book_id, score=4)

    resp = await client.patch(
        f"/reviews/{book_id}",
        json={"score": 2, "title": "Cambié de opinión", "body": "No tanto."},
        headers=_h(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 2
    assert data["title"] == "Cambié de opinión"

    book = await _get_book(session_factory, book_id)
    assert float(book.rating_avg) == 2.0


async def test_update_review_not_found(client, session_factory):
    token = await _register_and_token(client, "reviewuser7")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token, book_id)
    resp = await client.patch(
        f"/reviews/{book_id}", json={"title": "Nueva"}, headers=_h(token)
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "review_not_found"


async def test_like_unlike_and_unique(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser8")
    token_b = await _register_and_token(client, "reviewuser9")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)
    review = await _create_review(client, token_a, book_id)
    review_id = review["id"]

    resp = await client.post(f"/reviews/{review_id}/like", headers=_h(token_b))
    assert resp.status_code == 201

    # Like duplicado: no crea fila nueva
    resp = await client.post(f"/reviews/{review_id}/like", headers=_h(token_b))
    assert resp.status_code == 201
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.json()["like_count"] == 1

    resp = await client.delete(f"/reviews/{review_id}/like", headers=_h(token_b))
    assert resp.status_code == 204
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.json()["like_count"] == 0


async def test_cannot_like_own_review(client, session_factory):
    token = await _register_and_token(client, "reviewuser10")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token, book_id)
    review = await _create_review(client, token, book_id)
    resp = await client.post(f"/reviews/{review['id']}/like", headers=_h(token))
    assert resp.status_code == 400
    assert resp.json()["error"] == "cannot_like_own_review"


async def test_public_review_detail(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser11")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)
    review = await _create_review(client, token_a, book_id)
    review_id = review["id"]

    # Autenticado
    token_b = await _register_and_token(client, "reviewuser12")
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json()["id"] == review_id

    # Anónimo
    resp = await client.get(f"/reviews/{review_id}")
    assert resp.status_code == 200


async def test_private_reviews_visibility(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser13")
    token_b = await _register_and_token(client, "reviewuser14")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)

    # Privacidad PRIVATE ANTES de publicar: la review nace con visibilidad
    # snapshot PRIVATE (ADR-4).
    resp = await client.patch(
        "/profiles/me/privacy", json={"reviews_visibility": "PRIVATE"},
        headers=_h(token_a),
    )
    assert resp.status_code == 200

    review = await _create_review(client, token_a, book_id)
    review_id = review["id"]

    # Otro usuario: 403 en detalle
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.status_code == 403
    assert resp.json()["error"] == "review_private"

    # No aparece en el listado del libro ni para otro usuario ni anónimo (P1-1)
    resp = await client.get(f"/books/{book_id}/reviews", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    resp = await client.get(f"/books/{book_id}/reviews")
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    # Tampoco en la lista de reviews del autor para otro usuario
    resp = await client.get("/users/reviewuser13/reviews", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    # El autor siempre ve su review
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_a))
    assert resp.status_code == 200


async def test_review_visibility_snapshot_not_retroactive(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser13b")
    token_b = await _register_and_token(client, "reviewuser14b")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)

    review = await _create_review(client, token_a, book_id)  # snapshot PUBLIC
    review_id = review["id"]

    resp = await client.patch(
        "/profiles/me/privacy", json={"reviews_visibility": "PRIVATE"},
        headers=_h(token_a),
    )
    assert resp.status_code == 200

    # La review existente sigue siendo pública (el snapshot no es retroactivo)
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.status_code == 200

    # Una review nueva nace PRIVATE
    book2 = await _create_book(session_factory)
    await _add_to_library(client, token_a, book2)
    review2 = await _create_review(client, token_a, book2)
    resp = await client.get(f"/reviews/{review2['id']}", headers=_h(token_b))
    assert resp.status_code == 403


async def test_followers_reviews_visibility(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser15a")
    token_b = await _register_and_token(client, "reviewuser15b")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)

    resp = await client.patch(
        "/profiles/me/privacy", json={"reviews_visibility": "FOLLOWERS"},
        headers=_h(token_a),
    )
    assert resp.status_code == 200

    review = await _create_review(client, token_a, book_id)
    review_id = review["id"]

    # No seguidor: 403 en detalle, no aparece en el listado del libro
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.status_code == 403
    resp = await client.get(f"/books/{book_id}/reviews", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    # Anónimo: 403
    resp = await client.get(f"/reviews/{review_id}")
    assert resp.status_code == 403

    # Seguidor: ve la review y aparece en el listado del libro
    resp = await client.post("/users/reviewuser15a/follow", headers=_h(token_b))
    assert resp.status_code == 201
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.status_code == 200
    resp = await client.get(f"/books/{book_id}/reviews", headers=_h(token_b))
    assert any(item["id"] == review_id for item in resp.json()["items"])

    # El autor siempre ve su review
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_a))
    assert resp.status_code == 200


async def test_blocked_user_cannot_see_public_reviews(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser16a")
    token_b = await _register_and_token(client, "reviewuser16b")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)
    review = await _create_review(client, token_a, book_id)  # PUBLIC
    review_id = review["id"]

    # B bloquea a A: B no ve nada de A (ni siquiera lo público)
    resp = await client.post("/users/reviewuser16a/block", headers=_h(token_b))
    assert resp.status_code == 204
    resp = await client.get(f"/reviews/{review_id}", headers=_h(token_b))
    assert resp.status_code == 404
    resp = await client.get(f"/books/{book_id}/reviews", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_block_anonymous_hides_reviews_from_anonymous(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser17a")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)

    resp = await client.patch(
        "/profiles/me/privacy",
        json={"reviews_visibility": "PUBLIC", "block_anonymous": True},
        headers=_h(token_a),
    )
    assert resp.status_code == 200

    review = await _create_review(client, token_a, book_id)
    review_id = review["id"]

    resp = await client.get(f"/reviews/{review_id}")
    assert resp.status_code == 403
    resp = await client.get(f"/books/{book_id}/reviews")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_book_reviews_pagination(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser15")
    token_b = await _register_and_token(client, "reviewuser16")
    book_id = await _create_book(session_factory)
    await _add_to_library(client, token_a, book_id)
    await _add_to_library(client, token_b, book_id)
    await _create_review(client, token_a, book_id)
    await _create_review(client, token_b, book_id)

    resp = await client.get(f"/books/{book_id}/reviews?limit=1", headers=_h(token_a))
    assert resp.status_code == 200
    page = resp.json()
    assert len(page["items"]) == 1
    assert page["next"] is not None

    resp2 = await client.get(
        f"/books/{book_id}/reviews?limit=1&cursor={page['next']}",
        headers=_h(token_a),
    )
    page2 = resp2.json()
    assert len(page2["items"]) == 1
    assert page2["next"] is None

    ids = {page["items"][0]["id"], page2["items"][0]["id"]}
    assert len(ids) == 2


async def test_user_reviews_list(client, session_factory):
    token_a = await _register_and_token(client, "reviewuser17")
    book1 = await _create_book(session_factory)
    book2 = await _create_book(session_factory)
    await _add_to_library(client, token_a, book1)
    await _add_to_library(client, token_a, book2)
    await _create_review(client, token_a, book1, title="Primera")
    await _create_review(client, token_a, book2, title="Segunda")

    resp = await client.get("/users/reviewuser17/reviews", headers=_h(token_a))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


async def test_my_reviews_list(client, session_factory):
    token = await _register_and_token(client, "reviewuser18")
    book1 = await _create_book(session_factory)
    book2 = await _create_book(session_factory)
    await _add_to_library(client, token, book1)
    await _add_to_library(client, token, book2)
    await _create_review(client, token, book1)
    await _create_review(client, token, book2)

    resp = await client.get("/me/reviews", headers=_h(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2
