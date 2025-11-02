# Tour2Crypto Snapshot v3.5

## Architecture Overview
- **Contracts & Validation**: `t2c_contracts` holds JSON Schemas, Pydantic models, fixture factories, and ledger utilities ensuring ledger-first balances.
- **Events Layer**: `t2c_events` exposes schema-backed validations, synchronous event bus, and idempotent consumers.
- **Business Logic**: `t2c_logic` links trip completion, cashback accruals, and withdrawal flows, while `t2c_rules` enforces invariants R1–R7 on ledger movements.
- **Pipeline**: `t2c_pipeline` simulates collectors, async queue, retrying worker, and metrics for event ingestion.
- **Bot & Reports**: `t2c_bot` delivers a simulation-mode UX; `t2c_reports` aggregates daily metrics and weekly PnL with Telegram delivery shims.
- **API & Sync**: `t2c_api` provides FastAPI endpoints and static dashboard; `t2c_sync` exports SQLite data and Supabase upsert scripts.
- **Autonomy**: `t2c_autonomy` orchestrates scheduler jobs, self-healing guards, and consolidated monitoring; diagnostics live in `t2c_diag`.

## Environment Keys (.env)
| Key | Description | Default |
| --- | --- | --- |
| `MODE` | Runtime mode (`simulation` recommended offline) | `simulation` |
| `DB_PATH` | SQLite database path | `db/tour2crypto.db` |
| `BOT_TOKEN` / `ADMIN_CHAT_ID` | Telegram credentials (optional offline) | empty / `0` |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase placeholders for sync exports | empty |
| `OPENAI_API_KEY` | Reserved for future AI integration | empty |
| `REPORT_SCHEDULE` | Describes operational cadence | `daily` |
| `LOG_LEVEL` / `LOG_FILE` | Logging level and destination | `INFO` / `logs/t2c.log` |
| `SCHED_TICK` | Base scheduler tick interval (seconds) | `1` |
| `REPORT_INTERVAL` | Scheduler interval for scheduled reports | `86400` |
| `HEARTBEAT_MAX_AGE_SEC` | Max age for heartbeat freshness | `120` |
| `HEAL_DEADLETTER_THRESHOLD` | Dead-letter count before pipeline restart | `1` |
| `HEAL_REPORT_STALLED_TICKS` | Allowed consecutive stale report ticks | `3` |
| `HEAL_API_MIN_REQUESTS` | Expected API activity minimum | `0` |
| `HEAL_INTERVAL` | Interval for self-heal checks | `5` |

## Ledger Invariants (R1–R7)
1. **R1**: Ledger amounts are stored as strings and parse cleanly into `Decimal`.
2. **R2**: Ledger `direction` matches entry `type` (`cashback_accrual→credit`, `cashback_reversal→debit`, `withdrawal_lock→locked`, `payout→debit`, `withdrawal_release→unlock`).
3. **R3**: Available balance (`credit - debit - locked`) never falls below zero.
4. **R4**: `payout` entries require sufficient prior `withdrawal_lock` coverage.
5. **R5**: `withdrawal_release` cannot exceed existing locked amounts.
6. **R6**: `cashback_reversal` is bounded by matching trip accrual totals.
7. **R7**: Ledger types are limited to the sanctioned enum values.

## Autonomy Jobs & Self-Healing
- **Pipeline Tick**: Ensures events are queued and processed with retries/backoff.
- **Scheduled Report**: Generates Markdown daily summary and Telegram simulation delivery.
- **Heartbeat & Metrics**: Emits heartbeat timestamp and rotates metrics history.
- **Self-Heal**: Monitors dead letters, heartbeat age, stalled reports, and API activity, reinitialising the worker or forcing reports when thresholds are exceeded.

## UX / Monitoring Touchpoints
- **Bot Simulation**: `tour2crypto-bot` or `make bot-simulate` displays balances and admin controls offline.
- **Web Dashboard**: `t2c-api` (FastAPI) with static `t2c_api/static/index.html` for manual inspection.
- **Diagnostics**: `scripts/diag_run.py` summarises log and metric anomalies; metrics available via `/metrics` or `t2c_core.metrics.snapshot()`.

## Final E2E Checklist (≈5 minutes)
1. `python scripts/make_env.py` — ensure `.env` exists with desired overrides.
2. `python db/migrate.py` & `python db/seed.py` — reset SQLite schema and demo data.
3. `pytest -v` — confirm contract, pipeline, API, and autonomy tests pass.
4. `python scripts/pipeline_demo.py` & `python scripts/report_daily.py` — verify pipeline and reporting flows.
5. `t2c-start` (simulation) for limited ticks or `python scripts/start_all.py --max-ticks 5` — observe scheduler, self-healing logs, and generated metrics.

Version: **Spec v3.5** (extends SPEC v1 foundation with autonomy and monitoring).
