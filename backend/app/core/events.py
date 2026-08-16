"""Bus de eventos de dominio in-process (ADR-7).

Los servicios de dominio publican eventos **después** de confirmar la
transacción (`commit`). Los handlers se registran por módulo y se ejecutan
de forma asíncrona en el mismo proceso.

Sin outbox ni colas externas: a esta escala (monobloque, un worker) el
procesamiento en memoria es suficiente. Si algún día hay varios workers o
se necesita entrega fiable de emails, se migra a outbox + broker sin
cambiar la interfaz `publish`.

Reglas de uso:
- Los eventos se publican tras el commit (no dentro de la transacción).
- Los handlers NUNCA deben lanzar excepciones que rompan la petición:
  un fallo de un handler se loguea y no propaga.
- Los handlers deben ser idempotentes en la medida de lo posible.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.time import utcnow

logger = logging.getLogger(__name__)

DomainEventHandler = Callable[["DomainEvent"], Awaitable[None]]


@dataclass(frozen=True)
class DomainEvent:
    """Evento de dominio inmutable.

    `event_type` es el discriminador por el que los handlers se suscriben
    (p. ej. "profiles.updated", "reviews.created").
    `payload` contiene los datos relevantes para los handlers.
    """

    event_type: str
    payload: dict
    occurred_at: datetime = field(default_factory=utcnow)


class EventBus:
    """Registra handlers y publica eventos en proceso."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[DomainEventHandler]] = {}

    def subscribe(self, event_type: str, handler: DomainEventHandler) -> None:
        """Registra un handler asíncrono para un tipo de evento."""
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: DomainEventHandler) -> None:
        try:
            self._handlers[event_type].remove(handler)
        except (KeyError, ValueError):
            pass

    async def publish(self, event: DomainEvent) -> None:
        """Dispatch del evento a todos los handlers registrados.

        Un handler que falla se loguea pero no rompe la petición ni
        impide a los demás handlers.
        """
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return

        async def _safe(handler: DomainEventHandler) -> None:
            try:
                await handler(event)
            except Exception:  # noqa: BLE001 - los handlers no deben romper el flujo
                logger.exception("Event handler failed for %s", event.event_type)

        await asyncio.gather(*(_safe(h) for h in handlers))


# Singleton compartido por toda la aplicación.
event_bus = EventBus()
