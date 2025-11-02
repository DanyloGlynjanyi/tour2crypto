"""Shared metrics counters for Tour2Crypto components."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

_COUNTERS: Dict[str, int] = {
    "events_processed": 0,
    "events_retried": 0,
    "events_deadletter": 0,
    "reports_sent": 0,
    "api_requests": 0,
    "bot_actions": 0,
}

_HISTORY_LIMIT = 100


def inc(name: str, value: int = 1) -> None:
    """Increment ``name`` by ``value`` creating the counter if needed."""

    if name not in _COUNTERS:
        _COUNTERS[name] = 0
    _COUNTERS[name] += value


def reset() -> None:
    """Reset all known counters to zero."""

    for key in list(_COUNTERS):
        _COUNTERS[key] = 0


def snapshot() -> Dict[str, int]:
    """Return a copy of the current counters."""

    return dict(_COUNTERS)


def _read_history(path: Path) -> List[Dict[str, Dict[str, int]]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    history = data.get("history", [])
    if isinstance(history, list):
        return [entry for entry in history if isinstance(entry, dict)]
    return []


def dump(path: str = "logs/metrics.json") -> Dict[str, List[Dict[str, Dict[str, int]]]]:
    """Persist the metrics snapshot with a timestamped history."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    history = _read_history(output_path)
    history.append({
        "timestamp": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "counters": snapshot(),
    })
    if len(history) > _HISTORY_LIMIT:
        history = history[-_HISTORY_LIMIT:]

    payload = {"history": history}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


__all__ = ["inc", "reset", "snapshot", "dump"]
