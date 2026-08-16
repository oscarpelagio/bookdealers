"""Importa el CSV de Goodreads para la cuenta admin i crea les relacions
user_books (our library/shelves) amb l'estat mapejat des de l'exclusive shelf.

Replica exactament el wiring de l'endpoint POST /goodreads-csv però amb
l'usuari admin, garantint que els llibres importats queden lligats a la
seva biblioteca personal.

Ús (des del contenidor del backend):
    docker cp goodreads_library_export.csv back:/tmp/goodreads_library_export.csv
    docker compose exec -T back python scripts/import_goodreads_admin.py
"""

import asyncio
import io

from fastapi import UploadFile
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters import Z3950SearchAdapter
from app.auth.models import User
from app.clients import Z3950ImportClient
from app.core.db import async_engine
from app.crud import BookRepository, SearchRepository, CatalogRepository
from app.enums import ReadingStatus
from app.favorites.repository import FavoritesRepository
from app.models import UserBook
from app.shelves.availability_handler import (
    _query_availability_for_user,
)
from app.shelves.repository import ShelfRepository
from app.shelves.service import ShelfService
from app.services import Z3950SearchService
from app.utils import CsvUtils

ADMIN_EMAIL = "admin@example.com"
CSV_PATH = "/tmp/goodreads_library_export.csv"

_GOODREADS_SHELF_TO_STATUS = {
    "to-read": ReadingStatus.WANT_TO_READ,
    "currently-reading": ReadingStatus.READING,
    "read": ReadingStatus.READ,
}


def _map_shelf_status(exclusive_shelf: str | None) -> ReadingStatus:
    if exclusive_shelf:
        status = _GOODREADS_SHELF_TO_STATUS.get(exclusive_shelf.strip().lower())
        if status is not None:
            return status
    return ReadingStatus.WANT_TO_READ


async def main() -> None:
    with open(CSV_PATH, "rb") as f:
        data = f.read()
    upload = UploadFile(file=io.BytesIO(data), filename="goodreads_library_export.csv")

    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        admin = (
            await db.exec(select(User).where(User.email == ADMIN_EMAIL))
        ).first()
        if admin is None:
            raise SystemExit(f"No existeix l'usuari {ADMIN_EMAIL}")

        catalogs = await FavoritesRepository(db).list_user_catalogs(admin.id)
        import_catalog = next(
            (c.name for c in catalogs if c.service == "z3950"), None
        )
        if import_catalog is None:
            raise SystemExit("L'admin no té cap catàleg z3950 configurat")
        print(f"Catàleg d'importació: {import_catalog}")

        service = Z3950SearchService(
            BookRepository(db),
            SearchRepository(db),
            CatalogRepository(db),
            Z3950ImportClient(),
            Z3950SearchAdapter(),
        )
        shelf_service = ShelfService(ShelfRepository(db), db)
        await shelf_service.list_shelves(admin)

        rows = await CsvUtils.parse_goodreads_book(upload)
        imported = []
        errors = []
        for row in rows:
            title = row["title"]
            author = row["author"]
            shelf = row.get("exclusive_shelf") or None
            try:
                saved = await service.search_and_process(
                    title, author, import_catalog, max_results=1
                )
                if not saved:
                    continue
                status = await shelf_service.update_or_create_user_book(
                    admin, saved[0].id, status=_map_shelf_status(shelf)
                )
                imported.append((saved[0], shelf, status))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{title} -> {type(exc).__name__}: {exc}")

        print(f"== IMPORTADOS {len(imported)} de {len(rows)} ==")
        for book, shelf, status in imported:
            print(f"- {book.id} | [{status.status.value}] {book.title} | {book.author} | shelf: {shelf}")
        if errors:
            print("\n== ERRORES ==")
            for err in errors:
                print(" ", err)

        # Disparo manual de disponibilidad para los libros importados: el
        # handler de eventos solo se registra al arrancar FastAPI (vía
        # app.shelves.dependencies), así que en un script hay que invocarlo
        # directamente para los 3 servicios (z3950/ebiblio/todostuslibros).
        print("\n== CONSULTANDO DISPONIBILIDAD (3 servicios) ==")
        avail_ok, avail_fail = [], []
        for book, _shelf, _status in imported:
            try:
                await _query_availability_for_user(str(admin.id), book.id)
                avail_ok.append(book.id)
            except Exception as exc:  # noqa: BLE001
                avail_fail.append(f"{book.id} -> {type(exc).__name__}: {exc}")
        print(f"Disponibilidad consultada: {len(avail_ok)} | fallos: {len(avail_fail)}")
        for line in avail_fail:
            print(" ", line)

        from app.models import UserBook

        n = len(
            (
                await db.exec(
                    select(UserBook).where(UserBook.user_id == admin.id)
                )
            ).all()
        )
        print(f"\nTotal user_books de l'admin: {n}")


if __name__ == "__main__":
    asyncio.run(main())