"""Model per als articles relacionats d'un autor editorial (1:molts).

Cada fila és un ítem de "contingut relacionat" (videos, entrevistes,
articles...) d'un perfil (`author_source`). FK composta a
`author_source(author_key, editorial)` amb `ON DELETE CASCADE`; `posicion`
dona l'ordre original dins de la llista.
"""

from sqlalchemy import ForeignKeyConstraint
from sqlmodel import Field, SQLModel


class AuthorSourceRelated(SQLModel, table=True):
    """Un ítem de contingut relacionat d'un autor editorial."""

    __tablename__ = "author_source_related"
    __table_args__ = (
        ForeignKeyConstraint(
            ["author_key", "editorial"],
            ["author_source.author_key", "author_source.editorial"],
            name="fk_author_source_related_author_key_editorial",
            ondelete="CASCADE",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    author_key: str = Field(index=True, description="FK a author_source.author_key")
    editorial: str = Field(description="FK a author_source.editorial")
    posicion: int = Field(default=0, description="Ordre dins de la llista original")
    tipo: str | None = Field(default=None, description="'Vídeo' | 'Artículo' | ...")
    titulo: str | None = Field(default=None, description="Títol de l'ítem")
    url: str | None = Field(default=None, description="URL de l'ítem")
    fecha: str | None = Field(default=None, description="Data com apareix")
    descripcion: str | None = Field(default=None, description="Descripció curta")
    thumbnail: str | None = Field(default=None, description="Identitat de la miniatura")
    categoria: str | None = Field(default=None, description="Categoria de l'ítem")