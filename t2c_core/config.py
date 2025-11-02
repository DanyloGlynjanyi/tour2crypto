"""Environment configuration loader for Tour2Crypto."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

_ENV_CACHE: Optional[Dict[str, str]] = None


def _env_file() -> Path:
    cwd = Path.cwd()
    env_path = cwd / ".env"
    if env_path.exists():
        return env_path
    example = cwd / "example.env"
    return example


def _parse_env_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _load_cache() -> Dict[str, str]:
    global _ENV_CACHE
    if _ENV_CACHE is None:
        path = _env_file()
        _ENV_CACHE = _parse_env_file(path)
    return _ENV_CACHE


def get(key: str, default: Optional[str] = None) -> Optional[str]:
    """Return the configuration value for ``key``."""

    if key in os.environ:
        return os.environ[key]
    cache = _load_cache()
    return cache.get(key, default)


def get_bool(key: str, default: bool = False) -> bool:
    """Return a boolean configuration value."""

    value = get(key)
    if value is None:
        return default
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def get_int(key: str, default: int) -> int:
    """Return an integer configuration value."""

    value = get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


__all__ = ["get", "get_bool", "get_int"]
