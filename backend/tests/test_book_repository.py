"""Tests del BookRepository: dedup per normal_title i fusió de portades/holdings."""

from datetime import date

from app.crud import BookRepository
from app.models import Book
from app.schemas import BookBase

PORTADESBD = "https://portadesbd.diba.cat/img.php?i=bib_00000064"
SMALL_PORTADESBD = PORTADESBD + "&m=g"


def _repo() -> BookRepository:
    return BookRepository(db=None)


def _bookbase(
    title,
    *,
    thumbnail=None,
    small_thumbnail=None,
    pub_date=None,
    author="autor",
    holdings_count=None,
):
    return BookBase(
        title=title,
        author=author,
        language="cat",
        normal_title=title,
        normal_author=author,
        thumbnail=thumbnail,
        small_thumbnail=small_thumbnail,
        publisher_date=pub_date,
        holdings_count=holdings_count,
    )


def _db_book(**overrides) -> Book:
    data = dict(
        title="Titol",
        author="autor",
        language="cat",
        normal_title="titol",
        normal_author="autor",
    )
    data.update(overrides)
    return Book(**data)


async def test_dedup_prefers_candidate_with_cover():
    without_cover = _bookbase("T", pub_date=date(2020, 1, 1))
    with_cover = _bookbase("T", thumbnail="https://real.com/cover.jpg", pub_date=date(2010, 1, 1))

    result = _repo()._dedup_batch([without_cover, with_cover])

    assert result[("T", "autor", "cat")] is with_cover


async def test_dedup_keeps_recent_when_both_have_cover():
    older = _bookbase("T", thumbnail="https://real.com/a.jpg", pub_date=date(2010, 1, 1))
    newer = _bookbase("T", thumbnail="https://real.com/b.jpg", pub_date=date(2020, 1, 1))

    result = _repo()._dedup_batch([older, newer])

    assert result[("T", "autor", "cat")] is newer


async def test_merge_replaces_legacy_portadesbd_cover_with_validated():
    db_book = _db_book(thumbnail=PORTADESBD, small_thumbnail=SMALL_PORTADESBD)
    incoming = _bookbase("Titol", thumbnail="https://real.com/cover.jpg", small_thumbnail=None)

    merged = await _repo()._merge(db_book, incoming)

    assert merged.thumbnail == "https://real.com/cover.jpg"


async def test_merge_does_not_overwrite_non_portadesbd_cover():
    db_book = _db_book(thumbnail="https://books.google.com/cover.jpg")
    incoming = _bookbase("Titol", thumbnail=PORTADESBD)

    merged = await _repo()._merge(db_book, incoming)

    assert merged.thumbnail == "https://books.google.com/cover.jpg"


async def test_merge_keeps_current_cover_when_incoming_is_none():
    db_book = _db_book(thumbnail=PORTADESBD)
    incoming = _bookbase("Titol", thumbnail=None)

    merged = await _repo()._merge(db_book, incoming)

    assert merged.thumbnail == PORTADESBD


async def test_merge_fills_holdings_when_incoming_has_them():
    db_book = _db_book(holdings_count=None)
    incoming = _bookbase("Titol", holdings_count=28)

    merged = await _repo()._merge(db_book, incoming)

    assert merged.holdings_count == 28


async def test_merge_keeps_current_holdings_when_incoming_is_none():
    db_book = _db_book(holdings_count=28)
    incoming = _bookbase("Titol", holdings_count=None)

    merged = await _repo()._merge(db_book, incoming)

    assert merged.holdings_count == 28
