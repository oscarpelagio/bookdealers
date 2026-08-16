"""Model de la relació article del blog de La Central ↔ llibres.

Es guarda el títol i l'autor normalitzats (per a la cerca "apareix a" per SQL,
comparant títol + autor), i opcionalment el `book_id` del primer resultat
resolt per Z39.50 (igual que fa la importació del CSV). L'article_id +
posicion donen l'ordre dins de la llista del post.
"""

from sqlmodel import Field, SQLModel


class CentralBlogArticleBook(SQLModel, table=True):
    """Un llibre dins de la llista d'un article de La Central."""

    __tablename__ = "central_blog_article_book"

    id: int | None = Field(default=None, primary_key=True)
    article_id: int = Field(
        foreign_key="central_blog_article.id",
        index=True,
        description="FK al post del blog",
    )
    posicion: int = Field(default=0, description="Ordre dins de la llista de l'article")
    titulo_normalizado: str = Field(
        description="Títol normalitzat (minuscules, sense accents ni puntuació)"
    )
    autor_normalizado: str = Field(
        description="Autor normalitzat 'nombre apellido' (minuscules, sense accents)"
    )
    book_id: int | None = Field(
        default=None,
        foreign_key="books.id",
        index=True,
        description="Primer llibre del catàleg resolt per Z39.50 (cache de la cerca)",
    )