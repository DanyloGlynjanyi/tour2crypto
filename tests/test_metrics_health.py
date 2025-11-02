from __future__ import annotations

from t2c_core import health, metrics


def test_metrics_increment_and_health_snapshot(tmp_path) -> None:
    metrics.reset()
    metrics.inc("events_processed", 2)
    metrics.inc("reports_sent")
    snap = metrics.snapshot()
    assert snap["events_processed"] == 2
    assert snap["reports_sent"] == 1

    beat_path = tmp_path / "beat.txt"
    heartbeat_value = health.heartbeat(str(beat_path))
    assert heartbeat_value.endswith("Z")

    status = health.healthcheck(str(beat_path))
    assert status["ok"] is True
    assert status["last_beat_iso"].endswith("Z")
    assert status["metrics"]["events_processed"] == 2

    assert health.self_test() is True
