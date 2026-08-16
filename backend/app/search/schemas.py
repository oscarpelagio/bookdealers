"""Esquemas de validación del módulo de búsqueda social (FASE 10)."""

from __future__ import annotations

from datetime import date, datetime

from sqlmodel import SQLModel

from app.enums import PostType, Visibility
from app.social.schemas import UserBrief


class UserSearchResult(UserBrief):
    """Usuario encontrado en la búsqueda social."""


class BookSearchResult(SQLModel):
    """Libro del catálogo encontrado (búsqueda local sobre `books`)."""

    id: int
    title: str
    author: str
    thumbnail: str | None = None
    publisher: str | None = None
    publisher_date: date | None = None
    language: str
    page_count: int | None = None
    categories: str | None = None


class PostSearchResult(SQLModel):
    """Post público encontrado, con autor mínimo."""

    id: str
    type: PostType
    body: str
    visibility: Visibility
    book_id: int | None = None
    created_at: datetime
    author: UserBrief