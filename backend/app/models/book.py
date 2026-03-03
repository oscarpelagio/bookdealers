"""Models de dades per a la base de dades."""

from sqlmodel import Field, UniqueConstraint
from datetime import datetime

from app.schemas import BookBase

class Book(BookBase, table=True):
    """Model de base de dades per als llibres."""
    __tablename__ = "books"
    __table_args__ = (UniqueConstraint("title", "author", name="unique_book"),)

    id: int | None = Field(default=None, primary_key=True)
    created_at : datetime = Field(nullable = True, default_factory=datetime.utcnow)
