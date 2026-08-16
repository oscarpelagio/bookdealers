"""Dependencias del módulo de búsqueda social (FASE 10)."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.deps import get_db
from app.profiles.dependencies import get_optional_current_user
from app.search.repository import SearchRepository
from app.search.service import SearchService


async def get_search_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SearchService, None]:
    yield SearchService(SearchRepository(db))


def get_search_deps(
    service: SearchService = Depends(get_search_service),
    viewer: User | None = Depends(get_optional_current_user),
) -> dict:
    return {"service": service, "viewer": viewer}