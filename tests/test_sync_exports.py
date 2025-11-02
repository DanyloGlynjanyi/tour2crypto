from __future__ import annotations

import sqlite3
from pathlib import Path

from db.migrate import MIGRATIONS_DIR, apply_migrations
from t2c_contracts.factories import (
    ApplicationFactory,
    CashbackLedgerEntryFactory,
    TripFactory,
    WalletFactory,
    WithdrawalRequestFactory,
)
from t2c_sync.exporters import TABLES, export_sqlite_to_csv, export_sqlite_to_json
from t2c_sync.supabase_sql import generate_supabase_upsert_sql


def _bootstrap_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sync.db"
    apply_migrations(db_path=db_path, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(db_path)

    wallet = WalletFactory().build()
    application = ApplicationFactory().build(traveler_id=wallet["owner_id"], status="approved")
    trip = TripFactory().build(
        traveler_id=wallet["owner_id"],
        application_id=application["id"],
        status="completed",
    )
    withdrawal = WithdrawalRequestFactory().build(wallet_id=wallet["id"], requested_amount="7.50", status="processed")
    ledger_factory = CashbackLedgerEntryFactory()
    ledger_entry = ledger_factory.build(
        wallet_id=wallet["id"],
        trip_id=trip["id"],
        amount="12.00",
        entry_type="cashback",
    )

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
    conn.execute(
        "INSERT INTO cashback_ledger (id, wallet_id, trip_id, withdrawal_id, amount, entry_type, rule_type, direction,"
        " occurred_at, description, reference, lock_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ledger_entry["id"],
            wallet["id"],
            trip["id"],
            None,
            "12.00",
            "cashback",
            "cashback_accrual",
            "credit",
            ledger_entry["occurred_at"],
            ledger_entry["description"],
            ledger_entry["reference"],
            None,
        ),
    )
    conn.execute(
        "INSERT INTO audit_events (id, actor_id, entity_type, entity_id, action, payload, created_at, ip_address)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ledger_entry["reference"],
            wallet["owner_id"],
            "wallet",
            wallet["id"],
            "update",
            "{}",
            ledger_entry["occurred_at"],
            "127.0.0.1",
        ),
    )

    conn.commit()
    conn.close()
    return db_path


def test_sync_exports(tmp_path: Path) -> None:
    db_path = _bootstrap_db(tmp_path)
    out_dir = tmp_path / "exports"

    csv_files = export_sqlite_to_csv(str(db_path), out_dir)
    assert len(csv_files) == len(TABLES)
    for file_path in csv_files:
        content = file_path.read_text(encoding="utf-8").strip()
        assert content != ""
        assert content.splitlines()[0].count(",") + 1 >= 1

    json_files = export_sqlite_to_json(str(db_path), out_dir)
    assert len(json_files) == len(TABLES)
    for file_path in json_files:
        content = file_path.read_text(encoding="utf-8").strip()
        assert content.startswith("[")

    sql_path = generate_supabase_upsert_sql(out_dir)
    sql_content = sql_path.read_text(encoding="utf-8")
    for table in TABLES:
        assert f"INSERT INTO {table}" in sql_content
    assert "ON CONFLICT (id) DO UPDATE" in sql_content
