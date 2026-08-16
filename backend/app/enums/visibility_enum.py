from enum import Enum


class Visibility(str, Enum):
    """Visibilidad de una sección o contenido público.

    PUBLIC: cualquiera. FOLLOWERS: solo seguidores + autor.
    PRIVATE: solo el autor.
    """

    PUBLIC = "PUBLIC"
    FOLLOWERS = "FOLLOWERS"
    PRIVATE = "PRIVATE"
