from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

try:
    from t2c_api import create_app
except Exception:  # noqa: BLE001
    create_app = None

from db.migrate import MIGRATIONS_DIR, apply_migrations


@pytest.mark.skipif(create_app is None, reason="API package not available")
def test_metrics_and_health_endpoints(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    apply_migrations(db_path=db_path, migrations_dir=MIGRATIONS_DIR)
    app = create_app(str(db_path))
    client = TestClient(app)

    health_response = client.get("/health")
    assert health_response.status_code == 200
    body = health_response.json()
    assert body["ok"] is True
    assert "metrics" in body

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    metrics_body = metrics_response.json()
    assert "api_requests" in metrics_body
    assert isinstance(metrics_body["api_requests"], int)
