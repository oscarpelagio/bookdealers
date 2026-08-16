"""Esquemas de validación del módulo shelves."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field, model_validator
from sqlmodel import SQLModel

from app.enums import ReadingStatus, ShelfKind


class ShelfCreate(SQLModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=200)
    is_private: bool = False


class ShelfUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=200)
    is_private: bool | None = None
    position: int | None = Field(default=None, ge=0)


class ShelfResponse(SQLModel):
    id: str
    name: str
    slug: str
    kind: ShelfKind
    is_default: bool
    is_private: bool
    position: int
    description: str | None = None
    book_count: int = 0


class BookBrief(SQLModel):
    """Datos mínimos del libro para mostrar en estanterías/librería."""

    id: int
    title: str
    author: str
    thumbnail: str | None = None
    page_count: int | None = None
    language: str
    establishment_name: str | None = None
    price: float | None = None


class UserBookUpdate(SQLModel):
    """Cuerpo para crear/actualizar un UserBook vía PATCH."""

    status: ReadingStatus | None = None
    notes: str | None = None


class UserBookResponse(SQLModel):
    id: str
    book_id: int
    status: ReadingStatus
    current_page: int | None = None
    percent_read: float | None = None
    started_at: date | None = None
    finished_at: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    book: BookBrief


class ProgressUpdate(SQLModel):
    page: int | None = Field(default=None, ge=0)
    percent_read: float | None = Field(default=None, ge=0, le=100)
    note: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "ProgressUpdate":
        if self.page is None and self.percent_read is None:
            raise ValueError("Provide page or percent_read")
        return self


class ReadingProgressResponse(SQLModel):
    id: str
    page: int | None = None
    percent_read: float | None = None
    note: str | None = None
    created_at: datetime
