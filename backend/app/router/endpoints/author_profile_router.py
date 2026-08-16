"""API endpoint para el perfil de autor unificado (editoriales → Wikimedia)."""

from fastapi import APIRouter, Depends

from app.router import get_author_profile_lookup_service, get_central_article_repository
from app.schemas import AuthorProfileLookup, BookAppearsInResponse, BookAppearsInList
from app.services import AuthorProfileLookupService
from app.utils import NormalizationUtils
from app.crud import CentralArticleRepository

router = APIRouter()


@router.get("", response_model=AuthorProfileLookup)
async def get_author_profile(
    author: str,
    service: AuthorProfileLookupService = Depends(get_author_profile_lookup_service),
) -> AuthorProfileLookup:
    """Devuelve bio, foto y contenido relacionado de un autor si está en una
    editorial (Anagrama/Penguin). Si no, `found` es `false` y el front cae a
    Wikimedia (author-photo).
    """
    return await service.lookup(author)


@router.get("/appears-in", response_model=BookAppearsInResponse)
async def author_appears_in(
    author: str,
    central_repo: CentralArticleRepository = Depends(get_central_article_repository),
) -> BookAppearsInResponse:
    """Listas del blog de La Central con libros de un autor.

    Busca por autor normalizado ('Nombre Apellido' sin acentos), el mismo
    criterio usado al volcar los artículos.
    """
    norm_author = NormalizationUtils.normalize_text(
        NormalizationUtils.author_name_first(author)
    )
    rows = await central_repo.articles_by_author(norm_author)
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
    return BookAppearsInResponse(book_id=0, total=len(lists), lists=lists)
