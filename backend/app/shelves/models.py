"""Models del context SHELVES / LIBRARY.

Diseño (documento de arquitectura FASE 1 §1.5):
- `UserBook` (aggregate root): relación del usuario con un libro. El estado
  de lectura es la única fuente de verdad de las estanterías de estado
  (ADR-5). El progreso se guarda desnormalizado aquí y su historia en
  `ReadingProgress`.
- `Shelf` (aggregate root): estanterías de estado (seed 4) y custom.
  `ShelfItem` solo existe para estanterías CUSTOM.
- `ReadingProgress`: log append-only del progreso de un UserBook.

Timestamps timezone-aware (UTC). Fechas de lectura como DATE puro.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.enums import ReadingStatus, ShelfKind


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


def _uuid_pk():
    return Column(PgUUID(as_uuid=True), primary_key=True)


class Shelf(SQLModel, table=True):
    """Estantería de un usuario (STATUS o CUSTOM)."""

    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_shelves_user_slug"),
        Index("ix_shelves_user_kind", "user_id", "kind"),
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
    name: str = Field(sa_column=Column(String(80), nullable=False))
    slug: str = Field(sa_column=Column(String(80), nullable=False))
    kind: ShelfKind = Field(
        sa_column=Column(
            SAEnum(ShelfKind, name="shelf_kind"),
            nullable=False,
        )
    )
    is_default: bool = Field(default=False)
    is_private: bool = Field(default=False)
    position: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(String(200)))
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class UserBook(SQLModel, table=True):
    """Relación usuario↔libro: estado, fechas, notas y progreso."""

    __tablename__ = "user_books"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_user_books_user_book"),
        Index("ix_user_books_user_status", "user_id", "status"),
        CheckConstraint(
            "percent_read IS NULL OR (percent_read >= 0 AND percent_read <= 100)",
            name="ck_user_books_percent_range",
        ),
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
            ForeignKey("books.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    status: ReadingStatus = Field(
        sa_column=Column(
            SAEnum(ReadingStatus, name="reading_status"),
            nullable=False,
        )
    )
    current_page: int | None = Field(default=None, sa_column=Column(Integer))
    percent_read: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(5, 2))
    )
    started_at: date | None = Field(default=None, sa_column=Column(Date))
    finished_at: date | None = Field(default=None, sa_column=Column(Date))
    notes: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class ShelfItem(SQLModel, table=True):
    """Libro colocado en una estantería CUSTOM (solo custom, ADR-5)."""

    __tablename__ = "shelf_items"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "shelf_id", "book_id", name="uq_shelf_items_user_shelf_book"
        ),
        Index("ix_shelf_items_user_book", "user_id", "book_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    # user_id desnormalizado para joins y unicidad sin pasar por shelf.
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    shelf_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("shelves.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    book_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("books.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))


class ReadingProgress(SQLModel, table=True):
    """Historial append-only de progreso de un UserBook."""

    __tablename__ = "reading_progress"
    __table_args__ = (
        CheckConstraint(
            "percent_read IS NULL OR (percent_read >= 0 AND percent_read <= 100)",
            name="ck_reading_progress_percent_range",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_book_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("user_books.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    page: int | None = Field(default=None, sa_column=Column(Integer))
    percent_read: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(5, 2))
    )
    note: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=_datetime(required=True))
