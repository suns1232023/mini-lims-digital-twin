
"""
Incubator Digital Twin Entity
State machine: IDLE → LOADED → INCUBATING → COMPLETED → RELEASED
Failure path:  INCUBATING → ERROR → SAFE_STATE → IDLE
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from .base import DigitalTwinEntity, EventRecord, utcnow


VALID_TRANSITIONS = {
    "IDLE":       ["LOADED"],
    "LOADED":     ["INCUBATING", "IDLE"],
    "INCUBATING": ["COMPLETED", "ERROR"],
    "COMPLETED":  ["RELEASED"],
    "RELEASED":   ["IDLE"],
    "ERROR":      ["SAFE_STATE"],
    "SAFE_STATE": ["IDLE"],
}


class IncubatorTwin(DigitalTwinEntity):
    asset_type: str = "incubator"
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    door: str = "closed"
    setpoint_temperature: float = 37.0
    setpoint_humidity: float = 60.0

    def transition(
        self,
        target_state: str,
        source: str = "workflow_engine",
        correlation_id: Optional[str] = None,
        payload: Optional[Dict] = None,
    ) -> EventRecord:
        allowed = VALID_TRANSITIONS.get(self.status, [])
        if target_state not in allowed:
            raise ValueError(
                f"Invalid transition {self.status} → {target_state} "
                f"for {self.asset_id}. Allowed: {allowed}"
            )
        previous = self.status
        self.status = target_state
        self.updated_at = utcnow()

        event_map = {
            "LOADED":     "INCUBATOR_LOADED",
            "INCUBATING": "INCUBATOR_INCUBATION_STARTED",
            "COMPLETED":  "INCUBATOR_INCUBATION_COMPLETED",
            "RELEASED":   "INCUBATOR_RELEASED",
            "ERROR":      "INCUBATOR_TEMPERATURE_EXCURSION",
            "SAFE_STATE": "INCUBATOR_ALARM_ACKNOWLEDGED",
            "IDLE":       "INCUBATOR_RESET",
        }
        severity_map = {
            "ERROR": "ALARM",
            "SAFE_STATE": "WARNING",
        }
        return self.emit_event(
            event_type=event_map.get(target_state, "INCUBATOR_STATE_CHANGED"),
            source=source,
            previous_state={"status": previous},
            new_state={"status": target_state},
            payload=payload or {},
            severity=severity_map.get(target_state, "INFO"),
            correlation_id=correlation_id,
        )

    def update_telemetry(self, readings: Dict[str, Any]) -> EventRecord:
        self.temperature = readings.get("temperature", self.temperature)
        self.humidity = readings.get("humidity", self.humidity)
        self.door = readings.get("door", self.door)
        self.current_state.update({
            "temperature": self.temperature,
            "humidity": self.humidity,
            "door": self.door,
            "status": self.status,
        })
        self.last_telemetry_at = utcnow()
        self.updated_at = utcnow()
        return self.emit_event(
            event_type="INCUBATOR_TEMPERATURE_CHANGED",
            source="iot_gateway",
            new_state=self.current_state.copy(),
            severity="INFO",
        )

    def get_summary(self):
        s = super().get_summary()
        s.update({
            "temperature": self.temperature,
            "humidity": self.humidity,
            "door": self.door,
            "setpoint_temperature": self.setpoint_temperature,
        })
        return s

