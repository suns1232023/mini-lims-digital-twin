
"""Incubator Digital Twin Entity with explicit state machine."""
from __future__ import annotations
from typing import Any, Optional
from .base import DigitalTwinEntity, EventRecord, utcnow

VALID_TRANSITIONS: dict[str, list[str]] = {
    "IDLE":       ["LOADED"],
    "LOADED":     ["INCUBATING", "IDLE"],
    "INCUBATING": ["COMPLETED", "ERROR"],
    "COMPLETED":  ["RELEASED"],
    "RELEASED":   ["IDLE"],
    "ERROR":      ["SAFE_STATE"],
    "SAFE_STATE": ["IDLE"],
}
EVENT_MAP: dict[str, str] = {
    "LOADED":     "INCUBATOR_LOADED",
    "INCUBATING": "INCUBATOR_INCUBATION_STARTED",
    "COMPLETED":  "INCUBATOR_INCUBATION_COMPLETED",
    "RELEASED":   "INCUBATOR_RELEASED",
    "ERROR":      "INCUBATOR_TEMPERATURE_EXCURSION",
    "SAFE_STATE": "INCUBATOR_ALARM_ACKNOWLEDGED",
    "IDLE":       "INCUBATOR_RESET",
}
SEVERITY_MAP: dict[str, str] = {"ERROR": "ALARM", "SAFE_STATE": "WARNING"}


class IncubatorTwin(DigitalTwinEntity):
    asset_type: str = "incubator"
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    door: str = "closed"
    setpoint_temperature: float = 37.0

    def transition(
        self,
        target_state: str,
        source: str = "workflow_engine",
        correlation_id: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> EventRecord:
        allowed = VALID_TRANSITIONS.get(self.status, [])
        if target_state not in allowed:
            raise ValueError(
                f"Invalid transition {self.status!r} → {target_state!r} "
                f"for {self.asset_id}. Allowed: {allowed}"
            )
        previous = self.status
        self.status = target_state
        self.updated_at = utcnow().isoformat()
        self.current_state["status"] = target_state
        return self.emit_event(
            event_type=EVENT_MAP.get(target_state, "INCUBATOR_STATE_CHANGED"),
            source=source,
            previous_state={"status": previous},
            new_state={"status": target_state},
            payload=payload or {},
            severity=SEVERITY_MAP.get(target_state, "INFO"),
            correlation_id=correlation_id,
        )

    def update_telemetry(self, readings: dict[str, Any]) -> EventRecord:
        self.temperature = readings.get("temperature", self.temperature)
        self.humidity = readings.get("humidity", self.humidity)
        self.door = readings.get("door", self.door)
        self.current_state.update({
            "temperature": self.temperature,
            "humidity": self.humidity,
            "door": self.door,
            "status": self.status,
        })
        self.last_telemetry_at = utcnow().isoformat()
        self.updated_at = utcnow().isoformat()
        return self.emit_event(
            event_type="INCUBATOR_TEMPERATURE_CHANGED",
            source="iot_gateway",
            new_state=self.current_state.copy(),
        )

    def get_summary(self) -> dict[str, Any]:
        s = super().get_summary()
        s.update({"temperature": self.temperature, "humidity": self.humidity,
                  "door": self.door, "setpoint_temperature": self.setpoint_temperature})
        return s
