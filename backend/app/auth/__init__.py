"""Mòdul d'autenticació (registre, login, JWT, Google OAuth, RBAC)."""

from app.auth.exceptions import (
    AuthError,
    AuthenticationError,
    EmailVerificationError,
    ForbiddenError,
    InvalidCredentialsError,
    TooManyAttemptsError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
)
from app.auth.models import Role, RoleKey, User, UserRole, RefreshToken
from app.auth.repository import AuthRepository
from app.auth.router import router as auth_router
from app.auth.schemas import TokenPair, UserResponse
from app.auth.service import AuthService, seed_default_roles

__all__ = [
    "AuthError",
    "AuthenticationError",
    "AuthRepository",
    "AuthService",
    "EmailVerificationError",
    "ForbiddenError",
    "InvalidCredentialsError",
    "RefreshToken",
    "Role",
    "RoleKey",
    "TooManyAttemptsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenPair",
    "TokenRevokedError",
    "User",
    "UserResponse",
    "UserRole",
    "auth_router",
    "seed_default_roles",
]
