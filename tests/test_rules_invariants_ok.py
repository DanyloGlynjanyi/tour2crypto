from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from itertools import count

from t2c_contracts.factories import TripFactory, WalletFactory
from t2c_logic import (
    bus,
    get_wallet_balance,
    register_wallet,
    reset_state,
    rules_ledger,
    set_trip_reward,
)
from t2c_rules import assert_invariants, compute_available

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


def _withdrawal_requested_event(wallet_id: str, request_id: str, amount: str) -> dict:
    return {
        "event_id": _ulid(),
        "event_type": "withdrawal_requested",
        "event_time": _iso_now(),
        "payload": {
            "withdrawal_request_id": request_id,
            "wallet_id": wallet_id,
            "amount": amount,
        },
    }


def _withdrawal_paid_event(wallet_id: str, request_id: str, amount: str) -> dict:
    return {
        "event_id": _ulid(),
        "event_type": "withdrawal_paid",
        "event_time": _iso_now(),
        "payload": {
            "withdrawal_request_id": request_id,
            "wallet_id": wallet_id,
            "amount": amount,
            "transaction_id": "TX-lock-flow",
        },
    }


def test_happy_path_invariants_hold() -> None:
    reset_state()

    wallet_payload = WalletFactory().build()
    wallet = register_wallet(wallet_payload)

    trip = TripFactory().build(status="completed", traveler_id=wallet.owner_id)
    reward = Decimal("55.00")
    set_trip_reward(trip["id"], reward)

    bus.publish(_trip_completed_event(trip["id"], trip["traveler_id"]))
    assert compute_available(rules_ledger) == reward

    request_id = _ulid()
    locked_amount = Decimal("20.00")
    bus.publish(_withdrawal_requested_event(wallet.id, request_id, f"{locked_amount:.2f}"))
    assert compute_available(rules_ledger) == reward - locked_amount

    payout_amount = Decimal("20.00")
    bus.publish(_withdrawal_paid_event(wallet.id, request_id, f"{payout_amount:.2f}"))

    final_available = compute_available(rules_ledger)
    assert final_available == reward - payout_amount
    assert get_wallet_balance(wallet.id) == f"{reward - payout_amount:.2f}"

    assert_invariants(rules_ledger)
