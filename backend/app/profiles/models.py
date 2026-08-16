"""Models del context PROFILES.

Diseño (documento de arquitectura FASE 1 §1.4):
- `Profile` (aggregate root, 1:1 con `users`): identidad pública del usuario.
- `ProfilePreference` y `PrivacySetting` son parte del agregado (1:1), viven
  y mueren con el Profile; se modelan como tablas propias por claridad.
- `ReadingGoal` es un agregado propio: un objetivo por año y usuario.

Todos los timestamps son timezone-aware (UTC).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.enums import Visibility


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


class Profile(SQLModel, table=True):
    """Extensión 1:1 del `users` del módulo auth. Nunca hay 2 por usuario."""

    __tablename__ = "profiles"
    __table_args__ = (
        Index("ix_profiles_user_id", "user_id", unique=True),
        # Búsqueda social (F10): GIN trigram sobre display_name.
        Index(
            "ix_profiles_display_name_trgm", "display_name",
            postgresql_using="gin",
            postgresql_ops={"display_name": "gin_trgm_ops"},
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    display_name: str | None = Field(default=None, sa_column=Column(String(120)))
    bio: str | None = Field(default=None, sa_column=Column(String(500)))
    location: str | None = Field(default=None, sa_column=Column(String(120)))
    website: str | None = Field(default=None, sa_column=Column(String(500)))
    avatar_url: str | None = Field(default=None, sa_column=Column(String(500)))
    cover_url: str | None = Field(default=None, sa_column=Column(String(500)))
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class ProfilePreference(SQLModel, table=True):
    """Preferencias de producto del usuario (idioma, visibilidad por defecto)."""

    __tablename__ = "profile_preferences"
    __table_args__ = (
        Index("ix_profile_preferences_user_id", "user_id", unique=True),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    language: str | None = Field(default=None, sa_column=Column(String(10)))
    default_review_visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(
            SAEnum(Visibility, name="visibility"),
            nullable=False,
        ),
    )
    reading_tracking_enabled: bool = Field(default=True)
    content_languages: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String(10))),
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class PrivacySetting(SQLModel, table=True):
    """Visibilidad por sección del perfil público (ADR-4)."""

    __tablename__ = "privacy_settings"
    __table_args__ = (
        Index("ix_privacy_settings_user_id", "user_id", unique=True),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    profile_visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    library_visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    reviews_visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    lists_visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    activity_visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    allow_follows: bool = Field(default=True)
    show_reading_progress: bool = Field(default=True)
    block_anonymous: bool = Field(default=False)
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class ReadingGoal(SQLModel, table=True):
    """Objetivo anual de lectura de un usuario (libros y/o páginas)."""

    __tablename__ = "reading_goals"
    __table_args__ = (
        UniqueConstraint("user_id", "year", name="uq_reading_goals_user_year"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    year: int = Field(sa_column=Column(Integer, nullable=False))
    books_goal: int | None = Field(default=None, sa_column=Column(Integer))
    pages_goal: int | None = Field(default=None, sa_column=Column(Integer))
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))
