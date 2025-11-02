"""Demonstration of the local async event pipeline."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from t2c_contracts.factories import TripFactory, WalletFactory
from t2c_events import EventBus, IdempotentConsumer, InMemoryIdempotencyStore, validate_event
from t2c_logic import reset_state
from t2c_logic.handlers import (
    get_wallet_balance,
    handle_trip_completed,
    handle_withdrawal_paid,
    handle_withdrawal_requested,
    register_wallet,
    set_trip_reward,
)
from t2c_pipeline.collector import (
    collect_trip_completed,
    collect_withdrawal_paid,
    collect_withdrawal_requested,
    reset_withdrawal_context,
)
from t2c_pipeline.metrics import reset_metrics, snapshot
from t2c_pipeline.queue import AsyncEventQueue
from t2c_pipeline.worker import EventWorker


async def run_demo() -> None:
    """Wire the queue, worker, and handlers then process sample events."""

    reset_state()
    reset_metrics()
    reset_withdrawal_context()

    wallet_payload = WalletFactory().build()
    wallet = register_wallet(wallet_payload)
    user_id = wallet.owner_id

    trip_payload = TripFactory().build(traveler_id=user_id, status="completed")
    trip_id = trip_payload["id"]
    set_trip_reward(trip_id, Decimal("40.00"))

    bus = EventBus()
    trip_store = InMemoryIdempotencyStore()
    withdrawal_request_store = InMemoryIdempotencyStore()
    withdrawal_paid_store = InMemoryIdempotencyStore()

    bus.subscribe(
        "trip_completed",
        IdempotentConsumer("trip_completed", trip_store, handle_trip_completed, validate_event),
    )
    bus.subscribe(
        "withdrawal_requested",
        IdempotentConsumer(
            "withdrawal_requested",
            withdrawal_request_store,
            handle_withdrawal_requested,
            validate_event,
        ),
    )
    bus.subscribe(
        "withdrawal_paid",
        IdempotentConsumer("withdrawal_paid", withdrawal_paid_store, handle_withdrawal_paid, validate_event),
    )

    queue = AsyncEventQueue()
    worker = EventWorker(bus, queue, InMemoryIdempotencyStore(), base_backoff=0.01)

    await queue.put(collect_trip_completed(user_id, trip_id))
    withdrawal_requested_event = collect_withdrawal_requested(user_id, wallet.id, "30.00")
    await queue.put(withdrawal_requested_event)
    withdrawal_id = withdrawal_requested_event["payload"]["withdrawal_request_id"]
    await queue.put(collect_withdrawal_paid(withdrawal_id, "TX-DEMO-001", "2.50"))

    while True:
        processed = await worker.run_once()
        if not processed:
            break

    metrics_snapshot = snapshot()
    final_balance = get_wallet_balance(wallet.id)

    print("Queue size:", queue.qsize())
    print("Metrics:", metrics_snapshot)
    print("Dead letters:", len(worker.dead_letters))
    print("Wallet balance:", final_balance)


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
