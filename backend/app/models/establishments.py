from datetime import datetime
from sqlmodel import Field, SQLModel, UniqueConstraint

class Establishment(SQLModel, table=True):
    __tablename__ = "establishments"

    id : int | None = Field(default=None, primary_key=True)
    type : str
    name : str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
