"""Models del context FAVORITES / PREFS.

Dos agregados pequeños:
- `UserCatalog`: catálogos que usa un usuario (p. ej. admin usa aladi
  para z3950 y catalunya para eBiblio). Sustituye los catálogos hardcodeados.
- `UserFavoriteEstablishment`: establecimientos favoritos del usuario
  (bibliotecas físicas type=LIBRARY y librerías type=BOOK_SHOP).

Timestamps timezone-aware (UTC).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


def _uuid_pk():
    return Column(PgUUID(as_uuid=True), primary_key=True)


class UserCatalog(SQLModel, table=True):
    """Relación N:N entre un usuario y los catálogos que utiliza."""

    __tablename__ = "user_catalogs"
    __table_args__ = (
        UniqueConstraint("user_id", "catalog_id", name="uq_user_catalogs_user_catalog"),
        Index("ix_user_catalogs_user", "user_id"),
        Index("ix_user_catalogs_catalog", "catalog_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    catalog_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("catalogs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))


class UserFavoriteEstablishment(SQLModel, table=True):
    """Establecimientos favoritos de un usuario (bibliotecas y librerías)."""

    __tablename__ = "user_favorite_establishments"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "establishment_id",
            name="uq_user_fav_estab_user_estab",
        ),
        Index("ix_user_fav_estab_user", "user_id"),
        Index("ix_user_fav_estab_estab", "establishment_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    establishment_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("establishments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))


class UserSearchHistory(SQLModel, table=True):
    """Libros abiertos desde búsquedas (historial de búsquedas recientes).

    Una fila por (user, book): re-clickear actualiza `clicked_at` para
    mover el libro al principio del historial.
    """

    __tablename__ = "user_search_history"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "book_id",
            name="uq_user_search_history_user_book",
        ),
        Index("ix_user_search_history_user_clicked", "user_id", "clicked_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    book_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    clicked_at: datetime = Field(sa_column=_datetime(required=True))
