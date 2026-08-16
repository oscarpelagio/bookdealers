"""Model per a l'índex d'autors de Libros del Asteroide.

L'índex és lleuger: slug + nom dels ~241 autors que llista
librosdelasteroide.com en `/autores`. Serveix per resoldre un autor pel seu
nom i construir la URL de perfil `/autor/{slug}` sense depender de cercador:
el lookup peresós cerca aquí i descarrega NOMÉS el perfil triat, persistint-lo
a `author_source`.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class AsteroideAuthorIndex(SQLModel, table=True):
    """Una entrada de l'índex d'autors de Libros del Asteroide."""

    __tablename__ = "asteroide_author_index"

    slug: str = Field(primary_key=True, description="Slug de la pàgina de perfil")
    name: str = Field(description="Nom com apareix a l'índex, ex. 'Solla Sobral, Lucía'")
    name_normalized: str = Field(
        index=True, description="Nom normalitzat per cerca ('Nombre Apellido')"
    )
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
