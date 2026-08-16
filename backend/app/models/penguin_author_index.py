"""Model per a l'índex d'autors de Penguin.

L'índex és lleuger: nom + id + slug (+ miniatura) dels ~16k autors que
llista penguinlibros.com en `/es/5-autores?pageno=N`. Serveix per resoldre
un autor pel seu nom sense depender del cercador Elastico de Penguin (que
no respon a bots): el lookup peresós cerca aquí i descarrega NOMÉS el
perfil triat, persistint-lo a `author_source`.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class PenguinAuthorIndex(SQLModel, table=True):
    """Una entrada de l'índex d'autors de Penguin."""

    __tablename__ = "penguin_author_index"

    author_id: int = Field(primary_key=True)
    name: str = Field(description="Nom com apareix a l'índex (pot ser en majúscules)")
    name_normalized: str = Field(
        index=True, description="Nom normalitzat per cerca ('Nombre Apellido')"
    )
    slug: str = Field(description="Slug de la pàgina de perfil")
    thumb: str | None = Field(default=None, description="Miniatura 300px (static.megustaleer)")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)