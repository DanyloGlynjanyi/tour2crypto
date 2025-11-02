from __future__ import annotations

import pytest

from t2c_events.validators import validate_event
from t2c_pipeline.collector import (
    collect_trip_completed,
    collect_withdrawal_paid,
    collect_withdrawal_requested,
    reset_withdrawal_context,
)


def test_collectors_produce_valid_events() -> None:
    reset_withdrawal_context()

    trip_event = collect_trip_completed("A" * 26, "B" * 26)
    validate_event(trip_event)

    requested_event = collect_withdrawal_requested("A" * 26, "C" * 26, "15.00")
    validate_event(requested_event)

    withdrawal_id = requested_event["payload"]["withdrawal_request_id"]
    paid_event = collect_withdrawal_paid(withdrawal_id, "TX-VAL-001", "1.00")
    validate_event(paid_event)


def test_collect_withdrawal_paid_requires_known_request() -> None:
    reset_withdrawal_context()
    with pytest.raises(KeyError):
        collect_withdrawal_paid("UNKNOWN-WITHDRAWAL", "TX-NOPE", "0.00")
