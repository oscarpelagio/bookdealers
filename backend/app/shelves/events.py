"""Eventos de dominio emitidos por el módulo shelves.

Los consumirá el contexto de actividad/notificaciones (FASES 4/5/8).
"""

from __future__ import annotations

import uuid

from app.core.events import DomainEvent


def user_book_status_changed(
    user_id: uuid.UUID, book_id: int, status: str
) -> DomainEvent:
    return DomainEvent(
        event_type="shelves.user_book_status_changed",
        payload={"user_id": str(user_id), "book_id": book_id, "status": status},
    )


def user_book_removed(user_id: uuid.UUID, book_id: int) -> DomainEvent:
    return DomainEvent(
        event_type="shelves.user_book_removed",
        payload={"user_id": str(user_id), "book_id": book_id},
    )


def reading_progress_updated(
    user_id: uuid.UUID, book_id: int, *, page: int | None, percent: float | None
) -> DomainEvent:
    return DomainEvent(
        event_type="shelves.reading_progress_updated",
        payload={"user_id": str(user_id), "book_id": book_id, "page": page, "percent": percent},
    )


def shelf_created(user_id: uuid.UUID, shelf_id: uuid.UUID) -> DomainEvent:
    return DomainEvent(
        event_type="shelves.shelf_created",
        payload={"user_id": str(user_id), "shelf_id": str(shelf_id)},
    )


def shelf_deleted(user_id: uuid.UUID, shelf_id: uuid.UUID) -> DomainEvent:
    return DomainEvent(
        event_type="shelves.shelf_deleted",
        payload={"user_id": str(user_id), "shelf_id": str(shelf_id)},
    )
