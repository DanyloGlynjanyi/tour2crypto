"""FastAPI application exposing Tour2Crypto insights."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from t2c_core import config as core_config
from t2c_core import metrics as core_metrics
from t2c_core.health import healthcheck as core_healthcheck
from t2c_core.logging import get_logger

from .storage_sqlite import (
    compute_available_for_wallet,
    fetch_daily_summary,
    fetch_ledger,
    fetch_trips,
    fetch_wallet,
)

STATIC_INDEX = Path(__file__).with_name("static") / "index.html"
LOGGER = get_logger(__name__)


def create_app(db_path: str | None = None) -> FastAPI:
    """Create the FastAPI application bound to a SQLite database."""

    resolved_db_path = db_path or core_config.get("DB_PATH", "db/tour2crypto.db") or "db/tour2crypto.db"
    app = FastAPI(title="Tour2Crypto Dashboard API")
    app.state.db_path = resolved_db_path

    def _count_request(endpoint: str) -> None:
        core_metrics.inc("api_requests")
        LOGGER.info("API request: %s", endpoint)

    @app.get("/", response_class=HTMLResponse)
    def serve_index() -> str:
        _count_request("root")
        if not STATIC_INDEX.exists():
            raise HTTPException(status_code=500, detail="Dashboard file missing")
        return STATIC_INDEX.read_text(encoding="utf-8")

    @app.get("/health")
    def healthcheck() -> Dict[str, Any]:
        _count_request("health")
        return core_healthcheck()

    @app.get("/metrics")
    def metrics_endpoint() -> Dict[str, int]:
        _count_request("metrics")
        return core_metrics.snapshot()

    @app.get("/wallets/{user_id}/balance")
    def wallet_balance(user_id: str) -> Dict[str, str]:
        _count_request("wallet_balance")
        wallet = fetch_wallet(app.state.db_path, user_id)
        if wallet is None:
            balances = {"available": "0.00", "locked": "0.00"}
        else:
            balances = compute_available_for_wallet(app.state.db_path, wallet["id"])
        return {"user_id": user_id, **balances}

    @app.get("/trips")
    def list_trips(user_id: str | None = Query(default=None)) -> List[Dict[str, Any]]:
        _count_request("trips")
        return fetch_trips(app.state.db_path, user_id)

    @app.get("/ledger")
    def list_ledger(wallet_id: str = Query(..., min_length=1)) -> List[Dict[str, Any]]:
        _count_request("ledger")
        return fetch_ledger(app.state.db_path, wallet_id)

    @app.get("/reports/daily_summary")
    def daily_summary() -> Dict[str, Any]:
        _count_request("daily_summary")
        return fetch_daily_summary(app.state.db_path)

    return app


def main(argv: List[str] | None = None) -> None:
    """CLI entry point to run the API with uvicorn."""

    parser = argparse.ArgumentParser(description="Run the Tour2Crypto API server")
    parser.add_argument("--db", default=None, help="Path to the SQLite database")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", default=8000, type=int, help="Bind port")
    args = parser.parse_args(argv)

    app = create_app(args.db)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


cli = main
