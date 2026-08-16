"""Utilidades de tiempo compartidas (timezone-aware).

Se mantiene aquí `utcnow` para que los módulos sociales no dependan de
`app.auth.security` (se evita acoplar dominios). Es idéntico en
comportamiento al helper del módulo auth.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Datetime actual timezone-aware en UTC."""
    return datetime.now(timezone.utc)
