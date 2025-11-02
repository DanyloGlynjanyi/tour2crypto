"""Orchestration utilities wiring together the autonomy layer."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Optional

from t2c_core import config as core_config
from t2c_core.logging import get_logger
from t2c_core.metrics import dump as dump_metrics
from t2c_core.metrics import snapshot as metrics_snapshot
from t2c_events import EventBus, IdempotentConsumer, InMemoryIdempotencyStore, validate_event
from t2c_pipeline.collector import (
    collect_trip_completed,
    collect_withdrawal_paid,
    collect_withdrawal_requested,
)
from t2c_pipeline.queue import AsyncEventQueue
from t2c_pipeline.worker import EventWorker
from t2c_autonomy.scheduler import Job, Scheduler
from t2c_autonomy.self_heal import heal_api, heal_pipeline, heal_reports
from t2c_contracts.factories import TripFactory, WalletFactory
from t2c_logic.handlers import (
    handle_trip_completed,
    handle_withdrawal_paid,
    handle_withdrawal_requested,
    register_wallet,
    reset_state as reset_logic_state,
)

LOGGER = get_logger(__name__)


@dataclass
class AutonomyContext:
    """Runtime context for the autonomy layer."""

    bus: EventBus
    queue: AsyncEventQueue
    worker: EventWorker
    store: InMemoryIdempotencyStore
    scheduler: Scheduler
    jobs: Dict[str, Job]
    db_path: str
    user_id: str
    wallet_id: str
    trip_id: str
    withdrawal_id: Optional[str] = None
    generated_trip: bool = False
    generated_withdrawal: bool = False
    generated_payout: bool = False

    def update_worker(self, new_worker: EventWorker) -> None:
        self.worker = new_worker
        self.store = new_worker.store  # type: ignore[attr-defined]


def _prepare_logic_context(context: AutonomyContext, wallet_payload: Dict[str, str]) -> None:
    reset_logic_state()
    register_wallet(wallet_payload)


async def _maybe_enqueue_events(context: AutonomyContext) -> None:
    if context.queue.qsize() > 0:
        return

    if not context.generated_trip:
        event = collect_trip_completed(context.user_id, context.trip_id)
        await context.queue.put(event)
        context.generated_trip = True
        LOGGER.info("Queued synthetic trip_completed event")
        return

    if not context.generated_withdrawal:
        event = collect_withdrawal_requested(context.user_id, context.wallet_id, "15.00")
        context.withdrawal_id = event["payload"]["withdrawal_request_id"]
        await context.queue.put(event)
        context.generated_withdrawal = True
        LOGGER.info("Queued synthetic withdrawal_requested event")
        return

    if not context.generated_payout and context.withdrawal_id:
        event = collect_withdrawal_paid(context.withdrawal_id, "TX-AUTO", "0.50")
        await context.queue.put(event)
        context.generated_payout = True
        LOGGER.info("Queued synthetic withdrawal_paid event")


async def _run_pipeline_step(context: AutonomyContext) -> None:
    await _maybe_enqueue_events(context)
    await context.worker.run_once()


def _job_pipeline_tick(context: AutonomyContext) -> None:
    asyncio.run(_run_pipeline_step(context))


def _job_report_daily(context: AutonomyContext) -> None:
    from t2c_reports.generator import format_report_md, generate_daily_report
    from t2c_reports.sender import send_report_via_telegram

    report = generate_daily_report(context.db_path)
    text = format_report_md(report, "Scheduled Daily Report")
    send_report_via_telegram(text)


def _job_heartbeat() -> None:
    from t2c_core.health import heartbeat

    heartbeat()
    dump_metrics()


def _job_self_heal(context: AutonomyContext) -> None:
    new_worker = heal_pipeline(context.bus, context.queue, context.worker)
    if new_worker is not context.worker:
        context.update_worker(new_worker)
    heal_reports(context.db_path)
    heal_api()


def bootstrap() -> AutonomyContext:
    """Initialise the scheduler, worker, and supporting state."""

    db_path = core_config.get("DB_PATH", "db/tour2crypto.db") or "db/tour2crypto.db"
    user_wallet = WalletFactory().build()
    user_id = user_wallet["owner_id"]
    wallet_id = user_wallet["id"]
    trip_payload = TripFactory().build(traveler_id=user_id, status="completed")
    trip_id = trip_payload["id"]

    bus = EventBus()
    trip_store = InMemoryIdempotencyStore()
    withdrawal_store = InMemoryIdempotencyStore()
    payout_store = InMemoryIdempotencyStore()

    bus.subscribe(
        "trip_completed",
        IdempotentConsumer("trip_completed", trip_store, handle_trip_completed, validate_event),
    )
    bus.subscribe(
        "withdrawal_requested",
        IdempotentConsumer(
            "withdrawal_requested",
            withdrawal_store,
            handle_withdrawal_requested,
            validate_event,
        ),
    )
    bus.subscribe(
        "withdrawal_paid",
        IdempotentConsumer(
            "withdrawal_paid",
            payout_store,
            handle_withdrawal_paid,
            validate_event,
        ),
    )

    queue = AsyncEventQueue()
    worker_store = InMemoryIdempotencyStore()
    worker = EventWorker(bus, queue, worker_store)

    scheduler = Scheduler()
    context = AutonomyContext(
        bus=bus,
        queue=queue,
        worker=worker,
        store=worker_store,
        scheduler=scheduler,
        jobs={},
        db_path=db_path,
        user_id=user_id,
        wallet_id=wallet_id,
        trip_id=trip_id,
    )

    _prepare_logic_context(context, user_wallet)

    pipeline_interval = core_config.get_seconds("SCHED_TICK", 1.0)
    report_interval = core_config.get_seconds("REPORT_INTERVAL", 86400.0)
    heal_interval = core_config.get_seconds("HEAL_INTERVAL", 5.0)

    pipeline_job = Job("pipeline", pipeline_interval, lambda: _job_pipeline_tick(context))
    report_job = Job("report", report_interval, lambda: _job_report_daily(context))
    heartbeat_job = Job("heartbeat", pipeline_interval, _job_heartbeat)
    heal_job = Job("self_heal", heal_interval, lambda: _job_self_heal(context))

    for job in (pipeline_job, report_job, heartbeat_job, heal_job):
        scheduler.add_job(job)
        context.jobs[job.name] = job

    return context


def start_all(max_ticks: Optional[int] = None) -> AutonomyContext:
    """Start the autonomy scheduler loop."""

    context = bootstrap()
    loop_seconds = core_config.get_seconds("SCHED_TICK", 1.0)
    scheduler_ticks = context.scheduler.run_forever(loop_seconds=loop_seconds, max_ticks=max_ticks)
    LOGGER.info("Scheduler completed %s ticks", scheduler_ticks)
    LOGGER.info("Autonomy metrics snapshot: %s", metrics_snapshot())
    return context


__all__ = ["AutonomyContext", "bootstrap", "start_all"]
