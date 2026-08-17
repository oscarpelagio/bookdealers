"""Model de la relació llista genèrica ↔ llibres.

Es guarda el títol i l'autor normalitzats (per a la cerca "apareix a" per SQL,
comparant títol + autor), i opcionalment el `book_id` del primer resultat
resolt per Z39.50 (igual que fa la importació del CSV). El `list_id` +
posicion donen l'ordre dins de la llista.
"""

from sqlmodel import Field, SQLModel


class SourceListBook(SQLModel, table=True):
    """Un llibre dins de la llista d'una font web."""

    __tablename__ = "sourced_list_books"

    id: int | None = Field(default=None, primary_key=True)
    list_id: int = Field(
        foreign_key="sourced_lists.id",
        index=True,
        description="FK a la llista",
    )
    posicion: int = Field(default=0, description="Ordre dins de la llista")
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