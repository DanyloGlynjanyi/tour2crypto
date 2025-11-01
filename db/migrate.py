"""SQLite migration runner for Tour2Crypto."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "tour2crypto.db"
MIGRATIONS_DIR = BASE_DIR / "migrations"


def _load_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def apply_migrations(
    db_path: Path = DEFAULT_DB_PATH,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> List[Path]:
    migrations = sorted(p for p in migrations_dir.glob("*.sql") if p.is_file())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        for migration in migrations:
            sql = _load_sql(migration)
            connection.executescript(sql)
        connection.commit()
    return migrations


def main() -> None:
    migrations = apply_migrations()
    for migration in migrations:
        print(f"Applied migration: {migration.name}")
    print(f"SQLite database ready at {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    main()
