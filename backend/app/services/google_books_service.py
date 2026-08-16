"""Service for Google Books search."""

import asyncio
import logging

from app.adapters import GoogleBooksAdapter
from app.clients import GoogleBooksClient
from app.crud import BookRepository, SearchRepository

from .search_base_service import SearchBaseService

logger = logging.getLogger(__name__)


class GoogleBooksService(SearchBaseService):
    _semaphore = asyncio.Semaphore(1)
    _last_call: float = 0.0
    _min_interval: float = 1.0

    def __init__(
        self,
        book_repo: BookRepository,
        search_repo: SearchRepository,
        client: GoogleBooksClient,
        adapter: GoogleBooksAdapter,
    ):
        super().__init__(book_repo, search_repo, client, adapter)