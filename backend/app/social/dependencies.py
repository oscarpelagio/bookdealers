"""Dependencias de DI del módulo social.

FASE 4 no tiene handlers de eventos propios (las notificaciones llegan en
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
from app.social.repository import SocialRepository
from app.social.service import SocialService


def register() -> None:
    """Registra handlers de eventos del módulo (vacío en F4)."""
    return None


register()


def get_social_repository(db: AsyncSession = Depends(get_db)) -> SocialRepository:
    return SocialRepository(db)


def get_social_service(
    repo: SocialRepository = Depends(get_social_repository),
    db: AsyncSession = Depends(get_db),
) -> SocialService:
    return SocialService(repo, db)


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