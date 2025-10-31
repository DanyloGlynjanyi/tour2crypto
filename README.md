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

## Design Notes
- ULIDs are generated locally from the official character set using pseudo-random data, which is sufficient for tests and fixtures.
- All balances are computed from ledger entries to enforce ledger-first accounting.
- Destination addresses default to a short deterministic format and can be overridden via factory arguments.
- Event handlers cover both cashback accruals and withdrawal flows, ensuring ledger impacts remain deterministic and
  idempotent.
