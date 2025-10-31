from __future__ import annotations

import pytest

from t2c_rules import assert_invariants


def _wallet_id() -> str:
    return "A" * 26


def _lock_id() -> str:
    return "L" * 26


def test_payout_without_prior_lock_raises() -> None:
    ledger = [
        {
            "type": "payout",
            "wallet_id": _wallet_id(),
            "amount": "10.00",
            "direction": "debit",
            "lock_id": _lock_id(),
        }
    ]
    with pytest.raises(ValueError):
        assert_invariants(ledger)


def test_release_cannot_exceed_locked_amount() -> None:
    ledger = [
        {
            "type": "withdrawal_lock",
            "wallet_id": _wallet_id(),
            "amount": "05.00",
            "direction": "debit",
            "lock_id": _lock_id(),
        },
        {
            "type": "withdrawal_release",
            "wallet_id": _wallet_id(),
            "amount": "10.00",
            "lock_id": _lock_id(),
        },
    ]
    with pytest.raises(ValueError):
        assert_invariants(ledger)


def test_cashback_reversal_cannot_exceed_accrual() -> None:
    ledger = [
        {
            "type": "cashback_accrual",
            "wallet_id": _wallet_id(),
            "amount": "05.00",
            "direction": "credit",
            "trip_id": "T" * 26,
        },
        {
            "type": "cashback_reversal",
            "wallet_id": _wallet_id(),
            "amount": "10.00",
            "direction": "debit",
            "trip_id": "T" * 26,
        },
    ]
    with pytest.raises(ValueError):
        assert_invariants(ledger)


def test_unknown_ledger_type_is_rejected() -> None:
    ledger = [
        {
            "type": "bonus_award",
            "wallet_id": _wallet_id(),
            "amount": "01.00",
        }
    ]
    with pytest.raises(ValueError):
        assert_invariants(ledger)


def test_non_string_amount_is_invalid() -> None:
    ledger = [
        {
            "type": "cashback_accrual",
            "wallet_id": _wallet_id(),
            "amount": 1.0,
            "direction": "credit",
            "trip_id": "T" * 26,
        }
    ]
    with pytest.raises(ValueError):
        assert_invariants(ledger)
