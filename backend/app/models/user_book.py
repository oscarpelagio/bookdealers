from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models import ShelfStatus

class UserBook(SQLModel, table=True):
    __tablename__ = "user_books"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="unique_user_book"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    book_id: int = Field(foreign_key="books.id", index=True)
    shelf_status: ShelfStatus = Field(default=ShelfStatus.WANT_TO_READ)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=5000)
    is_favorite: bool = Field(default=False)
    created_at: datetime = Field(nullable = True, default_factory=datetime.utcnow)
    updated_at: datetime = Field(nullable = True, default_factory=datetime.utcnow)
