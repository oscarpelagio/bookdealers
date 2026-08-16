"""Repositorio de persistencia del módulo shelves.

Solo operaciones de base de datos; sin lógica de negocio.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.enums import ReadingStatus
from app.models import Book
from app.shelves.models import ReadingProgress, Shelf, ShelfItem, UserBook


class ShelfRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Shelf ----------

    async def get_by_id(self, shelf_id: uuid.UUID) -> Shelf | None:
        return await self.db.get(Shelf, shelf_id)

    async def get_by_user_slug(self, user_id: uuid.UUID, slug: str) -> Shelf | None:
        stmt = select(Shelf).where(Shelf.user_id == user_id, Shelf.slug == slug)
        return (await self.db.exec(stmt)).first()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Shelf]:
        stmt = (
            select(Shelf)
            .where(Shelf.user_id == user_id)
            .order_by(Shelf.kind, Shelf.position)
        )
        return (await self.db.exec(stmt)).all()

    async def create_shelf(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        slug: str,
        kind,
        position: int,
        is_default: bool = False,
        is_private: bool = False,
        description: str | None = None,
    ) -> Shelf:
        shelf = Shelf(
            user_id=user_id,
            name=name,
            slug=slug,
            kind=kind,
            position=position,
            is_default=is_default,
            is_private=is_private,
            description=description,
        )
        self.db.add(shelf)
        return shelf

    async def update_shelf(self, shelf: Shelf, *, fields: dict) -> Shelf:
        for key, value in fields.items():
            if value is not None:
                setattr(shelf, key, value)
        shelf.updated_at = utcnow()
        self.db.add(shelf)
        return shelf

    async def delete_shelf(self, shelf: Shelf) -> None:
        await self.db.delete(shelf)

    # ---------- ShelfItem (solo custom) ----------

    async def get_item(
        self, user_id: uuid.UUID, shelf_id: uuid.UUID, book_id: int
    ) -> ShelfItem | None:
        stmt = select(ShelfItem).where(
            ShelfItem.user_id == user_id,
            ShelfItem.shelf_id == shelf_id,
            ShelfItem.book_id == book_id,
        )
        return (await self.db.exec(stmt)).first()

    async def list_item_book_ids(self, shelf_id: uuid.UUID) -> list[int]:
        stmt = select(ShelfItem.book_id).where(ShelfItem.shelf_id == shelf_id)
        return (await self.db.exec(stmt)).all()

    async def count_items(self, shelf_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ShelfItem)
            .where(ShelfItem.shelf_id == shelf_id)
        )
        return (await self.db.exec(stmt)).one()

    async def create_item(
        self, user_id: uuid.UUID, shelf_id: uuid.UUID, book_id: int
    ) -> ShelfItem:
        item = ShelfItem(user_id=user_id, shelf_id=shelf_id, book_id=book_id)
        self.db.add(item)
        return item

    async def delete_item(self, item: ShelfItem) -> None:
        await self.db.delete(item)

    # ---------- UserBook ----------

    async def get_user_book(
        self, user_id: uuid.UUID, book_id: int
    ) -> UserBook | None:
        stmt = select(UserBook).where(
            UserBook.user_id == user_id, UserBook.book_id == book_id
        )
        return (await self.db.exec(stmt)).first()

    async def get_user_book_by_id(self, user_book_id: uuid.UUID) -> UserBook | None:
        return await self.db.get(UserBook, user_book_id)

    async def list_user_books(
        self, user_id: uuid.UUID, status: ReadingStatus | None = None
    ) -> list[UserBook]:
        stmt = select(UserBook).where(UserBook.user_id == user_id)
        if status is not None:
            stmt = stmt.where(UserBook.status == status)
        stmt = stmt.order_by(UserBook.updated_at.desc())
        return (await self.db.exec(stmt)).all()

    async def count_by_status(self, user_id: uuid.UUID, status: ReadingStatus) -> int:
        stmt = (
            select(func.count())
            .select_from(UserBook)
            .where(UserBook.user_id == user_id, UserBook.status == status)
        )
        return (await self.db.exec(stmt)).one()

    async def count_by_statuses(
        self, user_id: uuid.UUID
    ) -> dict[ReadingStatus, int]:
        """Conteo por estado en una sola query (evita N+1)."""
        stmt = (
            select(UserBook.status, func.count())
            .where(UserBook.user_id == user_id)
            .group_by(UserBook.status)
        )
        return {status: count for status, count in (await self.db.exec(stmt)).all()}

    async def count_items_by_shelf_ids(
        self, shelf_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not shelf_ids:
            return {}
        stmt = (
            select(ShelfItem.shelf_id, func.count())
            .where(ShelfItem.shelf_id.in_(shelf_ids))
            .group_by(ShelfItem.shelf_id)
        )
        rows = (await self.db.exec(stmt)).all()
        return {shelf_id: count for shelf_id, count in rows}

    async def create_user_book(
        self,
        *,
        user_id: uuid.UUID,
        book_id: int,
        status: ReadingStatus,
        started_at=None,
        finished_at=None,
        notes: str | None = None,
    ) -> UserBook:
        ub = UserBook(
            user_id=user_id,
            book_id=book_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            notes=notes,
        )
        self.db.add(ub)
        return ub

    async def update_user_book(self, ub: UserBook, *, fields: dict) -> UserBook:
        for key, value in fields.items():
            if value is not None:
                setattr(ub, key, value)
        ub.updated_at = utcnow()
        self.db.add(ub)
        return ub

    async def delete_user_book(self, ub: UserBook) -> None:
        await self.db.delete(ub)

    # ---------- ReadingProgress ----------

    async def create_progress(
        self,
        user_book_id: uuid.UUID,
        *,
        page: int | None,
        percent_read,
        note: str | None,
    ) -> ReadingProgress:
        rp = ReadingProgress(
            user_book_id=user_book_id,
            page=page,
            percent_read=percent_read,
            note=note,
        )
        self.db.add(rp)
        return rp

    async def list_progress(
        self, user_book_id: uuid.UUID, *, limit: int = 20
    ) -> list[ReadingProgress]:
        stmt = (
            select(ReadingProgress)
            .where(ReadingProgress.user_book_id == user_book_id)
            .order_by(ReadingProgress.created_at.desc())
            .limit(limit)
        )
        return (await self.db.exec(stmt)).all()

    # ---------- Book ----------

    async def get_book(self, book_id: int) -> Book | None:
        return await self.db.get(Book, book_id)

    async def get_books_by_ids(self, ids: list[int]) -> dict[int, Book]:
        if not ids:
            return {}
        stmt = select(Book).where(Book.id.in_(ids))
        return {b.id: b for b in (await self.db.exec(stmt)).all()}

    # ---------- Relaciones sociales para visibilidad (ADR-4) ----------

    async def get_follow(
        self, follower_id: uuid.UUID, followee_id: uuid.UUID
    ) -> Follow | None:
        from sqlalchemy import select as _select

        from app.social.models import Follow as FollowModel

        stmt = _select(FollowModel).where(
            FollowModel.follower_id == follower_id,
            FollowModel.followee_id == followee_id,
        )
        return (await self.db.exec(stmt)).first()

    async def get_block_relation(self, a: uuid.UUID, b: uuid.UUID) -> Block | None:
        from sqlalchemy import or_ as _or_
        from sqlalchemy import select as _select

        from app.social.models import Block as BlockModel

        stmt = _select(BlockModel).where(
            _or_(
                (BlockModel.blocker_id == a) & (BlockModel.blocked_id == b),
                (BlockModel.blocker_id == b) & (BlockModel.blocked_id == a),
            )
        )
        return (await self.db.exec(stmt)).first()