"""Minimal Aiogram types used for simulation."""

from __future__ import annotations

from typing import List


class User:
    """Simplified Telegram user representation."""

    def __init__(self, user_id: str) -> None:
        self.id = user_id


class Message:
    """Simplified message supporting `answer`."""

    def __init__(self, text: str = "", from_user: User | None = None) -> None:
        self.text = text
        self.from_user = from_user or User("anonymous")
        self.responses: List[str] = []

    async def answer(self, text: str) -> None:
        self.responses.append(text)
