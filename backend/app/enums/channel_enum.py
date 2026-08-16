from enum import Enum


class Channel(str, Enum):
    """Canal de entrega de una notificación (push_queue)."""

    INBOX = "INBOX"
    EMAIL = "EMAIL"
    PUSH = "PUSH"