"""Validation helpers built on top of JSON Schema."""

from __future__ import annotations

from typing import Any, Callable, Dict

from jsonschema import Draft202012Validator, ValidationError
from jsonschema.protocols import Validator
from pydantic import BaseModel, Field, validator

from .schemas import (
    APPLICATION_SCHEMA,
    AUDIT_EVENT_SCHEMA,
    CASHBACK_LEDGER_ENTRY_SCHEMA,
    ISO8601_UTC_PATTERN,
    MONEY_PATTERN,
    TRIP_SCHEMA,
    ULID_PATTERN,
    WALLET_SCHEMA,
    WITHDRAWAL_REQUEST_SCHEMA,
)

__all__ = [
    "ValidationError",
    "ApplicationModel",
    "AuditEventModel",
    "CashbackLedgerEntryModel",
    "TripModel",
    "WalletModel",
    "WithdrawalRequestModel",
    "validate_application",
    "validate_audit_event",
    "validate_cashback_ledger_entry",
    "validate_trip",
    "validate_wallet",
    "validate_withdrawal_request",
]

ValidatorFunc = Callable[[Dict[str, Any]], None]


def _compile_validator(schema: Dict[str, Any]) -> Validator:
    return Draft202012Validator(schema)


def _build_validation_function(schema: Dict[str, Any]) -> ValidatorFunc:
    validator_instance = _compile_validator(schema)

    def _validate(payload: Dict[str, Any]) -> None:
        validator_instance.validate(payload)

    return _validate


validate_trip = _build_validation_function(TRIP_SCHEMA)
validate_application = _build_validation_function(APPLICATION_SCHEMA)
validate_wallet = _build_validation_function(WALLET_SCHEMA)
validate_cashback_ledger_entry = _build_validation_function(CASHBACK_LEDGER_ENTRY_SCHEMA)
validate_withdrawal_request = _build_validation_function(WITHDRAWAL_REQUEST_SCHEMA)
validate_audit_event = _build_validation_function(AUDIT_EVENT_SCHEMA)


class TripModel(BaseModel):
    """Pydantic representation of a Trip."""

    id: str = Field(regex=ULID_PATTERN)
    traveler_id: str = Field(regex=ULID_PATTERN)
    application_id: str | None = Field(default=None, regex=ULID_PATTERN)
    destination: str
    start_at: str = Field(regex=ISO8601_UTC_PATTERN)
    end_at: str = Field(regex=ISO8601_UTC_PATTERN)
    created_at: str = Field(regex=ISO8601_UTC_PATTERN)
    status: str = Field(regex=r"^(planned|completed|cancelled)$")
    metadata: Dict[str, Any] | None = None


class ApplicationModel(BaseModel):
    id: str = Field(regex=ULID_PATTERN)
    traveler_id: str = Field(regex=ULID_PATTERN)
    trip_type: str
    submitted_at: str = Field(regex=ISO8601_UTC_PATTERN)
    status: str = Field(regex=r"^(draft|submitted|approved|rejected)$")
    notes: str | None = None


class WalletModel(BaseModel):
    id: str = Field(regex=ULID_PATTERN)
    owner_id: str = Field(regex=ULID_PATTERN)
    currency: str = Field(regex=r"^USDT$")
    created_at: str = Field(regex=ISO8601_UTC_PATTERN)
    description: str | None = None


class CashbackLedgerEntryModel(BaseModel):
    id: str = Field(regex=ULID_PATTERN)
    wallet_id: str = Field(regex=ULID_PATTERN)
    trip_id: str = Field(regex=ULID_PATTERN)
    amount: str = Field(regex=MONEY_PATTERN)
    entry_type: str = Field(regex=r"^(cashback|adjustment|withdrawal)$")
    occurred_at: str = Field(regex=ISO8601_UTC_PATTERN)
    description: str | None = None
    reference: str | None = None

    @property
    def signed_amount(self) -> str:
        return self.amount


class WithdrawalRequestModel(BaseModel):
    id: str = Field(regex=ULID_PATTERN)
    wallet_id: str = Field(regex=ULID_PATTERN)
    requested_amount: str = Field(regex=MONEY_PATTERN)
    status: str = Field(regex=r"^(pending|approved|rejected|processed)$")
    requested_at: str = Field(regex=ISO8601_UTC_PATTERN)
    processed_at: str | None = Field(default=None, regex=ISO8601_UTC_PATTERN)
    destination_address: str | None = None

    @validator("destination_address")
    def _destination_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 8:
            raise ValueError("destination_address must be at least 8 characters long")
        return value


class AuditEventModel(BaseModel):
    id: str = Field(regex=ULID_PATTERN)
    actor_id: str = Field(regex=ULID_PATTERN)
    entity_type: str
    entity_id: str = Field(regex=ULID_PATTERN)
    action: str
    payload: Dict[str, Any]
    created_at: str = Field(regex=ISO8601_UTC_PATTERN)
    ip_address: str | None = None
