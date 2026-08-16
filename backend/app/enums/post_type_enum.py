from enum import Enum


class PostType(str, Enum):
    """Tipo de publicación de un post."""

    TEXT = "TEXT"
    BOOK_SHARE = "BOOK_SHARE"
    MEDIA = "MEDIA"