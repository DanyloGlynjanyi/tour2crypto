"""Minimal uvicorn shim used for offline execution."""

from __future__ import annotations

from typing import Any


def run(app: Any, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Simulate running a server by printing a notice."""

    print(f"[uvicorn] Serving {getattr(app, 'title', 'FastAPI app')} on {host}:{port} (simulated)")


__all__ = ["run"]
