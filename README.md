# Tour2Crypto Contracts

This repository contains the Tour2Crypto contract definitions, JSON Schema validation helpers, fixture factories, and integration tests. The focus is on a ledger-first approach for wallet balances. All identifiers are ULID strings, timestamps use ISO8601 UTC format, and monetary values are stored as strings with a decimal dot.

## Features
- JSON Schema definitions for core contracts: Trip, Application, Wallet, Cashback Ledger Entry, Withdrawal Request, and Audit Event.
- Pydantic models mirroring the schemas for convenient Python usage.
- Faker-powered factories for generating realistic fixture payloads.
- Ledger utilities ensuring wallet balances are derived solely from ledger entries.
- Pytest suite covering validation and balance calculation.

## Requirements
- Python 3.11
- Dependencies: `jsonschema`, `pydantic`, `faker`, `pytest`

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
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

The sample command prints a JSON object with valid payload examples.

## Design Notes
- ULIDs are generated locally from the official character set using pseudo-random data, which is sufficient for tests and fixtures.
- All balances are computed from ledger entries to enforce ledger-first accounting.
- Destination addresses default to a short deterministic format and can be overridden via factory arguments.
