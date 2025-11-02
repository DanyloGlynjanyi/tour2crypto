"""Generate offline exports for Supabase synchronisation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from t2c_sync import export_sqlite_to_csv, export_sqlite_to_json, generate_supabase_upsert_sql


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create SQLite exports and Supabase SQL upserts")
    parser.add_argument("--db", default="db/tour2crypto.db", help="Path to the SQLite database")
    parser.add_argument("--out", default="exports", help="Output directory for exports")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_files = export_sqlite_to_csv(args.db, out_dir)
    json_files = export_sqlite_to_json(args.db, out_dir)
    sql_file = generate_supabase_upsert_sql(out_dir)

    print("CSV files:")
    for path in csv_files:
        print(f" - {path}")
    print("JSON files:")
    for path in json_files:
        print(f" - {path}")
    print(f"SQL file: {sql_file}")


if __name__ == "__main__":
    main()
