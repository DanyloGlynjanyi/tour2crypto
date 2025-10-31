"""Minimal JSON Schema validator for Tour2Crypto."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict

__all__ = ["Draft202012Validator", "ValidationError"]


class ValidationError(ValueError):
    """Raised when validation fails."""


@dataclass
class Draft202012Validator:
    schema: Dict[str, Any]

    def validate(self, instance: Dict[str, Any]) -> None:
        if not isinstance(instance, dict):
            raise ValidationError("Instance must be a JSON object")
        schema = self.schema
        properties: Dict[str, Dict[str, Any]] = schema.get("properties", {})
        required = schema.get("required", [])
        additional = schema.get("additionalProperties", True)

        for field in required:
            if field not in instance:
                raise ValidationError(f"Missing required field: {field}")

        if additional is False:
            for key in instance:
                if key not in properties:
                    raise ValidationError(f"Unexpected property: {key}")

        for key, value in instance.items():
            if key not in properties:
                continue
            prop = properties[key]
            self._validate_property(key, value, prop)

    def _validate_property(self, key: str, value: Any, prop: Dict[str, Any]) -> None:
        expected_type = prop.get("type")
        if expected_type == "string" and value is not None and not isinstance(value, str):
            raise ValidationError(f"Field '{key}' must be a string")
        if expected_type == "object" and not isinstance(value, dict):
            raise ValidationError(f"Field '{key}' must be an object")

        if "minLength" in prop and isinstance(value, str) and len(value) < prop["minLength"]:
            raise ValidationError(f"Field '{key}' is shorter than minimum length")

        pattern = prop.get("pattern")
        if pattern and isinstance(value, str):
            if not re.fullmatch(pattern, value):
                raise ValidationError(f"Field '{key}' does not match pattern")

        enum = prop.get("enum")
        if enum is not None and value not in enum:
            raise ValidationError(f"Field '{key}' must be one of {enum}")

        const = prop.get("const")
        if const is not None and value != const:
            raise ValidationError(f"Field '{key}' must equal {const}")

        if isinstance(value, dict) and prop.get("type") == "object":
            nested_schema = {
                "properties": prop.get("properties", {}),
                "required": prop.get("required", []),
                "additionalProperties": prop.get("additionalProperties", True),
            }
            Draft202012Validator(nested_schema).validate(value)
