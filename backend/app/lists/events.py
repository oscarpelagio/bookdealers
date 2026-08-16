"""Eventos de dominio emitidos por el módulo lists.

En F8 (notificaciones) estos eventos alimentan las notificaciones a los
colaboradores/usuarios implicados.
"""

from __future__ import annotations

from app.core.events import DomainEvent

LIST_CREATED = "lists.list_created"
LIST_UPDATED = "lists.list_updated"
LIST_DELETED = "lists.list_deleted"
LIST_ITEM_ADDED = "lists.list_item_added"
LIST_ITEM_REMOVED = "lists.list_item_removed"
COLLABORATOR_ADDED = "lists.collaborator_added"
COLLABORATOR_UPDATED = "lists.collaborator_updated"
COLLABORATOR_REMOVED = "lists.collaborator_removed"


def list_created(list_id: str, owner_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=LIST_CREATED,
        payload={"list_id": list_id, "owner_id": owner_id},
    )


def list_updated(list_id: str, owner_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=LIST_UPDATED,
        payload={"list_id": list_id, "owner_id": owner_id},
    )


def list_deleted(list_id: str, owner_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=LIST_DELETED,
        payload={"list_id": list_id, "owner_id": owner_id},
    )


def list_item_added(list_id: str, book_id: int, added_by: str) -> DomainEvent:
    return DomainEvent(
        event_type=LIST_ITEM_ADDED,
        payload={"list_id": list_id, "book_id": book_id, "added_by": added_by},
    )


def list_item_removed(list_id: str, book_id: int) -> DomainEvent:
    return DomainEvent(
        event_type=LIST_ITEM_REMOVED,
        payload={"list_id": list_id, "book_id": book_id},
    )


def collaborator_added(list_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=COLLABORATOR_ADDED,
        payload={"list_id": list_id, "user_id": user_id},
    )


def collaborator_updated(list_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=COLLABORATOR_UPDATED,
        payload={"list_id": list_id, "user_id": user_id},
    )


def collaborator_removed(list_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=COLLABORATOR_REMOVED,
        payload={"list_id": list_id, "user_id": user_id},
    )
