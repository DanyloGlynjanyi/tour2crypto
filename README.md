# Tour2Crypto Contracts, Events & Logic

This repository contains the Tour2Crypto contract definitions, JSON Schema validation helpers, fixture factories, and an event
layer with formal schemas and idempotent delivery. The focus is on a ledger-first approach for wallet balances. All identifiers
are ULID strings, timestamps use ISO8601 UTC format, and monetary values are stored as strings with a decimal dot.

## Features
- JSON Schema definitions for core contracts: Trip, Application, Wallet, Cashback Ledger Entry, Withdrawal Request, and Audit Event.
- Pydantic models mirroring the schemas for convenient Python usage.
- Faker-powered factories for generating realistic fixture payloads.
- Ledger utilities ensuring wallet balances are derived solely from ledger entries.
- Business logic module (`t2c_logic`) wiring event handlers to ledger and wallet state with idempotent processing.
- Event catalog covering application, trip, ledger, withdrawal, and wallet lifecycle events.
- Synchronous in-memory event bus with idempotent consumer helper and schema-driven validation layer.
- Pytest suite covering contract validation, ledger balance integration, and event flow scenarios.

## Requirements
- Python 3.11
- Dependencies: `jsonschema`, `pydantic`, `faker`, `pytest`

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
pip install --upgrade pip
pip install -e .
```

## Usage
Run the tests:
```bash
pytest -v
```

Generate a sample payload bundle:
```bash
make sample
```

The sample command prints a JSON object with valid payload examples for the core contracts.

## Event Layer Overview
- Event schemas live in `t2c_events/schemas` (one JSON file per event) with an index at `events_index.json` for easy discovery.
- Each event includes `event_id`, `event_type`, `event_time`, optional causation/correlation identifiers, and a typed payload.
- The `EventBus` provides synchronous publish/subscribe mechanics, while `IdempotentConsumer` uses an `IdempotencyStore` to
  prevent duplicate handler execution when the same `event_id` is observed multiple times.
- `t2c_events.validators` exposes helpers for validating events before handling.

## Business Logic Overview
- `t2c_logic` exposes a pre-wired `EventBus` that connects `trip_completed`, `withdrawal_requested`, and `withdrawal_paid`
  events to ledger operations.
- Cashback amounts default to **10.00 USDT** unless a specific trip reward is registered via `set_trip_reward` prior to
  emitting a `trip_completed` event.
- Withdrawal flows first place a temporary adjustment (lock) and then release it before applying the final payout, ensuring
  wallet balances remain ledger-first and idempotent across retries.

## Rules & Invariants
- `t2c_rules.assert_invariants` guards the ledger after each mutation, enforcing:
  - **R1** — ledger amounts are string-encoded decimals.
  - **R2** — directions align with types: cashback accrual → credit, reversal → debit, lock optional, payout → debit.
  - **R3** — available balance (`credit - debit - locked`) is never negative.
  - **R4** — payouts cannot exceed previously locked funds.
  - **R5** — releases never exceed the outstanding lock.
  - **R6** — cashback reversals never surpass accruals for the same trip.
  - **R7** — ledger types are restricted to the supported enum.
- Compute a snapshot with `t2c_rules.compute_available` and validate via `pytest -v tests/test_rules_invariants_ok.py`.

## Design Notes
- ULIDs are generated locally from the official character set using pseudo-random data, which is sufficient for tests and fixtures.
- All balances are computed from ledger entries to enforce ledger-first accounting.
- Destination addresses default to a short deterministic format and can be overridden via factory arguments.
- Event handlers cover both cashback accruals and withdrawal flows, ensuring ledger impacts remain deterministic and
  idempotent.

## Spec v1 & Reports
- The canonical specification lives in [`docs/SPEC_V1.md`](docs/SPEC_V1.md) with changelog updates in [`docs/CHANGELOG.md`](docs/CHANGELOG.md).
- Generate an end-to-end validation report (tests, smoke flow, invariants) via:
  ```bash
  make report
  ```
  The command writes `reports/e2e_report.md` with the latest results and summaries.

## Data Infrastructure (SQLite/Supabase)
- Apply migrations locally:
  ```bash
  make db-migrate
  ```
- Seed deterministic demo data and print a summary (wallet, ledger, balances):
  ```bash
  make db-seed
  ```
- SQLite DDL lives in [`db/schema_sqlite.sql`](db/schema_sqlite.sql) with matching migrations under [`db/migrations/`](db/migrations/).
- Supabase/Postgres DDL and RLS examples are available in [`db/schema_supabase.sql`](db/schema_supabase.sql) and [`db/rls_supabase.sql`](db/rls_supabase.sql).

## Event Pipeline (Local)
- Run the asyncio demo that wires the collector, queue, worker, and business handlers:
  ```bash
  python scripts/pipeline_demo.py
  ```
- Collectors simulate upstream producers that emit fully validated events, the async queue buffers them, and the worker performs validation, retry with exponential backoff, and dead-letter routing after exhausting attempts.
- Metrics (`processed_ok`, `retried`, `dead_lettered`) are exposed via `t2c_pipeline.metrics`, and the in-memory dead-letter list can be inspected from the worker instance.
- This local queue is intentionally lightweight; in production it can be swapped for a dedicated broker while reusing the collector and worker interfaces.

## Telegram Bot Layer (Simulation Mode)
- Launch the Aiogram-based simulation without contacting Telegram servers:
  ```bash
  make bot-simulate
  ```
- The bot wires user and admin routers, reuses the local event pipeline, and prints a summary with the final wallet balance.
- Offline-only mode: networking is disabled, so the application focuses on deterministic flows that can later be replaced with real polling.

## Web Dashboard API
- Start the FastAPI service bound to the seeded SQLite database:
  ```bash
  make api-run
  ```
- The CLI wraps `uvicorn` and exposes endpoints such as:
  - `GET /health` → service heartbeat.
  - `GET /wallets/{user_id}/balance` → ledger-first available & locked amounts.
  - `GET /trips?user_id=...` → traveller trips from SQLite.
  - `GET /ledger?wallet_id=...` → raw cashback ledger entries.
  - `GET /reports/daily_summary` → aggregate counts and total available.
- The root path serves a minimal HTML dashboard for quick inspection.

## Static Dashboard
- Open [`t2c_api/static/index.html`](t2c_api/static/index.html) in a browser after starting the API.
- The page is fully self-contained (no CDN) and issues `fetch` calls against `http://127.0.0.1:8000`.
- Provide a `user_id` or `wallet_id` to load balances, trip history, and ledger snapshots into interactive `<pre>` blocks.

## Supabase Sync (offline)
- Generate CSV, JSON, and SQL upsert artefacts ready for manual upload:
  ```bash
  make sync-export
  ```
- Outputs land in `exports/` and include `supabase_upsert.sql` with `INSERT ... ON CONFLICT` statements for all primary tables.
- The SQL assumes a primary key of `id` on each table (ledger, trips, wallets, applications, withdrawals, audit events) and updates the latest snapshot when run inside Supabase/Postgres.
