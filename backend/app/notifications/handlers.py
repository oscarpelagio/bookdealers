"""Handlers de eventos que crean notificaciones (FASE 8).

Se suscriben a eventos de F4 (social) y F6 (posts) y, si la preferencia
del destinatario lo permite, crean una notificación in-app (o encolan la
entrega EMAIL en `push_queue`). Se ejecutan tras el commit del evento,
en su propia sesión (mismo patrón que `reviews.counters`).

Reglas:
- Nunca notificar al propio actor (follow, self-like, self-comment).
- `in_app_master` apagado → no se crea nada in-app.
- `exceptions` JSONB permite desactivar/activar un tipo concreto.
- `actor_id` se guarda nullable: si el actor se borra, la notificación
  queda anónima (ON DELETE SET NULL).
- Los mensajes son genéricos (sin username) para que el preview siga
  siendo correcto cuando el actor ya no existe.
"""

from __future__ import annotations

import logging
import uuid

from sqlmodel import select

from app.core.db import async_session as _default_session
from app.core.events import DomainEvent
from app.enums import Channel, NotificationType, ObjectType, PushStatus
from app.notifications.models import Notification, NotificationSetting, PushQueue

logger = logging.getLogger(__name__)

_session_factory = _default_session

_MESSAGES = {
    NotificationType.FOLLOW: "Un usuario empezó a seguirte",
    NotificationType.REVIEW_LIKE: "A alguien le gustó tu review",
    NotificationType.COMMENT: "Nuevo comentario en tu post",
    NotificationType.MENTION: "Te mencionaron en una publicación",
    NotificationType.POST_LIKE: "A alguien le gustó tu post",
}

_MESSAGES_BY_OBJECT = {
    ObjectType.COMMENT: "A alguien le gustó tu comentario",
}


def set_session_factory(factory) -> None:
    """Override para tests: usar la fábrica de sesiones de la BD de test."""
    global _session_factory
    _session_factory = factory


def _delivery(setting: NotificationSetting | None, type_: NotificationType) -> dict:
    """Decide entrega in_app/email según la preferencia del usuario."""
    if setting is None:
        return {"in_app": True, "email": False}
    if not setting.in_app_master:
        return {"in_app": False, "email": False}
    exc = setting.exceptions or {}
    conf = exc.get(type_.value) or {}
    in_app = conf.get("in_app", True)
    email = setting.email_digest_enabled and conf.get("email", False)
    return {"in_app": in_app, "email": bool(email)}


def _message(type_: NotificationType, object_type: ObjectType | None) -> str:
    if type_ == NotificationType.POST_LIKE and object_type in _MESSAGES_BY_OBJECT:
        return _MESSAGES_BY_OBJECT[object_type]
    return _MESSAGES.get(type_, "Tienes una nueva notificación")


async def _is_suppressed(db, recipient_id: uuid.UUID, actor_id: uuid.UUID) -> bool:
    """No notificar si hay un bloqueo (cualquier dirección) o el destinatario
    tiene muteado al actor (ADR-4 / producto)."""
    from sqlalchemy import or_

    from app.social.models import Block, Mute

    stmt = select(Block).where(
        or_(
            (Block.blocker_id == recipient_id) & (Block.blocked_id == actor_id),
            (Block.blocker_id == actor_id) & (Block.blocked_id == recipient_id),
        )
    )
    if (await db.exec(stmt)).first() is not None:
        return True
    mute = select(Mute).where(
        (Mute.muter_id == recipient_id) & (Mute.mutee_id == actor_id)
    )
    return (await db.exec(mute)).first() is not None


async def _notify(
    *,
    recipient_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    type_: NotificationType,
    object_type: ObjectType | None = None,
    object_id: uuid.UUID | None = None,
) -> None:
    async with _session_factory() as db:
        if actor_id is not None and await _is_suppressed(db, recipient_id, actor_id):
            return
        stmt = select(NotificationSetting).where(
            NotificationSetting.user_id == recipient_id
        )
        setting = (await db.exec(stmt)).first()
        delivery = _delivery(setting, type_)

        if delivery["in_app"]:
            db.add(
                Notification(
                    recipient_id=recipient_id,
                    actor_id=actor_id,
                    type=type_,
                    object_type=object_type,
                    object_id=object_id,
                    message=_message(type_, object_type),
                )
            )
        if delivery["email"]:
            db.add(
                PushQueue(
                    user_id=recipient_id,
                    channel=Channel.EMAIL,
                    payload={"notification_type": type_.value},
                    status=PushStatus.PENDING,
                    attempts=0,
                )
            )
        await db.commit()


