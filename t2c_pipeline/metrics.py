"""Simple counters for the asynchronous event pipeline."""

from __future__ import annotations

from typing import Dict

_processed_ok = 0
_retried = 0
_dead_lettered = 0


def increment_processed_ok() -> None:
    global _processed_ok
    _processed_ok += 1


def increment_retried() -> None:
    global _retried
    _retried += 1


def increment_dead_lettered() -> None:
    global _dead_lettered
    _dead_lettered += 1


def snapshot() -> Dict[str, int]:
    return {
        "processed_ok": _processed_ok,
        "retried": _retried,
        "dead_lettered": _dead_lettered,
    }


def reset_metrics() -> None:
    global _processed_ok, _retried, _dead_lettered
    _processed_ok = 0
    _retried = 0
    _dead_lettered = 0


__all__ = [
    "increment_processed_ok",
    "increment_retried",
    "increment_dead_lettered",
    "snapshot",
    "reset_metrics",
]
