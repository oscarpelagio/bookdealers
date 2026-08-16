"""Service per resoldre els llibres de les llistes del blog de La Central.

Cada entrada (títol + autor normalitzats) es busca a Z39.50 i es queda amb el
primer resultat, igual que fa la importació del CSV de Goodreads. El `book_id`
resolt es guarda a `central_blog_article_book` per no tornar a buscar.
"""

import logging

from app.crud import BookRepository, CentralArticleRepository
from app.models import Book
from app.services.z3950_search_service import Z3950SearchService

logger = logging.getLogger(__name__)

DEFAULT_Z3950_CATALOG = "aladi"


def _author_surname(author_normalizado: str) -> str:
    """Última paraula de l'autor normalitzat ('eva baltasar' → 'baltasar')."""
    return author_normalizado.split()[-1] if author_normalizado else ""


class CentralListBooksService:
    """Resol i exposa els llibres d'una llista de La Central."""

    def __init__(
        self,
        central_repo: CentralArticleRepository,
        book_repo: BookRepository,
        z3950_search_service: Z3950SearchService,
    ):
        self.central_repo = central_repo
        self.book_repo = book_repo
        self.z3950_search_service = z3950_search_service

    async def resolve_books(self, article_id: int) -> list[Book]:
        """Resol tots els llibres d'una llista i torna els `Book` en ordre.

        Per cada entrada busca per Z39.50 (títol + apellido de l'autor) i es
        queda amb el primer resultat, cacheant el `book_id` a la base de dades.

        Les llistes solen repetir el mateix llibre en castellà i català; com
        els dos resolen al mateix `Book` (per `normal_title`), es dedupen
        quedant-se amb la primera aparició.
        """
        entries = await self.central_repo.books_in_article(article_id)
        books: list[Book] = []
        seen_titles: set[str] = set()
        for entry in entries:
            if entry.book_id:
                book = await self.book_repo.get_by_id(entry.book_id)
                if book is None:
                    continue
            else:
                title = entry.titulo_normalizado
                surname = _author_surname(entry.autor_normalizado)
                try:
                    saved = await self.z3950_search_service.search_and_process(
                        title, surname, DEFAULT_Z3950_CATALOG, max_results=1
                    )
                except Exception as exc:
                    logger.warning(
                        "Error buscant '%s' per '%s' en llista %s: %s",
                        title,
                        surname,
                        article_id,
                        exc,
                    )
                    continue
                if not saved:
                    continue
                await self.central_repo.set_book_id(entry.id, saved[0].id)
                book = await self.book_repo.get_by_id(saved[0].id)
                if book is None:
                    continue

            key = book.normal_title
            if key and key in seen_titles:
                continue
            seen_titles.add(key)
            books.append(book)
        return books