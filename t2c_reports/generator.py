"""Utilities for generating financial reports from SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict

_AMOUNT_ZERO = Decimal("0.00")


def _ensure_db_exists(db_path: str) -> Path:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return path


def _get_conn(db_path: str) -> sqlite3.Connection:
    path = _ensure_db_exists(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_decimal(value: object) -> Decimal:
    if value in (None, "", b""):
        return _AMOUNT_ZERO
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value}") from exc


def _format_amount(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _sum_amounts(rows: sqlite3.Cursor) -> Decimal:
    total = _AMOUNT_ZERO
    for (raw_amount,) in rows:
        total += _normalize_decimal(raw_amount).copy_abs()
    return total


def _compute_wallet_availability(conn: sqlite3.Connection) -> Decimal:
    try:
        rows = conn.execute("SELECT available_amount FROM wallet_balances")
    except sqlite3.OperationalError:
        rows = []
    totals = [_normalize_decimal(row["available_amount"]) for row in rows]
    if totals:
        return sum(totals, _AMOUNT_ZERO)

    per_wallet: Dict[str, Dict[str, Decimal]] = {}
    ledger_rows = conn.execute(
        "SELECT wallet_id, amount, rule_type FROM cashback_ledger"
    ).fetchall()
    for wallet_id, amount, rule_type in ledger_rows:
        wallet_totals = per_wallet.setdefault(
            wallet_id,
            {"credit": _AMOUNT_ZERO, "debit": _AMOUNT_ZERO, "locked": _AMOUNT_ZERO},
        )
        dec_amount = _normalize_decimal(amount).copy_abs()
        if rule_type == "cashback_accrual":
            wallet_totals["credit"] += dec_amount
        elif rule_type in {"cashback_reversal", "payout"}:
            wallet_totals["debit"] += dec_amount
        elif rule_type == "withdrawal_lock":
            wallet_totals["locked"] += dec_amount
        elif rule_type == "withdrawal_release":
            wallet_totals["locked"] -= dec_amount
    available = _AMOUNT_ZERO
    for totals in per_wallet.values():
        available += totals["credit"] - totals["debit"] - totals["locked"]
    return available


def generate_daily_report(db_path: str) -> Dict[str, object]:
    """Return aggregated statistics for the daily report."""

    with closing(_get_conn(db_path)) as conn:
        total_users = conn.execute(
            "SELECT COUNT(DISTINCT owner_id) FROM wallets"
        ).fetchone()[0]
        total_wallets = conn.execute("SELECT COUNT(*) FROM wallets").fetchone()[0]
        trips_completed = conn.execute(
            "SELECT COUNT(*) FROM trips WHERE status = 'completed'"
        ).fetchone()[0]
        cashback_total = _sum_amounts(
            conn.execute(
                "SELECT amount FROM cashback_ledger WHERE rule_type = 'cashback_accrual'"
            )
        )
        withdrawals_requested = conn.execute(
            "SELECT COUNT(*) FROM cashback_ledger WHERE rule_type = 'withdrawal_lock'"
        ).fetchone()[0]
        withdrawals_paid = conn.execute(
            "SELECT COUNT(*) FROM cashback_ledger WHERE rule_type = 'payout'"
        ).fetchone()[0]
        available_sum = _compute_wallet_availability(conn)

    return {
        "total_users": int(total_users or 0),
        "total_wallets": int(total_wallets or 0),
        "trips_completed": int(trips_completed or 0),
        "cashback_total_usdt": _format_amount(cashback_total),
        "withdrawals_requested": int(withdrawals_requested or 0),
        "withdrawals_paid": int(withdrawals_paid or 0),
        "available_sum_usdt": _format_amount(available_sum),
    }


def generate_weekly_pnl(db_path: str) -> Dict[str, str]:
    """Return inflow/outflow and net PnL totals for the week."""

    with closing(_get_conn(db_path)) as conn:
        inflow = _sum_amounts(
            conn.execute(
                "SELECT amount FROM cashback_ledger WHERE rule_type = 'cashback_accrual'"
            )
        )
        outflow = _sum_amounts(
            conn.execute(
                "SELECT amount FROM cashback_ledger WHERE rule_type = 'payout'"
            )
        )
    net = inflow - outflow
    return {
        "total_inflow_usdt": _format_amount(inflow),
        "total_outflow_usdt": _format_amount(outflow),
        "net_pnl_usdt": _format_amount(net),
    }


def format_report_md(report: Dict[str, object], title: str) -> str:
    """Render the report as a Markdown table."""

    lines = [f"### {title}", "", "| Metric | Value |", "| --- | --- |"]
    for key, value in report.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


__all__ = [
    "format_report_md",
    "generate_daily_report",
    "generate_weekly_pnl",
]
