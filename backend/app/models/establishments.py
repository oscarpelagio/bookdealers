from datetime import datetime
from sqlmodel import Field, SQLModel, UniqueConstraint

class Establishment(SQLModel, table=True):
    __tablename__ = "establishments"

    id : int | None = Field(default=None, primary_key=True)
    type : str
    name : str
    street: str | None = Field(default=None)
    postal_code: str | None = Field(default=None)
    city: str | None = Field(default=None)
    province: str | None = Field(default=None)
    catalog_id : int = Field(foreign_key="catalogs.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
