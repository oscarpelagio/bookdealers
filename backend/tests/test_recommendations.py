"""Tests del módulo de recomendaciones (FASE 11).

`GET /recommendations` (colaborativo por autor + fallback populares) y
`GET /feed/popular` (engagement con visibilidad).
"""

import datetime
import uuid as _uuid

import pytest
from sqlalchemy import text

from tests.conftest import random_email, valid_password


@pytest.fixture(autouse=True)
async def _clean_books(test_engine):
    """Los libros no se truncaban en conftest; se resetean aquí para que las
    recomendaciones (globales por rating) sean deterministas."""
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE books RESTART IDENTITY CASCADE"))
    yield


async def _register(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Reco User",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    login = await client.post(
        "/auth/login", json={"email": payload["email"], "password": valid_password()}
    )
    return login.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_book(
    session_factory,
    *,
    author: str = "Gabriel García Márquez",
    normal_author: str = "gabriel garcia marquez",
    rating_count: int = 0,
    rating_avg=None,
) -> int:
    from app.models import Book

    suffix = _uuid.uuid4().hex[:8]
    data = dict(
        title=f"Libro reco {suffix}",
        author=f"{author} {suffix}",
        language="es",
        normal_title=f"libro reco {suffix}",
        normal_author=normal_author,
        rating_count=rating_count,
        rating_avg=rating_avg,
    )
    async with session_factory() as session:
        book = Book(**data)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book.id


async def _user_id(session_factory, handle: str):
    from sqlmodel import select

    from app.auth.models import User

    async with session_factory() as session:
        user = (await session.exec(select(User).where(User.username == handle))).first()
        return user.id


