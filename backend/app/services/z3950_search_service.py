"""Service for Z39.50 search."""

import asyncio
import logging
from dataclasses import dataclass

from fastapi import UploadFile

from app.adapters import Z3950SearchAdapter
from app.clients import SearchBaseClient
from app.crud import BookRepository, SearchRepository, CatalogRepository
from app.models import Book
from app.schemas import BookBase, BookResponse
from app.utils import CsvUtils, NormalizationUtils, dedupe_by_original_title_prefer_castellano, filter_and_sort_books, is_placeholder_cover

from .search_base_service import SearchBaseService

logger = logging.getLogger(__name__)


@dataclass
class ImportedGoodreadsBook:
    """Libro resuelto desde una fila del CSV de Goodreads.

    `exclusive_shelf` es el valor crudo de la columna "Exclusive Shelf"
    (to-read / currently-reading / read) para mapearlo a ReadingStatus.
    """

    book: Book
    exclusive_shelf: str | None = None


class Z3950SearchService(SearchBaseService):
    _semaphore = asyncio.Semaphore(1)
    _last_call: float = 0.0
    _min_interval: float = 0.5

    def __init__(
        self,
        book_repo: BookRepository,
        search_repo: SearchRepository,
        catalog_repo: CatalogRepository,
        client: SearchBaseClient,
        adapter: Z3950SearchAdapter,
    ):
        super().__init__(book_repo, search_repo, client, adapter)
        self.catalog_repository = catalog_repo

    async def search_and_process(
        self, title: str | None, author: str | None, catalog_name: str, max_results: int = 10
    ) -> list[BookResponse]:
        catalog = await self.catalog_repository.get_catalog(catalog_name)
        if not catalog:
            return []

        cache_key = f"z3950:{catalog_name}:{self._build_cache_key(title, author)}"
        cached_books = await self.search_repository.check_cache(cache_key, max_results)
        if cached_books:
            return cached_books

        params = self.adapter.build_search(title, author, catalog, max_results)
        results = await self._rate_limited_search(params)
        books = self.adapter.response_adapter(results)
        books = filter_and_sort_books(books, title, author, min_score=50)
        books = await self._strip_placeholder_covers(books)
        saved_books = await self.book_repository.insert_books(books)
        await self.search_repository.save_cache(cache_key, saved_books)
        return saved_books

    async def search_author_and_process(
        self, author: str, catalog_name: str, max_results: int = 40
    ) -> list[BookResponse]:
        catalog = await self.catalog_repository.get_catalog(catalog_name)
        if not catalog:
            return []

        cache_key = f"z3950-author:{catalog_name}:{self._build_cache_key(None, author)}"
        cached_books = await self.search_repository.check_cache(cache_key, max_results)
        if cached_books:
            return cached_books

        params = self.adapter.build_search(None, author, catalog, max_results)
        results = await self._rate_limited_author_search(params)
        books = self.adapter.response_adapter(results)
        books = filter_and_sort_books(books, None, author, min_score=50)
        books = dedupe_by_original_title_prefer_castellano(books)
        books = await self._strip_placeholder_covers(books)
        saved_books = await self.book_repository.insert_books(books)
        saved_books.sort(key=lambda b: b.holdings_count or 0, reverse=True)
        await self.search_repository.save_cache(cache_key, saved_books)
        return saved_books

    async def _strip_placeholder_covers(self, books: list[BookBase]) -> list[BookBase]:
        """Nulifica les portades de portadesbd que siguin placeholders (GIF)."""
        cover_urls = {book.thumbnail for book in books} | {
            book.small_thumbnail for book in books
        }
        if cover_urls == {None}:
            return books

        results = await asyncio.gather(*(is_placeholder_cover(url) for url in cover_urls))
        placeholder = dict(zip(cover_urls, results))
        for book in books:
            if placeholder.get(book.thumbnail):
                book.thumbnail = None
            if placeholder.get(book.small_thumbnail):
                book.small_thumbnail = None
        return books

    async def _rate_limited_author_search(self, params: dict) -> dict:
        cls = type(self)
        async with cls._semaphore:
            loop = asyncio.get_event_loop()
            elapsed = loop.time() - cls._last_call
            if elapsed < cls._min_interval:
                await asyncio.sleep(cls._min_interval - elapsed)
            result = await self.client.fetch_books_author(params)
            cls._last_call = loop.time()
            return result

    async def import_goodreads_csv(
        self, file: UploadFile, catalog_name: str
    ) -> list[ImportedGoodreadsBook]:
        """Import books from a Goodreads CSV export searching via Z39.50."""
        rows = await CsvUtils.parse_goodreads_book(file)
        saved_books_list: list[ImportedGoodreadsBook] = []
        for row in rows:
            title = row["title"]
            author = row["author"]
            shelf = row.get("exclusive_shelf") or None
            try:
                saved_books = await self.search_and_process(
                    title, author, catalog_name, max_results=1
                )
                if saved_books:
                    saved_books_list.append(
                        ImportedGoodreadsBook(book=saved_books[0], exclusive_shelf=shelf)
                    )
            except Exception as exc:
                logger.error("Error processing '%s' by '%s': %s", title, author, exc)
                continue
        return saved_books_list
