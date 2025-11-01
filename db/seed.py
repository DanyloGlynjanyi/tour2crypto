"""Seed the SQLite database with deterministic demo data."""

from __future__ import annotations

import sqlite3
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from t2c_contracts.factories import (
    ApplicationFactory,
    AuditEventFactory,
    CashbackLedgerEntryFactory,
    TripFactory,
    WalletFactory,
    WithdrawalRequestFactory,
)
from t2c_contracts.ledger import compute_wallet_balance
from t2c_contracts.validation import (
    ApplicationModel,
    AuditEventModel,
    CashbackLedgerEntryModel,
    TripModel,
    WalletModel,
    WithdrawalRequestModel,
)
from t2c_rules import assert_invariants, compute_available

from db.migrate import DEFAULT_DB_PATH, MIGRATIONS_DIR, apply_migrations

DB_PATH = DEFAULT_DB_PATH


def _abs_amount(value: str) -> str:
    amount = Decimal(value)
    return f"{abs(amount):.2f}"


def seed() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    applied = apply_migrations(DB_PATH, MIGRATIONS_DIR)

    wallet_payload = WalletFactory().build()
    wallet = WalletModel(**wallet_payload)

    application_payload = ApplicationFactory().build(
        traveler_id=wallet.owner_id,
        status="approved",
    )
    application = ApplicationModel(**application_payload)

    trip_payload = TripFactory().build(
        traveler_id=wallet.owner_id,
        application_id=application.id,
        status="completed",
    )
    trip = TripModel(**trip_payload)

    withdrawal_payload = WithdrawalRequestFactory().build(
        wallet_id=wallet.id,
        requested_amount="4.00",
        status="processed",
    )
    withdrawal = WithdrawalRequestModel(**withdrawal_payload)

    ledger_factory = CashbackLedgerEntryFactory()

    cashback_entry = ledger_factory.build(
        wallet_id=wallet.id,
        trip_id=trip.id,
        amount="15.00",
        entry_type="cashback",
        reference=f"{trip.id}-cashback",
    )
    CashbackLedgerEntryModel(**cashback_entry)

    lock_entry = ledger_factory.build(
        wallet_id=wallet.id,
        trip_id=trip.id,
        amount="-4.00",
        entry_type="adjustment",
        reference=f"{withdrawal.id}-lock",
    )
    CashbackLedgerEntryModel(**lock_entry)

    payout_entry = ledger_factory.build(
        wallet_id=wallet.id,
        trip_id=trip.id,
        amount="-4.00",
        entry_type="withdrawal",
        reference=f"{withdrawal.id}-payout",
    )
    CashbackLedgerEntryModel(**payout_entry)

    release_entry = ledger_factory.build(
        wallet_id=wallet.id,
        trip_id=trip.id,
        amount="4.00",
        entry_type="adjustment",
        reference=f"{withdrawal.id}-release",
    )
    CashbackLedgerEntryModel(**release_entry)

    audit_payload = AuditEventFactory().build(entity_id=wallet.id)
    audit_event = AuditEventModel(**audit_payload)

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO wallets (id, owner_id, currency, created_at, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                wallet.id,
                wallet.owner_id,
                wallet.currency,
                wallet.created_at,
                wallet.description,
            ),
        )

        cursor.execute(
            """
            INSERT INTO applications (id, traveler_id, trip_type, submitted_at, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                application.id,
                application.traveler_id,
                application.trip_type,
                application.submitted_at,
                application.status,
                application.notes,
            ),
        )

        cursor.execute(
            """
            INSERT INTO trips (id, traveler_id, application_id, partner_id, destination, start_at, end_at, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trip.id,
                trip.traveler_id,
                trip.application_id,
                None,
                trip.destination,
                trip.start_at,
                trip.end_at,
                trip.created_at,
                trip.status,
            ),
        )

        cursor.execute(
            """
            INSERT INTO withdrawals (id, wallet_id, requested_amount, status, requested_at, processed_at, destination_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                withdrawal.id,
                withdrawal.wallet_id,
                withdrawal.requested_amount,
                withdrawal.status,
                withdrawal.requested_at,
                withdrawal.processed_at,
                withdrawal.destination_address,
            ),
        )

        ledger_rows: List[Dict[str, Any]] = [
            {
                "data": cashback_entry,
                "rule_type": "cashback_accrual",
                "direction": "credit",
                "lock_id": None,
            },
            {
                "data": lock_entry,
                "rule_type": "withdrawal_lock",
                "direction": "debit",
                "lock_id": withdrawal.id,
            },
            {
                "data": payout_entry,
                "rule_type": "payout",
                "direction": "debit",
                "lock_id": withdrawal.id,
            },
            {
                "data": release_entry,
                "rule_type": "withdrawal_release",
                "direction": None,
                "lock_id": withdrawal.id,
            },
        ]

        for row in ledger_rows:
            payload = row["data"]
            cursor.execute(
                """
                INSERT INTO cashback_ledger (
                    id,
                    wallet_id,
                    trip_id,
                    withdrawal_id,
                    amount,
                    entry_type,
                    rule_type,
                    direction,
                    occurred_at,
                    description,
                    reference,
                    lock_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["wallet_id"],
                    payload.get("trip_id"),
                    withdrawal.id,
                    payload["amount"],
                    payload["entry_type"],
                    row["rule_type"],
                    row["direction"],
                    payload["occurred_at"],
                    payload.get("description"),
                    payload.get("reference"),
                    row["lock_id"],
                ),
            )

        cursor.execute(
            """
            INSERT INTO audit_events (id, actor_id, entity_type, entity_id, action, payload, created_at, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_event.id,
                audit_event.actor_id,
                audit_event.entity_type,
                audit_event.entity_id,
                audit_event.action,
                str(audit_event.payload),
                audit_event.created_at,
                audit_event.ip_address,
            ),
        )

        connection.commit()

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM cashback_ledger WHERE wallet_id = ? ORDER BY occurred_at",
            (wallet.id,),
        ).fetchall()

    ledger_models = [
        CashbackLedgerEntryModel(
            id=row["id"],
            wallet_id=row["wallet_id"],
            trip_id=row["trip_id"],
            amount=row["amount"],
            entry_type=row["entry_type"],
            occurred_at=row["occurred_at"],
            description=row["description"],
            reference=row["reference"],
        )
        for row in rows
    ]
    balance = compute_wallet_balance(ledger_models)

    meta_by_reference = {row["data"].get("reference"): row for row in ledger_rows}
    rules_ledger = []
    for stored in rows:
        meta = meta_by_reference.get(stored["reference"])
        if meta is None:
            continue
        entry = {
            "type": meta["rule_type"],
            "wallet_id": stored["wallet_id"],
            "amount": _abs_amount(stored["amount"]),
        }
        if stored["direction"] and meta["rule_type"] != "withdrawal_release":
            entry["direction"] = stored["direction"]
        if stored["lock_id"]:
            entry["lock_id"] = stored["lock_id"]
        if stored["trip_id"]:
            entry["trip_id"] = stored["trip_id"]
        rules_ledger.append(entry)

    assert_invariants(rules_ledger)
    available = compute_available(rules_ledger)

    print("Applied migrations:")
    for migration in applied:
        print(f"  - {migration.name}")
    print("Seeded entities:")
    print("  - wallets: 1")
    print("  - applications: 1")
    print("  - trips: 1 (completed)")
    print("  - withdrawals: 1 (processed)")
    print("  - ledger entries: 4")
    print(f"Wallet {wallet.id} balance: {balance}")
    print(f"Available per invariants: {available:.2f}")


if __name__ == "__main__":
    seed()
