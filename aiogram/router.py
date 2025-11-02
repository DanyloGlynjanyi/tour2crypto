"""Minimal Router stub with decorator support."""

from __future__ import annotations

from typing import Any, Callable, Dict, List


class Router:
    """Collect message handlers with optional metadata."""

    def __init__(self, name: str | None = None) -> None:
        self.name = name or "router"
        self.message_handlers: List[Dict[str, Any]] = []

    def message(
        self,
        *,
        commands: set[str] | None = None,
        text: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that registers a message handler."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.message_handlers.append(
                {"callback": func, "commands": commands or set(), "text": text}
            )
            return func

        return decorator
