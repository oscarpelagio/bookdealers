"""Esquemes per al perfil d'autor unificat (editorials + fallback Wikimedia)."""

from sqlmodel import SQLModel


class PublisherRelatedItem(SQLModel):
    """Un ítem de 'contenido relacionado' d'una editorial (video, artículo...)."""

    tipo: str | None = None
    titulo: str | None = None
    url: str | None = None
    fecha: str | None = None
    descripcion: str | None = None
    thumbnail: str | None = None
    categoria: str | None = None


class AuthorProfileLookup(SQLModel):
    """Resultat de la cerca d'un autor a `author_source`."""

    found: bool = False
    editorial: str | None = None
    slug: str | None = None
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    extra: list[PublisherRelatedItem] | None = None