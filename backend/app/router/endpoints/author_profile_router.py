"""API endpoint para el perfil de autor unificado (editoriales → Wikimedia)."""

from fastapi import APIRouter, Depends

from app.router import get_author_profile_lookup_service, get_source_list_repository
from app.schemas import AuthorProfileLookup, BookAppearsInResponse, BookAppearsInList
from app.services import AuthorProfileLookupService
from app.utils import NormalizationUtils
from app.crud import SourceListRepository

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
    list_repo: SourceListRepository = Depends(get_source_list_repository),
) -> BookAppearsInResponse:
    """Llistes genèriques (La Central, etc.) amb llibres d'un autor.

    Busca per autor normalitzat ('Nombre Apellido' sense accents), el mateix
    criteri usat en bolcar les llistes.
    """
    norm_author = NormalizationUtils.normalize_text(
        NormalizationUtils.author_name_first(author)
    )
    rows = await list_repo.lists_by_author(norm_author)
    lists = [
        BookAppearsInList(
            list_id=slist.id,
            slug=slist.slug,
            url=slist.url,
            titulo=slist.titulo,
            autor=slist.autor,
            fecha=slist.fecha,
            portada_url=slist.portada_url,
            posicion=posicion,
        )
        for slist, posicion in rows
    ]
    return BookAppearsInResponse(book_id=0, total=len(lists), lists=lists)
