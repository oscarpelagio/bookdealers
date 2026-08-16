"""API endpoint para la foto de un autor."""

from fastapi import APIRouter, Depends

from app.services import AuthorPhotoService
from app.router import get_author_photo_service

router = APIRouter()


@router.get("")
async def get_author_photo(
    author: str,
    service: AuthorPhotoService = Depends(get_author_photo_service),
):
    """Devuelve la foto de un autor (Wikipedia → Wikidata → Google Images).

    La primera petición por autor cachea el resultado en `author_photos`;
    los siguientes requests no vuelven a llamar a las fuentes externas.
    """
    return await service.get_photo(author)