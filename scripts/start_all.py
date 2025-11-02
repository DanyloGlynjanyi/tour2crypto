"""Entry point to start the Tour2Crypto autonomy scheduler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from t2c_autonomy.orchestrator import start_all
from t2c_core.logging import get_logger

LOGGER = get_logger(__name__)


def main() -> str:
    parser = argparse.ArgumentParser(description="Start the autonomy scheduler")
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Number of scheduler ticks to run (omit for continuous run)",
    )
    args = parser.parse_args()
    start_all(max_ticks=args.max_ticks)
    message = "[AUTONOMY STARTED]"
    print(message)
    LOGGER.info("Autonomy layer started (max_ticks=%s)", args.max_ticks)
    return message


if __name__ == "__main__":
    main()
