"""Repositori per a operacions de favorits i catàlegs de l'usuari."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.enums import AvailabilityStatusEnum, EstablishmentTypeEnum, ReadingStatus
from app.favorites.models import (
    UserCatalog,
    UserFavoriteEstablishment,
    UserSearchHistory,
)
from app.models import Book, BookEstablishment, Catalog, Establishment, UserBook


class FavoritesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Catálogos del usuario ----------

    async def list_user_catalogs(self, user_id: uuid.UUID) -> list[Catalog]:
        stmt = (
            select(Catalog)
            .join(UserCatalog, UserCatalog.catalog_id == Catalog.id)
            .where(UserCatalog.user_id == user_id)
            .order_by(Catalog.service, Catalog.name)
        )
        return (await self.db.exec(stmt)).all()

    async def get_user_catalog(self, user_id: uuid.UUID, catalog_id: int) -> UserCatalog | None:
        stmt = select(UserCatalog).where(
            UserCatalog.user_id == user_id,
            UserCatalog.catalog_id == catalog_id,
        )
        return (await self.db.exec(stmt)).first()

    async def add_user_catalog(self, user_id: uuid.UUID, catalog_id: int) -> UserCatalog:
        row = UserCatalog(user_id=user_id, catalog_id=catalog_id)
        self.db.add(row)
        await self.db.flush()
        return row

    async def remove_user_catalog(self, row: UserCatalog) -> None:
        await self.db.delete(row)

    async def get_catalog(self, catalog_id: int) -> Catalog | None:
        return await self.db.get(Catalog, catalog_id)

    # ---------- Establecimientos favoritos ----------

    async def list_favorites(
        self,
        user_id: uuid.UUID,
        *,
        type: EstablishmentTypeEnum | list[EstablishmentTypeEnum] | None = None,
    ) -> list[Establishment]:
        stmt = (
            select(Establishment)
            .join(
                UserFavoriteEstablishment,
                UserFavoriteEstablishment.establishment_id == Establishment.id,
            )
            .where(UserFavoriteEstablishment.user_id == user_id)
        )
        if type is not None:
            types = [type] if isinstance(type, EstablishmentTypeEnum) else type
            stmt = stmt.where(Establishment.type.in_([t.value for t in types]))
        stmt = stmt.order_by(Establishment.name)
        return (await self.db.exec(stmt)).all()

    async def get_favorite(self, user_id: uuid.UUID, establishment_id: int) -> UserFavoriteEstablishment | None:
        stmt = select(UserFavoriteEstablishment).where(
            UserFavoriteEstablishment.user_id == user_id,
            UserFavoriteEstablishment.establishment_id == establishment_id,
        )
        return (await self.db.exec(stmt)).first()

    async def add_favorite(self, user_id: uuid.UUID, establishment_id: int) -> UserFavoriteEstablishment:
        row = UserFavoriteEstablishment(user_id=user_id, establishment_id=establishment_id)
        self.db.add(row)
        await self.db.flush()
        return row

    async def remove_favorite(self, row: UserFavoriteEstablishment) -> None:
        await self.db.delete(row)

    async def get_establishment(self, establishment_id: int) -> Establishment | None:
        return await self.db.get(Establishment, establishment_id)

    # ---------- Historial de búsquedas ----------

    async def record_search_click(
        self, user_id: uuid.UUID, book_id: int
    ) -> UserSearchHistory:
        """Registra un click sobre un libro; re-clickear refresca el timestamp."""
        stmt = select(UserSearchHistory).where(
            UserSearchHistory.user_id == user_id,
            UserSearchHistory.book_id == book_id,
        )
        row = (await self.db.exec(stmt)).first()
        if row is None:
            row = UserSearchHistory(user_id=user_id, book_id=book_id)
            self.db.add(row)
        else:
            row.clicked_at = utcnow()
        await self.db.flush()
        return row

    async def list_recent_search_books(
        self, user_id: uuid.UUID, limit: int = 5
    ) -> list[Book]:
        """Últimos libros clicados en búsquedas, más reciente primero."""
        stmt = (
            select(Book)
            .join(UserSearchHistory, UserSearchHistory.book_id == Book.id)
            .where(UserSearchHistory.user_id == user_id)
            .order_by(UserSearchHistory.clicked_at.desc())
            .limit(limit)
        )
        return (await self.db.exec(stmt)).all()

    async def clear_search_history(self, user_id: uuid.UUID) -> None:
        """Borra todo el historial de búsquedas del usuario."""
        stmt = delete(UserSearchHistory).where(UserSearchHistory.user_id == user_id)
        await self.db.exec(stmt)

    async def list_establishments(
        self,
        *,
        type: EstablishmentTypeEnum | None = None,
    ) -> list[Establishment]:
        stmt = select(Establishment)
        if type is not None:
            stmt = stmt.where(Establishment.type == type.value)
        stmt = stmt.order_by(Establishment.name)
        return (await self.db.exec(stmt)).all()

    # ---------- Home: estantes ----------

    async def list_reading_books(self, user_id: uuid.UUID) -> list[Book]:
        stmt = (
            select(Book)
            .join(UserBook, UserBook.book_id == Book.id)
            .where(UserBook.user_id == user_id, UserBook.status == ReadingStatus.READING)
            .order_by(UserBook.updated_at.desc())
        )
        return (await self.db.exec(stmt)).all()

    async def list_wtr_books_in_establishments(
        self,
        user_id: uuid.UUID,
        establishment_ids: list[int],
    ) -> list[Book]:
        """Libros WTR con disponibilidad AVAILABLE en los establecimientos dados."""
        if not establishment_ids:
            return []
        stmt = (
            select(Book)
            .join(UserBook, UserBook.book_id == Book.id)
            .join(BookEstablishment, BookEstablishment.book_id == Book.id)
            .where(
                UserBook.user_id == user_id,
                UserBook.status == ReadingStatus.WANT_TO_READ,
                BookEstablishment.establishment_id.in_(establishment_ids),
                BookEstablishment.status == AvailabilityStatusEnum.AVAILABLE,
            )
            .distinct()
        )
        return (await self.db.exec(stmt)).all()

    async def list_wtr_books_by_establishment(
        self,
        user_id: uuid.UUID,
        establishment_ids: list[int],
    ) -> dict[int, list[Book]]:
        """Libros WTR con disponibilidad AVAILABLE agrupados por establecimiento."""
        if not establishment_ids:
            return {}
        stmt = (
            select(Book, BookEstablishment.establishment_id)
            .join(UserBook, UserBook.book_id == Book.id)
            .join(BookEstablishment, BookEstablishment.book_id == Book.id)
            .where(
                UserBook.user_id == user_id,
                UserBook.status == ReadingStatus.WANT_TO_READ,
                BookEstablishment.establishment_id.in_(establishment_ids),
                BookEstablishment.status == AvailabilityStatusEnum.AVAILABLE,
            )
        )
        rows = (await self.db.exec(stmt)).all()
        grouped: dict[int, list[Book]] = {eid: [] for eid in establishment_ids}
        seen: set[tuple[int, int]] = set()
        for book, establishment_id in rows:
            key = (book.id, establishment_id)
            if key in seen:
                continue
            seen.add(key)
            grouped.setdefault(establishment_id, []).append(book)
        return grouped

    async def list_wtr_books_in_catalogs(
        self,
        user_id: uuid.UUID,
        catalog_ids: list[int],
    ) -> list[Book]:
        """Libros WTR con disponibilidad AVAILABLE en los catálogos dados."""
        if not catalog_ids:
            return []
        stmt = (
            select(Book)
            .join(UserBook, UserBook.book_id == Book.id)
            .join(BookEstablishment, BookEstablishment.book_id == Book.id)
            .join(Establishment, Establishment.id == BookEstablishment.establishment_id)
            .where(
                UserBook.user_id == user_id,
                UserBook.status == ReadingStatus.WANT_TO_READ,
                Establishment.catalog_id.in_(catalog_ids),
                BookEstablishment.status == AvailabilityStatusEnum.AVAILABLE,
            )
            .distinct()
        )
        return (await self.db.exec(stmt)).all()
