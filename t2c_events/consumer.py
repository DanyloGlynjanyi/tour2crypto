"""Idempotent event consumer implementation."""

from __future__ import annotations

from typing import Any, Callable, Dict

from .idempotency import IdempotencyStore

HandlerFunc = Callable[[Dict[str, Any]], None]
ValidatorFunc = Callable[[Dict[str, Any]], None]


class IdempotentConsumer:
    """Wrap a handler with idempotency and schema validation."""

    def __init__(
        self,
        event_type: str,
        store: IdempotencyStore,
        handler: HandlerFunc,
        validator: ValidatorFunc,
    ) -> None:
        self.event_type = event_type
        self.store = store
        self.handler = handler
        self.validator = validator

    def __call__(self, event: Dict[str, Any]) -> None:
        event_type = event.get("event_type")
        if event_type != self.event_type:
            raise ValueError(f"Unexpected event type: {event_type!r}")

        event_id = event.get("event_id")
        if not isinstance(event_id, str):
            raise ValueError("event_id must be provided as a string")

        self.validator(event)

        if self.store.has(event_id):
            return

        self.handler(event)
        self.store.set(event_id, event)


__all__ = ["IdempotentConsumer", "HandlerFunc", "ValidatorFunc"]
