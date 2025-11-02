"""Generate a final autonomy snapshot with metrics and diagnostics."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from t2c_autonomy.orchestrator import bootstrap
from t2c_core import config as core_config
from t2c_core import metrics as core_metrics
from t2c_diag import analyze

TABLES = [
    "applications",
    "wallets",
    "trips",
    "cashback_ledger",
    "withdrawals",
    "audit_events",
]


def _collect_counts(db_path: str) -> Dict[str, int | str]:
    counts: Dict[str, int | str] = {}
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for table in TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = int(cursor.fetchone()[0])
            except sqlite3.Error as exc:  # noqa: BLE001
                counts[table] = f"error: {exc}"
    except sqlite3.Error as exc:  # noqa: BLE001
        counts["error"] = str(exc)
    finally:
        if conn is not None:
            conn.close()
    return counts


def main() -> str:
    db_path = core_config.get("DB_PATH", "db/tour2crypto.db") or "db/tour2crypto.db"
    metrics_snapshot = core_metrics.snapshot()
    counts = _collect_counts(db_path)
    context = bootstrap()
    jobs = {
        name: {
            "interval_seconds": job.interval_seconds,
            "enabled": job.enabled,
            "last_run": job.last_run,
        }
        for name, job in context.jobs.items()
    }
    diagnostics = analyze()

    snapshot_path = Path("reports/final_snapshot.txt")
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    payload = {
        "timestamp_utc": now,
        "spec_version": "v3.5",
        "db_counts": counts,
        "metrics": metrics_snapshot,
        "jobs": jobs,
        "diagnostics": diagnostics,
    }

    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    message = f"[SNAPSHOT] {snapshot_path}"
    print(message)
    return message


if __name__ == "__main__":
    main()
