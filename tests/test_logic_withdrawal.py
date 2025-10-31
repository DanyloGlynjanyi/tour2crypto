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
    set_trip_reward,
    withdrawal_locks,
)

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
            "transaction_id": "TX999999",
        },
    }


def test_withdrawal_flow_locks_and_pays_out_funds() -> None:
    reset_state()

    wallet_payload = WalletFactory().build()
    wallet = register_wallet(wallet_payload)

    trip = TripFactory().build(status="completed", traveler_id=wallet.owner_id)
    cashback_amount = Decimal("80.00")
    set_trip_reward(trip["id"], cashback_amount)
    bus.publish(_trip_completed_event(trip["id"], trip["traveler_id"]))

    initial_balance = get_wallet_balance(wallet.id)
    assert initial_balance == f"{cashback_amount:.2f}"

    request_id = _ulid()
    requested_amount = Decimal("30.00")
    bus.publish(_withdrawal_requested_event(wallet.id, request_id, f"{requested_amount:.2f}"))

    assert request_id in withdrawal_locks
    assert len(ledger_entries) == 2
    lock_entry = ledger_entries[1]
    assert lock_entry.entry_type == "adjustment"
    assert lock_entry.amount == f"-{requested_amount:.2f}"

    locked_balance = get_wallet_balance(wallet.id)
    assert locked_balance == f"{cashback_amount - requested_amount:.2f}"

    bus.publish(_withdrawal_paid_event(wallet.id, request_id, f"{requested_amount:.2f}"))

    assert request_id not in withdrawal_locks
    # cashback + lock + unlock + payout
    assert len(ledger_entries) == 4
    payout_entry = ledger_entries[-1]
    assert payout_entry.entry_type == "withdrawal"
    assert payout_entry.amount == f"-{requested_amount:.2f}"

    final_balance = get_wallet_balance(wallet.id)
    assert final_balance == f"{cashback_amount - requested_amount:.2f}"
