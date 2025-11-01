"""Generate an end-to-end markdown report for Tour2Crypto."""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from t2c_contracts import (
    APPLICATION_SCHEMA,
    AUDIT_EVENT_SCHEMA,
    CASHBACK_LEDGER_ENTRY_SCHEMA,
    TRIP_SCHEMA,
    WALLET_SCHEMA,
    WITHDRAWAL_REQUEST_SCHEMA,
    validate_application,
    validate_audit_event,
    validate_cashback_ledger_entry,
    validate_trip,
    validate_wallet,
    validate_withdrawal_request,
)
from t2c_contracts.factories import (
    ApplicationFactory,
    AuditEventFactory,
    CashbackLedgerEntryFactory,
    TripFactory,
    WalletFactory,
    WithdrawalRequestFactory,
)
from t2c_logic import (
    bus,
    get_wallet_balance,
    register_wallet,
    reset_state as reset_logic_state,
    rules_ledger,
    set_trip_reward,
)
from t2c_rules import assert_invariants, compute_available
from t2c_events.validators import get_known_event_types

SPEC_VERSION = "v1.0.0"
REPORTS_DIR = ROOT / "reports"
REPORT_PATH = REPORTS_DIR / "e2e_report.md"


def _run_pytest() -> Tuple[bool, int, int, int, int, List[str]]:
    """Run pytest -q and derive outcome counts from the progress line."""

    cmd = [sys.executable, "-m", "pytest", "-q"]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    combined = (result.stdout or "") + (result.stderr or "")
    lines = combined.splitlines()

    marks = []
    for line in lines:
        if "[" in line and "]" in line and "%" in line:
            marks.append(line.split("[", 1)[0])
    progress = "".join(marks)

    counter = Counter(ch for ch in progress if ch.strip())
    passed = counter.get(".", 0) + counter.get("x", 0) + counter.get("X", 0)
    failed = counter.get("F", 0) + counter.get("E", 0)
    skipped = counter.get("s", 0) + counter.get("S", 0)
    total = sum(counter.values())
    success = result.returncode == 0
    return success, passed, failed, skipped, total, lines


def _ulid_seed() -> Iterable[str]:
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    while True:
        for char in alphabet:
            yield char * 26


_ULID_ITER = _ulid_seed()


def _next_ulid() -> str:
    return next(_ULID_ITER)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_trip_completed_event(trip_id: str, traveler_id: str) -> Dict[str, Any]:
    return {
        "event_id": _next_ulid(),
        "event_type": "trip_completed",
        "event_time": _iso_now(),
        "payload": {
            "trip_id": trip_id,
            "traveler_id": traveler_id,
            "status": "completed",
            "completed_at": _iso_now(),
        },
    }


def _build_withdrawal_requested_event(wallet_id: str, request_id: str, amount: str) -> Dict[str, Any]:
    return {
        "event_id": _next_ulid(),
        "event_type": "withdrawal_requested",
        "event_time": _iso_now(),
        "payload": {
            "withdrawal_request_id": request_id,
            "wallet_id": wallet_id,
            "amount": amount,
        },
    }


def _build_withdrawal_paid_event(wallet_id: str, request_id: str, amount: str) -> Dict[str, Any]:
    return {
        "event_id": _next_ulid(),
        "event_type": "withdrawal_paid",
        "event_time": _iso_now(),
        "payload": {
            "withdrawal_request_id": request_id,
            "wallet_id": wallet_id,
            "amount": amount,
            "transaction_id": "TX-SMOKE-001",
        },
    }


