"""API endpoints for Z39.50 Goodreads import."""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

from app.adapters import eBiblioAdapter, TodostuslibrosAdapter, Z3950Adapter
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.clients import eBiblioClient, TodostuslibrosClient, Z3950Client
from app.core.db import async_session
from app.crud import AvailabilityRepository, BookRepository, CatalogRepository
from app.enums import ReadingStatus
from app.favorites.dependencies import get_favorites_repository
from app.favorites.repository import FavoritesRepository
from app.router import get_z3950_import_service
from app.schemas import BookResponse
from app.services import EBiblioService, TodostuslibrosService, Z3950SearchService, Z3950Service
from app.shelves.dependencies import get_shelf_service
from app.shelves.service import ShelfService

logger = logging.getLogger(__name__)

router = APIRouter()

_GOODREADS_SHELF_TO_STATUS = {
    "to-read": ReadingStatus.WANT_TO_READ,
    "currently-reading": ReadingStatus.READING,
    "read": ReadingStatus.READ,
}


def _map_shelf_status(exclusive_shelf: str | None) -> ReadingStatus:
    """Mapea la columna 'Exclusive Shelf' de Goodreads a ReadingStatus."""
    if exclusive_shelf:
        status = _GOODREADS_SHELF_TO_STATUS.get(exclusive_shelf.strip().lower())
        if status is not None:
            return status
    return ReadingStatus.WANT_TO_READ


async def _launch_availability(
    book_ids: list[int],
    z3950_catalog: str,
    ebiblio_catalog: str | None,
) -> None:
    """Lanza la disponibilidad de los libros importados en z3950, todostuslibros
    y ebiblio (si el usuario tiene catálogo ebiblio configurado)."""
    async with async_session() as session:
        services: list[tuple[object, str, object]] = []
        try:
            clients = {
                "z3950": Z3950Client(),
                "todostuslibros": TodostuslibrosClient(),
            }
            services.append(
                (
                    Z3950Service(
                        BookRepository(session),
                        AvailabilityRepository(session),
                        CatalogRepository(session),
                        clients["z3950"],
                        Z3950Adapter(),
                    ),
                    z3950_catalog,
                    clients["z3950"],
                )
            )
            services.append(
                (
                    TodostuslibrosService(
                        BookRepository(session),
                        AvailabilityRepository(session),
                        CatalogRepository(session),
                        clients["todostuslibros"],
                        TodostuslibrosAdapter(),
                    ),
                    "todostuslibros",
                    clients["todostuslibros"],
                )
            )
            if ebiblio_catalog:
                clients["ebiblio"] = eBiblioClient()
                services.append(
                    (
                        EBiblioService(
                            BookRepository(session),
                            AvailabilityRepository(session),
                            CatalogRepository(session),
                            clients["ebiblio"],
                            eBiblioAdapter(),
                        ),
                        ebiblio_catalog,
                        clients["ebiblio"],
                    )
                )

            for book_id in book_ids:
                for service, catalog, _client in services:
                    try:
                        await service.get_availabity(book_id, catalog)
                    except Exception:
                        logger.exception(
                            "Disponibilidad fallida book_id=%s catalog=%s",
                            book_id,
                            catalog,
                        )
        finally:
            for client in clients.values():
                try:
                    await client.close()
                except Exception:
                    logger.exception("Error cerrando cliente HTTP")


@router.post("/goodreads-csv")
async def import_goodreads_csv(
    background_tasks: BackgroundTasks,
    csv_file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    z3950_search_service: Z3950SearchService = Depends(get_z3950_import_service),
    shelf_service: ShelfService = Depends(get_shelf_service),
    favorites_repo: FavoritesRepository = Depends(get_favorites_repository),
) -> list[BookResponse]:
    catalogs = await favorites_repo.list_user_catalogs(user.id)
    import_catalog = next(
        (c.name for c in catalogs if c.service == "z3950"), None
    )
    if import_catalog is None:
        raise ValueError("El usuario no tiene un catálogo z3950 configurado")
    imported = await z3950_search_service.import_goodreads_csv(csv_file, import_catalog)
    for entry in imported:
        await shelf_service.update_or_create_user_book(
            user,
            entry.book.id,
            status=_map_shelf_status(entry.exclusive_shelf),
        )
    if imported:
        ebiblio_catalog = next(
            (c.name for c in catalogs if c.service == "ebiblio"), None
        )
        background_tasks.add_task(
            _launch_availability,
            [entry.book.id for entry in imported],
            import_catalog,
            ebiblio_catalog,
        )
    return [entry.book for entry in imported]