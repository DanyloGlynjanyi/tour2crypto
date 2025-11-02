"""Utility script to scaffold a local .env file."""

from __future__ import annotations

from pathlib import Path

TEMPLATE = Path("example.env")
TARGET = Path(".env")


def main() -> None:
    if TARGET.exists():
        print(f"[SKIP] {TARGET} already exists")
        return
    if not TEMPLATE.exists():
        raise SystemExit("example.env template is missing")
    content = TEMPLATE.read_text(encoding="utf-8")
    TARGET.write_text(content, encoding="utf-8")
    print(f"[OK] Created {TARGET}")


if __name__ == "__main__":
    main()
