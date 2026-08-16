"""Model per a fonts editorials d'autors.

Una fila per (autor, editorial): el mateix autor pot estar en diverses
editorials (Anagrama, Penguin...), cadascuna amb la seva bio, foto i
"contenido relacionado" (`extra`). `author_key` és el nom normalitzat
(format "Nombre Apellido", sense accents) per unificar variants de la
mateixa persona ("Irene Solà" / "Solà, Irene").
"""

from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AuthorSource(SQLModel, table=True):
    """Una font editorial d'un autor."""

    __tablename__ = "author_source"

    author_key: str = Field(
        primary_key=True,
        description="Nom normalitzat ('Nombre Apellido', sense accents)",
    )
    editorial: str = Field(
        primary_key=True,
        description="Editorial/font: 'anagrama' | 'penguin'",
    )
    name: str = Field(description="Nom canònic com el mostra l'editorial")
    slug: str | None = Field(default=None, description="Identificador dins de l'editorial")
    description: str | None = Field(default=None, description="Bio del perfil")
    image_url: str | None = Field(default=None, description="Enllaç directe a la foto")
    extra: list | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Contingut relacionat: [{tipo, titulo, url, fecha, descripcion, thumbnail, categoria}]",
    )
    fetched_at: datetime = Field(default_factory=datetime.utcnow)