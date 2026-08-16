from enum import Enum


class CollaboratorRole(str, Enum):
    """Rol de un colaborador en una lista (FASE 7)."""

    EDITOR = "EDITOR"
    VIEWER = "VIEWER"