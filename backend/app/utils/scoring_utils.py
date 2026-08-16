from datetime import date

from thefuzz import fuzz

from app.schemas import BookBase
from app.utils import NormalizationUtils


PREFERRED_LANGUAGES = {"cat", "spa"}


def calculate_score(query_title: str | None, query_author: str | None, book: BookBase) -> float:
    q_title = NormalizationUtils.normalize_text(query_title) if query_title else ""
    q_author = NormalizationUtils.normalize_text(query_author) if query_author else ""

    title_score = fuzz.token_set_ratio(q_title, book.normal_title) if q_title else 0
    orig_score = fuzz.token_set_ratio(q_title, book.normal_original_title) if q_title and book.normal_original_title else 0
    author_score = fuzz.token_set_ratio(q_author, book.normal_author) if q_author else 0

    best_title = max(title_score, orig_score * 0.95)

    if q_title and q_author:
        score = best_title * 0.7 + author_score * 0.3
    elif q_title:
        score = float(best_title)
    elif q_author:
        score = float(author_score)
    else:
        score = 0.0

    if book.language in PREFERRED_LANGUAGES:
        score *= 1.2

    return score


def filter_and_sort_books(
    books: list[BookBase],
    title: str | None,
    author: str | None,
    min_score: float = 50,
) -> list[BookBase]:
    if not title and not author:
        return books

    scored: list[tuple[BookBase, float]] = [
        (book, calculate_score(title, author, book)) for book in books
    ]
    filtered = [(book, score) for book, score in scored if score >= min_score]
    filtered.sort(key=lambda x: x[1], reverse=True)
    return [book for book, _ in filtered]


def dedupe_by_original_title_prefer_castellano(
    books: list[BookBase],
) -> list[BookBase]:
    """Deja un único libro por título original.

    Entre variantes de la misma obra, prefiere la edición en castellano (`spa`),
    luego catalán (`cat`) y, a igualdad, la edición más reciente.
    """
    groups: dict[str, list[BookBase]] = {}
    for book in books:
        key = book.normal_original_title or book.normal_title
        groups.setdefault(key, []).append(book)

    result: list[BookBase] = []
    for group in groups.values():
        best = max(
            group,
            key=lambda b: (
                b.language == "spa",
                b.language == "cat",
                b.publisher_date or date(1, 1, 1),
            ),
        )
        result.append(best)
    return result
