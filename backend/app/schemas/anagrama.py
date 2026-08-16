"""Esquemes per a la consulta d'autors d'Anagrama."""

from sqlmodel import SQLModel


class AnagramaRelatedItem(SQLModel):
    """Un ítem de 'contenido relacionado' d'un autor (video, entrevista...)."""

    tipo: str | None = None
    titulo: str | None = None
    url: str | None = None
    fecha: str | None = None
    descripcion: str | None = None
    thumbnail: str | None = None


class AuthorAnagramaLookup(SQLModel):
    """Resultat de la cerca d'un autor a la taula `authors_anagrama`."""

    found: bool = False
    slug: str | None = None
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    extra: list[AnagramaRelatedItem] | None = None
