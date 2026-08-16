"""Eventos de dominio emitidos por el módulo social.

En fases posteriores (F8 notificaciones) estos eventos alimentan
notificaciones y, junto al log `activities` (append-only), el feed (F5).
"""

from __future__ import annotations

from app.core.events import DomainEvent

FOLLOW_CREATED = "social.follow_created"
BLOCK_CREATED = "social.block_created"
MUTE_CREATED = "social.mute_created"
REPORT_CREATED = "social.report_created"


def follow_created(follower_id: str, followee_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=FOLLOW_CREATED,
        payload={"follower_id": follower_id, "followee_id": followee_id},
    )


def block_created(blocker_id: str, blocked_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=BLOCK_CREATED,
        payload={"blocker_id": blocker_id, "blocked_id": blocked_id},
    )


def mute_created(muter_id: str, mutee_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=MUTE_CREATED,
        payload={"muter_id": muter_id, "mutee_id": mutee_id},
    )


def report_created(reporter_id: str, report_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=REPORT_CREATED,
        payload={"reporter_id": reporter_id, "report_id": report_id},
    )