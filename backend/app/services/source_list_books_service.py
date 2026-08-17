"""Service per resoldre els llibres de les llistes genèriques de fonts web.

Cada entrada (títol + autor normalitzats) es busca a Z39.50 i es queda amb el
primer resultat, igual que fa la importació del CSV de Goodreads. El `book_id`
resolt es guarda a `sourced_list_books` per no tornar a buscar.

Dedupe: les llistes repeteixen sovint la mateixa obra en diverses edicions i
idiomes. Es deduplica per (titulo_normalizado, autor_normalizado) i, entre els
candidats del mateix conjunt, es prefereix l'edició en català ('cat'); si no,
la castellana ('spa').
"""

import logging

from app.crud import BookRepository, SourceListRepository
from app.models import Book
from app.services.z3950_search_service import Z3950SearchService

logger = logging.getLogger(__name__)

DEFAULT_Z3950_CATALOG = "aladi"

_LANGUAGE_PREFERENCE = ("cat", "spa")


def _author_surname(author_normalizado: str) -> str:
    """Última paraula de l'autor normalitzat ('eva baltasar' → 'baltasar')."""
    return author_normalizado.split()[-1] if author_normalizado else ""


class SourceListBooksService:
    """Resol i exposa els llibres d'una llista genèrica."""

    def __init__(
        self,
        list_repo: SourceListRepository,
        book_repo: BookRepository,
        z3950_search_service: Z3950SearchService,
    ):
        self.list_repo = list_repo
        self.book_repo = book_repo
        self.z3950_search_service = z3950_search_service

    async def resolve_books(self, list_id: int) -> list[Book]:
        """Resol tots els llibres d'una llista i torna els `Book` en ordre.

        Per cada entrada busca per Z39.50 (títol + apellido de l'autor) i es
        queda amb el primer resultat, cacheant el `book_id` a la base de dades.

        Quan la mateixa obra apareix diverses vegades (títol + autor
        normalitzats iguals), es queda amb una única entrada, preferint
        l'edició en català ('cat'); si no, la castellana ('spa').
        """
        entries = await self.list_repo.books_in_list(list_id)
        books: list[Book] = []
        seen: set[tuple[str, str]] = set()
        for entry in entries:
            key = (entry.titulo_normalizado, entry.autor_normalizado)
            if key in seen:
                continue

            if entry.book_id:
                book = await self.book_repo.get_by_id(entry.book_id)
                if book is None:
                    continue
            else:
                title = entry.titulo_normalizado
                surname = _author_surname(entry.autor_normalizado)
                try:
                    saved = await self.z3950_search_service.search_and_process(
                        title, surname, DEFAULT_Z3950_CATALOG, max_results=5
                    )
                except Exception as exc:
                    logger.warning(
                        "Error buscant '%s' per '%s' en llista %s: %s",
                        title,
                        surname,
                        list_id,
                        exc,
                    )
                    continue
                if not saved:
                    continue
                book = self._prefer_book(saved)
                if book is None:
                    continue
                await self.list_repo.set_book_id(entry.id, book.id)

            if book.id is None:
                continue
            seen.add(key)
            books.append(book)
        return books

    @staticmethod
    def _prefer_book(saved: list[Book]) -> Book | None:
        """Tria l'edició preferida entre els resultats d'una obra.

        Preferència per idioma: 'cat', després 'spa', després qualsevol altre.
        A igualtat d'idioma, el primer amb portada vàlida; si no, el primer.
        """
        if not saved:
            return None
        best: Book | None = None
        best_rank = len(_LANGUAGE_PREFERENCE) + 1
        for book in saved:
            lang = (book.language or "").lower()
            rank = (
                _LANGUAGE_PREFERENCE.index(lang)
                if lang in _LANGUAGE_PREFERENCE
                else len(_LANGUAGE_PREFERENCE)
            )
            if best is None or rank < best_rank:
                best, best_rank = book, rank
            elif rank == best_rank:
                best_has_cover = bool(best.thumbnail or best.small_thumbnail)
                candidate_has_cover = bool(book.thumbnail or book.small_thumbnail)
                if candidate_has_cover and not best_has_cover:
                    best = book
        return best