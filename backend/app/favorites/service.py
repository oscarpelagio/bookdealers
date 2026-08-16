"""Servei de favorits i catàlegs de l'usuari (lògica de negoci)."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.enums import EstablishmentTypeEnum
from app.favorites.repository import FavoritesRepository
from app.favorites.schemas import (
    CatalogResponse,
    EstablishmentResponse,
    HomeResponse,
    HomeShelf,
    LibrariesResponse,
    LibraryShelf,
)
from app.shelves.schemas import BookBrief

LIBRARY_SHELF = "WTR_LIBRARIES"
EBIBLIO_SHELF = "WTR_EBIBLIO"
BOOKSTORE_SHELF = "WTR_BOOKSTORES"


def _book_brief(book, establishment_name: str | None = None) -> BookBrief:
    return BookBrief(
        id=book.id,
        title=book.title,
        author=book.author,
        thumbnail=book.thumbnail,
        page_count=book.page_count,
        language=book.language,
        establishment_name=establishment_name,
        price=float(book.price) if getattr(book, "price", None) is not None else None,
    )


def _catalog_response(catalog) -> CatalogResponse:
    return CatalogResponse(
        id=catalog.id,
        service=catalog.service,
        name=catalog.name,
        url=catalog.url,
    )


def _establishment_response(establishment, favorite: bool = True) -> EstablishmentResponse:
    return EstablishmentResponse(
        id=establishment.id,
        type=establishment.type,
        name=establishment.name,
        street=establishment.street,
        postal_code=establishment.postal_code,
        city=establishment.city,
        province=establishment.province,
        catalog_id=establishment.catalog_id,
        favorite=favorite,
    )


class FavoritesService:
    def __init__(self, repo: FavoritesRepository, db: AsyncSession):
        self.repo = repo
        self.db = db

    # ---------- Catálogos del usuario ----------

    async def list_catalogs(self, user) -> list[CatalogResponse]:
        catalogs = await self.repo.list_user_catalogs(user.id)
        return [_catalog_response(c) for c in catalogs]

    async def add_catalog(self, user, catalog_id: int) -> CatalogResponse:
        catalog = await self.repo.get_catalog(catalog_id)
        if catalog is None:
            raise ValueError("catalog_not_found")
        existing = await self.repo.get_user_catalog(user.id, catalog_id)
        if existing is not None:
            return _catalog_response(catalog)
        try:
            await self.repo.add_user_catalog(user.id, catalog_id)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
        return _catalog_response(catalog)

    async def remove_catalog(self, user, catalog_id: int) -> None:
        row = await self.repo.get_user_catalog(user.id, catalog_id)
        if row is not None:
            await self.repo.remove_user_catalog(row)
            await self.db.commit()

    # ---------- Establecimientos favoritos ----------

    async def list_favorites(
        self,
        user,
        type: EstablishmentTypeEnum | None = None,
    ) -> list[EstablishmentResponse]:
        favorites = await self.repo.list_favorites(user.id, type=type)
        return [_establishment_response(e) for e in favorites]

    async def list_establishments(
        self,
        user,
        type: EstablishmentTypeEnum | None = None,
    ) -> list[EstablishmentResponse]:
        """Todos los establecimientos del tipo dado, marcando los favoritos del usuario."""
        establishments = await self.repo.list_establishments(type=type)
        favorite_ids = {
            e.id for e in await self.repo.list_favorites(user.id, type=type)
        }
        return [
            _establishment_response(e, favorite=e.id in favorite_ids)
            for e in establishments
        ]

    async def add_favorite(self, user, establishment_id: int) -> EstablishmentResponse:
        establishment = await self.repo.get_establishment(establishment_id)
        if establishment is None:
            raise ValueError("establishment_not_found")
        existing = await self.repo.get_favorite(user.id, establishment_id)
        if existing is None:
            try:
                await self.repo.add_favorite(user.id, establishment_id)
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
        return _establishment_response(establishment)

    async def remove_favorite(self, user, establishment_id: int) -> None:
        row = await self.repo.get_favorite(user.id, establishment_id)
        if row is not None:
            await self.repo.remove_favorite(row)
            await self.db.commit()

    # ---------- Home: estantes ----------

    async def get_libraries(self, user) -> LibrariesResponse:
        """Bibliotecas favoritas, cada una con los libros disponibles en ella."""
        library_favs = await self.repo.list_favorites(
            user.id, type=EstablishmentTypeEnum.LIBRARY
        )
        grouped = await self.repo.list_wtr_books_by_establishment(
            user.id, [e.id for e in library_favs]
        )
        return LibrariesResponse(
            shelves=[
                LibraryShelf(
                    establishment=_establishment_response(e),
                    books=[_book_brief(b) for b in grouped.get(e.id, [])],
                )
                for e in library_favs
            ]
        )

    async def get_home(self, user) -> HomeResponse:
        catalogs = await self.repo.list_user_catalogs(user.id)

        library_catalog_ids = [c.id for c in catalogs if c.service == "z3950"]
        ebiblio_catalog_ids = [c.id for c in catalogs if c.service == "ebiblio"]

        library_favs = await self.repo.list_favorites(
            user.id, type=EstablishmentTypeEnum.LIBRARY
        )
        bookstore_favs = await self.repo.list_favorites(
            user.id, type=EstablishmentTypeEnum.BOOK_SHOP
        )

        reading = await self.repo.list_reading_books(user.id)
        wtr_ebiblio = await self.repo.list_wtr_books_in_catalogs(
            user.id, ebiblio_catalog_ids
        )
        wtr_bookstores = await self.repo.list_wtr_books_in_establishments(
            user.id, [e.id for e in bookstore_favs]
        )

        libraries_grouped = await self.repo.list_wtr_books_by_establishment(
            user.id, [e.id for e in library_favs]
        )
        wtr_libraries = [
            _book_brief(book, establishment_name=e.name)
            for e in library_favs
            for book in libraries_grouped.get(e.id, [])
        ]

        return HomeResponse(
            shelves=[
                HomeShelf(
                    key="READING",
                    title="Leyendo",
                    books=[_book_brief(b) for b in reading],
                ),
                HomeShelf(
                    key=LIBRARY_SHELF,
                    title="Disponible en bibliotecas cerca de ti",
                    books=wtr_libraries,
                ),
                HomeShelf(
                    key=EBIBLIO_SHELF,
                    title="Disponible en eBiblio",
                    books=[_book_brief(b) for b in wtr_ebiblio],
                ),
                HomeShelf(
                    key=BOOKSTORE_SHELF,
                    title="Disponible en librerías cercanas",
                    books=[_book_brief(b) for b in wtr_bookstores],
                ),
            ]
        )

    # ---------- Historial de búsquedas ----------

    async def record_search_click(self, user, book_id: int) -> None:
        """Guarda un click sobre un libro de búsqueda."""
        try:
            await self.repo.record_search_click(user.id, book_id)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()

    async def list_recent_searches(self, user, limit: int = 5) -> list[BookBrief]:
        """Últimos libros clicados en búsquedas (máx. `limit`)."""
        books = await self.repo.list_recent_search_books(user.id, limit=limit)
        return [_book_brief(b) for b in books]

    async def clear_search_history(self, user) -> None:
        """Borra todo el historial de búsquedas del usuario."""
        await self.repo.clear_search_history(user.id)
        await self.db.commit()
