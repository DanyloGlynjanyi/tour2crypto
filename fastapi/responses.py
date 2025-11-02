"""Response helpers for the minimal FastAPI shim."""

from __future__ import annotations

from typing import Any


class HTMLResponse:
    """Placeholder response wrapper preserving content."""

    media_type = "text/html"

    def __init__(self, content: Any) -> None:
        self.content = content


__all__ = ["HTMLResponse"]
