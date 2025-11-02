"""Minimal Aiogram 3.x compatible interface for offline simulation."""

from __future__ import annotations

from .bot import Bot
from .dispatcher import Dispatcher
from .router import Router
from .types import Message, User

__all__ = ["Bot", "Dispatcher", "Router", "Message", "User"]
