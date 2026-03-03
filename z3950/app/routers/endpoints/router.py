from fastapi import APIRouter, Depends

from ...services import Service
from ..dependencies import get_service

router = APIRouter()

@router.get("/search")
async def search(
    title: str, 
    author: str, 
    service: Service = Depends(get_service)
) -> dict :
    raw = await service.search_book(title, author)
    return {"response": raw}
