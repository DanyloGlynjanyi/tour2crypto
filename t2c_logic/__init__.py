"""Tour2Crypto event-driven business logic wiring."""

from __future__ import annotations

from t2c_events import EventBus, IdempotentConsumer, InMemoryIdempotencyStore, validate_event

from .handlers import (
    get_wallet_balance,
    handle_trip_completed,
    handle_withdrawal_paid,
    handle_withdrawal_requested,
    ledger_entries,
    make_cashback_entry,
    register_wallet,
    reset_state as _reset_handlers_state,
    set_trip_reward,
    trip_rewards,
    update_wallet_balance,
    wallet_balances,
    wallets,
    withdrawal_locks,
)

bus = EventBus()
_trip_store = InMemoryIdempotencyStore()
_withdrawal_requested_store = InMemoryIdempotencyStore()
_withdrawal_paid_store = InMemoryIdempotencyStore()

bus.subscribe(
    "trip_completed",
    IdempotentConsumer("trip_completed", _trip_store, handle_trip_completed, validate_event),
)
bus.subscribe(
    "withdrawal_requested",
    IdempotentConsumer(
        "withdrawal_requested",
        _withdrawal_requested_store,
        handle_withdrawal_requested,
        validate_event,
    ),
)
bus.subscribe(
    "withdrawal_paid",
    IdempotentConsumer(
        "withdrawal_paid",
        _withdrawal_paid_store,
        handle_withdrawal_paid,
        validate_event,
    ),
)


def reset_state() -> None:
    """Reset handler state and idempotency stores."""

    _reset_handlers_state()
    _trip_store.clear()
    _withdrawal_requested_store.clear()
    _withdrawal_paid_store.clear()


__all__ = [
    "bus",
    "register_wallet",
    "get_wallet_balance",
    "update_wallet_balance",
    "set_trip_reward",
    "make_cashback_entry",
    "wallets",
    "wallet_balances",
    "ledger_entries",
    "withdrawal_locks",
    "trip_rewards",
    "handle_trip_completed",
    "handle_withdrawal_requested",
    "handle_withdrawal_paid",
    "reset_state",
]
