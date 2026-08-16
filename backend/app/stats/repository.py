"""Repositorio de persistencia del módulo stats.

Solo lecturas sobre datos de F2/F3/F1; sin lógica de negocio.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.enums import ReadingStatus
from app.models import Book
from app.reviews.models import Rating
from app.shelves.models import UserBook


class StatsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Usuarios / visibilidad ----------

    async def get_user_by_handle(self, handle: str) -> User | None:
        stmt = select(User).where(User.username == handle)
        return (await self.db.exec(stmt)).first()

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_privacy(self, user_id: uuid.UUID):
        from app.profiles.models import PrivacySetting

        stmt = select(PrivacySetting).where(PrivacySetting.user_id == user_id)
        return (await self.db.exec(stmt)).first()

    async def get_follow(self, follower_id: uuid.UUID, followee_id: uuid.UUID):
        from app.social.models import Follow

        stmt = select(Follow).where(
            Follow.follower_id == follower_id, Follow.followee_id == followee_id
        )
        return (await self.db.exec(stmt)).first()

    async def get_block_relation(self, a: uuid.UUID, b: uuid.UUID):
        from sqlalchemy import or_

        from app.social.models import Block

        stmt = select(Block).where(
            or_(
                (Block.blocker_id == a) & (Block.blocked_id == b),
                (Block.blocker_id == b) & (Block.blocked_id == a),
            )
        )
        return (await self.db.exec(stmt)).first()

    # ---------- Lectura (datos de stats) ----------

    async def read_books_in_year(
        self, user_id: uuid.UUID, year: int
    ) -> list[tuple[UserBook, Book]]:
        """UserBooks marcados como leídos y terminados en `year`, con su libro."""
        stmt = (
            select(UserBook, Book)
            .join(Book, Book.id == UserBook.book_id)
            .where(
                UserBook.user_id == user_id,
                UserBook.status == ReadingStatus.READ,
                UserBook.finished_at.isnot(None),
                func.extract("year", UserBook.finished_at) == year,
            )
        )
        rows = (await self.db.exec(stmt)).all()
        return [(ub, book) for ub, book in rows]

    async def finished_dates(self, user_id: uuid.UUID) -> list[date]:
        """Fechas `finished_at` de lecturas terminadas, para calcular la racha."""
        stmt = (
            select(UserBook.finished_at)
            .where(
                UserBook.user_id == user_id,
                UserBook.status == ReadingStatus.READ,
                UserBook.finished_at.isnot(None),
            )
        )
        return [row for row in (await self.db.exec(stmt)).all()]

    async def count_books(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            UserBook.user_id == user_id,
            UserBook.status == ReadingStatus.READ,
        )
        return (await self.db.exec(stmt)).one()

    async def get_ratings(
        self, user_id: uuid.UUID, book_ids: list[int]
    ) -> dict[int, int]:
        if not book_ids:
            return {}
        stmt = (
            select(Rating.book_id, Rating.score)
            .where(Rating.user_id == user_id, Rating.book_id.in_(book_ids))
        )
        rows = (await self.db.exec(stmt)).all()
        return {book_id: score for book_id, score in rows}

    async def get_goal(self, user_id: uuid.UUID, year: int):
        from app.profiles.models import ReadingGoal

        stmt = select(ReadingGoal).where(
            ReadingGoal.user_id == user_id, ReadingGoal.year == year
        )
        return (await self.db.exec(stmt)).first()