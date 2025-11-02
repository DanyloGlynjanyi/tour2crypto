"""Rule-based offline diagnostics derived from logs and metrics."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Dict, List


def _tail(path: Path, limit: int = 1000) -> List[str]:
    if not path.exists():
        return []
    lines = deque(maxlen=limit)
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            lines.append(line.rstrip())
    return list(lines)


def _load_metrics(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"history": [], "counters": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"history": [], "counters": {}}
    history = payload.get("history", [])
    counters: Dict[str, int] = {}
    if history:
        latest = history[-1]
        if isinstance(latest, dict):
            counters = dict(latest.get("counters", {}) or {})
    return {"history": history, "counters": counters}


def analyze(log_path: str = "logs/t2c.log", metrics_path: str = "logs/metrics.json") -> Dict[str, Any]:
    """Inspect logs and metrics to produce diagnostic recommendations."""

    log_file = Path(log_path)
    metrics_file = Path(metrics_path)

    log_tail = _tail(log_file)
    metrics_data = _load_metrics(metrics_file)
    counters: Dict[str, int] = {k: int(v) for k, v in metrics_data.get("counters", {}).items()}
    history = metrics_data.get("history", [])

    findings: List[str] = []
    recommendations: List[str] = []

    warn_errors = [line for line in log_tail if "ERROR" in line or "WARNING" in line]
    if warn_errors:
        findings.append(f"Detected {len(warn_errors)} warning/error log entries")

    if counters.get("events_deadletter", 0) > 0:
        recommendations.append("Перевірити handler або схему події для dead-letter записів")

    if counters.get("reports_sent", 0) == 0:
        recommendations.append("Переконатися, що планувальник звітів та права Telegram налаштовані")

    if counters.get("events_retried", 0) > counters.get("events_processed", 0):
        recommendations.append("Перевірити брокер, бекоф або handler через підвищений рівень ретраїв")

    if len(history) >= 2:
        previous = history[-2].get("counters", {}) if isinstance(history[-2], dict) else {}
        delta_api = counters.get("api_requests", 0) - int(previous.get("api_requests", 0) or 0)
        if previous.get("api_requests", 0) and delta_api <= 0:
            recommendations.append("Активність API знизилась — перевірити доступність сервера")

    diagnostics = {
        "counters": counters,
        "findings": findings,
        "recommendations": recommendations,
        "log_tail": log_tail[-20:],
    }
    return diagnostics


__all__ = ["analyze"]
