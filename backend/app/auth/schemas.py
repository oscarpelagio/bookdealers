"""Esquemes Pydantic d'entrada/sortida del mòdul d'autenticació."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings

USERNAME_PATTERN = r"^[a-zA-Z0-9_.]{3,30}$"


def normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_password_policy(password: str) -> str:
    """Valida la contrasenya segons la política configurada (2026: length-first)."""
    if len(password) < settings.password_min_length:
        raise ValueError("Password is too short.")
    if len(password) > settings.password_max_length:
        raise ValueError("Password is too long.")
    if settings.password_require_uppercase and not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain an uppercase letter.")
    if settings.password_require_lowercase and not re.search(r"[a-z]", password):
        raise ValueError("Password must contain a lowercase letter.")
    if settings.password_require_digit and not re.search(r"\d", password):
        raise ValueError("Password must contain a digit.")
    if settings.password_require_symbol and not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must contain a symbol.")
    return password


# ---------- Entrada ----------


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)
    device_id: str | None = Field(default=None, max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def _strip_email(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("username", mode="before")
    @classmethod
    def _strip_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str) -> str:
        if not re.fullmatch(USERNAME_PATTERN, value):
            raise ValueError("Username must be 3-30 chars: letters, digits, _ or .")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_policy(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    device_id: str | None = Field(default=None, max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def _strip_email(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
    device_id: str | None = Field(default=None, max_length=255)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
    logout_everywhere: bool = False


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=1, description="ID token de Google")
    device_id: str | None = Field(default=None, max_length=255)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def _strip_email(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_policy(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_policy(value)


# ---------- Sortida ----------


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: str | None
    roles: list[str]
    is_email_verified: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_in: int
    refresh_token_expires_in: int
    expires_at: datetime


class RegisterResponse(BaseModel):
    user: UserResponse
    requires_email_verification: bool
    # Només es retorna quan l'enviament de correu està desactivat (dev/testing).
    dev_verification_url: str | None = None
    dev_reset_url: str | None = None


class MessageResponse(BaseModel):
    message: str


class PasswordResetRequestResponse(BaseModel):
    message: str
    # Només es retorna quan l'enviament de correu està desactivat (dev/testing).
    dev_reset_url: str | None = None
