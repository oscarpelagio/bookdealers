from datetime import datetime
from sqlmodel import Field, SQLModel, UniqueConstraint

class Catalog(SQLModel, table=True):
    __tablename__ = "catalogs"
    __table_args__ = (UniqueConstraint("service", "name", name="unique_catalog"),)

    id: int | None = Field(default=None, primary_key=True)
    service: str
    name: str
    url: str
    port: int | None
    base: str | None
    link: str | None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
