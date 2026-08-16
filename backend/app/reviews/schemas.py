"""Esquemas de validación del módulo reviews."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel

from app.enums import Visibility


class ReviewCreate(SQLModel):
    """Cuerpo para crear una review (el rating es obligatorio)."""

    score: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    body: str | None = None
    spoiler: bool = False
    language: str | None = Field(default=None, max_length=10)


class ReviewUpdate(SQLModel):
    """Cuerpo para actualizar una review existente."""

    score: int | None = Field(default=None, ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    body: str | None = None
    spoiler: bool | None = None
    language: str | None = Field(default=None, max_length=10)


class AuthorBrief(SQLModel):
    """Datos mínimos del autor para mostrar junto a una review."""

    id: str
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class ReviewBookBrief(SQLModel):
    """Datos mínimos del libro de una review."""

    id: int
    title: str
    author: str
    thumbnail: str | None = None


class ReviewResponse(SQLModel):
    id: str
    book_id: int
    title: str | None = None
    body: str | None = None
    spoiler: bool = False
    language: str | None = None
    score: int | None = None
    like_count: int = 0
    created_at: datetime
    updated_at: datetime
    author: AuthorBrief
    book: ReviewBookBrief


class ReviewPage(SQLModel):
    """Página de reviews (cursor pagination)."""

    items: list[ReviewResponse]
    next: str | None = None


class ReviewLikeResponse(SQLModel):
    id: str
    review_id: str
    created_at: datetime


class MyReviewResponse(ReviewResponse):
    """Review propia; incluye la visibilidad con la que se publicó."""

    visibility: Visibility
