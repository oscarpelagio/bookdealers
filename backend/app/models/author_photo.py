"""Model de dades per a la cache de fotos d'autors."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class AuthorPhoto(SQLModel, table=True):
    """Foto d'un autor, cacheada per no re-consultar les fonts cada vegada.

    `status` val `found` (hi ha foto a `photo_url`) o `missing` (no s'ha
    trobat res; s'emmaga igualment per no repetir el scraping).
    """
    __tablename__ = "author_photos"

    author_key: str = Field(primary_key=True)
    photo_url: str | None = Field(default=None)
    source: str | None = Field(default=None)
    status: str = Field(default="missing")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)