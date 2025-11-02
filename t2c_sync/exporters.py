"""SQLite export helpers for offline synchronisation."""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict, Iterable, List

TABLES: tuple[str, ...] = (
    "applications",
    "wallets",
    "trips",
    "cashback_ledger",
    "withdrawals",
    "audit_events",
)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_output(out_dir: str | Path) -> Path:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in info]


def _rows_as_dicts(rows: Iterable[sqlite3.Row], columns: List[str]) -> List[Dict[str, str | None]]:
    results: List[Dict[str, str | None]] = []
    for row in rows:
        entry = {column: row[column] for column in columns}
        results.append(entry)
    return results


def export_sqlite_to_csv(db_path: str, out_dir: str | Path) -> List[Path]:
    """Export selected tables to CSV with headers."""

    output_dir = _ensure_output(out_dir)
    created: List[Path] = []
    with closing(_connect(db_path)) as conn:
        for table in TABLES:
            columns = _table_columns(conn, table)
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            file_path = output_dir / f"{table}.csv"
            with file_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([row[column] if row[column] is not None else "" for column in columns])
            created.append(file_path)
    return created


def export_sqlite_to_json(db_path: str, out_dir: str | Path) -> List[Path]:
    """Export selected tables to JSON array files."""

    output_dir = _ensure_output(out_dir)
    created: List[Path] = []
    with closing(_connect(db_path)) as conn:
        for table in TABLES:
            columns = _table_columns(conn, table)
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data = _rows_as_dicts(rows, columns)
            file_path = output_dir / f"{table}.json"
            file_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            created.append(file_path)
    return created


__all__ = ["export_sqlite_to_csv", "export_sqlite_to_json", "TABLES"]
