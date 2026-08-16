"""Dependencias de DI del módulo favorites."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_db
from app.favorites.repository import FavoritesRepository
from app.favorites.service import FavoritesService


def get_favorites_repository(db: AsyncSession = Depends(get_db)) -> FavoritesRepository:
    return FavoritesRepository(db)


def get_favorites_service(
    repo: FavoritesRepository = Depends(get_favorites_repository),
    db: AsyncSession = Depends(get_db),
) -> FavoritesService:
    return FavoritesService(repo, db)
