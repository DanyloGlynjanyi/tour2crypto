from __future__ import annotations

import json
from pathlib import Path

from t2c_diag import analyze


def test_analyze_generates_recommendations(tmp_path) -> None:
    log_path = tmp_path / "t2c.log"
    log_lines = [
        "2024-01-01T00:00:00Z INFO worker - start",
        "2024-01-01T00:01:00Z ERROR worker - failure",
    ]
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    metrics_path = tmp_path / "metrics.json"
    metrics_payload = {
        "history": [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "counters": {
                    "events_processed": 1,
                    "events_retried": 2,
                    "events_deadletter": 1,
                    "reports_sent": 0,
                    "api_requests": 5,
                },
            },
            {
                "timestamp": "2024-01-01T01:00:00Z",
                "counters": {
                    "events_processed": 2,
                    "events_retried": 3,
                    "events_deadletter": 1,
                    "reports_sent": 0,
                    "api_requests": 5,
                },
            },
        ]
    }
    metrics_path.write_text(json.dumps(metrics_payload), encoding="utf-8")

    report = analyze(str(log_path), str(metrics_path))
    assert report["counters"]["events_deadletter"] == 1
    joined_recos = " ".join(report["recommendations"])
    assert "dead-letter" in joined_recos
    assert "планувальник" in joined_recos
    assert "API" in joined_recos
    assert "ретра" in joined_recos
    assert any("ERROR" in line for line in report["log_tail"])
