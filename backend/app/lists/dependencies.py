"""Dependencias de DI del módulo lists.

No hay handlers de eventos propios en F7 (las notificaciones llegan en
F8); `register()` se deja como punto de anclaje simétrico al patrón de
`reviews` para fases posteriores.
"""

from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import (
    bearer_scheme,
    get_auth_repository,
    get_current_user,
)
from app.auth.exceptions import AuthError
from app.auth.models import User
from app.auth.repository import AuthRepository
from app.core.deps import get_db
from app.lists.repository import ListsRepository
from app.lists.service import ListsService


def register() -> None:
    """Registra handlers de eventos del módulo (vacío en F7)."""
    return None


register()


def get_lists_repository(db: AsyncSession = Depends(get_db)) -> ListsRepository:
    return ListsRepository(db)


def get_lists_service(
    repo: ListsRepository = Depends(get_lists_repository),
    db: AsyncSession = Depends(get_db),
) -> ListsService:
    return ListsService(repo, db)


async def get_optional_current_user(
    credentials = Depends(bearer_scheme),
    repo: AuthRepository = Depends(get_auth_repository),
) -> User | None:
    """Devuelve el usuario autenticado o `None` si no hay token válido."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials, repo)
    except AuthError:
        return None
