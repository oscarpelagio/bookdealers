"""Handlers de eventos que mantienen los contadores denormalizados de `books`
(ADR-9).

Se recomputan a partir de los agregados en cada evento (`rating_changed`,
`review_changed`), lo que los hace idempotentes. Se ejecutan tras el commit
de la operación que los generó, en su propia sesión.

`_session_factory` es intercambiable para los tests (apunta a la BD de test).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlmodel import func, select

from app.core.db import async_session as _default_session
from app.core.events import DomainEvent
from app.models import Book
from app.reviews.models import Rating, Review

logger = logging.getLogger(__name__)

_session_factory = _default_session


def set_session_factory(factory) -> None:
    """Override para tests: usar la fábrica de sesiones de la BD de test."""
    global _session_factory
    _session_factory = factory


async def _recompute_rating(book_id: int) -> None:
    async with _session_factory() as db:
        stmt = select(func.count(Rating.id), func.avg(Rating.score)).where(
            Rating.book_id == book_id
        )
        count, avg = (await db.exec(stmt)).one()
        book = await db.get(Book, book_id)
        if book is None:
            return
        book.rating_count = count or 0
        book.rating_avg = Decimal(str(round(float(avg), 2))) if avg is not None else None
        await db.commit()


async def _recompute_review_count(book_id: int) -> None:
    async with _session_factory() as db:
        stmt = select(func.count(Review.id)).where(
            Review.book_id == book_id, Review.deleted_at.is_(None)
        )
        count = (await db.exec(stmt)).one()
        book = await db.get(Book, book_id)
        if book is None:
            return
        book.review_count = count or 0
        await db.commit()


async def on_rating_changed(event: DomainEvent) -> None:
    try:
        await _recompute_rating(event.payload["book_id"])
    except Exception:  # noqa: BLE001 - los handlers no deben romper el flujo
        logger.exception("rating_changed handler failed")


async def on_review_changed(event: DomainEvent) -> None:
    try:
        await _recompute_review_count(event.payload["book_id"])
    except Exception:  # noqa: BLE001 - los handlers no deben romper el flujo
        logger.exception("review_changed handler failed")


_registered = False


def register() -> None:
    """Registra los handlers en el bus (idempotente)."""
    global _registered
    if _registered:
        return
    from app.core.events import event_bus

    from app.reviews.events import RATING_CHANGED, REVIEW_CHANGED

    event_bus.subscribe(RATING_CHANGED, on_rating_changed)
    event_bus.subscribe(REVIEW_CHANGED, on_review_changed)
    _registered = True
