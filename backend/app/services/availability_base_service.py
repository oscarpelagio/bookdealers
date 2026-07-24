"""
Basic service for consultation
"""

from abc import ABC
import asyncio
import logging

from app.adapters import AvailabilityBaseAdapter
from app.clients import AvailabilityBaseClient
from app.crud import BookRepository, AvailabilityRepository, CatalogRepository

logger = logging.getLogger(__name__)

class AvailabilityBaseService(ABC):
    SERVICE_NAME: str = ""
    _semaphore = asyncio.Semaphore(1)

    def __init__(
        self, 
        book_repo: BookRepository,
        availability_repo: AvailabilityRepository,
        catalog_repo: CatalogRepository,
        client: AvailabilityBaseClient,
        adapter: AvailabilityBaseAdapter
        
    ):
        self.book_repository = book_repo
        self.availability_repository = availability_repo
        self.catalog_repository = catalog_repo
        self.client = client
        self.adapter = adapter

    async def get_availabity(self, book_id: int, catalog: str):
        book = await self.book_repository.get_by_id(book_id)
        catalog = await self.catalog_repository.get_catalog(catalog)

        if not book or not catalog:
            return []

        cached = await self.availability_repository.get_availability(book, catalog)
        if cached:
            return cached

        search_request = self.adapter.build_search(book, catalog)
        
        try:
            async with self._semaphore:
                respuesta = await self.client.fetch_books(search_request)
            availability = self.adapter.response_adapter(book, catalog, respuesta)
            if availability:
                await self.availability_repository.save_availability(availability)
                return availability
        except Exception as e:
            logger.exception("Error en la llamada externa: %s", e)
            return []

    async def sync_outdated_availability(self, days: int) -> dict:
        """
        Sincronitza disponibilitats caducades per servei.
        Continua si algun registre falla.
        """
        if days <= 0:
            return {"total": 0, "updated": 0, "failed": 0}

        if not self.SERVICE_NAME:
            logger.warning("SERVICE_NAME no configurat per %s", self.__class__.__name__)
            return {"total": 0, "updated": 0, "failed": 0}

        outdated_pairs = await self.availability_repository.get_outdated_availability(
            days=days,
            service=self.SERVICE_NAME,
        )

        total = len(outdated_pairs)
        updated = 0
        failed = 0

        for book_id, catalog_name in outdated_pairs:
            try:
                await self.get_availabity(book_id, catalog_name)
                updated += 1
            except Exception:
                failed += 1
                logger.exception(
                    "Error sincronizando book_id=%s catalog=%s",
                    book_id,
                    catalog_name,
                )
                continue

        return {"total": total, "updated": updated, "failed": failed}
