from enum import Enum


class PushStatus(str, Enum):
    """Estado de un mensaje de la push_queue."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"