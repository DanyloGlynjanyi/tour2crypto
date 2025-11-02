from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

from fastapi.testclient import TestClient

from db.migrate import MIGRATIONS_DIR, apply_migrations
from t2c_api import create_app
from t2c_contracts.factories import (
    ApplicationFactory,
    CashbackLedgerEntryFactory,
    TripFactory,
    WalletFactory,
    WithdrawalRequestFactory,
)


def _setup_database(tmp_path: Path) -> Dict[str, str]:
    db_path = tmp_path / "api.db"
    apply_migrations(db_path=db_path, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(db_path)

    wallet = WalletFactory().build()
    application = ApplicationFactory().build(traveler_id=wallet["owner_id"], status="approved")
    trip = TripFactory().build(
        traveler_id=wallet["owner_id"],
        application_id=application["id"],
        status="completed",
    )
    withdrawal = WithdrawalRequestFactory().build(wallet_id=wallet["id"], requested_amount="5.00", status="processed")

    conn.execute(
        "INSERT INTO wallets (id, owner_id, currency, created_at, description) VALUES (?, ?, ?, ?, ?)",
        (
            wallet["id"],
            wallet["owner_id"],
            wallet["currency"],
            wallet["created_at"],
            wallet["description"],
        ),
    )
    conn.execute(
        "INSERT INTO applications (id, traveler_id, trip_type, submitted_at, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (
            application["id"],
            application["traveler_id"],
            application["trip_type"],
            application["submitted_at"],
            application["status"],
            application["notes"],
        ),
    )
    conn.execute(
        "INSERT INTO trips (id, traveler_id, application_id, partner_id, destination, start_at, end_at, created_at, status)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            trip["id"],
            trip["traveler_id"],
            trip["application_id"],
            None,
            trip["destination"],
            trip["start_at"],
            trip["end_at"],
            trip["created_at"],
            trip["status"],
        ),
    )
    conn.execute(
        "INSERT INTO withdrawals (id, wallet_id, requested_amount, status, requested_at, processed_at, destination_address)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            withdrawal["id"],
            withdrawal["wallet_id"],
            withdrawal["requested_amount"],
            withdrawal["status"],
            withdrawal["requested_at"],
            withdrawal.get("processed_at"),
            withdrawal.get("destination_address"),
        ),
    )

    ledger_factory = CashbackLedgerEntryFactory()
    accrual = ledger_factory.build(
        wallet_id=wallet["id"],
        trip_id=trip["id"],
        amount="20.00",
        entry_type="cashback",
    )
    lock = ledger_factory.build(
        wallet_id=wallet["id"],
        trip_id=trip["id"],
        amount="5.00",
        entry_type="withdrawal",
    )
    release = ledger_factory.build(
        wallet_id=wallet["id"],
        trip_id=trip["id"],
        amount="5.00",
        entry_type="withdrawal",
    )
    payout = ledger_factory.build(
        wallet_id=wallet["id"],
        trip_id=trip["id"],
        amount="5.00",
        entry_type="withdrawal",
    )

    conn.execute(
        "INSERT INTO cashback_ledger (id, wallet_id, trip_id, withdrawal_id, amount, entry_type, rule_type, direction,"
        " occurred_at, description, reference, lock_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            accrual["id"],
            wallet["id"],
            trip["id"],
            None,
            "20.00",
            "cashback",
            "cashback_accrual",
            "credit",
            accrual["occurred_at"],
            accrual["description"],
            accrual["reference"],
            None,
        ),
    )
    conn.execute(
        "INSERT INTO cashback_ledger (id, wallet_id, trip_id, withdrawal_id, amount, entry_type, rule_type, direction,"
        " occurred_at, description, reference, lock_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            lock["id"],
            wallet["id"],
            trip["id"],
            withdrawal["id"],
            "5.00",
            "withdrawal",
            "withdrawal_lock",
            "debit",
            lock["occurred_at"],
            lock["description"],
            lock["reference"],
            lock["reference"],
        ),
    )
    conn.execute(
        "INSERT INTO cashback_ledger (id, wallet_id, trip_id, withdrawal_id, amount, entry_type, rule_type, direction,"
        " occurred_at, description, reference, lock_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            release["id"],
            wallet["id"],
            trip["id"],
            withdrawal["id"],
            "5.00",
            "withdrawal",
            "withdrawal_release",
            None,
            release["occurred_at"],
            release["description"],
            release["reference"],
            lock["reference"],
        ),
    )
    conn.execute(
        "INSERT INTO cashback_ledger (id, wallet_id, trip_id, withdrawal_id, amount, entry_type, rule_type, direction,"
        " occurred_at, description, reference, lock_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            payout["id"],
            wallet["id"],
            trip["id"],
            withdrawal["id"],
            "5.00",
            "withdrawal",
            "payout",
            "debit",
            payout["occurred_at"],
            payout["description"],
            payout["reference"],
            lock["reference"],
        ),
    )

    audit_id = accrual["reference"]
    conn.execute(
        "INSERT INTO audit_events (id, actor_id, entity_type, entity_id, action, payload, created_at, ip_address)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            audit_id,
            wallet["owner_id"],
            "wallet",
            wallet["id"],
            "update",
            "{}",
            accrual["occurred_at"],
            "127.0.0.1",
        ),
    )

    conn.commit()
    conn.close()

    return {
        "db_path": str(db_path),
        "user_id": wallet["owner_id"],
        "wallet_id": wallet["id"],
        "trip_id": trip["id"],
    }


def test_api_endpoints(tmp_path: Path) -> None:
    context = _setup_database(tmp_path)
    app = create_app(context["db_path"])
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"ok": True}

    balance = client.get(f"/wallets/{context['user_id']}/balance")
    assert balance.status_code == 200
    balance_payload = balance.json()
    assert balance_payload["user_id"] == context["user_id"]
    assert balance_payload["available"] == "15.00"
    assert balance_payload["locked"] == "0.00"

    trips = client.get(f"/trips?user_id={context['user_id']}")
    assert trips.status_code == 200
    trips_payload = trips.json()
    assert len(trips_payload) == 1
    assert trips_payload[0]["traveler_id"] == context["user_id"]

    ledger = client.get(f"/ledger?wallet_id={context['wallet_id']}")
    assert ledger.status_code == 200
    ledger_payload = ledger.json()
    assert len(ledger_payload) == 4
    assert {entry["rule_type"] for entry in ledger_payload} == {
        "cashback_accrual",
        "withdrawal_lock",
        "withdrawal_release",
        "payout",
    }

    summary = client.get("/reports/daily_summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["users"] == 1
    assert summary_payload["wallets"] == 1
    assert summary_payload["trips"] == 1
    assert summary_payload["ledger_entries"] == 4
    assert summary_payload["total_available"] == "15.00"
