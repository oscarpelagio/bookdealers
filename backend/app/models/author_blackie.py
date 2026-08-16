"""Model per al volcat d'autors de l'editorial Blackie Books.

Cada fila és un autor amb el seu nom, la bio i l'enllaç directe a la foto
(y no el fitxer). `slug` és la part final de la ruta de perfil
(`https://blackiebooks.org/autor/{slug}/`).
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class AuthorBlackie(SQLModel, table=True):
    """Un autor de l'índex d'autors de Blackie Books (blackiebooks.org/autores)."""

    __tablename__ = "authors_blackie"

    slug: str = Field(primary_key=True, description="Slug de perfil, ex. gloria-fuertes")
    name: str = Field(description="Nom complet com es mostra, ex. 'Gloria Fuertes'")
    description: str | None = Field(default=None, description="Bio (div .wp-content del perfil)")
    image_url: str | None = Field(default=None, description="Enllaç directe a la foto (img.wp-post-image)")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)