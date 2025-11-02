from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from t2c_autonomy.self_heal import heal_api, heal_pipeline, heal_reports, reset_state
from t2c_core import metrics as core_metrics
from t2c_events import EventBus, InMemoryIdempotencyStore
from t2c_pipeline.queue import AsyncEventQueue
from t2c_pipeline.worker import EventWorker


def setup_function() -> None:  # noqa: D401
    """Reset heal state and metrics before each test."""

    reset_state()
    core_metrics.reset()


def test_heal_pipeline_reinitialises_on_deadletters(tmp_path: Path) -> None:
    core_metrics.inc("events_deadletter")
    heartbeat_file = tmp_path / "heartbeat.txt"
    heartbeat_file.write_text("2000-01-01T00:00:00Z", encoding="utf-8")

    bus = EventBus()
    queue = AsyncEventQueue()
    worker = EventWorker(bus, queue, InMemoryIdempotencyStore())
    worker.dead_letters.append({"event": {"event_id": "demo"}})

    new_worker = heal_pipeline(bus, queue, worker, heartbeat_path=str(heartbeat_file))

    assert new_worker is not worker
    assert not worker.dead_letters
    snapshot = core_metrics.snapshot()
    assert snapshot["heals_attempted"] >= 1
    assert snapshot["heals_succeeded"] >= 1


def test_heal_reports_forces_generation() -> None:
    calls: dict[str, str] = {}

    def fake_generate_daily_report(db_path: str) -> dict[str, str]:  # noqa: ARG001
        return {
            "total_users": "1",
            "total_wallets": "1",
            "trips_completed": "1",
            "cashback_total_usdt": "10.00",
            "withdrawals_requested": "1",
            "withdrawals_paid": "1",
            "available_sum_usdt": "5.00",
        }

    def fake_format_report_md(report: dict[str, str], title: str) -> str:  # noqa: ARG001
        calls["title"] = title
        return title

    def fake_send_report(text: str) -> str:
        calls["text"] = text
        core_metrics.inc("reports_sent")
        return text

    with patch("t2c_reports.generator.generate_daily_report", fake_generate_daily_report), patch(
        "t2c_reports.generator.format_report_md", fake_format_report_md
    ), patch("t2c_reports.sender.send_report_via_telegram", fake_send_report):
        assert heal_reports("db/test.db", stalled_ticks=2) is False
        assert heal_reports("db/test.db", stalled_ticks=2) is False
        assert heal_reports("db/test.db", stalled_ticks=2) is True

    assert calls["title"] == "Self-Heal Daily Report"
    assert calls["text"] == "Self-Heal Daily Report"


def test_heal_api_warns_on_low_activity() -> None:
    assert heal_api(min_requests=0) is False
    before = core_metrics.snapshot()["heals_attempted"]
    assert heal_api(min_requests=1) is False
    after = core_metrics.snapshot()["heals_attempted"]
    assert after >= before + 1
