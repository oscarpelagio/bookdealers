"""Models de dades per a la base de dades."""

from decimal import Decimal
from datetime import datetime

from sqlalchemy import Column, Index, Numeric
from sqlmodel import Field, UniqueConstraint

from app.schemas import BookBase

class Book(BookBase, table=True):
    """Model de base de dades per als llibres."""
    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint("normal_title", "normal_author", "language", name="unique_book"),
        # Búsqueda social (F10): índices GIN trigram sobre columnas normalizadas.
        Index(
            "ix_books_normal_title_trgm", "normal_title",
            postgresql_using="gin",
            postgresql_ops={"normal_title": "gin_trgm_ops"},
        ),
        Index(
            "ix_books_normal_author_trgm", "normal_author",
            postgresql_using="gin",
            postgresql_ops={"normal_author": "gin_trgm_ops"},
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    created_at : datetime = Field(nullable = True, default_factory=datetime.utcnow)

    # Precio único del libro en euros (lo aporta todostuslibros).
    price: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(8, 2), nullable=True)
    )

    # Contadores denormalizados de reviews/ratings (ADR-9). Se actualizan
    # vía eventos `reviews.rating_changed` / `reviews.review_changed`.
    # Aditivo: el resto de BookBase no los expone en la API.
    rating_avg: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(3, 2), nullable=True)
    )
    rating_count: int = Field(default=0)
    review_count: int = Field(default=0)
