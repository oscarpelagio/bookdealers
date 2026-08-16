"""API endpoint para buscar un autor en el índice de Anagrama."""

from fastapi import APIRouter, Depends

from app.router import get_anagrama_lookup_service
from app.schemas import AuthorAnagramaLookup
from app.services import AnagramaLookupService

router = APIRouter()


@router.get("", response_model=AuthorAnagramaLookup)
async def get_author_anagrama(
    author: str,
    service: AnagramaLookupService = Depends(get_anagrama_lookup_service),
) -> AuthorAnagramaLookup:
    """Devuelve bio, foto y contenido relacionado de un autor si está en Anagrama.

    Si no hay coincidencia, `found` es `false` y el resto de campos van a `null`.
    """
    return await service.lookup(author)
