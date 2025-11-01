"""Simple synchronous in-memory event bus."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, Iterable, List

Handler = Callable[[Dict[str, Any]], None]


class EventBus:
    """A lightweight synchronous event bus."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register a handler for the given event type."""

        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def publish(self, event: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""

        event_type = event.get("event_type")
        if event_type is None:
            raise ValueError("event_type is required")

        for handler in list(self._subscribers.get(event_type, [])):
            handler(event)

    def subscribers(self, event_type: str) -> Iterable[Handler]:
        """Return the registered subscribers for inspection/testing."""

        return tuple(self._subscribers.get(event_type, ()))


__all__ = ["EventBus", "Handler"]
