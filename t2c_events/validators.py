"""Validation helpers for event payloads."""

from __future__ import annotations

from typing import Any, Dict

from jsonschema import Draft202012Validator, ValidationError

from .schemas import load_event_schema, load_events_index


_VALIDATORS: Dict[str, Draft202012Validator] = {}


def _get_validator(event_type: str) -> Draft202012Validator:
    if event_type not in _VALIDATORS:
        schema = load_event_schema(event_type)
        _VALIDATORS[event_type] = Draft202012Validator(schema)
    return _VALIDATORS[event_type]


def validate_event(event: Dict[str, Any]) -> None:
    event_type = event.get("event_type")
    if not isinstance(event_type, str):
        raise ValidationError("event_type must be provided as a string")
    validator = _get_validator(event_type)
    validator.validate(event)


def get_known_event_types() -> tuple[str, ...]:
    index = load_events_index()
    return tuple(sorted(index.keys()))


def validate_event_type(event_type: str, event: Dict[str, Any]) -> None:
    validator = _get_validator(event_type)
    validator.validate(event)


__all__ = ["ValidationError", "validate_event", "validate_event_type", "get_known_event_types"]
