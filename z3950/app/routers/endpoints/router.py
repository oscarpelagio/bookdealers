from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from ...services import Service
from ..dependencies import get_service

router = APIRouter()

@router.get("/search", response_class=PlainTextResponse)
async def search(
    title: str, 
    author: str,
    url: str,
    port: int,
    base: str,
    service: Service = Depends(get_service)
):
    raw = await service.search_book(title, author, url, port, base)
    return raw

@router.get("/search-brief", response_class=PlainTextResponse)
async def search_brief(
    title: str = "",
    author: str = "",
    url: str = "",
    port: int = 0,
    base: str = "",
    service: Service = Depends(get_service)
):
    raw = await service.search_book_brief(title, author, url, port, base)
    return raw

@router.get("/search-author", response_class=PlainTextResponse)
async def search_author(
    author: str = "",
    url: str = "",
    port: int = 0,
    base: str = "",
    service: Service = Depends(get_service)
):
    raw = await service.search_book_author(author, url, port, base)
    return raw