"""Models del context REVIEWS (FASE 3).

Diseño (documento de arquitectura §1.6 y §2.10):
- `Rating` (aggregate root): score 1..5, único por (user, book). Se crea al
  valorar con/sin review. Hard delete: borrar la review NO borra el rating.
- `Review` (aggregate root): texto + rating opcional (score sobrevive si el
  rating se borra vía `rating_id ON DELETE SET NULL`). Soft delete via
  `deleted_at` para permitir re-review por el mismo user+book (índice
  parcial de unicidad sobre reviews activas).
- `ReviewLike` (entidad owned de Review): like único por (user, review).

`book_id` referencia `books.id` (INT) con ON DELETE RESTRICT: no se toca
el catálogo. Timestamps timezone-aware (UTC).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.enums import Visibility


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


def _uuid_pk():
    return Column(PgUUID(as_uuid=True), primary_key=True)


class Rating(SQLModel, table=True):
    """Valoración de un usuario sobre un libro (1..5 estrellas)."""

    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_ratings_user_book"),
        CheckConstraint("score BETWEEN 1 AND 5", name="ck_ratings_score_range"),
        Index("ix_ratings_book_id", "book_id"),
        Index("ix_ratings_user_id", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    book_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("books.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    score: int = Field(
        sa_column=Column(SmallInteger, nullable=False),
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class Review(SQLModel, table=True):
    """Reseña de un usuario sobre un libro (soft-deletable)."""

    __tablename__ = "reviews"
    __table_args__ = (
        # Solo una review ACTIVA por (user, book); permite re-review tras
        # soft delete (ADR-8).
        Index(
            "ix_reviews_active_user_book",
            "user_id",
            "book_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_reviews_book_created", "book_id", text("created_at DESC")),
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_rating_id", "rating_id", unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    book_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("books.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    title: str | None = Field(default=None, sa_column=Column(String(200)))
    body: str | None = Field(default=None, sa_column=Column(Text))
    rating_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("ratings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    language: str | None = Field(default=None, sa_column=Column(String(10)))
    spoiler: bool = Field(default=False)
    # Snapshot de la visibilidad del autor al publicar (ADR-4), igual que
    # `activities.visibility`: los cambios de privacidad posteriores no
    # afectan a las reviews ya publicadas.
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(
            SAEnum(Visibility, name="visibility"),
            nullable=False,
        ),
    )
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class ReviewLike(SQLModel, table=True):
    """Like de un usuario a una review."""

    __tablename__ = "review_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "review_id", name="uq_review_likes_user_review"),
        Index("ix_review_likes_review_id", "review_id"),
        Index("ix_review_likes_user_id", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    review_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
