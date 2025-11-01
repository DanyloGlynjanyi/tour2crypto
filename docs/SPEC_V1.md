# Tour2Crypto Specification v1.0.0

## Overview
Tour2Crypto combines travel rewards with a ledger-first crypto wallet. This specification captures the v1 data contracts,
event catalog, business rules, and UX navigation for the platform. All identifiers are ULIDs, timestamps use ISO8601 UTC,
and monetary values are decimal strings denominated in USDT.

## Data Model
Each contract is represented as both JSON Schema and Pydantic model in `t2c_contracts`.

### Trip
| Field | Type | Description |
| --- | --- | --- |
| `id` | ULID string | Trip identifier. |
| `traveler_id` | ULID string | Traveler who owns the trip. |
| `application_id` | ULID string (optional) | Associated application reference. |
| `destination` | string | Destination city or location. |
| `start_at` | ISO8601 UTC string | Trip start timestamp. |
| `end_at` | ISO8601 UTC string | Trip end timestamp. |
| `created_at` | ISO8601 UTC string | Record creation timestamp. |
| `status` | enum (`planned`, `completed`, `cancelled`) | Trip lifecycle status. |
| `metadata` | object (optional) | Arbitrary key/value metadata. |

### Application
| Field | Type | Description |
| --- | --- | --- |
| `id` | ULID string | Application identifier. |
| `traveler_id` | ULID string | Owner of the application. |
| `trip_type` | string | Requested trip category. |
| `submitted_at` | ISO8601 UTC string | Submission timestamp. |
| `status` | enum (`draft`, `submitted`, `approved`, `rejected`) | Approval state. |
| `notes` | string (optional) | Reviewer or applicant notes. |

### Wallet
| Field | Type | Description |
| --- | --- | --- |
| `id` | ULID string | Wallet identifier. |
| `owner_id` | ULID string | Traveler owning the wallet. |
| `currency` | string (`USDT`) | Ledger currency. |
| `created_at` | ISO8601 UTC string | Creation timestamp. |
| `description` | string (optional) | Wallet label. |

### CashbackLedger Entry
| Field | Type | Description |
| --- | --- | --- |
| `id` | ULID string | Ledger entry identifier. |
| `wallet_id` | ULID string | Wallet impacted by the entry. |
| `trip_id` | ULID string | Trip that triggered the entry. |
| `amount` | decimal string (±) | Amount applied to the ledger. |
| `entry_type` | enum (`cashback`, `adjustment`, `withdrawal`) | Ledger classification. |
| `occurred_at` | ISO8601 UTC string | Event timestamp for the entry. |
| `description` | string (optional) | Human readable context. |
| `reference` | string (optional) | External correlation id. |

### WithdrawalRequest
| Field | Type | Description |
| --- | --- | --- |
| `id` | ULID string | Withdrawal request identifier. |
| `wallet_id` | ULID string | Wallet requesting funds. |
| `requested_amount` | decimal string | Requested payout amount. |
| `status` | enum (`pending`, `approved`, `rejected`, `processed`) | Workflow status. |
| `requested_at` | ISO8601 UTC string | Request timestamp. |
| `processed_at` | ISO8601 UTC string (optional) | Fulfillment timestamp. |
| `destination_address` | string (optional) | Payout destination. |

### AuditEvent
| Field | Type | Description |
| --- | --- | --- |
| `id` | ULID string | Audit event identifier. |
| `actor_id` | ULID string | Actor who performed the action. |
| `entity_type` | string | Domain entity touched. |
| `entity_id` | ULID string | Identifier of the impacted entity. |
| `action` | string | Action verb. |
| `payload` | object | JSON payload describing the action. |
| `created_at` | ISO8601 UTC string | Event creation timestamp. |
| `ip_address` | string (optional) | Source IP (if known). |

## Event Model
Events are described as JSON Schema files in `t2c_events/schemas` with a shared envelope:
`event_id` (ULID), `event_type` (enum), `event_time` (ISO8601 UTC), optional `causation_id` and
`correlation_id`, and a typed `payload`.

