"""Eventos de dominio emitidos por el módulo posts.

En F8 (notificaciones) estos eventos alimentan las notificaciones; en
adelante, `posts.mention_detected` avisa al usuario mencionado.
"""

from __future__ import annotations

from app.core.events import DomainEvent

POST_CREATED = "posts.post_created"
POST_UPDATED = "posts.post_updated"
POST_DELETED = "posts.post_deleted"
COMMENT_CREATED = "posts.comment_created"
COMMENT_DELETED = "posts.comment_deleted"
POST_LIKED = "posts.post_liked"
POST_UNLIKED = "posts.post_unliked"
COMMENT_LIKED = "posts.comment_liked"
COMMENT_UNLIKED = "posts.comment_unliked"
MENTION_DETECTED = "posts.mention_detected"


def post_created(post_id: str, author_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=POST_CREATED,
        payload={"post_id": post_id, "author_id": author_id},
    )


def post_updated(post_id: str, author_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=POST_UPDATED,
        payload={"post_id": post_id, "author_id": author_id},
    )


def post_deleted(post_id: str, author_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=POST_DELETED,
        payload={"post_id": post_id, "author_id": author_id},
    )


def comment_created(comment_id: str, post_id: str, author_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=COMMENT_CREATED,
        payload={
            "comment_id": comment_id,
            "post_id": post_id,
            "author_id": author_id,
        },
    )


def comment_deleted(comment_id: str, post_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=COMMENT_DELETED,
        payload={"comment_id": comment_id, "post_id": post_id},
    )


def post_liked(post_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=POST_LIKED,
        payload={"post_id": post_id, "user_id": user_id},
    )


def post_unliked(post_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=POST_UNLIKED,
        payload={"post_id": post_id, "user_id": user_id},
    )


def comment_liked(comment_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=COMMENT_LIKED,
        payload={"comment_id": comment_id, "user_id": user_id},
    )


def comment_unliked(comment_id: str, user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=COMMENT_UNLIKED,
        payload={"comment_id": comment_id, "user_id": user_id},
    )


def mention_detected(content_type: str, content_id: str, mentioned_user_id: str) -> DomainEvent:
    return DomainEvent(
        event_type=MENTION_DETECTED,
        payload={
            "content_type": content_type,
            "content_id": content_id,
            "mentioned_user_id": mentioned_user_id,
        },
    )
