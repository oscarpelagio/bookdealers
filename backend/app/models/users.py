from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at : datetime = Field(nullable = True, default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(nullable = True, default_factory=lambda: datetime.now(timezone.utc))
