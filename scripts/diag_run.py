"""Generate offline diagnostics based on logs and metrics."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from t2c_core.metrics import snapshot
from t2c_diag import analyze

OUTPUT_PATH = Path("reports/diagnostics.md")


def main() -> None:
    diagnostics = analyze()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Tour2Crypto Diagnostics", ""]
    lines.append("## Findings")
    findings = diagnostics.get("findings", []) or ["(none)"]
    for entry in findings:
        lines.append(f"- {entry}")
    lines.append("")

    lines.append("## Recommendations")
    recommendations = diagnostics.get("recommendations", []) or ["(none)"]
    for entry in recommendations:
        lines.append(f"- {entry}")
    lines.append("")

    lines.append("## Current Metrics Snapshot")
    metrics_snapshot = snapshot()
    for key, value in sorted(metrics_snapshot.items()):
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Recent Log Tail")
    for line in diagnostics.get("log_tail", []):
        lines.append(f"> {line}")
    if not diagnostics.get("log_tail"):
        lines.append("> (log file empty)")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Diagnostics written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
