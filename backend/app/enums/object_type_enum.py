from enum import Enum


class ObjectType(str, Enum):
    """Tipo de objeto al que apunta una actividad (polimórfico)."""

    POST = "POST"
    COMMENT = "COMMENT"
    REVIEW = "REVIEW"
    RATING = "RATING"
    BOOK = "BOOK"
    GOAL = "GOAL"
    USER_BOOK = "USER_BOOK"
