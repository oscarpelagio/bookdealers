"""API endpoints for fetching books."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud import BookRepository, CentralArticleRepository
from app.router import get_book_repository, get_central_article_repository
from app.schemas import BookResponse, BookAppearsInResponse, BookAppearsInList

router = APIRouter()


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    book_repo: BookRepository = Depends(get_book_repository),
) -> BookResponse:
    """Devuelve un libro completo por su id."""
    book = await book_repo.get_by_id(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return BookResponse.model_validate(book)


@router.get("/{book_id}/appears-in", response_model=BookAppearsInResponse)
async def book_appears_in(
    book_id: int,
    book_repo: BookRepository = Depends(get_book_repository),
    central_repo: CentralArticleRepository = Depends(get_central_article_repository),
) -> BookAppearsInResponse:
    """Listas del blog de La Central donde aparece un libro.

    Compara por título + autor normalizados (mismo criterio de
    `NormalizationUtils.normalize_text` usado al volcar los artículos).
    """
    book = await book_repo.get_by_id(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    rows = await central_repo.book_appears_in(book.normal_title, book.normal_author)
    lists = [
        BookAppearsInList(
            article_id=article.id,
            slug=article.slug,
            url=article.url,
            titulo=article.titulo,
            autor=article.autor,
            fecha=article.fecha,
            portada_url=article.portada_url,
            posicion=posicion,
        )
        for article, posicion in rows
    ]
    return BookAppearsInResponse(book_id=book_id, total=len(lists), lists=lists)
