"""Ledger invariants ensuring Tour2Crypto financial flows remain consistent."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping, MutableMapping, Sequence

TWOPLACES = Decimal("0.01")

_ALLOWED_TYPES = {
    "cashback_accrual",
    "cashback_reversal",
    "withdrawal_lock",
    "withdrawal_release",
    "payout",
}

_DIRECTION_REQUIREMENTS: Dict[str, str] = {
    "cashback_accrual": "credit",
    "cashback_reversal": "debit",
    "payout": "debit",
}

_OPTIONAL_DIRECTIONS: Dict[str, frozenset[str | None]] = {
    "withdrawal_lock": frozenset({None, "debit"}),
    "withdrawal_release": frozenset({None}),
}


@dataclass
class LockHistory:
    locked: Decimal = Decimal("0.00")
    released: Decimal = Decimal("0.00")
    paid: Decimal = Decimal("0.00")


@dataclass
class WalletState:
    credit: Decimal = Decimal("0.00")
    debit: Decimal = Decimal("0.00")
    locked: Decimal = Decimal("0.00")
    locks: Dict[str, Decimal] = field(default_factory=dict)
    history: Dict[str, LockHistory] = field(default_factory=dict)


def _normalize_amount(amount: str, index: int) -> Decimal:
    try:
        value = Decimal(amount)
    except (InvalidOperation, TypeError):  # pragma: no cover - TypeError handled explicitly
        raise ValueError(f"Ledger entry #{index} amount '{amount}' is not a valid decimal string") from None

    quantized = value.quantize(TWOPLACES)
    if value != quantized:
        raise ValueError(f"Ledger entry #{index} amount '{amount}' must have two decimal places")
    if quantized < Decimal("0.00"):
        raise ValueError(f"Ledger entry #{index} amount '{amount}' must be non-negative")
    return quantized


def _get_wallet_state(states: MutableMapping[str, WalletState], wallet_id: str, index: int) -> WalletState:
    if not isinstance(wallet_id, str) or not wallet_id:
        raise ValueError(f"Ledger entry #{index} must include a wallet_id")
    return states.setdefault(wallet_id, WalletState())


def _validate_direction(entry_type: str, direction: str | None, index: int) -> None:
    if direction is not None and direction not in {"credit", "debit"}:
        raise ValueError(f"Ledger entry #{index} has unsupported direction '{direction}'")

    required = _DIRECTION_REQUIREMENTS.get(entry_type)
    if required is not None:
        if direction != required:
            raise ValueError(
                f"Ledger entry #{index} expects direction '{required}' for type '{entry_type}'",
            )
        return

    optional = _OPTIONAL_DIRECTIONS.get(entry_type)
    if optional is not None and direction not in optional:
        raise ValueError(
            f"Ledger entry #{index} direction '{direction}' is not allowed for type '{entry_type}'",
        )


def _require_lock_id(entry: Mapping[str, Any], index: int) -> str:
    lock_id = entry.get("lock_id")
    if not isinstance(lock_id, str) or not lock_id:
        raise ValueError(f"Ledger entry #{index} requires a lock_id")
    return lock_id


def _require_trip_id(entry: Mapping[str, Any], index: int) -> str:
    trip_id = entry.get("trip_id")
    if not isinstance(trip_id, str) or not trip_id:
        raise ValueError(f"Ledger entry #{index} requires a trip_id")
    return trip_id


def _process_ledger(ledger: Sequence[Mapping[str, Any]]) -> Dict[str, WalletState]:
    states: Dict[str, WalletState] = {}
    accruals: Dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0.00"))

    for index, entry in enumerate(ledger):
        if not isinstance(entry, Mapping):
            raise ValueError(f"Ledger entry #{index} must be a mapping")

        entry_type = entry.get("type")
        if entry_type not in _ALLOWED_TYPES:
            raise ValueError(f"Ledger entry #{index} has unsupported type '{entry_type}'")

        amount_value = entry.get("amount")
        if not isinstance(amount_value, str):
            raise ValueError(f"Ledger entry #{index} amount must be provided as a string")
        amount = _normalize_amount(amount_value, index)

        direction = entry.get("direction")
        _validate_direction(entry_type, direction, index)

        wallet_id = entry.get("wallet_id")
        state = _get_wallet_state(states, wallet_id, index)

        if entry_type == "cashback_accrual":
            state.credit += amount
            trip_id = entry.get("trip_id")
            if isinstance(trip_id, str) and trip_id:
                accruals[(wallet_id, trip_id)] += amount

        elif entry_type == "cashback_reversal":
            state.debit += amount
            trip_id = _require_trip_id(entry, index)
            key = (wallet_id, trip_id)
            accrued = accruals.get(key, Decimal("0.00"))
            if amount > accrued:
                raise ValueError(
                    f"Ledger entry #{index} cashback reversal exceeds accrued amount for trip '{trip_id}'",
                )
            accruals[key] = accrued - amount

        elif entry_type == "withdrawal_lock":
            lock_id = _require_lock_id(entry, index)
            state.locked += amount
            state.locks[lock_id] = state.locks.get(lock_id, Decimal("0.00")) + amount
            history = state.history.setdefault(lock_id, LockHistory())
            history.locked += amount

        elif entry_type == "withdrawal_release":
            lock_id = _require_lock_id(entry, index)
            current = state.locks.get(lock_id, Decimal("0.00"))
            if amount > current:
                raise ValueError(
                    f"Ledger entry #{index} release amount exceeds locked balance for lock '{lock_id}'",
                )
            remaining = current - amount
            if remaining == Decimal("0.00"):
                state.locks.pop(lock_id, None)
            else:
                state.locks[lock_id] = remaining
            state.locked -= amount
            if state.locked < Decimal("0.00"):
                raise ValueError(
                    f"Ledger entry #{index} release drives locked balance negative",
                )
            history = state.history.setdefault(lock_id, LockHistory())
            history.released += amount

        elif entry_type == "payout":
            lock_id = _require_lock_id(entry, index)
            history = state.history.get(lock_id)
            if history is None or history.locked <= Decimal("0.00"):
                raise ValueError(
                    f"Ledger entry #{index} payout references unknown lock '{lock_id}'",
                )
            current = state.locks.get(lock_id, Decimal("0.00"))
            if amount > current:
                raise ValueError(
                    f"Ledger entry #{index} payout exceeds locked balance for lock '{lock_id}'",
                )
            if history.locked < history.paid + amount:
                raise ValueError(
                    f"Ledger entry #{index} payout exceeds total locked funds for lock '{lock_id}'",
                )
            state.debit += amount
            history.paid += amount

        else:  # pragma: no cover - all types handled above
            raise ValueError(f"Ledger entry #{index} uses unsupported type '{entry_type}'")

        available = state.credit - state.debit - state.locked
        if available < Decimal("0.00"):
            raise ValueError(
                f"Ledger entry #{index} causes available balance to become negative for wallet '{wallet_id}'",
            )

    return states


def compute_available(ledger: Sequence[Mapping[str, Any]]) -> Decimal:
    """Compute the aggregated available balance across all wallets in the ledger."""

    states = _process_ledger(ledger)
    total = Decimal("0.00")
    for state in states.values():
        total += state.credit - state.debit - state.locked
    return total.quantize(TWOPLACES)


def assert_invariants(ledger: Sequence[Mapping[str, Any]]) -> None:
    """Validate that the ledger satisfies all invariants."""

    _process_ledger(ledger)


__all__ = ["assert_invariants", "compute_available"]
