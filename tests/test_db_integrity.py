from __future__ import annotations

import sqlite3
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

TWOPLACES = Decimal('0.01')

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

DB_PATH = Path("db") / "tour2crypto.db"


@pytest.fixture(scope="module")
def seeded_db() -> Path:
    result = subprocess.run([sys.executable, "db/seed.py"], check=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    assert DB_PATH.exists(), "Seed script did not create the database"
    return DB_PATH


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def test_tables_populated(seeded_db: Path) -> None:
    with _connect(seeded_db) as connection:
        for table in [
            "wallets",
            "applications",
            "trips",
            "withdrawals",
            "cashback_ledger",
            "audit_events",
        ]:
            cursor = connection.execute(f"SELECT COUNT(*) AS count FROM {table}")
            assert cursor.fetchone()["count"] > 0, f"Table {table} should contain seed data"


def test_wallet_balance_view_matches_ledger(seeded_db: Path) -> None:
    with _connect(seeded_db) as connection:
        wallet_row = connection.execute("SELECT * FROM wallets LIMIT 1").fetchone()
        assert wallet_row is not None
        wallet_id = wallet_row["id"]

        view_row = connection.execute(
            "SELECT credit_total, debit_total, locked_total, available_amount FROM wallet_balances WHERE wallet_id = ?",
            (wallet_id,),
        ).fetchone()
        assert view_row is not None
        credit_from_view = Decimal(view_row["credit_total"]).quantize(TWOPLACES)
        debit_from_view = Decimal(view_row["debit_total"]).quantize(TWOPLACES)
        locked_from_view = Decimal(view_row["locked_total"]).quantize(TWOPLACES)
        available_from_view = Decimal(view_row["available_amount"]).quantize(TWOPLACES)

        ledger_rows = connection.execute(
            "SELECT * FROM cashback_ledger WHERE wallet_id = ?",
            (wallet_id,),
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
            for row in ledger_rows
        ]
        balance = Decimal(compute_wallet_balance(ledger_models)).quantize(TWOPLACES)

        def amount_abs(row: sqlite3.Row) -> Decimal:
            return abs(Decimal(row["amount"])).quantize(TWOPLACES)

        expected_credit = sum(
            (amount_abs(row) for row in ledger_rows if row["rule_type"] == "cashback_accrual"),
            Decimal("0.00"),
        ).quantize(TWOPLACES)
        expected_debit = sum(
            (
                amount_abs(row)
                for row in ledger_rows
                if row["rule_type"] in {"cashback_reversal", "payout"}
            ),
            Decimal("0.00"),
        ).quantize(TWOPLACES)
        total_locks = sum(
            (amount_abs(row) for row in ledger_rows if row["rule_type"] == "withdrawal_lock"),
            Decimal("0.00"),
        )
        total_releases = sum(
            (amount_abs(row) for row in ledger_rows if row["rule_type"] == "withdrawal_release"),
            Decimal("0.00"),
        )
        expected_locked = (total_locks - total_releases).quantize(TWOPLACES)
        assert expected_locked >= Decimal("0.00")

        expected_available = (expected_credit - expected_debit - expected_locked).quantize(TWOPLACES)

        assert credit_from_view == expected_credit
        assert debit_from_view == expected_debit
        assert locked_from_view == expected_locked
        assert available_from_view == expected_available
        assert balance == available_from_view


def test_ledger_rules_and_relationships(seeded_db: Path) -> None:
    with _connect(seeded_db) as connection:
        ledger_rows = connection.execute("SELECT * FROM cashback_ledger").fetchall()
        allowed_entry_types = {"cashback", "adjustment", "withdrawal"}
        allowed_directions = {None, "credit", "debit"}
        allowed_rule_types = {
            "cashback_accrual",
            "cashback_reversal",
            "withdrawal_lock",
            "withdrawal_release",
            "payout",
        }
        for row in ledger_rows:
            assert row["entry_type"] in allowed_entry_types
            assert row["direction"] in allowed_directions
            assert row["rule_type"] in allowed_rule_types

        lock_totals: dict[str, Decimal] = {}
        for row in ledger_rows:
            if row["rule_type"] == "withdrawal_lock":
                lock_totals[row["lock_id"]] = lock_totals.get(row["lock_id"], Decimal("0.00")) + abs(Decimal(row["amount"]))

        for row in ledger_rows:
            if row["rule_type"] == "payout":
                lock_id = row["lock_id"]
                assert lock_id in lock_totals
                assert abs(Decimal(row["amount"])) <= lock_totals[lock_id]

        rules_ledger = []
        for row in ledger_rows:
            entry = {
                "type": row["rule_type"],
                "wallet_id": row["wallet_id"],
            }
            amount_value = abs(Decimal(row["amount"]))
            entry["amount"] = f"{amount_value:.2f}"
            if row["rule_type"] != "withdrawal_release" and row["direction"]:
                entry["direction"] = row["direction"]
            if row["lock_id"]:
                entry["lock_id"] = row["lock_id"]
            if row["trip_id"]:
                entry["trip_id"] = row["trip_id"]
            rules_ledger.append(entry)

        assert_invariants(rules_ledger)
        available = compute_available(rules_ledger)
        assert available >= Decimal("0.00")


def test_row_validation_against_contracts(seeded_db: Path) -> None:
    with _connect(seeded_db) as connection:
        wallet_row = connection.execute("SELECT * FROM wallets LIMIT 1").fetchone()
        WalletModel(
            id=wallet_row["id"],
            owner_id=wallet_row["owner_id"],
            currency=wallet_row["currency"],
            created_at=wallet_row["created_at"],
            description=wallet_row["description"],
        )

        application_row = connection.execute("SELECT * FROM applications LIMIT 1").fetchone()
        ApplicationModel(
            id=application_row["id"],
            traveler_id=application_row["traveler_id"],
            trip_type=application_row["trip_type"],
            submitted_at=application_row["submitted_at"],
            status=application_row["status"],
            notes=application_row["notes"],
        )

        trip_row = connection.execute("SELECT * FROM trips LIMIT 1").fetchone()
        TripModel(
            id=trip_row["id"],
            traveler_id=trip_row["traveler_id"],
            application_id=trip_row["application_id"],
            destination=trip_row["destination"],
            start_at=trip_row["start_at"],
            end_at=trip_row["end_at"],
            created_at=trip_row["created_at"],
            status=trip_row["status"],
        )

        withdrawal_row = connection.execute("SELECT * FROM withdrawals LIMIT 1").fetchone()
        WithdrawalRequestModel(
            id=withdrawal_row["id"],
            wallet_id=withdrawal_row["wallet_id"],
            requested_amount=withdrawal_row["requested_amount"],
            status=withdrawal_row["status"],
            requested_at=withdrawal_row["requested_at"],
            processed_at=withdrawal_row["processed_at"],
            destination_address=withdrawal_row["destination_address"],
        )

        audit_row = connection.execute("SELECT * FROM audit_events LIMIT 1").fetchone()
        AuditEventModel(
            id=audit_row["id"],
            actor_id=audit_row["actor_id"],
            entity_type=audit_row["entity_type"],
            entity_id=audit_row["entity_id"],
            action=audit_row["action"],
            payload={"seed": audit_row["payload"]},
            created_at=audit_row["created_at"],
            ip_address=audit_row["ip_address"],
        )

        ledger_row = connection.execute("SELECT * FROM cashback_ledger LIMIT 1").fetchone()
        CashbackLedgerEntryModel(
            id=ledger_row["id"],
            wallet_id=ledger_row["wallet_id"],
            trip_id=ledger_row["trip_id"],
            amount=ledger_row["amount"],
            entry_type=ledger_row["entry_type"],
            occurred_at=ledger_row["occurred_at"],
            description=ledger_row["description"],
            reference=ledger_row["reference"],
        )
