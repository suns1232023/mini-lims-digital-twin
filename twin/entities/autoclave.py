
"""
Autoclave Digital Twin Entity
Normal: IDLE → LOADING → RUNNING → COOLING → COMPLETED → RELEASED
Failure: RUNNING → ERROR → SAFE_STATE → MAINTENANCE → VALIDATION → RELEASED
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from .base import DigitalTwinEntity, EventRecord, utcnow


VALID_TRANSITIONS = {
    "IDLE":        ["LOADING"],
    "LOADING":     ["RUNNING", "IDLE"],
    "RUNNING":     ["COOLING", "ERROR"],
    "COOLING":     ["COMPLETED"],
    "COMPLETED":   ["RELEASED"],
    "RELEASED":    ["IDLE"],
    "ERROR":       ["SAFE_STATE"],
    "SAFE_STATE":  ["MAINTENANCE"],
    "MAINTENANCE": ["VALIDATION"],
    "VALIDATION":  ["RELEASED"],
}

EVENT_MAP = {
    "LOADING":     "AUTOCLAVE_LOADING_STARTED",
    "RUNNING":     "AUTOCLAVE_STARTED",
    "COOLING":     "AUTOCLAVE_COOLING_STARTED",
    "COMPLETED":   "AUTOCLAVE_COMPLETED",
    "RELEASED":    "AUTOCLAVE_RELEASED",
    "ERROR":       "AUTOCLAVE_FAILED",
    "SAFE_STATE":  "AUTOCLAVE_SAFE_STATE_ENTERED",
    "MAINTENANCE": "AUTOCLAVE_MAINTENANCE_STARTED",
    "VALIDATION":  "AUTOCLAVE_VALIDATION_STARTED",
    "IDLE":        "AUTOCLAVE_RESET",
}

SEVERITY_MAP = {
    "ERROR":      "CRITICAL",
    "SAFE_STATE": "WARNING",
    "RUNNING":    "INFO",
}


class AutoclaveTwin(DigitalTwinEntity):
    asset_type: str = "autoclave"
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    countdown_sec: int = 0
    cycle_total: int = 0
    cycle_time_sec: int = 1200  # 20 min default

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

        if target_state == "RUNNING":
            self.countdown_sec = self.cycle_time_sec
            self.temperature = 121.0
        elif target_state == "COMPLETED":
            self.cycle_total += 1
            self.countdown_sec = 0
        elif target_state == "IDLE":
            self.temperature = 25.0
            self.countdown_sec = 0

        self.current_state.update({
            "status": self.status,
            "temperature": self.temperature,
            "pressure": self.pressure,
            "countdown_sec": self.countdown_sec,
            "cycle_total": self.cycle_total,
        })

        return self.emit_event(
            event_type=EVENT_MAP.get(target_state, "AUTOCLAVE_STATE_CHANGED"),
            source=source,
            previous_state={"status": previous},
            new_state={"status": target_state},
            payload=payload or {},
            severity=SEVERITY_MAP.get(target_state, "INFO"),
            correlation_id=correlation_id,
        )

    def update_telemetry(self, readings: Dict[str, Any]) -> EventRecord:
        self.temperature = readings.get("temperature", self.temperature)
        self.pressure = readings.get("pressure", self.pressure)
        if self.status == "RUNNING" and self.countdown_sec > 0:
            self.countdown_sec = max(0, self.countdown_sec - 2)
        self.current_state.update({
            "temperature": self.temperature,
            "pressure": self.pressure,
            "countdown_sec": self.countdown_sec,
            "status": self.status,
        })
        self.last_telemetry_at = utcnow()
        self.updated_at = utcnow()
        return self.emit_event(
            event_type="AUTOCLAVE_TELEMETRY_UPDATED",
            source="iot_gateway",
            new_state=self.current_state.copy(),
            severity="INFO",
        )

    def get_summary(self):
        s = super().get_summary()
        s.update({
            "temperature": self.temperature,
            "pressure": self.pressure,
            "countdown_sec": self.countdown_sec,
            "cycle_total": self.cycle_total,
        })
        return s

