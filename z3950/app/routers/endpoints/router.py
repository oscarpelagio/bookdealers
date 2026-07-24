from fastapi import APIRouter, Depends

from ...services import Service
from ..dependencies import get_service

router = APIRouter()

@router.get("/search")
async def search(
    title: str, 
    author: str,
    url: str,
    port: int,
    base: str,
    service: Service = Depends(get_service)
) :
    raw = await service.search_book(title, author, url, port, base)
    print(raw)
    return raw