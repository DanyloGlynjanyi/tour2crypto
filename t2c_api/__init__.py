"""FastAPI application for the Tour2Crypto dashboard."""

from __future__ import annotations

from pathlib import Path

from .app import create_app

__all__ = ["create_app"]

# Ensure the static directory is packaged.
STATIC_ROOT = Path(__file__).with_name("static")
__all__.append("STATIC_ROOT")
