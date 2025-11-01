"""Protocols for the minimal jsonschema shim."""

from __future__ import annotations

from typing import Protocol


class Validator(Protocol):
    def validate(self, instance: dict) -> None:
        """Validate the given instance."""
