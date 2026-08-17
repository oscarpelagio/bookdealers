"""Model de l'article del blog de La Central."""

from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class CentralBlogArticle(SQLModel, table=True):
    """Un post de la categoria temàtiques del blog de La Central."""

    __tablename__ = "central_blog_article"

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True, description="Identificador de la URL, ex. 'eclipsis-192672'")
    url: str = Field(description="URL completa de l'article")
    tipo: str | None = Field(default=None, description="Categoria, ex. 'Temàtica'")
    titulo: str = Field(description="Títol h3 de l'article")
    subtitulo: str | None = Field(default=None, description="Subtítol curt h4, ex. 'Quedant tot escur com si fos de nit'")
    intro: str | None = Field(default=None, description="Blockquote introductori citat («...»)")
    autor: str | None = Field(default=None, description="Author sense el prefix 'Per '")
    fecha: str | None = Field(default=None, description="Data com apareix, ex. '26.7.2026'")
    cuerpo: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Cos de l'article en text pla",
    )
    portada_url: str | None = Field(default=None, description="URL de la imatge de portada")
    status: str = Field(default="pending", description="pending | done")
    fetched_at: datetime | None = Field(default=None)