"""Simple cron-like scheduler built on the Python standard library."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from t2c_core.logging import get_logger

LOGGER = get_logger(__name__)


@dataclass
class Job:
    """A scheduled job executed at fixed intervals."""

    name: str
    interval_seconds: float
    func: Callable[[], None]
    last_run: Optional[float] = None
    enabled: bool = True
    def due(self, now: float) -> bool:
        if not self.enabled:
            return False
        if self.last_run is None:
            return True
        return now - self.last_run >= self.interval_seconds

    def run(self, now: float) -> None:
        LOGGER.info("Running job %s", self.name)
        try:
            self.func()
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Job %s failed: %s", self.name, exc)
        finally:
            self.last_run = now


class Scheduler:
    """A lightweight scheduler that executes jobs sequentially."""

    def __init__(self) -> None:
        self._jobs: List[Job] = []

    @property
    def jobs(self) -> List[Job]:
        return list(self._jobs)

    def add_job(self, job: Job) -> None:
        self._jobs.append(job)
        LOGGER.info(
            "Registered job %s to run every %ss", job.name, job.interval_seconds
        )

    def tick(self, now: Optional[float] = None) -> int:
        """Execute jobs that are due. Returns number of jobs executed."""

        executed = 0
        current = time.monotonic() if now is None else now
        for job in self._jobs:
            if job.due(current):
                job.run(current)
                executed += 1
        return executed

    def run_forever(self, loop_seconds: float = 1.0, max_ticks: Optional[int] = None) -> int:
        """Run scheduler loop until ``max_ticks`` is reached (if provided)."""

        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            self.tick()
            ticks += 1
            if loop_seconds > 0:
                time.sleep(loop_seconds)
        return ticks


__all__ = ["Job", "Scheduler"]
