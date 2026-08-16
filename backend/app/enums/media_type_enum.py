from enum import Enum


class MediaType(str, Enum):
    """Tipo de archivo multimedia asociado a un post."""

    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"