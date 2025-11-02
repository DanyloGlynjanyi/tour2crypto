"""CLI helper for generating and sending the weekly PnL report."""

from __future__ import annotations

from pathlib import Path

from t2c_reports import (
    format_report_md,
    generate_weekly_pnl,
    send_report_via_telegram,
)

DEFAULT_DB = Path("db/tour2crypto.db")


def main(db_path: str | None = None) -> str:
    path = Path(db_path) if db_path else DEFAULT_DB
    report = generate_weekly_pnl(str(path))
    text = format_report_md(report, "Weekly PnL Report")
    send_report_via_telegram(text)
    message = "[OK] Weekly PnL report sent (simulation)"
    print(message)
    return message


if __name__ == "__main__":
    main()
