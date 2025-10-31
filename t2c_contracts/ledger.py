"""Ledger utilities for wallet balance calculations."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Iterable

from .validation import CashbackLedgerEntryModel

TWOPLACES = Decimal("0.01")

__all__ = ["compute_wallet_balance"]


def _normalize_amount(amount: str) -> Decimal:
    decimal_amount = Decimal(amount)
    return decimal_amount.quantize(TWOPLACES, rounding=ROUND_DOWN)


def compute_wallet_balance(entries: Iterable[CashbackLedgerEntryModel]) -> str:
    """Compute wallet balance strictly from ledger entries."""

    total = Decimal("0.00")
    for entry in entries:
        total += _normalize_amount(entry.amount)
    return f"{total.quantize(TWOPLACES, rounding=ROUND_DOWN):.2f}"
