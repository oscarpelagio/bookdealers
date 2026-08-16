"""Endpoints del blog de La Central (llistes temàtiques)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud import BookRepository, CentralArticleRepository
from app.router.dependencies import (
    get_central_article_repository,
    get_z3950_search_service,
    get_book_repository,
)
from app.schemas import BookResponse, CentralListResponse
from app.services import CentralListBooksService, Z3950SearchService

router = APIRouter()


@router.get("/{slug}", response_model=CentralListResponse)
async def get_central_list(
    slug: str,
    central_repo: CentralArticleRepository = Depends(get_central_article_repository),
) -> CentralListResponse:
    """Detall d'una llista (article) del blog de La Central per slug."""
    article = await central_repo.get_by_slug(slug)
    if article is None or article.status != "done":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    return CentralListResponse(
        article_id=article.id,
        slug=article.slug,
        url=article.url,
        tipo=article.tipo,
        titulo=article.titulo,
        subtitulo=article.subtitulo,
        intro=article.intro,
        autor=article.autor,
        fecha=article.fecha,
        cuerpo=article.cuerpo,
        portada_url=article.portada_url,
    )


@router.get("/{slug}/books", response_model=list[BookResponse])
async def get_central_list_books(
    slug: str,
    central_repo: CentralArticleRepository = Depends(get_central_article_repository),
    book_repo: BookRepository = Depends(get_book_repository),
    z3950_search_service: Z3950SearchService = Depends(get_z3950_search_service),
) -> list[BookResponse]:
    """Llistat de llibres d'una llista, resolts per Z39.50 (igual que el CSV).

    Cada entrada de la llista es busca (títol + apellido de l'autor) i es queda
    amb el primer resultat. El resultat es cachea a `central_blog_article_book`.
    """
    article = await central_repo.get_by_slug(slug)
    if article is None or article.status != "done":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")

    service = CentralListBooksService(central_repo, book_repo, z3950_search_service)
    books = await service.resolve_books(article.id)
    return [BookResponse.model_validate(book) for book in books]