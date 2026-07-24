"""Service for Google Books search."""

import asyncio
import logging

from fastapi import UploadFile

from app.adapters import GoogleBooksAdapter
from app.clients import GoogleBooksClient
from app.crud import BookRepository, SearchRepository
from app.models import Book
from app.utils import CsvUtils

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

    async def import_goodreads_csv(self, file: UploadFile) -> list[Book]:
        """Import books from a Goodreads CSV export."""
        books = await CsvUtils.parse_goodreads_book(file)
        saved_books_list: list[Book] = []
        for book in books:
            title = book["title"]
            author = book["author"]
            try:
                saved_books = await self.search_and_process(title, author, 1)
                saved_books_list.extend(saved_books)
            except Exception as exc:
                logger.error("Error processing '%s' by '%s': %s", title, author, exc)
                continue
        return saved_books_list

