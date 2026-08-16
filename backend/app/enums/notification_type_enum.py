from enum import Enum


class NotificationType(str, Enum):
    """Tipo de notificación (FASE 8)."""

    FOLLOW = "FOLLOW"
    REVIEW_LIKE = "REVIEW_LIKE"
    COMMENT = "COMMENT"
    MENTION = "MENTION"
    POST_LIKE = "POST_LIKE"
    POST_ON_BOOK = "POST_ON_BOOK"
    GOAL = "GOAL"
    SYSTEM = "SYSTEM"