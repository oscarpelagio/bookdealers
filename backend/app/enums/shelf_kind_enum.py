from enum import Enum


class ShelfKind(str, Enum):
    """Tipo de estantería.

    STATUS: las tres estanterías de estado (to-read / currently-reading /
    read). Su contenido se DERIVA de `user_books.status` (ADR-5), no se
    insertan items manualmente.
    CUSTOM: estanterías creadas por el usuario, con items explícitos.
    """

    STATUS = "STATUS"
    CUSTOM = "CUSTOM"
