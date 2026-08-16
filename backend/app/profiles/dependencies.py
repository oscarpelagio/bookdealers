"""Dependencias de DI del módulo profiles."""

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
from app.profiles.repository import ProfileRepository
from app.profiles.service import ProfileService


def get_profile_repository(db: AsyncSession = Depends(get_db)) -> ProfileRepository:
    return ProfileRepository(db)


def get_profile_service(
    repo: ProfileRepository = Depends(get_profile_repository),
    db: AsyncSession = Depends(get_db),
) -> ProfileService:
    return ProfileService(repo, db)


async def get_optional_current_user(
    credentials = Depends(bearer_scheme),
    repo: AuthRepository = Depends(get_auth_repository),
) -> User | None:
    """Devuelve el usuario autenticado o `None` si no hay token válido.

    Reutiliza `get_current_user` de auth: si falla la autenticación se
    degrada a anónimo en vez de lanzar 401. Útil para endpoints públicos
    que enriquecen la respuesta cuando hay sesión.
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials, repo)
    except AuthError:
        return None
