"""Esquemes de resposta del context FAVORITES / PREFS."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import SQLModel

from app.enums import EstablishmentTypeEnum
from app.shelves.schemas import BookBrief


class CatalogResponse(SQLModel):
    id: int
    service: str
    name: str
    url: str | None = None


class EstablishmentResponse(SQLModel):
    id: int
    type: EstablishmentTypeEnum
    name: str
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    province: str | None = None
    catalog_id: int
    favorite: bool = True


class FavoriteEstablishmentCreated(SQLModel):
    establishment: EstablishmentResponse
    created_at: datetime


class LibraryShelf(SQLModel):
    """Una biblioteca favorita con los libros disponibles en ella."""
    establishment: EstablishmentResponse
    books: list[BookBrief] = []


class LibrariesResponse(SQLModel):
    shelves: list[LibraryShelf] = []


class HomeShelf(SQLModel):
    key: str
    title: str
    books: list[BookBrief] = []


class HomeResponse(SQLModel):
    shelves: list[HomeShelf] = []
