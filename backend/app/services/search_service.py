"""Servei de lògica de negoci per als llibres."""

import logging, asyncio

from fastapi import UploadFile

from app.adapters import GoogleBooksAdapter
from app.clients import GoogleBooksClient
from app.crud import BookRepository, SearchRepository
from app.models import Book
from app.utils import CsvUtils

logger = logging.getLogger(__name__)

class SearchService:

    # Semáforo: máximo 1 llamada concurrente a Google Books API
    _google_semaphore = asyncio.Semaphore(1)
    _last_google_call: float = 0.0
    _min_interval: float = 1.0  # 1 segundo entre llamadas (~60/min, bajo el límite de 100/min)

    def __init__(
        self, 
        book_repo: BookRepository,
        search_repo: SearchRepository,
        client: GoogleBooksClient,
        adapter: GoogleBooksAdapter
        
    ):
        self.book_repository = book_repo
        self.search_repository = search_repo
        self.google_client = client
        self.google_adapter = adapter

    async def _rate_limited_search(self, search: str, max_results: int) -> dict:
        """
        Wrapper que garantiza máximo 1 llamada/segundo a Google Books API.
        """
        async with self._google_semaphore:
            loop = asyncio.get_event_loop()
            elapsed = loop.time() - SearchService._last_google_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)

            result = await self.google_client.search_books(search, max_results)
            SearchService._last_google_call = loop.time()
            return result

    async def search_and_process(self, title: str | None, author: str | None, max_results: int = 10) -> list[Book] :
        """
        Cerca llibres i els processa (fins a 10 resultats).
        """
        search = self.google_adapter.build_search(title, author)
        cached_books = await self.search_repository.check_cache(search)
        if cached_books:
            return cached_books
        results = await self._rate_limited_search(search, max_results)
        books = self.google_adapter.parse_books(results)
        saved_books = await self.book_repository.insert_books(books)
        await self.search_repository.save_cache(search, saved_books)
        return saved_books
    
    async def import_goodreads_csv(self, file: UploadFile) -> list[Book] :
        """
        Importa llibres des d'un CSV de Goodreads.
        El rate limiting es gestiona dins search_and_process via _rate_limited_search.
        """
        books = await CsvUtils.parse_goodreads_book(file)
        saved_books_list = []
        for book in books:
            title = book["title"]
            author = book["author"]
            try:
                saved_books = await self.search_and_process(title, author, 1)
                saved_books_list.extend(saved_books)
            except Exception as e:
                logger.error(f"Error processing '{title}' by '{author}': {e}")
                continue
        return saved_books_list
