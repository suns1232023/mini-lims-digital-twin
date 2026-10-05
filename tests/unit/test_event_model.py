
"""
Unit Tests — Event Model
Tests: event creation, field validation, immutability, schema compliance.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from twin.entities.base import EventRecord
from twin.schemas.events import validate_event, VALID_SEVERITIES


class TestEventRecord:
    def test_event_has_required_fields(self):
        event = EventRecord(
            event_type="INCUBATOR_LOADED",
            source="twin_engine",
            asset_id="INC-01",
        )
        assert event.event_id
        assert event.timestamp
        assert event.event_type == "INCUBATOR_LOADED"
        assert event.source == "twin_engine"
        assert event.asset_id == "INC-01"
        assert event.severity == "INFO"
        assert event.correlation_id

    def test_event_id_is_unique(self):
        e1 = EventRecord(event_type="A", source="s", asset_id="X")
        e2 = EventRecord(event_type="A", source="s", asset_id="X")
        assert e1.event_id != e2.event_id

    def test_correlation_id_is_unique(self):
        e1 = EventRecord(event_type="A", source="s", asset_id="X")
        e2 = EventRecord(event_type="A", source="s", asset_id="X")
        assert e1.correlation_id != e2.correlation_id

    def test_event_is_immutable(self):
        event = EventRecord(event_type="A", source="s", asset_id="X")
        with pytest.raises(Exception):
            event.event_type = "B"

    def test_event_default_severity_is_info(self):
        event = EventRecord(event_type="A", source="s", asset_id="X")
        assert event.severity == "INFO"

    def test_event_custom_severity(self):
        event = EventRecord(event_type="A", source="s", asset_id="X", severity="CRITICAL")
        assert event.severity == "CRITICAL"

    def test_event_with_sample_id(self):
        event = EventRecord(
            event_type="SAMPLE_MOVED",
            source="api",
            asset_id="PB-01",
            sample_id="SMP-0001",
        )
        assert event.sample_id == "SMP-0001"

    def test_event_previous_and_new_state(self):
        event = EventRecord(
            event_type="INCUBATOR_STATE_CHANGED",
            source="twin_engine",
            asset_id="INC-01",
            previous_state={"status": "IDLE"},
            new_state={"status": "LOADED"},
        )
        assert event.previous_state == {"status": "IDLE"}
        assert event.new_state == {"status": "LOADED"}

    def test_event_payload(self):
        event = EventRecord(
            event_type="ALARM_CREATED",
            source="rules_engine",
            asset_id="INC-01",
            payload={"rule_id": "INC_TEMP_HIGH", "value": 42.0},
        )
        assert event.payload["rule_id"] == "INC_TEMP_HIGH"


class TestEventValidation:
    def test_valid_event_passes(self):
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-10-04T00:00:00+00:00",
            "event_type": "INCUBATOR_LOADED",
            "source": "twin_engine",
            "asset_id": "INC-01",
            "severity": "INFO",
            "correlation_id": "550e8400-e29b-41d4-a716-446655440001",
        }
        errors = validate_event(event)
        assert errors == []

    def test_missing_required_field(self):
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-10-04T00:00:00+00:00",
            "event_type": "INCUBATOR_LOADED",
            # missing source, asset_id, severity, correlation_id
        }
        errors = validate_event(event)
        assert len(errors) > 0

    def test_invalid_severity_detected(self):
        event = {
            "event_id": "x", "timestamp": "t", "event_type": "E",
            "source": "api", "asset_id": "A",
            "severity": "INVALID_SEVERITY",
            "correlation_id": "y",
        }
        errors = validate_event(event)
        assert any("severity" in e.lower() for e in errors)

    def test_valid_severities_set(self):
        assert "INFO" in VALID_SEVERITIES
        assert "WARNING" in VALID_SEVERITIES
        assert "ALARM" in VALID_SEVERITIES
        assert "CRITICAL" in VALID_SEVERITIES

