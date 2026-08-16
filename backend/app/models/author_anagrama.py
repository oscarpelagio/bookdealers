"""Model per al volcat d'autors de l'editorial Anagrama.

Cada fila és un autor amb el seu nom, la bio, l'enllaç directe a la foto
(i no el fitxer) i el bloc de "contenido relacionado" (videos/entrevistes,
articles...) serialitzat en `extra`.
"""

from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AuthorAnagrama(SQLModel, table=True):
    """Un autor de l'índex d'autors d'Anagrama (anagrama-ed.es/autores)."""

    __tablename__ = "authors_anagrama"

    slug: str = Field(primary_key=True, description="Ruta de perfil, ex. /autor/abel-max-12")
    name: str = Field(description="Nom complet com es mostra, ex. 'Enriquez, Mariana'")
    description: str | None = Field(default=None, description="Bio (div .prose del perfil)")
    image_url: str | None = Field(default=None, description="Enllaç directe a la foto (no el fitxer)")
    extra: list | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Ítems de 'contenido relacionado': [{tipo, titulo, url, fecha, descripcion, thumbnail}]",
    )
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
