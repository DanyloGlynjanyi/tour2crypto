from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Any, Dict, List

import pytest

from t2c_contracts.factories import (
    ApplicationFactory,
    CashbackLedgerEntryFactory,
    TripFactory,
    WalletFactory,
    WithdrawalRequestFactory,
)
from t2c_contracts.validation import CashbackLedgerEntryModel
from t2c_events import (
    EventBus,
    IdempotentConsumer,
    InMemoryIdempotencyStore,
    validate_event,
)
from t2c_events.validators import ValidationError as EventValidationError, get_known_event_types


_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_COUNTER = count()


def _ulid() -> str:
    idx = next(_COUNTER)
    char = _ALPHABET[idx % len(_ALPHABET)]
    return char * 26


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": _ulid(),
        "event_type": event_type,
        "event_time": _iso_now(),
        "payload": payload,
    }


def _application_payload(status: str, *, reason: str | None = None) -> Dict[str, Any]:
    application = ApplicationFactory().build(status=status)
    payload: Dict[str, Any] = {
        "application_id": application["id"],
        "traveler_id": application["traveler_id"],
        "status": status,
    }
    if reason:
        payload["reason"] = reason
    return payload


def _trip_payload(status: str, *, reason: str | None = None) -> Dict[str, Any]:
    trip = TripFactory().build(status=status)
    payload: Dict[str, Any] = {
        "trip_id": trip["id"],
        "traveler_id": trip["traveler_id"],
        "status": status,
    }
    if status == "planned":
        payload["booking_reference"] = "BOOKING"
    if status == "completed":
        payload["completed_at"] = _iso_now()
    if reason:
        payload["reason"] = reason
    return payload


def _ledger_payload(entry_type: str, *, reason: str | None = None) -> Dict[str, Any]:
    ledger_entry = CashbackLedgerEntryFactory().build(entry_type=entry_type)
    payload: Dict[str, Any] = {
        "ledger_entry_id": ledger_entry["id"],
        "wallet_id": ledger_entry["wallet_id"],
        "trip_id": ledger_entry["trip_id"],
        "amount": ledger_entry["amount"],
        "entry_type": entry_type,
    }
    if reason:
        payload["reason"] = reason
    return payload


def _withdrawal_payload(
    *,
    reason: str | None = None,
    transaction_id: str | None = None,
    lock_id: str | None = None,
    include_destination: bool = False,
) -> Dict[str, Any]:
    withdrawal = WithdrawalRequestFactory().build()
    payload: Dict[str, Any] = {
        "withdrawal_request_id": withdrawal["id"],
        "wallet_id": withdrawal["wallet_id"],
        "amount": withdrawal["requested_amount"],
    }
    if transaction_id:
        payload["transaction_id"] = transaction_id
    if reason:
        payload["reason"] = reason
    if lock_id:
        payload["lock_id"] = lock_id
    if include_destination and "destination_address" in withdrawal:
        payload.setdefault("destination_address", withdrawal["destination_address"])
    return payload


def _wallet_payload(*, reason: str | None = None, note: str | None = None) -> Dict[str, Any]:
    wallet = WalletFactory().build()
    payload: Dict[str, Any] = {"wallet_id": wallet["id"]}
    if reason:
        payload["reason"] = reason
    if note:
        payload["note"] = note
    return payload


