"""Base service for external book search providers."""

import asyncio
from abc import ABC
from typing import Protocol

from app.adapters import SearchBaseAdapter
from app.crud import BookRepository, SearchRepository
from app.schemas import BookResponse


class SearchClient(Protocol):
    async def fetch_books(self, params: dict) -> dict:
        """Fetch raw data from the external provider."""
        raise NotImplementedError


class SearchBaseService(ABC):
    _semaphore: asyncio.Semaphore = asyncio.Semaphore(1)
    _last_call: float = 0.0
    _min_interval: float = 0.0

    def __init__(
        self,
        book_repo: BookRepository,
        search_repo: SearchRepository,
        client: SearchClient,
        adapter: SearchBaseAdapter,
    ):
        self.book_repository = book_repo
        self.search_repository = search_repo
        self.client = client
        self.adapter = adapter

    async def _rate_limited_search(self, params: dict) -> dict:
        cls = type(self)
        async with cls._semaphore:
            loop = asyncio.get_event_loop()
            elapsed = loop.time() - cls._last_call
            if elapsed < cls._min_interval:
                await asyncio.sleep(cls._min_interval - elapsed)

            result = await self.client.fetch_books(params)
            cls._last_call = loop.time()
            return result

    async def search_and_process(
        self, title: str | None, author: str | None, max_results: int = 10
    ) -> list[BookResponse]:
        """Search books and store up to the requested number of results."""
        cache_key = self._build_cache_key(title, author)
        cached_books = await self.search_repository.check_cache(cache_key, max_results)
        if cached_books:
            return cached_books

        params = self.adapter.build_search(title, author, max_results)
        results = await self._rate_limited_search(params)
        books = self.adapter.response_adapter(results)
        saved_books = await self.book_repository.insert_books(books)
        await self.search_repository.save_cache(cache_key, saved_books)
        return saved_books

    @staticmethod
    def _build_cache_key(title: str | None, author: str | None) -> str:
        title_part = (title or "").strip()
        author_part = (author or "").strip()
        return f"title:{title_part} author:{author_part}".strip()
