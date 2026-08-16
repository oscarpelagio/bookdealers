"""Dependencias de DI del módulo shelves.

Al importarse este módulo (vía el router) se registra el handler de eventos
que lanza la consulta de disponibilidad al añadir libros a la librería.
"""

from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_db
from app.shelves.availability_handler import register
from app.shelves.repository import ShelfRepository
from app.shelves.service import ShelfService

register()


def get_shelf_repository(db: AsyncSession = Depends(get_db)) -> ShelfRepository:
    return ShelfRepository(db)


def get_shelf_service(
    repo: ShelfRepository = Depends(get_shelf_repository),
    db: AsyncSession = Depends(get_db),
) -> ShelfService:
    return ShelfService(repo, db)
