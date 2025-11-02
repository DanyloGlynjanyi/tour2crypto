"""Event collector helpers for simulating upstream producers."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Dict

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Track withdrawal context so paid events can reference the originating request.
_withdrawal_context: Dict[str, Dict[str, str]] = {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _quantize(amount: str) -> str:
    value = Decimal(amount)
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_DOWN):.2f}"


def _ulid(seed: int | None = None) -> str:
    if seed is not None:
        return (_ALPHABET[seed % len(_ALPHABET)] * 26)[:26]
    now = datetime.now(timezone.utc)
    base = int(now.timestamp() * 1000)
    chars = []
    for shift in range(26):
        index = (base + shift * 37) % len(_ALPHABET)
        chars.append(_ALPHABET[index])
    return "".join(chars)[:26]


def collect_trip_completed(user_id: str, trip_id: str) -> Dict[str, str | Dict[str, str]]:
    """Return a valid `trip_completed` event."""

    event = {
        "event_id": _ulid(),
        "event_type": "trip_completed",
        "event_time": _iso_now(),
        "payload": {
            "trip_id": trip_id,
            "traveler_id": user_id,
            "status": "completed",
            "completed_at": _iso_now(),
        },
    }
    return event


def collect_withdrawal_requested(user_id: str, wallet_id: str, amount: str) -> Dict[str, str | Dict[str, str]]:
    """Return a valid `withdrawal_requested` event and store context for payout."""

    normalized_amount = _quantize(amount)
    withdrawal_id = _ulid()
    _withdrawal_context[withdrawal_id] = {
        "wallet_id": wallet_id,
        "amount": normalized_amount,
        "user_id": user_id,
    }
    event = {
        "event_id": _ulid(),
        "event_type": "withdrawal_requested",
        "event_time": _iso_now(),
        "payload": {
            "withdrawal_request_id": withdrawal_id,
            "wallet_id": wallet_id,
            "amount": normalized_amount,
        },
    }
    return event


def collect_withdrawal_paid(withdrawal_id: str, txid: str, fee_usdt: str) -> Dict[str, str | Dict[str, str]]:
    """Return a valid `withdrawal_paid` event using stored context and deducting fees."""

    context = _withdrawal_context.pop(withdrawal_id, None)
    if context is None:
        raise KeyError(f"Unknown withdrawal request: {withdrawal_id}")

    gross = Decimal(context["amount"])
    fee = Decimal(fee_usdt)
    net = gross - fee
    if net <= Decimal("0.00"):
        net = Decimal("0.00")
    net = net.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    event = {
        "event_id": _ulid(),
        "event_type": "withdrawal_paid",
        "event_time": _iso_now(),
        "payload": {
            "withdrawal_request_id": withdrawal_id,
            "wallet_id": context["wallet_id"],
            "amount": f"{net:.2f}",
            "transaction_id": txid,
        },
    }
    return event


def reset_withdrawal_context() -> None:
    """Clear stored withdrawal context (useful for tests)."""

    _withdrawal_context.clear()


__all__ = [
    "collect_trip_completed",
    "collect_withdrawal_requested",
    "collect_withdrawal_paid",
    "reset_withdrawal_context",
]
