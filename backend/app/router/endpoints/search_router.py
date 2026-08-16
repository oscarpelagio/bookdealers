"""API endpoints for book search."""

from fastapi import APIRouter, Query, Depends, HTTPException, status

from app.router import get_google_books_service, get_open_library_service, get_z3950_search_service
from app.schemas import BookResponse
from app.services import GoogleBooksService, OpenLibraryService, Z3950SearchService

router = APIRouter()

@router.get("/z3950", response_model=list[BookResponse])
async def search_z3950(
    title: str | None = Query(None, description="Book title to search"),
    author: str | None = Query(None, description="Book author to search"),
    catalog: str = Query(..., description="Catalog name (aladi, argus, cabib)"),
    service: Z3950SearchService = Depends(get_z3950_search_service),
) -> list[BookResponse]:
    """
    Search books by title, author, or both using z3950.
    """

    books = await service.search_and_process(title, author, catalog)

    return books


@router.get("/z3950/author", response_model=list[BookResponse])
async def search_z3950_by_author(
    author: str = Query(..., min_length=1, description="Book author to search"),
    catalog: str = Query(..., description="Catalog name (aladi, argus, cabib)"),
    service: Z3950SearchService = Depends(get_z3950_search_service),
) -> list[BookResponse]:
    """
    Search books by author only, using z3950. Returns one edition per work,
    preferring the Spanish edition.
    """

    books = await service.search_author_and_process(author, catalog)

    return books


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
