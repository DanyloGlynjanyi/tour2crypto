from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from itertools import count

from t2c_contracts.factories import TripFactory, WalletFactory
from t2c_logic import (
    bus,
    get_wallet_balance,
    ledger_entries,
    register_wallet,
    reset_state,
    rules_ledger,
    set_trip_reward,
)
from t2c_rules import compute_available

_COUNTER = count()
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _ulid() -> str:
    idx = next(_COUNTER)
    char = _ALPHABET[idx % len(_ALPHABET)]
    return char * 26


def _iso_now() -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    return timestamp.isoformat().replace("+00:00", "Z")


def _trip_completed_event(trip_id: str, traveler_id: str) -> dict:
    return {
        "event_id": _ulid(),
        "event_type": "trip_completed",
        "event_time": _iso_now(),
        "payload": {
            "trip_id": trip_id,
            "traveler_id": traveler_id,
            "status": "completed",
            "completed_at": _iso_now(),
        },
    }


def test_trip_completed_creates_cashback_entry_and_updates_balance() -> None:
    reset_state()

    trip = TripFactory().build(status="completed")
    wallet_payload = WalletFactory().build(owner_id=trip["traveler_id"])
    wallet = register_wallet(wallet_payload)

    reward = Decimal("42.75")
    set_trip_reward(trip["id"], reward)

    event = _trip_completed_event(trip["id"], trip["traveler_id"])
    bus.publish(event)

    assert len(ledger_entries) == 1
    entry = ledger_entries[0]
    assert entry.wallet_id == wallet.id
    assert entry.trip_id == trip["id"]
    assert entry.amount == f"{reward:.2f}"
    assert entry.entry_type == "cashback"

    balance = get_wallet_balance(wallet.id)
    assert balance == f"{reward:.2f}"
    assert len(rules_ledger) == 1
    rule_entry = rules_ledger[0]
    assert rule_entry["type"] == "cashback_accrual"
    assert compute_available(rules_ledger) == reward
