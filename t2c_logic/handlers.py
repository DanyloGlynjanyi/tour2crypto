"""Business logic handlers linking events, ledger, and wallets."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List

from t2c_contracts.factories import CashbackLedgerEntryFactory
from t2c_contracts.ledger import compute_wallet_balance
from t2c_contracts.validation import CashbackLedgerEntryModel, WalletModel

TWOPLACES = Decimal("0.01")
DEFAULT_CASHBACK_AMOUNT = Decimal("10.00")

wallets: Dict[str, WalletModel] = {}
wallet_balances: Dict[str, str] = {}
_wallets_by_owner: Dict[str, str] = {}
ledger_entries: List[CashbackLedgerEntryModel] = []
ledger_by_reference: Dict[str, CashbackLedgerEntryModel] = {}
withdrawal_locks: Dict[str, Decimal] = {}
trip_rewards: Dict[str, Decimal] = {}

_ledger_factory = CashbackLedgerEntryFactory()


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(TWOPLACES, rounding=ROUND_DOWN)


def _amount_to_str(amount: Decimal) -> str:
    return f"{_quantize(amount):.2f}"


def register_wallet(payload: Dict[str, Any]) -> WalletModel:
    """Register a wallet for in-memory processing."""

    wallet = WalletModel(**payload)
    wallets[wallet.id] = wallet
    _wallets_by_owner[wallet.owner_id] = wallet.id
    wallet_balances[wallet.id] = "0.00"
    return wallet


def get_wallet_balance(wallet_id: str) -> str:
    """Return the cached balance for the given wallet."""

    if wallet_id not in wallet_balances:
        update_wallet_balance(wallet_id)
    return wallet_balances[wallet_id]


def update_wallet_balance(wallet_id: str) -> str:
    """Recompute the wallet balance from ledger entries."""

    if wallet_id not in wallets:
        raise KeyError(f"Wallet {wallet_id} is not registered")

    related_entries = [entry for entry in ledger_entries if entry.wallet_id == wallet_id]
    balance = compute_wallet_balance(related_entries)
    wallet_balances[wallet_id] = balance
    return balance


def set_trip_reward(trip_id: str, amount: Decimal) -> None:
    """Override the cashback amount for a specific trip."""

    trip_rewards[trip_id] = _quantize(amount)


def _record_ledger_entry(
    *,
    wallet_id: str,
    amount: Decimal,
    entry_type: str,
    reference: str,
    description: str | None = None,
    trip_id: str | None = None,
) -> CashbackLedgerEntryModel:
    if wallet_id not in wallets:
        raise KeyError(f"Wallet {wallet_id} is not registered")

    if reference in ledger_by_reference:
        return ledger_by_reference[reference]

    payload = _ledger_factory.build(
        wallet_id=wallet_id,
        trip_id=trip_id or wallet_id,
        amount=_amount_to_str(amount),
        entry_type=entry_type,
        description=description,
        reference=reference,
    )
    entry = CashbackLedgerEntryModel(**payload)
    ledger_entries.append(entry)
    ledger_by_reference[reference] = entry
    update_wallet_balance(wallet_id)
    return entry


def make_cashback_entry(
    *,
    wallet_id: str,
    trip_id: str,
    amount: Decimal,
    reference: str,
    description: str | None = None,
) -> CashbackLedgerEntryModel:
    """Create a cashback ledger entry and update the wallet balance."""

    return _record_ledger_entry(
        wallet_id=wallet_id,
        trip_id=trip_id,
        amount=amount,
        entry_type="cashback",
        reference=reference,
        description=description or f"Cashback for trip {trip_id}",
    )


def handle_trip_completed(event: Dict[str, Any]) -> None:
    payload = event["payload"]
    traveler_id = payload["traveler_id"]
    trip_id = payload["trip_id"]
    wallet_id = _wallets_by_owner.get(traveler_id)
    if wallet_id is None:
        raise KeyError(f"No wallet registered for traveler {traveler_id}")

    amount = trip_rewards.pop(trip_id, DEFAULT_CASHBACK_AMOUNT)
    make_cashback_entry(
        wallet_id=wallet_id,
        trip_id=trip_id,
        amount=amount,
        reference=event["event_id"],
    )


def handle_withdrawal_requested(event: Dict[str, Any]) -> None:
    payload = event["payload"]
    wallet_id = payload["wallet_id"]
    request_id = payload["withdrawal_request_id"]
    amount = _quantize(Decimal(payload["amount"]))
    withdrawal_locks[request_id] = amount

    _record_ledger_entry(
        wallet_id=wallet_id,
        amount=-amount,
        entry_type="adjustment",
        reference=f"{event['event_id']}-lock",
        description=f"Withdrawal lock {request_id}",
        trip_id=payload.get("trip_id"),
    )


def handle_withdrawal_paid(event: Dict[str, Any]) -> None:
    payload = event["payload"]
    wallet_id = payload["wallet_id"]
    request_id = payload["withdrawal_request_id"]
    amount = _quantize(Decimal(payload["amount"]))
    transaction_id = payload["transaction_id"]

    locked_amount = withdrawal_locks.pop(request_id, Decimal("0.00"))
    if locked_amount:
        _record_ledger_entry(
            wallet_id=wallet_id,
            amount=locked_amount,
            entry_type="adjustment",
            reference=f"{event['event_id']}-unlock",
            description=f"Release withdrawal lock {request_id}",
            trip_id=payload.get("trip_id"),
        )

    _record_ledger_entry(
        wallet_id=wallet_id,
        amount=-amount,
        entry_type="withdrawal",
        reference=event["event_id"],
        description=f"Withdrawal payout {transaction_id}",
        trip_id=payload.get("trip_id"),
    )


def reset_state() -> None:
    """Clear in-memory state for deterministic tests."""

    wallets.clear()
    wallet_balances.clear()
    _wallets_by_owner.clear()
    ledger_entries.clear()
    ledger_by_reference.clear()
    withdrawal_locks.clear()
    trip_rewards.clear()


__all__ = [
    "wallets",
    "wallet_balances",
    "ledger_entries",
    "ledger_by_reference",
    "withdrawal_locks",
    "trip_rewards",
    "register_wallet",
    "get_wallet_balance",
    "update_wallet_balance",
    "set_trip_reward",
    "make_cashback_entry",
    "handle_trip_completed",
    "handle_withdrawal_requested",
    "handle_withdrawal_paid",
    "reset_state",
]
