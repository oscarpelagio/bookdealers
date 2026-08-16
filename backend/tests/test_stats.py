"""Tests del módulo stats (FASE 9).

Estadísticas derivadas de `user_books` + `ratings` + `reading_goals`:
libros leídos, páginas, avg rating, mejor género, racha y progreso del
goal anual. Sin tablas propias.
"""

import datetime
import uuid as _uuid

from tests.conftest import random_email, valid_password


async def _register_and_token(client, username: str) -> str:
    payload = {
        "email": random_email(),
        "username": username,
        "password": valid_password(),
        "full_name": "Stats User",
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
    session_factory, *, categories: str = "Fiction", page_count: int = 200
) -> int:
    from app.models import Book

    suffix = _uuid.uuid4().hex[:8]
    data = dict(
        title=f"Llibre stat {suffix}",
        author=f"Autora {suffix}",
        language="es",
        normal_title=f"llibre stat {suffix}",
        normal_author=f"autora {suffix}",
        categories=categories,
        page_count=page_count,
    )
    async with session_factory() as session:
        book = Book(**data)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book.id


async def _mark_read(
    session_factory, user_id, book_id, *, finished_at, started_at=None
) -> None:
    from app.enums import ReadingStatus
    from app.shelves.models import UserBook

    async with session_factory() as session:
        ub = UserBook(
            user_id=user_id,
            book_id=book_id,
            status=ReadingStatus.READ,
            started_at=started_at or finished_at,
            finished_at=finished_at,
        )
        session.add(ub)
        await session.commit()


async def _rate(
    session_factory, user_id, book_id: int, score: int
) -> None:
    import datetime as _dt
    import uuid

    from app.reviews.models import Rating

    now = _dt.datetime.now(_dt.timezone.utc)
    async with session_factory() as session:
        rating = Rating(
            user_id=user_id,
            book_id=book_id,
            score=score,
            created_at=now,
            updated_at=now,
        )
        session.add(rating)
        await session.commit()


async def _user_id(session_factory, handle: str):
    from app.auth.models import User
    from sqlmodel import select

    async with session_factory() as session:
        user = (await session.exec(select(User).where(User.username == handle))).first()
        return user.id


async def test_empty_stats(client):
    token = await _register_and_token(client, "statsanon")
    resp = await client.get("/users/statsanon/stats", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == datetime.date.today().year
    assert data["books_read"] == 0
    assert data["pages_read"] == 0
    assert data["avg_rating"] is None
    assert data["top_genre"] is None
    assert data["streak_days"] == 0
    assert data["books_total"] == 0
    assert data["goal"] is None


async def test_stats_computed_for_year(client, session_factory):
    token = await _register_and_token(client, "leecora")
    user_id = await _user_id(session_factory, "leecora")

    b1 = await _create_book(session_factory, categories="Fiction", page_count=200)
    b2 = await _create_book(session_factory, categories="Fiction", page_count=300)
    b3 = await _create_book(
        session_factory, categories="Science Fiction", page_count=400
    )
    b_old = await _create_book(session_factory, categories="Fiction", page_count=999)

    for b, day in ((b1, 10), (b2, 11), (b3, 12)):
        await _mark_read(
            session_factory, user_id, b, finished_at=datetime.date(2025, 3, day)
        )
    await _mark_read(
        session_factory, user_id, b_old, finished_at=datetime.date(2024, 3, 12)
    )

    await _rate(session_factory, user_id, b1, 4)
    await _rate(session_factory, user_id, b2, 5)
    await _rate(session_factory, user_id, b3, 3)

    resp = await client.get("/users/leecora/stats?year=2025", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2025
    assert data["books_read"] == 3
    assert data["pages_read"] == 900
    assert data["avg_rating"] == 4.0
    assert data["top_genre"] == "Fiction"
    assert data["streak_days"] == 3
    assert data["books_total"] == 4  # incluye el libro leído en 2024


async def test_stats_year_filter_excludes_other_years(client, session_factory):
    token = await _register_and_token(client, "filternos")
    user_id = await _user_id(session_factory, "filternos")

    b_a = await _create_book(session_factory)
    b_b = await _create_book(session_factory)
    await _mark_read(
        session_factory, user_id, b_a, finished_at=datetime.date(2025, 6, 1)
    )
    await _mark_read(
        session_factory, user_id, b_b, finished_at=datetime.date(2025, 6, 2)
    )

    resp = await client.get("/users/filternos/stats?year=2025", headers=_h(token))
    assert resp.status_code == 200
    assert resp.json()["books_read"] == 2

    resp = await client.get("/users/filternos/stats?year=2024", headers=_h(token))
    assert resp.status_code == 200
    assert resp.json()["books_read"] == 0


async def test_stats_goal_progress(client, session_factory):
    token = await _register_and_token(client, "objectius")
    user_id = await _user_id(session_factory, "objectius")

    for _ in range(2):
        bid = await _create_book(session_factory, page_count=200)
        await _mark_read(
            session_factory, user_id, bid, finished_at=datetime.date(2026, 3, 1)
        )

    goal = await client.put(
        "/profiles/me/goals/2026",
        json={"year": 2026, "books_goal": 8, "pages_goal": 800},
        headers=_h(token),
    )
    assert goal.status_code == 200, goal.text

    resp = await client.get("/users/objectius/stats", headers=_h(token))
    assert resp.status_code == 200
    goal_data = resp.json()["goal"]
    assert goal_data["books_read"] == 2
    assert goal_data["books_goal"] == 8
    assert goal_data["books_progress_pct"] == 25.0
    assert goal_data["pages_read"] == 400
    assert goal_data["pages_progress_pct"] == 50.0


async def test_stats_year_out_of_range_validation(client):
    token = await _register_and_token(client, "validano")
    resp = await client.get("/users/validano/stats?year=1999", headers=_h(token))
    assert resp.status_code == 422
    resp = await client.get("/users/validano/stats?year=3000", headers=_h(token))
    assert resp.status_code == 422


async def test_stats_private_library(client, session_factory):
    token = await _register_and_token(client, "privadas")
    user_id = await _user_id(session_factory, "privadas")

    bid = await _create_book(session_factory)
    await _mark_read(
        session_factory, user_id, bid, finished_at=datetime.date(2026, 1, 10)
    )

    privacy = await client.patch(
        "/profiles/me/privacy",
        json={"library_visibility": "PRIVATE"},
        headers=_h(token),
    )
    assert privacy.status_code == 200, privacy.text

    anon = await client.get("/users/privadas/stats?year=2026")
    assert anon.status_code == 403
    assert anon.json()["error"] == "stats_private"

    other = await _register_and_token(client, "lallavista")
    resp = await client.get(
        "/users/privadas/stats?year=2026", headers=_h(other)
    )
    assert resp.status_code == 403

    own = await client.get("/users/privadas/stats?year=2026", headers=_h(token))
    assert own.status_code == 200


async def test_stats_user_not_found(client):
    token = await _register_and_token(client, "nadiex")
    resp = await client.get("/users/noexistejo/stats", headers=_h(token))
    assert resp.status_code == 404