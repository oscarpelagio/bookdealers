from enum import Enum


class ReportTarget(str, Enum):
    """Tipo de objeto que puede ser reportado (polimórfico, sin FK)."""

    USER = "USER"
    POST = "POST"
    COMMENT = "COMMENT"
    REVIEW = "REVIEW"
    LIST = "LIST"
