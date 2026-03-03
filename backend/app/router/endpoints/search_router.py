"""Endpoints de l'API per a Google Books."""

from fastapi import APIRouter, Query, Depends

from app.router import get_book_service
from app.schemas import BookResponse
from app.services import SearchService

router = APIRouter()

@router.get("/by-title", response_model=list[BookResponse])
async def search_by_title(
    title: str | None = Query(None, description="Títol del llibre a cercar"),
    author: str | None = Query(None, description="Autor del llibre a cercar"),
    service: SearchService = Depends(get_book_service),
) -> list[BookResponse]:
    """
    Cerca llibres per títol, autor o ambdos.
    """
    books = await service.search_and_process(title, author)
    return books
