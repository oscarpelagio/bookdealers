"""Availability synchronization tasks"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.db import async_session
from app.crud import BookRepository, AvailabilityRepository, CatalogRepository
from app.services import EBiblioService, TodostuslibrosService, Z3950Service
from app.clients import eBiblioClient, TodostuslibrosClient, Z3950Client
from app.adapters import eBiblioAdapter, TodostuslibrosAdapter, Z3950Adapter

logger = logging.getLogger(__name__)


async def _run_sync(service_cls, client, adapter, days: int) -> dict:
    async with async_session() as session:
        try:
            book_repo = BookRepository(session)
            availability_repo = AvailabilityRepository(session)
            catalog_repo = CatalogRepository(session)
            service = service_cls(book_repo, availability_repo, catalog_repo, client, adapter)
            return await service.sync_outdated_availability(days)
        finally:
            try:
                await client.close()
            except Exception:
                logger.exception("Error closing HTTP client")


async def sync_ebiblio_job() -> None:
    try:
        result = await _run_sync(
            EBiblioService,
            eBiblioClient(),
            eBiblioAdapter(),
            settings.EBIBLIO_SYNC_DAYS,
        )
        logger.info("EBiblio sync finished: %s", result)
    except Exception:
        logger.exception("EBiblio sync error")


async def sync_todostuslibros_job() -> None:
    try:
        result = await _run_sync(
            TodostuslibrosService,
            TodostuslibrosClient(),
            TodostuslibrosAdapter(),
            settings.TODOSTUSLIBROS_SYNC_DAYS,
        )
        logger.info("Todostuslibros sync finished: %s", result)
    except Exception:
        logger.exception("Todostuslibros sync error")


async def sync_library_job() -> None:
    try:
        result = await _run_sync(
            Z3950Service,
            Z3950Client(),
            Z3950Adapter(),
            settings.LIBRARY_SYNC_DAYS,
        )
        logger.info("Z3950 sync finished: %s", result)
    except Exception:
        logger.exception("Z3950 sync error")
