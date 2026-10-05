
"""
Digital Twin Base Entity — source of truth for all asset state.
UI must never be the source of truth.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventRecord(BaseModel):
    """Immutable event record. Never modified after creation."""
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


class DigitalTwinEntity(BaseModel):
    """Base class for all Digital Twin entities."""
    asset_id: str
    asset_type: str
    name: str
    room_id: Optional[str] = None
    status: str = "IDLE"
    current_state: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    active_alarm_ids: list[str] = Field(default_factory=list)
    active_sample_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())
    last_telemetry_at: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    # In-memory event log (not serialized)
    _events: list[EventRecord] = []

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "_events", [])

    def emit_event(
        self,
        event_type: str,
        source: str = "twin_engine",
        previous_state: Optional[dict] = None,
        new_state: Optional[dict] = None,
        payload: Optional[dict] = None,
        severity: str = "INFO",
        sample_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> EventRecord:
        event = EventRecord(
            event_type=event_type,
            source=source,
            asset_id=self.asset_id,
            sample_id=sample_id,
            previous_state=previous_state or {},
            new_state=new_state or self.current_state.copy(),
            payload=payload or {},
            severity=severity,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )
        self._events.append(event)
        return event

    def update_telemetry(self, readings: dict[str, Any]) -> EventRecord:
        previous = self.current_state.copy()
        self.current_state.update(readings)
        self.updated_at = utcnow().isoformat()
        self.last_telemetry_at = utcnow().isoformat()
        return self.emit_event(
            event_type="TELEMETRY_UPDATED",
            source="iot_gateway",
            previous_state=previous,
            new_state=self.current_state.copy(),
        )

    def get_events(self) -> list[EventRecord]:
        return list(self._events)

    def get_summary(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "name": self.name,
            "room_id": self.room_id,
            "status": self.status,
            "current_state": self.current_state,
            "active_alarms": len(self.active_alarm_ids),
            "active_samples": len(self.active_sample_ids),
            "updated_at": self.updated_at,
            "last_telemetry_at": self.last_telemetry_at,
        }
