"""Handlers de eventos que lanzan la consulta de disponibilidad al añadir
libros a la librería del usuario.

Cuando un usuario añade un libro a sus listas (manual o vía import de
Goodreads) se publica `shelves.user_book_status_changed`; este handler
dispara la consulta de disponibilidad contra los catálogos que usa el
usuario (z3950, ebiblio y todostuslibros). Los servicios de disponibilidad
ya cachean y persisten el resultado, así que aquí solo se orquesta la
llamada.

Sigue el patrón de `reviews/counters.py`: sesión propia y registro
idempotente vía `register()`.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Type

from app.adapters import eBiblioAdapter, TodostuslibrosAdapter, Z3950Adapter
from app.clients import eBiblioClient, TodostuslibrosClient, Z3950Client
from app.core.db import async_session as _default_session
from app.core.events import DomainEvent
from app.crud import AvailabilityRepository, BookRepository, CatalogRepository
from app.favorites.repository import FavoritesRepository
from app.services import EBiblioService, TodostuslibrosService, Z3950Service

logger = logging.getLogger(__name__)

_session_factory = _default_session

USER_BOOK_STATUS_CHANGED = "shelves.user_book_status_changed"

# Servicio -> (clase de servicio, clase de cliente, clase de adapter).
_SERVICES: dict[str, tuple[Type, Type, Type]] = {
    "z3950": (Z3950Service, Z3950Client, Z3950Adapter),
    "ebiblio": (EBiblioService, eBiblioClient, eBiblioAdapter),
    "todostuslibros": (TodostuslibrosService, TodostuslibrosClient, TodostuslibrosAdapter),
}


async def _query_availability_for_catalog(
    service_cls: Type,
    client_cls: Type,
    adapter_cls: Type,
    book_id: int,
    catalog_name: str,
) -> None:
    client = client_cls()
    async with _session_factory() as session:
        try:
            service = service_cls(
                BookRepository(session),
                AvailabilityRepository(session),
                CatalogRepository(session),
                client,
                adapter_cls(),
            )
            await service.get_availabity(book_id, catalog_name)
        finally:
            try:
                await client.close()
            except Exception:
                logger.exception("Error cerrando el cliente de disponibilidad")


async def _query_availability_for_user(user_id: str, book_id: int) -> None:
    async with _session_factory() as session:
        favorites = FavoritesRepository(session)
        catalogs = await favorites.list_user_catalogs(uuid.UUID(user_id))

    tasks = []
    for catalog in catalogs:
        spec = _SERVICES.get(catalog.service)
        if spec is None:
            continue
        tasks.append(
            _query_availability_for_catalog(*spec, book_id, catalog.name)
        )

    # todostuslibros es un catálogo global: se consulta siempre,
    # aunque el usuario no lo tenga añadido a sus catálogos.
    async with _session_factory() as session:
        catalog_repo = CatalogRepository(session)
        global_catalog = await catalog_repo.get_catalog_by_service("todostuslibros")
    if global_catalog is not None:
        spec = _SERVICES.get("todostuslibros")
        if spec is not None:
            tasks.append(
                _query_availability_for_catalog(*spec, book_id, global_catalog.name)
            )

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def on_user_book_status_changed(event: DomainEvent) -> None:
    try:
        await _query_availability_for_user(
            event.payload["user_id"], event.payload["book_id"]
        )
    except Exception:  # noqa: BLE001 - los handlers no deben romper el flujo
        logger.exception("user_book availability handler failed")


_registered = False


def register() -> None:
    """Registra el handler en el bus (idempotente)."""
    global _registered
    if _registered:
        return
    from app.core.events import event_bus

    event_bus.subscribe(USER_BOOK_STATUS_CHANGED, on_user_book_status_changed)
    _registered = True