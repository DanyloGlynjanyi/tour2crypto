"""Entry point for generating sample payloads."""

from __future__ import annotations

import json
from typing import Any, Dict

from .factories import (
    ApplicationFactory,
    AuditEventFactory,
    CashbackLedgerEntryFactory,
    TripFactory,
    WalletFactory,
    WithdrawalRequestFactory,
)


def build_sample_payloads() -> Dict[str, Any]:
    trip_factory = TripFactory()
    application_factory = ApplicationFactory()
    wallet_factory = WalletFactory()
    ledger_factory = CashbackLedgerEntryFactory()
    withdrawal_factory = WithdrawalRequestFactory()
    audit_factory = AuditEventFactory()

    wallet = wallet_factory.build()
    trip = trip_factory.build(traveler_id=wallet["owner_id"])
    application = application_factory.build(traveler_id=wallet["owner_id"], id=trip["application_id"])
    ledger_entries = [
        ledger_factory.build(wallet_id=wallet["id"], trip_id=trip["id"], amount="10.00", entry_type="cashback"),
        ledger_factory.build(wallet_id=wallet["id"], trip_id=trip["id"], amount="-2.50", entry_type="withdrawal"),
    ]
    withdrawal = withdrawal_factory.build(wallet_id=wallet["id"], requested_amount="7.50")
    audit_event = audit_factory.build(entity_id=wallet["id"], actor_id=wallet["owner_id"])

    return {
        "trip": trip,
        "application": application,
        "wallet": wallet,
        "ledger_entries": ledger_entries,
        "withdrawal_request": withdrawal,
        "audit_event": audit_event,
    }


def main() -> None:
    payloads = build_sample_payloads()
    print(json.dumps(payloads, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
