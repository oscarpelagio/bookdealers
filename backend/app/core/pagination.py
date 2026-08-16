"""Paginación por cursor opaco (keyset pagination).

Se usa un cursor base64 que codifica `(created_at, id)` para paginar de
forma estable aunque se inserten/borren filas entre páginas (a diferencia
de OFFSET). El cursor es opaco para el cliente.

Convención: los endpoints que paginan devuelven
`{"items": [...], "next": <cursor | None>}`.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime

# El cursor codifica el valor de ordenación y el id como separador de
# desempate. Se evita exponer la marca temporal en claro para que el
# cliente no pueda saltarse rangos arbitrarios.
_CURSOR_PREFIX = "bd1"


def encode_cursor(created_at: datetime, id: uuid.UUID | int) -> str:
    """Codifica una posición de página a cursor opaco base64."""
    payload = json.dumps(
        {
            "t": created_at.isoformat(),
            "id": str(id),
        },
        separators=(",", ":"),
    )
    raw = f"{_CURSOR_PREFIX}:{payload}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str | None) -> tuple[datetime, uuid.UUID | int] | None:
    """Decodifica un cursor. Devuelve `None` si es inválido o vacío."""
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        if not raw.startswith(f"{_CURSOR_PREFIX}:"):
            return None
        data = json.loads(raw[len(_CURSOR_PREFIX) + 1 :])
        created_at = datetime.fromisoformat(data["t"])
        raw_id = data["id"]
        try:
            row_id: uuid.UUID | int = uuid.UUID(raw_id)
        except ValueError:
            row_id = int(raw_id)
        return created_at, row_id
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def build_page(items: list, next_cursor: str | None) -> dict:
    """Construye la respuesta de página estándar."""
    return {"items": items, "next": next_cursor}
