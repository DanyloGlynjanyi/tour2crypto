"""JSON Schemas for Tour2Crypto contracts."""

from __future__ import annotations

ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"
MONEY_PATTERN = r"^-?\d+\.\d{2}$"
ISO8601_UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"

TRIP_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Trip",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "traveler_id",
        "destination",
        "start_at",
        "end_at",
        "created_at",
        "status",
    ],
    "properties": {
        "id": {"type": "string", "pattern": ULID_PATTERN},
        "traveler_id": {"type": "string", "pattern": ULID_PATTERN},
        "application_id": {"type": "string", "pattern": ULID_PATTERN},
        "destination": {"type": "string", "minLength": 1},
        "start_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "end_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "created_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "status": {"type": "string", "enum": ["planned", "completed", "cancelled"]},
        "metadata": {"type": "object", "additionalProperties": True},
    },
}

APPLICATION_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Application",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "traveler_id",
        "trip_type",
        "submitted_at",
        "status",
    ],
    "properties": {
        "id": {"type": "string", "pattern": ULID_PATTERN},
        "traveler_id": {"type": "string", "pattern": ULID_PATTERN},
        "trip_type": {"type": "string", "minLength": 1},
        "submitted_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "status": {"type": "string", "enum": ["draft", "submitted", "approved", "rejected"]},
        "notes": {"type": "string"},
    },
}

WALLET_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Wallet",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "owner_id",
        "currency",
        "created_at",
    ],
    "properties": {
        "id": {"type": "string", "pattern": ULID_PATTERN},
        "owner_id": {"type": "string", "pattern": ULID_PATTERN},
        "currency": {"type": "string", "const": "USDT"},
        "created_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "description": {"type": "string"},
    },
}

CASHBACK_LEDGER_ENTRY_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CashbackLedgerEntry",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "wallet_id",
        "trip_id",
        "amount",
        "entry_type",
        "occurred_at",
    ],
    "properties": {
        "id": {"type": "string", "pattern": ULID_PATTERN},
        "wallet_id": {"type": "string", "pattern": ULID_PATTERN},
        "trip_id": {"type": "string", "pattern": ULID_PATTERN},
        "amount": {"type": "string", "pattern": MONEY_PATTERN},
        "entry_type": {"type": "string", "enum": ["cashback", "adjustment", "withdrawal"]},
        "occurred_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "description": {"type": "string"},
        "reference": {"type": "string"},
    },
}

WITHDRAWAL_REQUEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "WithdrawalRequest",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "wallet_id",
        "requested_amount",
        "status",
        "requested_at",
    ],
    "properties": {
        "id": {"type": "string", "pattern": ULID_PATTERN},
        "wallet_id": {"type": "string", "pattern": ULID_PATTERN},
        "requested_amount": {"type": "string", "pattern": MONEY_PATTERN},
        "status": {"type": "string", "enum": ["pending", "approved", "rejected", "processed"]},
        "requested_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "processed_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "destination_address": {"type": "string", "minLength": 8},
    },
}

AUDIT_EVENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AuditEvent",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "actor_id",
        "entity_type",
        "entity_id",
        "action",
        "payload",
        "created_at",
    ],
    "properties": {
        "id": {"type": "string", "pattern": ULID_PATTERN},
        "actor_id": {"type": "string", "pattern": ULID_PATTERN},
        "entity_type": {"type": "string", "minLength": 1},
        "entity_id": {"type": "string", "pattern": ULID_PATTERN},
        "action": {"type": "string", "minLength": 1},
        "payload": {"type": "object", "additionalProperties": True},
        "created_at": {"type": "string", "pattern": ISO8601_UTC_PATTERN},
        "ip_address": {"type": "string"},
    },
}

__all__ = [
    "APPLICATION_SCHEMA",
    "AUDIT_EVENT_SCHEMA",
    "CASHBACK_LEDGER_ENTRY_SCHEMA",
    "ISO8601_UTC_PATTERN",
    "MONEY_PATTERN",
    "TRIP_SCHEMA",
    "ULID_PATTERN",
    "WALLET_SCHEMA",
    "WITHDRAWAL_REQUEST_SCHEMA",
]
