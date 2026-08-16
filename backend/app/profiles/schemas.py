"""Esquemas de validación del módulo profiles."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, HttpUrl, field_validator
from sqlmodel import SQLModel

from app.enums import Visibility


class ProfileUpdate(SQLModel):
    """Campos editables del perfil propio."""

    display_name: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)

    @field_validator("website", "avatar_url", "cover_url", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ProfilePublicResponse(SQLModel):
    """Perfil visible para un tercero (respeta privacidad)."""

    id: str
    username: str
    display_name: str | None = None
    bio: str | None = None
    location: str | None = None
    website: str | None = None
    avatar_url: str | None = None
    cover_url: str | None = None
    joined_at: datetime
    is_following: bool = False

    class Config:
        from_attributes = True


class ProfileMeResponse(ProfilePublicResponse):
    """Perfil del usuario autenticado (sin restricción de privacidad)."""

    preferences: "PreferenceResponse"
    privacy: "PrivacyResponse"


class PreferenceResponse(SQLModel):
    language: str | None = None
    default_review_visibility: Visibility = Visibility.PUBLIC
    reading_tracking_enabled: bool = True
    content_languages: list[str] | None = None


class PreferenceUpdate(SQLModel):
    language: str | None = Field(default=None, max_length=10)
    default_review_visibility: Visibility | None = None
    reading_tracking_enabled: bool | None = None
    content_languages: list[str] | None = Field(default=None, max_length=10)


class PrivacyResponse(SQLModel):
    profile_visibility: Visibility = Visibility.PUBLIC
    library_visibility: Visibility = Visibility.PUBLIC
    reviews_visibility: Visibility = Visibility.PUBLIC
    lists_visibility: Visibility = Visibility.PUBLIC
    activity_visibility: Visibility = Visibility.PUBLIC
    allow_follows: bool = True
    show_reading_progress: bool = True
    block_anonymous: bool = False


class PrivacyUpdate(SQLModel):
    profile_visibility: Visibility | None = None
    library_visibility: Visibility | None = None
    reviews_visibility: Visibility | None = None
    lists_visibility: Visibility | None = None
    activity_visibility: Visibility | None = None
    allow_follows: bool | None = None
    show_reading_progress: bool | None = None
    block_anonymous: bool | None = None


class ReadingGoalCreate(SQLModel):
    year: int = Field(ge=2000, le=2100)
    books_goal: int | None = Field(default=None, ge=1)
    pages_goal: int | None = Field(default=None, ge=1)


class ReadingGoalResponse(SQLModel):
    id: str
    year: int
    books_goal: int | None = None
    pages_goal: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
