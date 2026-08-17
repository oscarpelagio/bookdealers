"""Model genèric de llista procedent d'una font web (La Central, etc.)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class SourceList(SQLModel, table=True):
    """Una llista curada publicada en una web (article d'un blog, etc.).

    `source` identifica la procedència (ex. 'lacentral') i `slug` és
    l'identificador dins de la font. La combinació (source, slug) és única.
    """

    __tablename__ = "sourced_lists"
    __table_args__ = (
        UniqueConstraint("source", "slug", name="uq_sourced_lists_source_slug"),
    )

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(description="Procedència, ex. 'lacentral'")
    slug: str = Field(index=True, description="Identificador de la URL, ex. 'eclipsis-192672'")
    url: str = Field(description="URL completa de la llista")
    tipo: str | None = Field(default=None, description="Categoria, ex. 'Temàtica'")
    titulo: str = Field(description="Títol de la llista")
    subtitulo: str | None = Field(default=None, description="Subtítol curt, ex. 'Quedant tot escur com si fos de nit'")
    intro: str | None = Field(default=None, description="Intro citada («...»)")
    autor: str | None = Field(default=None, description="Autor sense el prefix 'Per '")
    fecha: str | None = Field(default=None, description="Data com apareix, ex. '26.7.2026'")
    cuerpo: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Cos de la llista en text pla",
    )
    portada_url: str | None = Field(default=None, description="URL de la imatge de portada")
    status: str = Field(default="pending", description="pending | done")
    fetched_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )