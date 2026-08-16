"""Rutas de la búsqueda social (FASE 10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.search.dependencies import get_search_deps
from app.search.schemas import BookSearchResult, PostSearchResult, UserSearchResult
from app.search.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/users", response_model=list[UserSearchResult])
async def search_users(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    deps: dict = Depends(get_search_deps),
) -> list[UserSearchResult]:
    service: SearchService = deps["service"]
    return await service.search_users(query=q, viewer=deps["viewer"], limit=limit)


@router.get("/books", response_model=list[BookSearchResult])
async def search_books(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    deps: dict = Depends(get_search_deps),
) -> list[BookSearchResult]:
    service: SearchService = deps["service"]
    return await service.search_books(query=q, limit=limit)


@router.get("/posts", response_model=list[PostSearchResult])
async def search_posts(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    deps: dict = Depends(get_search_deps),
) -> list[PostSearchResult]:
    service: SearchService = deps["service"]
    return await service.search_posts(query=q, viewer=deps["viewer"], limit=limit)