def _run_smoke_flow() -> Dict[str, Any]:
    reset_logic_state()

    wallet_payload = WalletFactory().build()
    wallet = register_wallet(wallet_payload)

    trip_payload = TripFactory().build(status="completed", traveler_id=wallet.owner_id)
    set_trip_reward(trip_payload["id"], Decimal("45.00"))

    bus.publish(_build_trip_completed_event(trip_payload["id"], trip_payload["traveler_id"]))
    balance_after_cashback = get_wallet_balance(wallet.id)

    request_payload = WithdrawalRequestFactory().build(wallet_id=wallet.id, requested_amount="15.00")
    bus.publish(
        _build_withdrawal_requested_event(
            wallet.id,
            request_payload["id"],
            request_payload["requested_amount"],
        )
    )
    balance_after_lock = get_wallet_balance(wallet.id)

    bus.publish(
        _build_withdrawal_paid_event(
            wallet.id,
            request_payload["id"],
            request_payload["requested_amount"],
        )
    )
    final_balance = get_wallet_balance(wallet.id)

    rules_snapshot = [dict(entry) for entry in rules_ledger]
    available = compute_available(rules_snapshot)

    invariants_status = "OK"
    invariants_error = None
    try:
        assert_invariants(rules_snapshot)
    except ValueError as exc:  # pragma: no cover - captured in report
        invariants_status = "FAIL"
        invariants_error = str(exc)

    return {
        "wallet_id": wallet.id,
        "trip_id": trip_payload["id"],
        "request_id": request_payload["id"],
        "balances": {
            "after_cashback": balance_after_cashback,
            "after_lock": balance_after_lock,
            "final": final_balance,
        },
        "ledger_entries": len(rules_snapshot),
        "available": f"{available:.2f}",
        "invariants": {
            "status": invariants_status,
            "error": invariants_error,
        },
    }


def _validate_contract_instances() -> List[str]:
    validators = [
        (TripFactory().build(), validate_trip, "Trip"),
        (ApplicationFactory().build(), validate_application, "Application"),
        (WalletFactory().build(), validate_wallet, "Wallet"),
        (CashbackLedgerEntryFactory().build(), validate_cashback_ledger_entry, "CashbackLedgerEntry"),
        (WithdrawalRequestFactory().build(), validate_withdrawal_request, "WithdrawalRequest"),
        (AuditEventFactory().build(), validate_audit_event, "AuditEvent"),
    ]

    validated: List[str] = []
    for payload, validator, label in validators:
        validator(payload)
        validated.append(label)
    return validated


def _count_contract_schemas() -> int:
    schemas = [
        TRIP_SCHEMA,
        APPLICATION_SCHEMA,
        WALLET_SCHEMA,
        CASHBACK_LEDGER_ENTRY_SCHEMA,
        WITHDRAWAL_REQUEST_SCHEMA,
        AUDIT_EVENT_SCHEMA,
    ]
    return len(schemas)


def _count_event_schemas() -> int:
    return len(get_known_event_types())


def _build_report(
    pytest_result: Tuple[bool, int, int, int, int, List[str]],
    smoke: Dict[str, Any],
    validated_entities: List[str],
) -> str:
    success, passed, failed, skipped, total, lines = pytest_result
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    test_status = "PASS" if success else "FAIL"
    pytest_output = "\n".join(lines)

    report_lines = [
        f"# E2E Report — {timestamp} (UTC)",
        "",
        "## Specification",
        f"- Version: {SPEC_VERSION}",
        "- Document: docs/SPEC_V1.md",
        "",
        "## Test Results",
        "- Command: `pytest -q`",
        f"- Status: {test_status}",
        f"- Summary: {passed} passed / {failed} failed / {skipped} skipped / {total} total",
        "- Output:",
        "```",
        pytest_output,
        "```",
        "",
        "## Smoke Scenario",
        f"- Wallet: {smoke['wallet_id']}",
        f"- Trip: {smoke['trip_id']}",
        f"- Withdrawal Request: {smoke['request_id']}",
        f"- Balance after cashback: {smoke['balances']['after_cashback']}",
        f"- Balance after lock: {smoke['balances']['after_lock']}",
        f"- Final balance: {smoke['balances']['final']}",
        f"- Ledger entries recorded: {smoke['ledger_entries']}",
        f"- Available balance: {smoke['available']}",
        "",
        "## Invariants",
        f"- Status: {smoke['invariants']['status']}",
    ]

    if smoke["invariants"]["error"]:
        report_lines.append(f"- Error: {smoke['invariants']['error']}")

    report_lines.extend(
        [
            "",
            "## Validation",
            "- Entities validated: " + ", ".join(validated_entities),
            "",
            "## Counters",
            f"- Contract schemas: {_count_contract_schemas()}",
            f"- Event schemas: {_count_event_schemas()}",
            f"- Tests executed: {total}",
        ]
    )

    return "\n".join(report_lines)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    pytest_result = _run_pytest()
    smoke = _run_smoke_flow()
    validated_entities = _validate_contract_instances()
    report_content = _build_report(pytest_result, smoke, validated_entities)

    REPORT_PATH.write_text(report_content + "\n", encoding="utf-8")
    print(f"Report generated at {REPORT_PATH}")


if __name__ == "__main__":
    main()
