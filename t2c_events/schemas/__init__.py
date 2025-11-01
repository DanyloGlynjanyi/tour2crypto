"""Helpers for loading event schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

SCHEMAS_DIR = Path(__file__).resolve().parent
INDEX_PATH = SCHEMAS_DIR / "events_index.json"


def load_events_index() -> Dict[str, str]:
    with INDEX_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_event_schema(event_type: str) -> Dict[str, object]:
    index = load_events_index()
    try:
        schema_path = SCHEMAS_DIR / index[event_type]
    except KeyError as exc:  # pragma: no cover - protective guard
        raise KeyError(f"Unknown event type: {event_type}") from exc
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


__all__ = ["load_events_index", "load_event_schema", "SCHEMAS_DIR", "INDEX_PATH"]
