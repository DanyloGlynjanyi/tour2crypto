"""Health and heartbeat helpers for Tour2Crypto services."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional

from .metrics import dump, snapshot


def heartbeat(path: str = "logs/heartbeat.txt") -> str:
    """Write the current UTC timestamp to ``path`` and return it."""

    timestamp = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    heartbeat_path = Path(path)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text(timestamp, encoding="utf-8")
    return timestamp


def _read_heartbeat(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def healthcheck(path: str = "logs/heartbeat.txt") -> Dict[str, object]:
    """Return a structured health status payload."""

    heartbeat_path = Path(path)
    last = _read_heartbeat(heartbeat_path)
    metrics_snapshot = snapshot()
    ok = bool(last) or bool(metrics_snapshot)
    return {"ok": ok, "last_beat_iso": last, "metrics": metrics_snapshot}


def self_test() -> bool:
    """Run a lightweight internal validation of the health subsystem."""

    try:
        with TemporaryDirectory() as tmp:
            temp_path = Path(tmp) / "metrics.json"
            dump(str(temp_path))
            return temp_path.exists()
    except Exception:  # noqa: BLE001
        return False


__all__ = ["heartbeat", "healthcheck", "self_test"]
