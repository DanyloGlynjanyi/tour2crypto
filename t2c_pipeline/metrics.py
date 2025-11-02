"""Simple counters for the asynchronous event pipeline."""

from __future__ import annotations

from typing import Dict

from t2c_core import metrics as core_metrics


def increment_processed_ok() -> None:
    core_metrics.inc("events_processed")


def increment_retried() -> None:
    core_metrics.inc("events_retried")


def increment_dead_lettered() -> None:
    core_metrics.inc("events_deadletter")


def snapshot() -> Dict[str, int]:
    counters = core_metrics.snapshot()
    return {
        "processed_ok": counters.get("events_processed", 0),
        "retried": counters.get("events_retried", 0),
        "dead_lettered": counters.get("events_deadletter", 0),
    }


def reset_metrics() -> None:
    core_metrics.reset()


__all__ = [
    "increment_processed_ok",
    "increment_retried",
    "increment_dead_lettered",
    "snapshot",
    "reset_metrics",
]
