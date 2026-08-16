from enum import Enum


class ActivityVerb(str, Enum):
    """Verbo del log append-only de actividad de usuario."""

    SHELF_UPDATED = "SHELF_UPDATED"
    RATING_ADDED = "RATING_ADDED"
    REVIEW_ADDED = "REVIEW_ADDED"
    FOLLOWED = "FOLLOWED"
    POST = "POST"
    COMMENTED = "COMMENTED"
    LIST_CREATED = "LIST_CREATED"
    GOAL_UPDATED = "GOAL_UPDATED"
    JOINED = "JOINED"
