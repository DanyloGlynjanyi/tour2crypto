from __future__ import annotations

from t2c_autonomy.orchestrator import bootstrap, start_all
from t2c_autonomy.scheduler import Scheduler


def test_bootstrap_creates_context(monkeypatch) -> None:
    monkeypatch.setenv("SCHED_TICK", "0")
    context = bootstrap()
    assert isinstance(context.scheduler, Scheduler)
    assert "pipeline" in context.jobs
    assert context.worker is not None


def test_start_all_runs_limited(monkeypatch) -> None:
    monkeypatch.setenv("SCHED_TICK", "0")
    context = start_all(max_ticks=2)
    assert "self_heal" in context.jobs
    assert context.scheduler is not None
