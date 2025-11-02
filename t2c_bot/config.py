"""Configuration helpers for the Tour2Crypto bot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    """Static configuration used for offline simulation."""

    token: str = "FAKE_TOKEN_FOR_OFFLINE"
    mode: str = "simulation"
    admin_chat_id: int = 0


def get_config() -> BotConfig:
    """Return the default bot configuration."""

    return BotConfig()
