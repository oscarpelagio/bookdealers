"""Esquemes de resposta per a les llistes genèriques de fonts web."""

from sqlmodel import SQLModel, Field


class SourceListResponse(SQLModel):
    """Detall d'una llista (article d'una font web, ex. La Central)."""

    list_id: int
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


class BookAppearsInList(SQLModel):
    """Una llista on apareix un llibre."""

    list_id: int
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