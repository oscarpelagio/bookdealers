"""Tests del bus de eventos in-process (core.events)."""

from app.core.events import DomainEvent, event_bus


async def test_publish_calls_registered_handler():
    received = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    event_bus.subscribe("test.type", handler)
    try:
        await event_bus.publish(DomainEvent(event_type="test.type", payload={"a": 1}))
        assert len(received) == 1
        assert received[0].payload == {"a": 1}
    finally:
        event_bus.unsubscribe("test.type", handler)


async def test_publish_without_handlers_is_noop():
    # No debe lanzar ni hacer nada.
    await event_bus.publish(DomainEvent(event_type="unknown.type", payload={}))


async def test_failing_handler_does_not_block_others():
    calls = []

    async def failing(event: DomainEvent) -> None:
        raise RuntimeError("boom")

    async def ok(event: DomainEvent) -> None:
        calls.append(1)

    event_bus.subscribe("test.fail", failing)
    event_bus.subscribe("test.fail", ok)
    try:
        # El handler roto no debe propagar la excepción al caller.
        await event_bus.publish(DomainEvent(event_type="test.fail", payload={}))
        assert calls == [1]
    finally:
        event_bus.unsubscribe("test.fail", failing)
        event_bus.unsubscribe("test.fail", ok)
