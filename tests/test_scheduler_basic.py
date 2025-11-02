from __future__ import annotations

from t2c_autonomy.scheduler import Job, Scheduler


def test_scheduler_executes_jobs_by_interval() -> None:
    scheduler = Scheduler()
    run_log: list[str] = []

    scheduler.add_job(Job("fast", 1.0, lambda: run_log.append("fast")))
    scheduler.add_job(Job("slow", 2.0, lambda: run_log.append("slow")))

    assert scheduler.tick(now=0.0) == 2
    assert run_log == ["fast", "slow"]

    assert scheduler.tick(now=0.5) == 0
    assert run_log == ["fast", "slow"]

    assert scheduler.tick(now=1.1) == 1
    assert run_log == ["fast", "slow", "fast"]

    assert scheduler.tick(now=2.5) == 2
    assert run_log[-2:] == ["fast", "slow"]