async def on_follow_created(event: DomainEvent) -> None:
    follower_id = uuid.UUID(event.payload["follower_id"])
    followee_id = uuid.UUID(event.payload["followee_id"])
    await _notify(
        recipient_id=followee_id,
        actor_id=follower_id,
        type_=NotificationType.FOLLOW,
    )


async def on_review_liked(event: DomainEvent) -> None:
    from app.reviews.models import Review

    review_id = uuid.UUID(event.payload["review_id"])
    liker_id = uuid.UUID(event.payload["user_id"])
    async with _session_factory() as db:
        review = await db.get(Review, review_id)
        if review is None or review.user_id == liker_id:
            return
        author_id = review.user_id
    await _notify(
        recipient_id=author_id,
        actor_id=liker_id,
        type_=NotificationType.REVIEW_LIKE,
        object_type=ObjectType.REVIEW,
        object_id=review_id,
    )


async def on_post_liked(event: DomainEvent) -> None:
    from app.posts.models import Post

    post_id = uuid.UUID(event.payload["post_id"])
    liker_id = uuid.UUID(event.payload["user_id"])
    async with _session_factory() as db:
        post = await db.get(Post, post_id)
        if post is None or post.author_id == liker_id:
            return
        author_id = post.author_id
    await _notify(
        recipient_id=author_id,
        actor_id=liker_id,
        type_=NotificationType.POST_LIKE,
        object_type=ObjectType.POST,
        object_id=post_id,
    )


async def on_comment_liked(event: DomainEvent) -> None:
    from app.posts.models import Comment

    comment_id = uuid.UUID(event.payload["comment_id"])
    liker_id = uuid.UUID(event.payload["user_id"])
    async with _session_factory() as db:
        comment = await db.get(Comment, comment_id)
        if comment is None or comment.author_id == liker_id:
            return
        author_id = comment.author_id
    await _notify(
        recipient_id=author_id,
        actor_id=liker_id,
        type_=NotificationType.POST_LIKE,
        object_type=ObjectType.COMMENT,
        object_id=comment_id,
    )


async def on_comment_created(event: DomainEvent) -> None:
    from app.posts.models import Post

    post_id = uuid.UUID(event.payload["post_id"])
    commenter_id = uuid.UUID(event.payload["author_id"])
    comment_id = uuid.UUID(event.payload["comment_id"])
    async with _session_factory() as db:
        post = await db.get(Post, post_id)
        if post is None or post.author_id == commenter_id:
            return
        post_author = post.author_id
    await _notify(
        recipient_id=post_author,
        actor_id=commenter_id,
        type_=NotificationType.COMMENT,
        object_type=ObjectType.COMMENT,
        object_id=comment_id,
    )


async def on_mention_detected(event: DomainEvent) -> None:
    from app.posts.models import Comment, Post

    content_type = event.payload["content_type"]
    content_id = uuid.UUID(event.payload["content_id"])
    mentioned_id = uuid.UUID(event.payload["mentioned_user_id"])

    async with _session_factory() as db:
        author_id = None
        if content_type == "POST":
            obj = await db.get(Post, content_id)
            author_id = obj.author_id if obj else None
        elif content_type == "COMMENT":
            obj = await db.get(Comment, content_id)
            author_id = obj.author_id if obj else None
        if author_id is None or author_id == mentioned_id:
            return
    await _notify(
        recipient_id=mentioned_id,
        actor_id=author_id,
        type_=NotificationType.MENTION,
        object_type=ObjectType.POST if content_type == "POST" else ObjectType.COMMENT,
        object_id=content_id,
    )


_registered = False


def register() -> None:
    """Registra los handlers en el bus (idempotente)."""
    global _registered
    if _registered:
        return
    from app.core.events import event_bus

    from app.posts.events import (
        COMMENT_CREATED,
        COMMENT_LIKED,
        MENTION_DETECTED,
        POST_LIKED,
    )
    from app.reviews.events import REVIEW_LIKED
    from app.social.events import FOLLOW_CREATED

    event_bus.subscribe(FOLLOW_CREATED, on_follow_created)
    event_bus.subscribe(REVIEW_LIKED, on_review_liked)
    event_bus.subscribe(POST_LIKED, on_post_liked)
    event_bus.subscribe(COMMENT_LIKED, on_comment_liked)
    event_bus.subscribe(COMMENT_CREATED, on_comment_created)
    event_bus.subscribe(MENTION_DETECTED, on_mention_detected)
    _registered = True
