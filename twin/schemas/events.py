
"""
Event Schema — Pydantic models for all Digital Twin events.
Used for validation against contracts/event.json.
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid
from twin.entities.base import utcnow


class EventSchema(BaseModel):
    """Canonical event schema. Must match contracts/event.json."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
    event_type: str
    source: str
    asset_id: str
    sample_id: Optional[str] = None
    previous_state: dict[str, Any] = Field(default_factory=dict)
    new_state: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: str = "INFO"
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"frozen": True}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


VALID_SEVERITIES = {"INFO", "WARNING", "ALARM", "CRITICAL"}
VALID_SOURCES = {"iot_gateway", "api", "workflow_engine", "rules_engine",
                 "simulator", "twin_engine", "architecture_audit"}

KNOWN_EVENT_TYPES = {
    # Incubator
    "INCUBATOR_LOADED", "INCUBATOR_INCUBATION_STARTED", "INCUBATOR_INCUBATION_COMPLETED",
    "INCUBATOR_RELEASED", "INCUBATOR_TEMPERATURE_EXCURSION", "INCUBATOR_ALARM_ACKNOWLEDGED",
    "INCUBATOR_RECOVERED", "INCUBATOR_RESET", "INCUBATOR_TEMPERATURE_CHANGED",
    "INCUBATOR_STATE_CHANGED", "TELEMETRY_UPDATED",
    # Autoclave
    "AUTOCLAVE_LOADING_STARTED", "AUTOCLAVE_STARTED", "AUTOCLAVE_COOLING_STARTED",
    "AUTOCLAVE_COMPLETED", "AUTOCLAVE_RELEASED", "AUTOCLAVE_FAILED",
    "AUTOCLAVE_SAFE_STATE_ENTERED", "AUTOCLAVE_MAINTENANCE_STARTED",
    "AUTOCLAVE_VALIDATION_STARTED", "AUTOCLAVE_VALIDATION_PASSED",
    "AUTOCLAVE_RESET", "AUTOCLAVE_TELEMETRY_UPDATED", "AUTOCLAVE_STATE_CHANGED",
    # Pass Box
    "TRANSFER_WINDOW_LOCKED", "TRANSFER_WINDOW_UV_STARTED", "TRANSFER_WINDOW_OPENED",
    "TRANSFER_WINDOW_CLOSED", "TRANSFER_WINDOW_RESET", "TRANSFER_WINDOW_INTERLOCK_VIOLATED",
    "PASS_BOX_TELEMETRY_UPDATED", "PASS_BOX_STATE_CHANGED",
    # Sample
    "SAMPLE_REGISTERED", "SAMPLE_RECEIVED", "SAMPLE_PREPARED", "SAMPLE_TESTING_STARTED",
    "SAMPLE_INCUBATION_STARTED", "SAMPLE_INCUBATION_COMPLETED", "SAMPLE_READING_COMPLETED",
    "SAMPLE_APPROVED", "SAMPLE_REJECTED", "SAMPLE_REPORTED", "SAMPLE_ARCHIVED",
    "SAMPLE_MOVED", "SAMPLE_RETEST_INITIATED",
    # Alarm
    "ALARM_CREATED", "ALARM_ACKNOWLEDGED", "ALARM_RESOLVED",
    # Workflow
    "WORKFLOW_BLOCKED", "WORKFLOW_RELEASED", "WORKFLOW_TIMEOUT",
    # Environment
    "PRESSURE_EXCURSION", "TEMPERATURE_EXCURSION", "HUMIDITY_EXCURSION",
    "SENSOR_FAILURE", "SENSOR_RECOVERED",
}


def validate_event(event: dict[str, Any]) -> list[str]:
    """Validate an event dict. Returns list of validation errors."""
    errors = []
    required = ["event_id", "timestamp", "event_type", "source", "asset_id", "severity", "correlation_id"]
    for field in required:
        if field not in event:
            errors.append(f"Missing required field: {field!r}")
    if "severity" in event and event["severity"] not in VALID_SEVERITIES:
        errors.append(f"Invalid severity {event['severity']!r}. Must be one of {VALID_SEVERITIES}")
    return errors


