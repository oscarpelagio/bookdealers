"""Esquemes de resposta per a les llistes del blog de La Central."""

from sqlmodel import SQLModel, Field


class BookAppearsInList(SQLModel):
    """Una llista (post del blog) on apareix un llibre."""

    article_id: int
    slug: str
    url: str
    titulo: str
    autor: str | None = None
    fecha: str | None = None
    portada_url: str | None = None
    posicion: int = Field(default=0, description="Posició del llibre dins la llista")


class BookAppearsInResponse(SQLModel):
    """Resposta de 'a on apareix un llibre'."""

    book_id: int
    total: int
    lists: list[BookAppearsInList]


class CentralListResponse(SQLModel):
    """Detall d'una llista (article) del blog de La Central."""

    article_id: int
    slug: str
    url: str
    tipo: str | None = None
    titulo: str
    subtitulo: str | None = None
    intro: str | None = None
    autor: str | None = None
    fecha: str | None = None
    cuerpo: str | None = None
    portada_url: str | None = None