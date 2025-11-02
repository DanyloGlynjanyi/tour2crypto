"""Central logging setup for Tour2Crypto."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import get

_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"
_CONFIGURED = False


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = (get("LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    log_file = get("LOG_FILE", "logs/t2c.log") or "logs/t2c.log"
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_FORMAT)

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [file_handler, stream_handler]

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with the shared format and handlers."""

    _configure()
    return logging.getLogger(name)


__all__ = ["get_logger"]
