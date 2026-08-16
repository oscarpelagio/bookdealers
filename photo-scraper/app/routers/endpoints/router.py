from fastapi import APIRouter, Depends

from ...services import Service
from ..dependencies import get_service

router = APIRouter()


@router.get("/image")
async def image(
    author: str,
    service: Service = Depends(get_service),
):
    """Primera imagen de Google para un autor.

    `state` puede ser `ok`, `missing` (sin resultados), `blocked` (CAPTCHA
    de Google) o `error` (fallo de red/navegador). En los tres últimos
    `image_url` es `null`.
    """
    return await service.search_image(author)