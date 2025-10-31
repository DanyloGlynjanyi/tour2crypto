from __future__ import annotations

from decimal import Decimal

from t2c_contracts.factories import CashbackLedgerEntryFactory, WalletFactory
from t2c_contracts.ledger import compute_wallet_balance
from t2c_contracts.validation import CashbackLedgerEntryModel, WalletModel


def test_wallet_balance_is_ledger_first() -> None:
    wallet_payload = WalletFactory().build()
    wallet = WalletModel(**wallet_payload)

    ledger_factory = CashbackLedgerEntryFactory()
    entries = [
        CashbackLedgerEntryModel(**ledger_factory.build(wallet_id=wallet.id, amount="15.00", entry_type="cashback")),
        CashbackLedgerEntryModel(**ledger_factory.build(wallet_id=wallet.id, amount="-3.40", entry_type="withdrawal")),
        CashbackLedgerEntryModel(**ledger_factory.build(wallet_id=wallet.id, amount="1.25", entry_type="adjustment")),
    ]

    balance = compute_wallet_balance(entries)
    assert balance == "12.85"
    total = sum(Decimal(entry.amount) for entry in entries)
    assert balance == f"{total:.2f}"
