"""Self-healing helpers for the autonomy layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from t2c_core import config as core_config
from t2c_core import metrics as core_metrics
from t2c_core.logging import get_logger
from t2c_events import EventBus
from t2c_events.idempotency import InMemoryIdempotencyStore
from t2c_pipeline.queue import AsyncEventQueue
from t2c_pipeline.worker import EventWorker

LOGGER = get_logger(__name__)

_HEARTBEAT_PATH = "logs/heartbeat.txt"
_DEAD_LETTER_LOG = Path("logs/dead_letters.jsonl")
_REPORTS_LAST_COUNT: Optional[int] = None
_REPORTS_STALLED_TICKS = 0
_API_LAST_COUNT: Optional[int] = None


def _parse_iso8601(value: str) -> Optional[datetime]:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _heartbeat_age_seconds(path: str) -> Optional[float]:
    heartbeat_path = Path(path)
    if not heartbeat_path.exists():
        return None
    content = heartbeat_path.read_text(encoding="utf-8").strip()
    if not content:
        return None
    parsed = _parse_iso8601(content)
    if parsed is None:
        return None
    now = datetime.now(timezone.utc)
    delta = now - parsed
    return delta.total_seconds()


def _persist_dead_letters(worker: EventWorker) -> None:
    if not worker.dead_letters:
        return
    _DEAD_LETTER_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _DEAD_LETTER_LOG.open("a", encoding="utf-8") as handle:
        for entry in worker.dead_letters:
            handle.write(json.dumps(entry))
            handle.write("\n")
    worker.dead_letters.clear()


def heal_pipeline(
    bus: EventBus,
    queue: AsyncEventQueue,
    worker: EventWorker,
    *,
    heartbeat_path: str = _HEARTBEAT_PATH,
) -> EventWorker:
    """Ensure the pipeline worker is healthy, reinitialising if required."""

    core_metrics.inc("heals_attempted")
    counters = core_metrics.snapshot()
    threshold = core_config.get_int("HEAL_DEADLETTER_THRESHOLD", 1)
    max_age = core_config.get_int("HEARTBEAT_MAX_AGE_SEC", 120)

    deadletters = counters.get("events_deadletter", 0)
    heartbeat_age = _heartbeat_age_seconds(heartbeat_path)
    should_restart = deadletters >= threshold
    if heartbeat_age is None or heartbeat_age > max_age:
        should_restart = True

    if not should_restart:
        return worker

    LOGGER.warning(
        "Pipeline health degraded (deadletters=%s, heartbeat_age=%s); restarting worker",
        deadletters,
        heartbeat_age,
    )
    _persist_dead_letters(worker)
    new_store = InMemoryIdempotencyStore()
    new_worker = EventWorker(
        bus,
        queue,
        new_store,
        max_retries=worker.max_retries,
        base_backoff=worker.base_backoff,
    )
    core_metrics.inc("heals_succeeded")
    return new_worker


def heal_reports(db_path: str, *, stalled_ticks: Optional[int] = None) -> bool:
    """Trigger a report if the regular flow stalled."""

    global _REPORTS_LAST_COUNT, _REPORTS_STALLED_TICKS
    core_metrics.inc("heals_attempted")
    counters = core_metrics.snapshot()
    current = counters.get("reports_sent", 0)
    if _REPORTS_LAST_COUNT is None:
        _REPORTS_LAST_COUNT = current
        _REPORTS_STALLED_TICKS = 0
        return False

    if current > _REPORTS_LAST_COUNT:
        _REPORTS_LAST_COUNT = current
        _REPORTS_STALLED_TICKS = 0
        return False

    _REPORTS_STALLED_TICKS += 1
    limit = stalled_ticks or core_config.get_int("HEAL_REPORT_STALLED_TICKS", 3)
    if _REPORTS_STALLED_TICKS < limit:
        return False

    LOGGER.warning("Reports stalled for %s ticks; forcing daily report", _REPORTS_STALLED_TICKS)
    from t2c_reports.generator import format_report_md, generate_daily_report
    from t2c_reports.sender import send_report_via_telegram

    try:
        report = generate_daily_report(db_path)
        text = format_report_md(report, "Self-Heal Daily Report")
        send_report_via_telegram(text)
        _REPORTS_LAST_COUNT = core_metrics.snapshot().get("reports_sent", current)
        _REPORTS_STALLED_TICKS = 0
        core_metrics.inc("heals_succeeded")
        return True
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Failed to generate forced report: %s", exc)
        return False


def heal_api(min_requests: Optional[int] = None) -> bool:
    """Emit warnings if API activity looks stalled."""

    global _API_LAST_COUNT
    core_metrics.inc("heals_attempted")
    counters = core_metrics.snapshot()
    current = counters.get("api_requests", 0)
    min_expected = min_requests if min_requests is not None else core_config.get_int(
        "HEAL_API_MIN_REQUESTS", 0
    )

    if _API_LAST_COUNT is None:
        _API_LAST_COUNT = current
        return False

    if current >= min_expected and current > _API_LAST_COUNT:
        _API_LAST_COUNT = current
        return False

    LOGGER.warning(
        "API activity below expectation (current=%s, last=%s, min=%s)",
        current,
        _API_LAST_COUNT,
        min_expected,
    )
    return False


def reset_state() -> None:
    """Reset module-level counters (useful for tests)."""

    global _REPORTS_LAST_COUNT, _REPORTS_STALLED_TICKS, _API_LAST_COUNT
    _REPORTS_LAST_COUNT = None
    _REPORTS_STALLED_TICKS = 0
    _API_LAST_COUNT = None


__all__ = ["heal_pipeline", "heal_reports", "heal_api", "reset_state"]