### Event Catalog
| Event Type | Payload Highlights |
| --- | --- |
| `application_created` | `application_id`, `traveler_id`, `status`, optional `reason`. |
| `application_approved` | `application_id`, `traveler_id`, approval metadata. |
| `application_rejected` | `application_id`, `traveler_id`, rejection `reason`. |
| `trip_booked` | `trip_id`, `traveler_id`, `status`, `booking_reference`. |
| `trip_completed` | `trip_id`, `traveler_id`, `status`, `completed_at`. |
| `trip_cancelled` | `trip_id`, `traveler_id`, cancellation `reason`. |
| `ledger_cashback_accrued` | `ledger_entry_id`, `wallet_id`, `trip_id`, `amount`, `entry_type`. |
| `ledger_cashback_reversed` | Accrual reversal reason and entry identifiers. |
| `withdrawal_requested` | `withdrawal_request_id`, `wallet_id`, `amount`, optional destination. |
| `withdrawal_locked` | `withdrawal_request_id`, `wallet_id`, `lock_id`, `amount`. |
| `withdrawal_paid` | `withdrawal_request_id`, `wallet_id`, `amount`, `transaction_id`. |
| `withdrawal_rejected` | `withdrawal_request_id`, `wallet_id`, rejection `reason`. |
| `wallet_frozen` | `wallet_id`, suspension `reason`. |
| `wallet_reactivated` | `wallet_id`, reinstatement note. |

### Idempotency Guarantees
- Each event is processed through `IdempotentConsumer` with per-type stores ensuring at-least-once delivery without
  double execution when `event_id` repeats.
- Schema validation occurs before handler invocation, guaranteeing payload shape alignment.
- Business handlers are deterministic and ledger-first; repeating the same event yields no additional ledger mutation.

## Ledger Rules (R1–R7)
1. **R1 — Amount Format**: Ledger amounts are decimal strings parsable into `Decimal` and fixed to two decimal places.
2. **R2 — Direction & Type**: Directions align with types: cashback accrual → credit, cashback reversal → debit, withdrawal
   lock → optional debit, payout → debit, withdrawal release → neutral on credit/debit.
3. **R3 — Non-negative Availability**: Available balance (`credit - debit - locked`) never becomes negative.
4. **R4 — Lock Before Payout**: Payout entries require a prior withdrawal lock with sufficient funds.
5. **R5 — Release Bounds**: Withdrawal releases cannot exceed the outstanding locked amount.
6. **R6 — Cashback Reversal Bound**: Reversals never exceed total accrual for the same trip and wallet.
7. **R7 — Type Enum**: Only supported ledger types are permitted; unrecognized values are rejected.

## UX Navigation Map
1. **Traveler Dashboard** — Summary of trips, wallet balance, and recent events.
2. **Trip Planner** — Create and manage trip applications, view approval status.
3. **Rewards Ledger** — Inspect cashback accruals, reversals, locks, and payouts.
4. **Withdrawal Center** — Initiate withdrawals, monitor locks, submit payout details.
5. **Compliance Console** — Review audit events, freeze/reactivate wallets, manage manual overrides.

## Glossary
- **ULID** — Universally Unique Lexicographically Sortable Identifier (`26`-character Crockford base32 string).
- **ISO8601 UTC** — Timestamp formatted as `YYYY-MM-DDTHH:MM:SSZ` in Coordinated Universal Time.
- **Ledger-first** — Wallet balance is derived solely from ledger entries; no direct balance mutation exists.
- **bps** — Basis points; equal to one hundredth of one percent, used for fee or reward rate discussions.

## Versioning
This specification follows Semantic Versioning. The current release is **SPEC v1.0.0**. Future updates will increment MAJOR
for breaking changes, MINOR for backward-compatible additions, and PATCH for clarifications without behavior changes.
