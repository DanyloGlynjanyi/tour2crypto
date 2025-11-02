"""SQLite helpers for the Tour2Crypto API."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def get_conn(db_path: str) -> sqlite3.Connection:
    """Return a connection with row factory enabled."""

    path = Path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def fetch_wallet(db_path: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the first wallet owned by the given user."""

    with closing(get_conn(db_path)) as conn:
        row = conn.execute(
            "SELECT * FROM wallets WHERE owner_id = ? ORDER BY created_at LIMIT 1",
            (user_id,),
        ).fetchone()
        return _row_to_dict(row)


def fetch_trips(db_path: str, user_id: str | None = None) -> List[Dict[str, Any]]:
    """Fetch trips, optionally filtered by traveler."""

    with closing(get_conn(db_path)) as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM trips WHERE traveler_id = ? ORDER BY created_at",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trips ORDER BY created_at",
            ).fetchall()
        return [_row_to_dict(row) for row in rows if row is not None]


def fetch_ledger(db_path: str, wallet_id: str) -> List[Dict[str, Any]]:
    """Return ledger entries for the given wallet."""

    with closing(get_conn(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM cashback_ledger WHERE wallet_id = ? ORDER BY occurred_at",
            (wallet_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows if row is not None]


def _normalize_decimal(value: str | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value))


def _aggregate_locked(entries: Iterable[Dict[str, Any]]) -> Decimal:
    locked = Decimal("0.00")
    for entry in entries:
        rule_type = entry.get("rule_type")
        amount = _normalize_decimal(entry.get("amount"))
        amount = abs(amount)
        if rule_type == "withdrawal_lock":
            locked += amount
        elif rule_type == "withdrawal_release":
            locked -= amount
    return locked


def compute_available_for_wallet(db_path: str, wallet_id: str) -> Dict[str, str]:
    """Compute available and locked balances for a wallet."""

    with closing(get_conn(db_path)) as conn:
        row = conn.execute(
            "SELECT available_amount, locked_total FROM wallet_balances WHERE wallet_id = ?",
            (wallet_id,),
        ).fetchone()
        if row is not None:
            available = _normalize_decimal(row["available_amount"])
            locked = _normalize_decimal(row["locked_total"])
        else:
            ledger_rows = conn.execute(
                "SELECT amount, rule_type FROM cashback_ledger WHERE wallet_id = ?",
                (wallet_id,),
            ).fetchall()
            credit = Decimal("0.00")
            debit = Decimal("0.00")
            entry_dicts: List[Dict[str, Any]] = []
            for ledger_row in ledger_rows:
                entry = {
                    "amount": ledger_row["amount"],
                    "rule_type": ledger_row["rule_type"],
                }
                entry_dicts.append(entry)
                amount = _normalize_decimal(entry["amount"])
                amount = abs(amount)
                rule_type = entry["rule_type"]
                if rule_type == "cashback_accrual":
                    credit += amount
                elif rule_type in {"cashback_reversal", "payout"}:
                    debit += amount
            locked = _aggregate_locked(entry_dicts)
            available = credit - debit - locked
        return {
            "available": f"{available.quantize(Decimal('0.01')):.2f}",
            "locked": f"{locked.quantize(Decimal('0.01')):.2f}",
        }


def fetch_daily_summary(db_path: str) -> Dict[str, Any]:
    """Return counts and aggregate balances for the dashboard."""

    with closing(get_conn(db_path)) as conn:
        summary: Dict[str, Any] = {}
        summary["users"] = conn.execute(
            "SELECT COUNT(DISTINCT owner_id) FROM wallets",
        ).fetchone()[0]
        summary["wallets"] = conn.execute("SELECT COUNT(*) FROM wallets").fetchone()[0]
        summary["trips"] = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
        summary["ledger_entries"] = conn.execute("SELECT COUNT(*) FROM cashback_ledger").fetchone()[0]

        rows = conn.execute("SELECT available_amount FROM wallet_balances").fetchall()
        total_available = sum((_normalize_decimal(row["available_amount"]) for row in rows), Decimal("0.00"))
        summary["total_available"] = f"{total_available.quantize(Decimal('0.01')):.2f}"
        return summary


def fetch_wallet_balances(db_path: str) -> List[Dict[str, Any]]:
    with closing(get_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM wallet_balances").fetchall()
        return [_row_to_dict(row) for row in rows if row is not None]


__all__ = [
    "compute_available_for_wallet",
    "fetch_daily_summary",
    "fetch_ledger",
    "fetch_trips",
    "fetch_wallet",
    "fetch_wallet_balances",
    "get_conn",
]
