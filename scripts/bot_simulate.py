"""Run the Tour2Crypto bot in offline simulation mode."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from t2c_bot.app import main


def run() -> str:
    """Execute the bot simulation and return the status message."""

    result = main()
    print("Simulation result:", result)
    return result


if __name__ == "__main__":
    run()
