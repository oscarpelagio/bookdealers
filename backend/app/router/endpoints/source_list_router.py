"""Endpoints de les llistes genèriques de fonts web (sourced_lists)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.source_list_seed import materialize_source_list
from app.crud import BookRepository, SourceListRepository
from app.router.dependencies import (
    get_book_repository,
    get_source_list_repository,
    get_z3950_search_service,
)
from app.schemas import BookResponse, SourceListResponse
from app.services import SourceListBooksService, Z3950SearchService

router = APIRouter()

DEFAULT_SOURCE = "lacentral"


@router.get("/{slug}", response_model=SourceListResponse)
async def get_source_list(
    slug: str,
    source: str = Query(default=DEFAULT_SOURCE),
    list_repo: SourceListRepository = Depends(get_source_list_repository),
) -> SourceListResponse:
    """Detall d'una llista genèrica per slug (dins d'una font).

    Si la llista no existeix a la BD però sí al seed JSON, es materialitza
    (perezosa) i es retorna.
    """
    slist = await list_repo.get_by_slug(slug, source)
    if slist is None:
        slist = await materialize_source_list(source, slug)
    if slist is None or slist.status != "done":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    return SourceListResponse(
        list_id=slist.id,
        slug=slist.slug,
        url=slist.url,
        tipo=slist.tipo,
        titulo=slist.titulo,
        subtitulo=slist.subtitulo,
        intro=slist.intro,
        autor=slist.autor,
        fecha=slist.fecha,
        cuerpo=slist.cuerpo,
        portada_url=slist.portada_url,
    )


@router.get("/{slug}/books", response_model=list[BookResponse])
async def get_source_list_books(
    slug: str,
    source: str = Query(default=DEFAULT_SOURCE),
    list_repo: SourceListRepository = Depends(get_source_list_repository),
    book_repo: BookRepository = Depends(get_book_repository),
    z3950_search_service: Z3950SearchService = Depends(get_z3950_search_service),
) -> list[BookResponse]:
    """Llistat de llibres d'una llista, resolts per Z39.50 (igual que el CSV).

    Cada entrada de la llista es busca (títol + apellido de l'autor) i es queda
    amb el primer resultat, preferint l'edició catalana i, si no, la castellana.
    El resultat es cachea a `sourced_list_books`.
    """
    slist = await list_repo.get_by_slug(slug, source)
    if slist is None:
        slist = await materialize_source_list(source, slug)
    if slist is None or slist.status != "done":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")

    service = SourceListBooksService(list_repo, book_repo, z3950_search_service)
    books = await service.resolve_books(slist.id)
    return [BookResponse.model_validate(book) for book in books]