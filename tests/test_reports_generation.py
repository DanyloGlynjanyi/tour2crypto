from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from t2c_reports import (
    format_report_md,
    generate_daily_report,
    generate_weekly_pnl,
    send_report_via_telegram,
)


@pytest.fixture()
def temp_db(tmp_path: Path) -> str:
    db_path = tmp_path / "reports.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE wallets (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE trips (
                id TEXT PRIMARY KEY,
                traveler_id TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE cashback_ledger (
                id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                trip_id TEXT,
                amount TEXT NOT NULL,
                rule_type TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE withdrawals (
                id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                requested_amount TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO wallets (id, owner_id, currency, created_at) VALUES (?, ?, 'USDT', ?)",
            [
                ("W1", "U1", "2024-01-01T00:00:00Z"),
                ("W2", "U2", "2024-01-02T00:00:00Z"),
            ],
        )
        conn.executemany(
            "INSERT INTO trips (id, traveler_id, status) VALUES (?, ?, ?)",
            [
                ("T1", "U1", "completed"),
                ("T2", "U2", "planned"),
            ],
        )
        conn.executemany(
            "INSERT INTO cashback_ledger (id, wallet_id, trip_id, amount, rule_type) VALUES (?, ?, ?, ?, ?)",
            [
                ("L1", "W1", "T1", "25.00", "cashback_accrual"),
                ("L2", "W1", "T1", "10.00", "withdrawal_lock"),
                ("L3", "W1", "T1", "10.00", "payout"),
                ("L4", "W2", "T2", "15.00", "cashback_accrual"),
            ],
        )
        conn.execute(
            "INSERT INTO withdrawals (id, wallet_id, requested_amount, status) VALUES (?, ?, ?, ?)",
            ("WD1", "W1", "10.00", "processed"),
        )
        conn.commit()
    finally:
        conn.close()
    return str(db_path)


def test_generate_daily_report_returns_expected_keys(temp_db: str) -> None:
    report = generate_daily_report(temp_db)
    assert set(report.keys()) == {
        "total_users",
        "total_wallets",
        "trips_completed",
        "cashback_total_usdt",
        "withdrawals_requested",
        "withdrawals_paid",
        "available_sum_usdt",
    }
    assert report["cashback_total_usdt"].endswith(".00")
    assert isinstance(report["total_users"], int)


def test_generate_weekly_pnl_outputs_strings(temp_db: str) -> None:
    report = generate_weekly_pnl(temp_db)
    assert report == {
        "total_inflow_usdt": "40.00",
        "total_outflow_usdt": "10.00",
        "net_pnl_usdt": "30.00",
    }


def test_format_report_md_contains_all_metrics(temp_db: str) -> None:
    report = generate_daily_report(temp_db)
    rendered = format_report_md(report, "Daily")
    for key in report:
        assert key in rendered
    assert rendered.startswith("### Daily")


def test_send_report_simulation_prints(capsys: pytest.CaptureFixture[str]) -> None:
    result = send_report_via_telegram("Sample Report", mode="simulation")
    captured = capsys.readouterr().out
    assert "[SIMULATION]" in captured
    assert result.startswith("[SIMULATION]")
