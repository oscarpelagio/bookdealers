"""Servicio de visibilidad (ADR-4).

Función pura y sin dependencias de modelos para evitar acoplamientos
circulares: cada módulo le pasa los datos que ya conoce (sección de
privacidad, relación con el autor) y esta decide si el contenido es
visible para un espectador.

Reglas transversales (ver documento FASE 0, §0.3):
- El autor siempre ve su propio contenido.
- Un bloqueo oculta el contenido del bloqueado (y viceversa).
- PRIVATE solo lo ve el autor. FOLLOWERS lo ven autor + seguidores.
- Un usuario soft-deleteado o inactivo nunca debe ser visible.

A medida que lleguen módulos nuevos (social, feed) se añaden parámetros
sin cambiar la firma base.
"""

from __future__ import annotations

from app.enums import Visibility


def is_visible(
    section: Visibility,
    *,
    viewer_id,
    author_id,
    is_author: bool | None = None,
    is_follower: bool = False,
    is_blocked: bool = False,
    author_active: bool = True,
) -> bool:
    """Decide si una sección del autor es visible para el espectador."""
    if is_author is None:
        is_author = viewer_id == author_id
    if author_active is False:
        return False
    if is_author:
        return True
    if is_blocked:
        return False
    if section == Visibility.PUBLIC:
        return True
    if section == Visibility.FOLLOWERS:
        return is_follower
    return False
