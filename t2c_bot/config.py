"""Configuration helpers for the Tour2Crypto bot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from t2c_core import config as core_config


@dataclass(frozen=True)
class BotConfig:
    """Configuration used for bot simulation and future deployments."""

    token: str
    mode: str
    admin_chat_id: int


_cached_config: Optional[BotConfig] = None


def get_config() -> BotConfig:
    """Return the memoized bot configuration derived from .env settings."""

    global _cached_config
    if _cached_config is None:
        token = core_config.get("BOT_TOKEN", "FAKE_TOKEN_FOR_OFFLINE") or "FAKE_TOKEN_FOR_OFFLINE"
        mode = core_config.get("MODE", "simulation") or "simulation"
        admin_chat_id = core_config.get_int("ADMIN_CHAT_ID", 0)
        _cached_config = BotConfig(token=token, mode=mode, admin_chat_id=admin_chat_id)
    return _cached_config


__all__ = ["BotConfig", "get_config"]