def _event_builders() -> Dict[str, Dict[str, Any]]:
    return {
        "application_created": _build_event("application_created", _application_payload("submitted")),
        "application_approved": _build_event("application_approved", _application_payload("approved")),
        "application_rejected": _build_event(
            "application_rejected",
            _application_payload("rejected", reason="Insufficient data"),
        ),
        "trip_booked": _build_event(
            "trip_booked",
            _trip_payload("planned"),
        ),
        "trip_completed": _build_event(
            "trip_completed",
            _trip_payload("completed"),
        ),
        "trip_cancelled": _build_event(
            "trip_cancelled",
            _trip_payload("cancelled", reason="Weather"),
        ),
        "ledger_cashback_accrued": _build_event(
            "ledger_cashback_accrued",
            _ledger_payload("cashback"),
        ),
        "ledger_cashback_reversed": _build_event(
            "ledger_cashback_reversed",
            _ledger_payload("adjustment", reason="Trip cancelled"),
        ),
        "withdrawal_requested": _build_event(
            "withdrawal_requested",
            _withdrawal_payload(include_destination=True),
        ),
        "withdrawal_locked": _build_event(
            "withdrawal_locked",
            _withdrawal_payload(lock_id=_ulid()),
        ),
        "withdrawal_paid": _build_event(
            "withdrawal_paid",
            _withdrawal_payload(transaction_id="TX123456"),
        ),
        "withdrawal_rejected": _build_event(
            "withdrawal_rejected",
            _withdrawal_payload(reason="Compliance"),
        ),
        "wallet_frozen": _build_event(
            "wallet_frozen",
            _wallet_payload(reason="Suspicious activity"),
        ),
        "wallet_reactivated": _build_event(
            "wallet_reactivated",
            _wallet_payload(note="Manual review complete"),
        ),
    }


def test_all_event_schemas_accept_valid_payloads() -> None:
    builders = _event_builders()
    assert set(builders) == set(get_known_event_types())
    for event in builders.values():
        validate_event(event)


def test_invalid_event_is_rejected() -> None:
    event = _build_event("application_created", {"application_id": "short"})
    with pytest.raises(EventValidationError):
        validate_event(event)


def test_idempotent_consumer_handles_duplicate_events_once() -> None:
    bus = EventBus()
    store = InMemoryIdempotencyStore()
    processed: List[Dict[str, Any]] = []

    def handler(event: Dict[str, Any]) -> None:
        processed.append(event)

    sample_event = _event_builders()["application_approved"]
    consumer = IdempotentConsumer(
        event_type=sample_event["event_type"],
        store=store,
        handler=handler,
        validator=validate_event,
    )
    bus.subscribe(sample_event["event_type"], consumer)

    bus.publish(sample_event)
    bus.publish(sample_event)

    assert len(processed) == 1
    assert store.has(sample_event["event_id"])


def test_trip_completed_triggers_cashback_accrual() -> None:
    bus = EventBus()
    trip_store = InMemoryIdempotencyStore()
    ledger_store = InMemoryIdempotencyStore()
    ledger_entries: List[Dict[str, Any]] = []

    def ledger_handler(event: Dict[str, Any]) -> None:
        payload = event["payload"]
        entry_payload = CashbackLedgerEntryFactory().build(
            id=payload["ledger_entry_id"],
            wallet_id=payload["wallet_id"],
            trip_id=payload["trip_id"],
            amount=payload["amount"],
            entry_type="cashback",
        )
        ledger_entries.append(entry_payload)
        CashbackLedgerEntryModel(**entry_payload)

    ledger_consumer = IdempotentConsumer(
        event_type="ledger_cashback_accrued",
        store=ledger_store,
        handler=ledger_handler,
        validator=validate_event,
    )
    bus.subscribe("ledger_cashback_accrued", ledger_consumer)

    wallet = WalletFactory().build()

    def trip_handler(event: Dict[str, Any]) -> None:
        payload = event["payload"]
        ledger_entry = CashbackLedgerEntryFactory().build(
            wallet_id=wallet["id"],
            trip_id=payload["trip_id"],
            amount="25.00",
            entry_type="cashback",
        )
        ledger_event = _build_event(
            "ledger_cashback_accrued",
            {
                "ledger_entry_id": ledger_entry["id"],
                "wallet_id": ledger_entry["wallet_id"],
                "trip_id": ledger_entry["trip_id"],
                "amount": ledger_entry["amount"],
                "entry_type": "cashback",
            },
        )
        bus.publish(ledger_event)

    trip_consumer = IdempotentConsumer(
        event_type="trip_completed",
        store=trip_store,
        handler=trip_handler,
        validator=validate_event,
    )
    bus.subscribe("trip_completed", trip_consumer)

    trip_event = _event_builders()["trip_completed"]
    trip_event["payload"]["trip_id"] = TripFactory().build(status="completed")["id"]
    bus.publish(trip_event)

    assert len(ledger_entries) == 1
    entry = ledger_entries[0]
    assert entry["wallet_id"] == wallet["id"]
    assert entry["amount"] == "25.00"
