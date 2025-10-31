from __future__ import annotations

import pytest

from t2c_contracts import (
    APPLICATION_SCHEMA,
    TRIP_SCHEMA,
    ValidationError,
    validate_application,
    validate_trip,
)
from t2c_contracts.factories import ApplicationFactory, TripFactory


class TestTripValidation:
    def test_valid_trip_passes(self) -> None:
        payload = TripFactory().build()
        validate_trip(payload)

    def test_trip_schema_metadata(self) -> None:
        assert TRIP_SCHEMA["title"] == "Trip"
        assert "required" in TRIP_SCHEMA

    def test_trip_rejects_invalid_ulid(self) -> None:
        payload = TripFactory().build()
        payload["id"] = "not-a-ulid"
        with pytest.raises(ValidationError):
            validate_trip(payload)


class TestApplicationValidation:
    def test_valid_application_passes(self) -> None:
        payload = ApplicationFactory().build()
        validate_application(payload)

    def test_application_schema_structure(self) -> None:
        assert APPLICATION_SCHEMA["title"] == "Application"
        assert "required" in APPLICATION_SCHEMA

    def test_application_rejects_invalid_status(self) -> None:
        payload = ApplicationFactory().build()
        payload["status"] = "unknown"
        with pytest.raises(ValidationError):
            validate_application(payload)