async def _rate(session_factory, user_id, book_id: int, score: int) -> None:
    import uuid

    from app.reviews.models import Rating

    now = datetime.datetime.now(datetime.timezone.utc)
    async with session_factory() as session:
        session.add(
            Rating(
                user_id=user_id,
                book_id=book_id,
                score=score,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()


async def _add_to_library(session_factory, user_id, book_id: int) -> None:
    from app.enums import ReadingStatus
    from app.shelves.models import UserBook

    today = datetime.date.today()
    async with session_factory() as session:
        session.add(
            UserBook(
                user_id=user_id,
                book_id=book_id,
                status=ReadingStatus.READ,
                started_at=today,
                finished_at=today,
            )
        )
        await session.commit()


async def _like(session_factory, post_id: str, user_id) -> None:
    from app.posts.models import PostLike

    now = datetime.datetime.now(datetime.timezone.utc)
    async with session_factory() as session:
        session.add(
            PostLike(user_id=user_id, post_id=_uuid.UUID(post_id), created_at=now)
        )
        await session.commit()


async def _comment(session_factory, post_id: str, user_id) -> None:
    from app.posts.models import Comment

    now = datetime.datetime.now(datetime.timezone.utc)
    async with session_factory() as session:
        session.add(
            Comment(
                author_id=user_id,
                post_id=_uuid.UUID(post_id),
                body="Un comentario",
                created_at=now,
            )
        )
        await session.commit()


async def test_recommendations_cold_data_returns_popular(client, session_factory):
    token = await _register(client, "coldstart")
    await _create_book(
        session_factory,
        author="Isaac Asimov",
        normal_author="isaac asimov",
        rating_count=10,
        rating_avg=4.8,
    )

    resp = await client.get("/recommendations", headers=_h(token))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["source"] == "popular"
    assert "Asimov" in items[0]["book"]["author"]


async def test_recommendations_anonymous_popular(client, session_factory):
    await _create_book(
        session_factory,
        author="Terry Pratchett",
        normal_author="terry pratchett",
        rating_count=5,
        rating_avg=4.2,
    )
    resp = await client.get("/recommendations")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["source"] == "popular"


async def test_recommendations_author_based(client, session_factory):
    token = await _register(client, "autorlect")
    user_id = await _user_id(session_factory, "autorlect")

    liked = await _create_book(
        session_factory, author="Autora Favorita", normal_author="autora favorita"
    )
    other = await _create_book(
        session_factory,
        author="Autora Favorita",
        normal_author="autora favorita",
        rating_count=7,
        rating_avg=4.5,
    )
    distractor = await _create_book(
        session_factory,
        author="Otra Autora",
        normal_author="otra autora",
        rating_count=9,
        rating_avg=4.9,
    )
    await _rate(session_factory, user_id, liked, 5)

    resp = await client.get("/recommendations", headers=_h(token))
    assert resp.status_code == 200
    items = resp.json()
    rec_ids = {item["book"]["id"] for item in items}
    assert other in rec_ids
    by_id = {item["book"]["id"]: item for item in items}
    assert by_id[other]["source"] == "author"
    author_sourced = {item["book"]["id"] for item in items if item["source"] == "author"}
    assert other in author_sourced
    assert distractor not in author_sourced


async def test_recommendations_excludes_rated_and_library(client, session_factory):
    token = await _register(client, "excluid")
    user_id = await _user_id(session_factory, "excluid")

    rated = await _create_book(
        session_factory, author="Misma Autora", normal_author="misma autora"
    )
    in_library = await _create_book(
        session_factory,
        author="Misma Autora",
        normal_author="misma autora",
        rating_count=4,
        rating_avg=4.0,
    )
    await _rate(session_factory, user_id, rated, 4)
    await _add_to_library(session_factory, user_id, in_library)

    resp = await client.get("/recommendations", headers=_h(token))
    assert resp.status_code == 200
    rec_ids = {item["book"]["id"] for item in resp.json()}
    assert rated not in rec_ids
    assert in_library not in rec_ids


async def test_recommendations_collaborative(client, session_factory):
    token_a = await _register(client, "collabuser")
    user_a = await _user_id(session_factory, "collabuser")
    token_b = await _register(client, "collabtwins")
    user_b = await _user_id(session_factory, "collabtwins")

    seed_book = await _create_book(
        session_factory, author="Autor Semilla", normal_author="autor semilla"
    )
    shared_love = await _create_book(
        session_factory, author="Autor Afin", normal_author="autor afin"
    )

    await _rate(session_factory, user_a, seed_book, 5)
    await _rate(session_factory, user_b, seed_book, 5)
    await _rate(session_factory, user_b, shared_love, 5)
    await _create_book(
        session_factory, author="Autor Semilla", normal_author="autor semilla"
    )

    resp = await client.get("/recommendations", headers=_h(token_a))
    assert resp.status_code == 200
    items = resp.json()
    by_id = {item["book"]["id"]: item for item in items}
    assert shared_love in by_id
    assert by_id[shared_love]["source"] == "collaborative"
    assert by_id[shared_love]["score"] > 0


async def test_popular_posts_ranking_and_visibility(client, session_factory):
    token_pub = await _register(client, "popwriter")
    pub_id = await _user_id(session_factory, "popwriter")
    token_l1 = await _register(client, "poplike1")
    token_l2 = await _register(client, "poplike2")
    token_l3 = await _register(client, "poplike3")
    user_l1 = await _user_id(session_factory, "poplike1")
    user_l2 = await _user_id(session_factory, "poplike2")
    user_l3 = await _user_id(session_factory, "poplike3")
    token_c = await _register(client, "popcoment")
    user_c = await _user_id(session_factory, "popcoment")

    p_high = (
        await client.post(
            "/posts", json={"body": "top del día", "visibility": "PUBLIC"},
            headers=_h(token_pub),
        )
    ).json()
    p_low = (
        await client.post(
            "/posts", json={"body": "post discreto", "visibility": "PUBLIC"},
            headers=_h(token_pub),
        )
    ).json()
    p_private = (
        await client.post(
            "/posts", json={"body": "privado viral", "visibility": "PRIVATE"},
            headers=_h(token_pub),
        )
    ).json()

    await _like(session_factory, p_high["id"], user_l1)
    await _like(session_factory, p_high["id"], user_l2)
    await _comment(session_factory, p_high["id"], user_c)
    await _like(session_factory, p_low["id"], user_l3)
    await _like(session_factory, p_private["id"], user_l1)
    await _like(session_factory, p_private["id"], user_l2)
    await _like(session_factory, p_private["id"], user_l3)

    anon = await client.get("/feed/popular")
    assert anon.status_code == 200
    ids = [p["id"] for p in anon.json()]
    assert ids[0] == p_high["id"]
    assert p_private["id"] not in ids
    assert ids.index(p_high["id"]) < ids.index(p_low["id"])
    first = anon.json()[0]
    assert first["like_count"] == 2
    assert first["comment_count"] == 1

    author = await client.get("/feed/popular", headers=_h(token_pub))
    author_ids = [p["id"] for p in author.json()]
    assert author_ids[0] == p_high["id"]
    assert p_private["id"] in author_ids


async def test_popular_posts_limit(client, session_factory):
    token = await _register(client, "limitfeed")
    pub_id = await _user_id(session_factory, "limitfeed")
    other = await _register(client, "limitotro")
    other_id = await _user_id(session_factory, "limitotro")

    for i in range(4):
        post = await client.post(
            "/posts", json={"body": f"feed item {i}", "visibility": "PUBLIC"},
            headers=_h(token),
        )
        await _like(session_factory, post.json()["id"], other_id)

    resp = await client.get("/feed/popular?limit=2", headers=_h(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.get("/feed/popular?limit=0", headers=_h(token))
    assert resp.status_code == 422