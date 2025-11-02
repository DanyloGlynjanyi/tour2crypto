"""Minimal Bot stub."""

from __future__ import annotations


class Bot:
    """Lightweight bot holder for simulation mode."""

    def __init__(self, token: str) -> None:
        self.token = token

    async def send_message(self, chat_id: str, text: str) -> None:
        """Simulate sending a message by no-op."""

        _ = (chat_id, text)
