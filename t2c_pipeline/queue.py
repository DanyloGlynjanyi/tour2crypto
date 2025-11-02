"""Async queue primitives for the event pipeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

EventEnvelope = Dict[str, Any]
EventPayload = Dict[str, Any]


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AsyncEventQueue:
    """A lightweight asyncio-backed queue for event envelopes."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[EventEnvelope] = asyncio.Queue()

    def _make_envelope(self, event: EventPayload) -> EventEnvelope:
        return {"event": event, "retries": 0, "published_at": _iso_now()}

    async def put(self, event: EventPayload) -> None:
        """Push a new event onto the queue."""

        await self._queue.put(self._make_envelope(event))

    async def put_envelope(self, envelope: EventEnvelope) -> None:
        """Requeue an existing envelope (e.g., for retries)."""

        await self._queue.put(envelope)

    async def get(self) -> EventEnvelope:
        """Retrieve the next envelope, waiting if necessary."""

        envelope = await self._queue.get()
        return envelope

    def empty(self) -> bool:
        return self._queue.empty()

    def qsize(self) -> int:
        return self._queue.qsize()


__all__ = ["AsyncEventQueue", "EventEnvelope", "EventPayload"]
