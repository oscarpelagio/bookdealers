"""API endpoints for book search."""

from fastapi import APIRouter, Query, Depends, HTTPException, status

from app.router import get_google_books_service, get_open_library_service
from app.schemas import BookResponse
from app.services import GoogleBooksService, OpenLibraryService

router = APIRouter()

@router.get("/google", response_model=list[BookResponse])
async def search_by_title(
    title: str | None = Query(None, description="Book title to search"),
    author: str | None = Query(None, description="Book author to search"),
    service: GoogleBooksService = Depends(get_google_books_service),
) -> list[BookResponse]:
    """
    Search books by title, author, or both using Google.
    """

    books = await service.search_and_process(title, author)

    return books


@router.get("/openlibrary", response_model=list[BookResponse])
async def search_openlibrary(
    title: str | None = Query(None, description="Book title to search"),
    author: str | None = Query(None, description="Book author to search"),
    service: OpenLibraryService = Depends(get_open_library_service),
) -> list[BookResponse]:
    """
    Search books by title, author, or both using Open Library.
    """

    books = await service.search_and_process(title, author)

    return books
