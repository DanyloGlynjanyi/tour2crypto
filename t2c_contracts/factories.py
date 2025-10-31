"""Factories for generating contract fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from random import choices
from typing import Any, Dict

from faker import Faker

from .validation import (
    ApplicationModel,
    AuditEventModel,
    CashbackLedgerEntryModel,
    TripModel,
    WalletModel,
    WithdrawalRequestModel,
)

faker = Faker()

_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _ulid() -> str:
    return "".join(choices(_ULID_ALPHABET, k=26))


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _money(amount: Decimal | None = None) -> str:
    value = amount if amount is not None else Decimal(faker.pydecimal(left_digits=3, right_digits=2, positive=True))
    return f"{value.quantize(Decimal('0.01')):.2f}"


@dataclass
class TripFactory:
    """Factory for Trip payloads."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": _ulid(),
            "traveler_id": _ulid(),
            "application_id": _ulid(),
            "destination": faker.city(),
            "start_at": _iso_now(),
            "end_at": _iso_now(),
            "created_at": _iso_now(),
            "status": faker.random_element(["planned", "completed", "cancelled"]),
            "metadata": {"loyalty": faker.random_element(["gold", "silver", "bronze"])},
        }
        payload.update(overrides)
        TripModel(**payload)
        return payload


@dataclass
class ApplicationFactory:
    """Factory for Application payloads."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": _ulid(),
            "traveler_id": _ulid(),
            "trip_type": faker.random_element(["adventure", "relax", "cultural"]),
            "submitted_at": _iso_now(),
            "status": faker.random_element(["draft", "submitted", "approved", "rejected"]),
            "notes": faker.sentence(),
        }
        payload.update(overrides)
        ApplicationModel(**payload)
        return payload


@dataclass
class WalletFactory:
    """Factory for Wallet payloads."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": _ulid(),
            "owner_id": _ulid(),
            "currency": "USDT",
            "created_at": _iso_now(),
            "description": faker.sentence(nb_words=6),
        }
        payload.update(overrides)
        WalletModel(**payload)
        return payload


@dataclass
class CashbackLedgerEntryFactory:
    """Factory for CashbackLedgerEntry payloads."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": _ulid(),
            "wallet_id": overrides.get("wallet_id", _ulid()),
            "trip_id": overrides.get("trip_id", _ulid()),
            "amount": _money(),
            "entry_type": faker.random_element(["cashback", "adjustment", "withdrawal"]),
            "occurred_at": _iso_now(),
            "description": faker.sentence(),
            "reference": _ulid(),
        }
        payload.update(overrides)
        CashbackLedgerEntryModel(**payload)
        return payload


@dataclass
class WithdrawalRequestFactory:
    """Factory for WithdrawalRequest payloads."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": _ulid(),
            "wallet_id": overrides.get("wallet_id", _ulid()),
            "requested_amount": _money(),
            "status": faker.random_element(["pending", "approved", "rejected", "processed"]),
            "requested_at": _iso_now(),
            "destination_address": faker.bothify(text="USDT####DEST"),
        }
        payload.update(overrides)
        WithdrawalRequestModel(**payload)
        return payload


@dataclass
class AuditEventFactory:
    """Factory for AuditEvent payloads."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": _ulid(),
            "actor_id": _ulid(),
            "entity_type": faker.random_element(["wallet", "trip", "application"]),
            "entity_id": _ulid(),
            "action": faker.random_element(["create", "update", "delete"]),
            "payload": {"details": faker.sentence()},
            "created_at": _iso_now(),
            "ip_address": faker.ipv4_public(),
        }
        payload.update(overrides)
        AuditEventModel(**payload)
        return payload
