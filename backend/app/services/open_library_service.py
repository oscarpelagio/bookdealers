"""Service for Open Library search."""

import asyncio

from app.adapters import OpenLibraryAdapter
from app.clients import OpenLibraryClient
from app.crud import BookRepository, SearchRepository

from .search_base_service import SearchBaseService


class OpenLibraryService(SearchBaseService):
    _semaphore = asyncio.Semaphore(1)
    _last_call: float = 0.0
    _min_interval: float = 0.2

    def __init__(
        self,
        book_repo: BookRepository,
        search_repo: SearchRepository,
        client: OpenLibraryClient,
        adapter: OpenLibraryAdapter,
    ):
        super().__init__(book_repo, search_repo, client, adapter)
