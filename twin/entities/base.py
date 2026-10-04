
"""
Digital Twin Base Entity
Every physical laboratory asset has a Digital Twin representation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventRecord(BaseModel):
    """Immutable event record — never modified after creation."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=utcnow)
    event_type: str
    source: str
    asset_id: str
    sample_id: Optional[str] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "INFO"
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AssetMetadata(BaseModel):
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial: Optional[str] = None
    capacity_ml: Optional[float] = None
    dimensions_m: Optional[str] = None
    clean_grade: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class DigitalTwinEntity(BaseModel):
    """
    Base class for all Digital Twin entities.
    Represents a physical laboratory asset with full state tracking.
    """
    # Identity
    asset_id: str
    asset_type: str
    name: str

    # Location
    room_id: Optional[str] = None

    # State
    status: str = "IDLE"
    current_state: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    metadata: AssetMetadata = Field(default_factory=AssetMetadata)

    # Relationships
    related_assets: List[str] = Field(default_factory=list)
    active_sample_ids: List[str] = Field(default_factory=list)

    # Alarms
    active_alarm_ids: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_telemetry_at: Optional[datetime] = None

    # Event history (in-memory, last N events)
    _event_history: List[EventRecord] = []

    class Config:
        arbitrary_types_allowed = True

    def emit_event(
        self,
        event_type: str,
        source: str = "twin_engine",
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        payload: Optional[Dict] = None,
        severity: str = "INFO",
        sample_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> EventRecord:
        """Create and record an immutable event for this asset."""
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
        self._event_history.append(event)
        return event

    def update_telemetry(self, readings: Dict[str, Any]) -> EventRecord:
        """Update current state from sensor readings."""
        previous = self.current_state.copy()
        self.current_state.update(readings)
        self.updated_at = utcnow()
        self.last_telemetry_at = utcnow()
        return self.emit_event(
            event_type="TELEMETRY_UPDATED",
            source="iot_gateway",
            previous_state=previous,
            new_state=self.current_state.copy(),
            severity="INFO",
        )

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary suitable for API responses."""
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "name": self.name,
            "room_id": self.room_id,
            "status": self.status,
            "current_state": self.current_state,
            "active_alarms": len(self.active_alarm_ids),
            "active_samples": len(self.active_sample_ids),
            "updated_at": self.updated_at.isoformat(),
            "last_telemetry_at": self.last_telemetry_at.isoformat() if self.last_telemetry_at else None,
        }

