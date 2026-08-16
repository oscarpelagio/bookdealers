"""Dependències del mòdul d'autenticació.

Proveeix la DI del servei i les dependències de protecció d'endpoints:
usuari actual, rols requerits i rate limiting del login.
"""

import uuid
from functools import lru_cache

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.exceptions import (
    ForbiddenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
)
from app.auth.google import GoogleIdTokenVerifier
from app.auth.models import RoleKey, User
from app.auth.ratelimit import login_rate_limiter
from app.auth.repository import AuthRepository
from app.auth.security import decode_access_token
from app.auth.service import AuthService
from app.core.deps import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_repository(db: AsyncSession = Depends(get_db)) -> AuthRepository:
    return AuthRepository(db)


def get_auth_service(
    repo: AuthRepository = Depends(get_auth_repository),
) -> AuthService:
    return AuthService(repo)


@lru_cache
def get_google_verifier() -> GoogleIdTokenVerifier:
    return GoogleIdTokenVerifier()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    repo: AuthRepository = Depends(get_auth_repository),
) -> User:
    """Resol l'usuari autenticat a partir del Bearer token (access JWT)."""
    if credentials is None or not credentials.credentials:
        raise TokenMissingError()

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalidError() from exc

    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidError()

    try:
        user = await repo.get_by_id(uuid.UUID(user_id))
    except ValueError as exc:
        raise TokenInvalidError() from exc

    if user is None or not user.is_active or user.deleted_at is not None:
        raise TokenInvalidError()
    return user


def require_roles(*roles: RoleKey):
    """Dependència que comprova que l'usuari té almenys un dels rols indicats."""

    async def _checker(
        user: User = Depends(get_current_user),
        repo: AuthRepository = Depends(get_auth_repository),
    ) -> User:
        user_roles = await repo.get_user_roles(user.id)
        allowed = {role.value for role in roles}
        if not allowed.intersection(user_roles):
            raise ForbiddenError()
        return user

    return _checker


async def check_login_rate_limit(request: Request, email: str) -> None:
    """Protecció de força bruta: llindar de peticions per IP+email."""
    client_host = request.client.host if request.client else "unknown"
    await login_rate_limiter.check(f"{client_host}:{email}")
