"""Esquemas de validación del módulo lists."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel

from app.enums import CollaboratorRole, Visibility
from app.social.schemas import UserBrief


class BookBrief(SQLModel):
    """Datos mínimos de un libro en los items de lista."""

    id: int
    title: str
    author: str
    thumbnail: str | None = None


class ListCreate(SQLModel):
    """Cuerpo para crear una lista."""

    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    visibility: Visibility = Visibility.PUBLIC


class ListUpdate(SQLModel):
    """Cuerpo para actualizar una lista (solo owner)."""

    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    visibility: Visibility | None = None


class ListSummary(SQLModel):
    """Lista para listados (con conteo de items)."""

    id: str
    title: str
    slug: str
    description: str | None = None
    visibility: Visibility
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
    owner: UserBrief


class ListDetail(ListSummary):
    """Lista con colaboradores y permisos del espectador."""

    collaborators: list["ListCollaboratorBrief"] = []
    is_owner: bool = False
    is_collaborator: bool = False
    can_edit: bool = False


class ListPage(SQLModel):
    """Página de listas (cursor pagination)."""

    items: list[ListSummary]
    next: str | None = None


class ListItemAdd(SQLModel):
    """Cuerpo para añadir un libro a la lista."""

    book_id: int
    note: str | None = Field(default=None, max_length=200)
    position: int | None = Field(default=None, ge=0)


class ListItemBrief(SQLModel):
    """Item de lista con el libro curado."""

    id: str
    book: BookBrief
    note: str | None = None
    position: int
    added_by: UserBrief
    created_at: datetime


class ListItemPage(SQLModel):
    """Página de items (cursor pagination)."""

    items: list[ListItemBrief]
    next: str | None = None


class ListCollaboratorAdd(SQLModel):
    """Cuerpo para añadir un colaborador (solo owner)."""

    user_id: uuid.UUID
    role: CollaboratorRole = CollaboratorRole.VIEWER
    can_add_books: bool | None = None


class ListCollaboratorUpdate(SQLModel):
    """Cuerpo para actualizar el rol/capacidades de un colaborador."""

    role: CollaboratorRole | None = None
    can_add_books: bool | None = None


class ListCollaboratorBrief(SQLModel):
    """Colaborador de una lista."""

    id: str
    user: UserBrief
    role: CollaboratorRole
    can_add_books: bool
    created_at: datetime


# Referencia cruzada para el forward ref de ListDetail.
ListDetail.model_rebuild()