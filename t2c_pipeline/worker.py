"""Async worker that bridges the queue and event bus."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from t2c_core import config as core_config
from t2c_core import metrics as core_metrics
from t2c_core.health import heartbeat
from t2c_core.logging import get_logger
from t2c_events import EventBus
from t2c_events.idempotency import IdempotencyStore
from t2c_events.validators import validate_event

from .queue import AsyncEventQueue

LOGGER = get_logger(__name__)


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
            heartbeat()
            core_metrics.dump()
            return False

        envelope = await self.queue.get()
        event: Dict[str, Any] = envelope["event"]
        event_id = event.get("event_id")
        event_type = event.get("event_type", "unknown")

        processed = True

        if isinstance(event_id, str) and self.store.has(event_id):
            LOGGER.info("Skipping already processed event %s", event_id)
            core_metrics.inc("events_processed")
            heartbeat()
            core_metrics.dump()
            return True

        try:
            validate_event(event)
            self.bus.publish(event)
            if isinstance(event_id, str):
                self.store.set(event_id, event)
            core_metrics.inc("events_processed")
            LOGGER.info("Processed event %s (%s)", event_id, event_type)
            if event_type in {"trip_completed", "withdrawal_paid"}:
                db_path = core_config.get("DB_PATH", "db/tour2crypto.db") or "db/tour2crypto.db"
                try:
                    from t2c_reports.generator import (
                        format_report_md,
                        generate_daily_report,
                    )
                    from t2c_reports.sender import send_report_via_telegram

                    report = generate_daily_report(db_path)
                    text = format_report_md(report, "Auto Daily Report (triggered by event)")
                    send_report_via_telegram(text)
                except Exception as report_exc:  # noqa: BLE001
                    LOGGER.warning("Report generation failed: %s", report_exc)
                    envelope["report_error"] = str(report_exc)
        except Exception as exc:  # noqa: BLE001
            envelope["error"] = str(exc)
            envelope["retries"] = envelope.get("retries", 0) + 1
            core_metrics.inc("events_retried")
            LOGGER.warning(
                "Retrying event %s (%s) attempt %s due to %s",
                event_id,
                event_type,
                envelope["retries"],
                exc,
            )
            if envelope["retries"] >= self.max_retries:
                core_metrics.inc("events_deadletter")
                self.dead_letters.append(dict(envelope))
                LOGGER.error("Dead-lettered event %s after %s retries", event_id, envelope["retries"])
            else:
                backoff = self.base_backoff * (2 ** envelope["retries"])
                if backoff > 0:
                    await asyncio.sleep(backoff)
                await self.queue.put_envelope(envelope)
        heartbeat()
        core_metrics.dump()
        return processed


__all__ = ["EventWorker"]
