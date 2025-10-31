"""Minimal subset of Pydantic for Tour2Crypto."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, get_type_hints

__all__ = ["BaseModel", "Field", "validator"]


class ValidationError(ValueError):
    """Raised when model validation fails."""


@dataclass
class FieldInfo:
    default: Any
    regex: Optional[str]


_UNSET = object()


def Field(*, default: Any = _UNSET, regex: Optional[str] = None) -> FieldInfo:
    return FieldInfo(default=default, regex=regex)


@dataclass
class ValidatorDef:
    fields: Tuple[str, ...]
    function: Callable[..., Any]


def validator(*fields: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "__pydantic_validator_fields__", fields)
        return func

    return decorator


class BaseModelMeta(type):
    def __new__(mcls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]):
        validators: List[ValidatorDef] = []
        for attr_name, value in list(namespace.items()):
            fields = getattr(value, "__pydantic_validator_fields__", None)
            if fields:
                validators.append(ValidatorDef(tuple(fields), value))
        namespace["__validators__"] = validators

        annotations = namespace.get("__annotations__", {})
        fields_info: Dict[str, FieldInfo] = {}

        for field_name, annotation in annotations.items():
            default_value = namespace.get(field_name, _UNSET)
            if isinstance(default_value, FieldInfo):
                fields_info[field_name] = default_value
                namespace.pop(field_name)
            else:
                fields_info[field_name] = FieldInfo(default=default_value, regex=None)

        namespace["__fields__"] = fields_info
        return super().__new__(mcls, name, bases, namespace)


class BaseModel(metaclass=BaseModelMeta):
    __fields__: Dict[str, FieldInfo]
    __validators__: List[ValidatorDef]

    def __init__(self, **data: Any) -> None:
        hints = get_type_hints(self.__class__)
        values: Dict[str, Any] = {}

        for field_name, field_info in self.__fields__.items():
            value = data.pop(field_name, _UNSET)
            if value is _UNSET:
                if field_info.default is not _UNSET:
                    value = field_info.default
                else:
                    raise ValidationError(f"Missing field '{field_name}'")

            expected_type = hints.get(field_name)
            if expected_type is str and value is not None and not isinstance(value, str):
                raise ValidationError(f"Field '{field_name}' must be a string")

            if field_info.regex and value is not None:
                if not re.fullmatch(field_info.regex, value):
                    raise ValidationError(f"Field '{field_name}' does not match pattern")

            values[field_name] = value

        if data:
            unexpected = ", ".join(sorted(data.keys()))
            raise ValidationError(f"Unexpected fields: {unexpected}")

        for validator_def in self.__validators__:
            for field_name in validator_def.fields:
                current = values.get(field_name)
                new_value = validator_def.function(self.__class__, current)
                values[field_name] = new_value

        for field_name, value in values.items():
            setattr(self, field_name, value)

    def dict(self) -> Dict[str, Any]:
        return {field: getattr(self, field) for field in self.__fields__}
