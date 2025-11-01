"""Idempotency helpers for event consumption."""

from __future__ import annotations

from typing import Dict, Protocol


class IdempotencyStore(Protocol):
    """Abstract storage for processed event identifiers."""

    def has(self, event_id: str) -> bool:
        """Return True if the event id has already been processed."""

    def set(self, event_id: str, payload: Dict[str, object]) -> None:
        """Record the processed event."""

    def get(self, event_id: str) -> Dict[str, object] | None:
        """Return the stored payload for the processed event if present."""

    def clear(self) -> None:
        """Remove all tracked event identifiers."""


class InMemoryIdempotencyStore:
    """In-memory implementation of :class:`IdempotencyStore`."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, object]] = {}

    def has(self, event_id: str) -> bool:
        return event_id in self._store

    def set(self, event_id: str, payload: Dict[str, object]) -> None:
        self._store[event_id] = payload

    def get(self, event_id: str) -> Dict[str, object] | None:
        return self._store.get(event_id)

    def clear(self) -> None:
        self._store.clear()


__all__ = ["IdempotencyStore", "InMemoryIdempotencyStore"]
