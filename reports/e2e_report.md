# E2E Report — 2025-10-31 08:19:43Z (UTC)

## Specification
- Version: v1.0.0
- Document: docs/SPEC_V1.md

## Test Results
- Command: `pytest -q`
- Status: PASS
- Summary: 19 passed / 0 failed / 0 skipped / 19 total
- Output:
```
...................                                                                                                      [100%]
```

## Smoke Scenario
- Wallet: 1Y0RKG7ZCJQ03YVXWEQR9918HQ
- Trip: 8DTP1SSSNBNH4KX8QKB7Y1MN2Q
- Withdrawal Request: RHAMRZEY2N3GPVRSGDT64A638H
- Balance after cashback: 45.00
- Balance after lock: 30.00
- Final balance: 30.00
- Ledger entries recorded: 4
- Available balance: 30.00

## Invariants
- Status: OK

## Validation
- Entities validated: Trip, Application, Wallet, CashbackLedgerEntry, WithdrawalRequest, AuditEvent

## Counters
- Contract schemas: 6
- Event schemas: 14
- Tests executed: 19
