"""Async worker that bridges the queue and event bus."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from t2c_events import EventBus
from t2c_events.idempotency import IdempotencyStore
from t2c_events.validators import validate_event

from . import metrics
from .queue import AsyncEventQueue


class EventWorker:
    """Consume queued events, enforce validation, and publish to the bus."""

    def __init__(
        self,
        bus: EventBus,
        queue: AsyncEventQueue,
        store: IdempotencyStore,
        *,
        max_retries: int = 3,
        base_backoff: float = 0.05,
    ) -> None:
        self.bus = bus
        self.queue = queue
        self.store = store
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.dead_letters: List[Dict[str, Any]] = []

    async def run_once(self) -> bool:
        """Process a single envelope if available."""

        if self.queue.empty():
            return False

        envelope = await self.queue.get()
        event: Dict[str, Any] = envelope["event"]
        event_id = event.get("event_id")

        if isinstance(event_id, str) and self.store.has(event_id):
            metrics.increment_processed_ok()
            return True

        try:
            validate_event(event)
            self.bus.publish(event)
            if isinstance(event_id, str):
                self.store.set(event_id, event)
            metrics.increment_processed_ok()
            if event.get("event_type") in {"trip_completed", "withdrawal_paid"}:
                try:
                    from t2c_reports.generator import (
                        format_report_md,
                        generate_daily_report,
                    )
                    from t2c_reports.sender import send_report_via_telegram

                    report = generate_daily_report("db/tour2crypto.db")
                    text = format_report_md(report, "Auto Daily Report (triggered by event)")
                    send_report_via_telegram(text)
                except Exception as report_exc:  # noqa: BLE001
                    envelope["report_error"] = str(report_exc)
        except Exception as exc:  # noqa: BLE001
            envelope["error"] = str(exc)
            envelope["retries"] = envelope.get("retries", 0) + 1
            metrics.increment_retried()
            if envelope["retries"] >= self.max_retries:
                metrics.increment_dead_lettered()
                self.dead_letters.append(dict(envelope))
            else:
                backoff = self.base_backoff * (2 ** envelope["retries"])
                if backoff > 0:
                    await asyncio.sleep(backoff)
                await self.queue.put_envelope(envelope)
        return True


__all__ = ["EventWorker"]
