"""Generate SQL scripts for Supabase upserts based on local exports."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

from .exporters import TABLES


def _format_value(value: str) -> str:
    if value == "":
        return "NULL"
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _build_values(rows: Iterable[dict], columns: List[str]) -> List[str]:
    values: List[str] = []
    for row in rows:
        entry = ", ".join(_format_value(str(row.get(column, ""))) for column in columns)
        values.append(f"({entry})")
    return values


def generate_supabase_upsert_sql(out_dir: str | Path) -> Path:
    """Create a SQL file with INSERT .. ON CONFLICT statements for each table."""

    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sql_path = output_dir / "supabase_upsert.sql"

    statements: List[str] = []
    for table in TABLES:
        csv_path = output_dir / f"{table}.csv"
        if not csv_path.exists():
            statements.append(f"-- {table}: export missing, skipped")
            continue
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                statements.append(f"-- {table}: no columns detected")
                continue
            columns = reader.fieldnames
            rows = list(reader)
            if not rows:
                statements.append(f"-- {table}: no rows to upsert")
                continue
            values = _build_values(rows, columns)
            column_list = ", ".join(columns)
            update_columns = [column for column in columns if column != "id"]
            if update_columns:
                update_clause = ",\n      ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
                conflict_clause = f"ON CONFLICT (id) DO UPDATE SET\n      {update_clause}"
            else:
                conflict_clause = "ON CONFLICT (id) DO NOTHING"
            statement = (
                f"-- Upsert for {table}\n"
                f"INSERT INTO {table} ({column_list}) VALUES\n  "
                + ",\n  ".join(values)
                + f"\n{conflict_clause};"
            )
            statements.append(statement)

    sql_path.write_text("\n\n".join(statements) + "\n", encoding="utf-8")
    return sql_path


__all__ = ["generate_supabase_upsert_sql"]
