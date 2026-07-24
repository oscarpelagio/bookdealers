from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, UniqueConstraint

from app.enums import AvailabilityStatusEnum

class BookEstablishment(SQLModel, table=True):
    __tablename__ = "book_establishment"
    __table_args__ = (UniqueConstraint("book_id", "establishment_id", "language", name="unique_book_establishment"),)
    id: int | None = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="books.id", index=True)
    establishment_id: int = Field(foreign_key="establishments.id", index=True)
    language: str = Field(index=True)
    status: AvailabilityStatusEnum = Field(default=None, index=True)
    queue: int | None = None
    link: str | None = None
    created_at: datetime = Field(nullable = True, default_factory=datetime.utcnow)
    updated_at: datetime = Field(nullable = True, default_factory=datetime.utcnow)
