"""Models del context LISTS & COLLABORATORS (FASE 7).

Diseño (documento de arquitectura §2.22–2.24 y §2.3):
- `List`: lista curada de libros del owner. UNIQUE (owner_id, slug),
  soft delete (ADR-8). Al borrar se libera el slug para poder re-crear
  una lista con el mismo título ("re-curar").
- `ListItem`: libro en una lista. UNIQUE (list_id, book_id) → no se puede
  añadir el mismo libro dos veces. `book_id` FK RESTRICT al catálogo;
  cascade duro si se borra la lista físicamente.
- `ListCollaborator`: usuario invitado por el owner. UNIQUE (list_id,
  user_id). `role` EDITOR (añade/elimina items) o VIEWER (solo ver);
  `can_add_books` amplía a los VIEWER para añadir libros concretos.

Invariantes (agregado `List`): solo la owner cambia título/descripción/
visibilidad y gestiona colaboradores; EDITOR puede añadir/eliminar items.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.enums import CollaboratorRole, Visibility


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


def _uuid_pk():
    return Column(PgUUID(as_uuid=True), primary_key=True)


def _user_fk(name: str, *, ondelete: str = "CASCADE") -> Column:
    return Column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete=ondelete),
        nullable=False,
    )


class List(SQLModel, table=True):
    """Lista curada de libros de un usuario."""

    __tablename__ = "lists"
    __table_args__ = (
        UniqueConstraint("owner_id", "slug", name="uq_lists_owner_slug"),
        Index("ix_lists_owner", "owner_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    owner_id: uuid.UUID = Field(sa_column=_user_fk("owner_id"))
    title: str = Field(sa_column=Column(String(150), nullable=False))
    description: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    slug: str = Field(sa_column=Column(String(160), nullable=False))
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class ListItem(SQLModel, table=True):
    """Libro curado dentro de una lista."""

    __tablename__ = "list_items"
    __table_args__ = (
        UniqueConstraint("list_id", "book_id", name="uq_list_items_list_book"),
        Index("ix_list_items_list", "list_id"),
        Index("ix_list_items_book", "book_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    list_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("lists.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    book_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("books.id", ondelete="RESTRICT"), nullable=False
        )
    )
    added_by: uuid.UUID = Field(sa_column=_user_fk("added_by"))
    note: str | None = Field(
        default=None, sa_column=Column(String(200), nullable=True)
    )
    position: int = Field(sa_column=Column(Integer, nullable=False))
    created_at: datetime = Field(sa_column=_datetime(required=True))


class ListCollaborator(SQLModel, table=True):
    """Usuario invitado por el owner a colaborar en una lista."""

    __tablename__ = "list_collaborators"
    __table_args__ = (
        UniqueConstraint("list_id", "user_id", name="uq_list_collaborators_list_user"),
        Index("ix_list_collaborators_list", "list_id"),
        Index("ix_list_collaborators_user", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    list_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("lists.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    user_id: uuid.UUID = Field(sa_column=_user_fk("user_id"))
    role: CollaboratorRole = Field(
        sa_column=Column(
            SAEnum(CollaboratorRole, name="collaborator_role"), nullable=False
        )
    )
    can_add_books: bool = Field(
        sa_column=Column(Boolean, nullable=False, default=False)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
