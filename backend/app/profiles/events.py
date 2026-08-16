"""Eventos de dominio emitidos por el módulo profiles."""

from __future__ import annotations

import uuid

from app.core.events import DomainEvent


def profile_updated(user_id: uuid.UUID) -> DomainEvent:
    return DomainEvent(
        event_type="profiles.updated",
        payload={"user_id": str(user_id)},
    )


def reading_goal_created(
    user_id: uuid.UUID, goal_id: uuid.UUID, year: int
) -> DomainEvent:
    return DomainEvent(
        event_type="profiles.reading_goal_created",
        payload={"user_id": str(user_id), "goal_id": str(goal_id), "year": year},
    )


def reading_goal_updated(
    user_id: uuid.UUID, goal_id: uuid.UUID, year: int
) -> DomainEvent:
    return DomainEvent(
        event_type="profiles.reading_goal_updated",
        payload={"user_id": str(user_id), "goal_id": str(goal_id), "year": year},
    )


def reading_goal_deleted(user_id: uuid.UUID, year: int) -> DomainEvent:
    return DomainEvent(
        event_type="profiles.reading_goal_deleted",
        payload={"user_id": str(user_id), "year": year},
    )
