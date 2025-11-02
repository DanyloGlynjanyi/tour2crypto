from __future__ import annotations

import asyncio

from t2c_events import EventBus, InMemoryIdempotencyStore
from t2c_pipeline.collector import collect_trip_completed
from t2c_pipeline.metrics import reset_metrics, snapshot
from t2c_pipeline.queue import AsyncEventQueue
from t2c_pipeline.worker import EventWorker


def test_worker_retries_and_event_succeeds() -> None:
    reset_metrics()
    try:
        bus = EventBus()
        queue = AsyncEventQueue()
        worker = EventWorker(bus, queue, InMemoryIdempotencyStore(), max_retries=5, base_backoff=0.0)

        attempts = {"count": 0}

        def flaky_handler(event: dict) -> None:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("temporary failure")

        bus.subscribe("trip_completed", flaky_handler)
        event = collect_trip_completed("A" * 26, "B" * 26)

        async def _run() -> None:
            await queue.put(event)
            while True:
                processed = await worker.run_once()
                if not processed:
                    break

        asyncio.run(_run())

        metrics_snapshot = snapshot()
        assert attempts["count"] == 3
        assert metrics_snapshot["retried"] >= 2
        assert metrics_snapshot["dead_lettered"] == 0
        assert not worker.dead_letters
    finally:
        reset_metrics()


def test_worker_dead_letters_after_max_retries() -> None:
    reset_metrics()
    try:
        bus = EventBus()
        queue = AsyncEventQueue()
        worker = EventWorker(bus, queue, InMemoryIdempotencyStore(), max_retries=2, base_backoff=0.0)

        def always_fail(_event: dict) -> None:
            raise RuntimeError("permanent failure")

        bus.subscribe("trip_completed", always_fail)
        event = collect_trip_completed("C" * 26, "D" * 26)

        async def _run() -> None:
            await queue.put(event)
            while True:
                processed = await worker.run_once()
                if not processed:
                    break

        asyncio.run(_run())

        metrics_snapshot = snapshot()
        assert metrics_snapshot["dead_lettered"] == 1
        assert worker.dead_letters
        assert worker.dead_letters[0]["retries"] >= 2
    finally:
        reset_metrics()
