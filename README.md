# Tour2Crypto Contracts & Events

This repository contains the Tour2Crypto contract definitions, JSON Schema validation helpers, fixture factories, and an event
layer with formal schemas and idempotent delivery. The focus is on a ledger-first approach for wallet balances. All identifiers
are ULID strings, timestamps use ISO8601 UTC format, and monetary values are stored as strings with a decimal dot.

## Features
- JSON Schema definitions for core contracts: Trip, Application, Wallet, Cashback Ledger Entry, Withdrawal Request, and Audit Event.
- Pydantic models mirroring the schemas for convenient Python usage.
- Faker-powered factories for generating realistic fixture payloads.
- Ledger utilities ensuring wallet balances are derived solely from ledger entries.
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

## Design Notes
- ULIDs are generated locally from the official character set using pseudo-random data, which is sufficient for tests and fixtures.
- All balances are computed from ledger entries to enforce ledger-first accounting.
- Destination addresses default to a short deterministic format and can be overridden via factory arguments.
- Event handlers in tests demonstrate chaining from `trip_completed` to `ledger_cashback_accrued`, ensuring ledger impacts remain
  deterministic.
