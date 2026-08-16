"""Eventos de dominio emitidos por el módulo reviews.

Los consumidores actualizan los contadores denormalizados de `books`
(ADR-9) y, en fases posteriores, alimentan activity/notificaciones.
"""

from __future__ import annotations

from app.core.events import DomainEvent

RATING_CHANGED = "reviews.rating_changed"
REVIEW_CHANGED = "reviews.review_changed"
REVIEW_LIKED = "reviews.review_liked"
REVIEW_UNLIKED = "reviews.review_unliked"


def rating_changed(book_id: int) -> DomainEvent:
    return DomainEvent(
        event_type=RATING_CHANGED,
        payload={"book_id": book_id},
    )


def review_changed(book_id: int) -> DomainEvent:
    return DomainEvent(
        event_type=REVIEW_CHANGED,
        payload={"book_id": book_id},
    )


def review_liked(review_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=REVIEW_LIKED,
        payload={"review_id": review_id, "user_id": user_id},
    )


def review_unliked(review_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=REVIEW_UNLIKED,
        payload={"review_id": review_id, "user_id": user_id},
    )
