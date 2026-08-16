from enum import Enum


class MentionTarget(str, Enum):
    """Tipo de contenido donde se detectó una mención."""

    POST = "POST"
    COMMENT = "COMMENT"