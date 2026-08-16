"""Esquemes de validació per a l'API."""

from datetime import date
from decimal import Decimal
from sqlmodel import SQLModel, Field


class BookBase(SQLModel):
    """Esquema base amb camps comuns."""
    title: str
    author: str
    author_biblioteca: str | None = None
    publisher: str | None = None
    publisher_date: date | None = None
    description: str | None = None
    isbn: str | None = Field(index=True, default=None) 
    page_count: int | None = None
    print_type: str | None = None
    categories: str | None = None
    maturity_rating: str | None = None
    small_thumbnail: str | None = None
    thumbnail: str | None = None
    language: str
    preview_link: str | None = None
    original_title: str | None = None
    bib_id: str | None = Field(index=True, default=None)
    normal_title: str = Field(index=True, nullable=False)
    normal_author: str = Field(index=True, nullable=False)
    normal_original_title: str | None = Field(default=None)
    price: Decimal | None = Field(default=None, description="Preu únic del llibre (EUR).")
    holdings_count: int | None = Field(
        default=None,
        description="Nombre total d'unitats (holdings) del llibre als catàlegs.",
    )

class BookCreate(BookBase):
    """Esquema per crear un llibre nou."""
    pass


class BookUpdate(SQLModel):
    """Esquema per actualitzar un llibre existent."""
    title: str | None = None
    author: str | None = None
    author_biblioteca: str | None = None
    publisher: str | None = None
    publisher_date: date | None  = None
    description: str | None = None
    isbn: str | None = None
    page_count: int | None = None
    print_type: str | None = None
    categories: str | None = None
    maturity_rating: str | None = None
    small_thumbnail: str | None = None
    thumbnail: str | None = None
    language: str | None = None
    preview_link: str | None = None
    original_title: str | None = None
    bib_id: str | None = None
    price: Decimal | None = None


class BookResponse(BookBase):
    """Esquema de resposta de l'API."""
    id: int

    class Config:
        from_attributes = True


class BookSearchResponse(SQLModel):
    """Esquema per respostes de cerca."""
    query: str
    total_results: int
    books: list[BookResponse]
