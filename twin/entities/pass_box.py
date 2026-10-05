
"""Pass Box (Transfer Window) Digital Twin Entity with interlock detection."""
from __future__ import annotations
from typing import Any, Optional
from .base import DigitalTwinEntity, EventRecord, utcnow

VALID_TRANSITIONS: dict[str, list[str]] = {
    "IDLE":            ["LOCKED"],
    "LOCKED":          ["UV_DISINFECTING", "IDLE"],
    "UV_DISINFECTING": ["OPEN"],
    "OPEN":            ["TRANSFERRING", "INTERLOCK_ALARM"],
    "TRANSFERRING":    ["CLOSED"],
    "CLOSED":          ["IDLE"],
    "INTERLOCK_ALARM": ["IDLE"],
}
EVENT_MAP: dict[str, str] = {
    "LOCKED":          "TRANSFER_WINDOW_LOCKED",
    "UV_DISINFECTING": "TRANSFER_WINDOW_UV_STARTED",
    "OPEN":            "TRANSFER_WINDOW_OPENED",
    "TRANSFERRING":    "SAMPLE_MOVED",
    "CLOSED":          "TRANSFER_WINDOW_CLOSED",
    "IDLE":            "TRANSFER_WINDOW_RESET",
    "INTERLOCK_ALARM": "TRANSFER_WINDOW_INTERLOCK_VIOLATED",
}


class PassBoxTwin(DigitalTwinEntity):
    asset_type: str = "pass_box"
    door_a: str = "closed"
    door_b: str = "closed"
    uv_status: str = "off"
    adjacent_room_id: Optional[str] = None
    interlock_enabled: bool = True

    def transition(
        self,
        target_state: str,
        source: str = "workflow_engine",
        sample_id: Optional[str] = None,
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
        if target_state == "UV_DISINFECTING":
            self.uv_status = "running"
        elif target_state == "OPEN":
            self.uv_status = "complete"
        elif target_state == "IDLE":
            self.uv_status = "off"
            self.door_a = "closed"
            self.door_b = "closed"
        self.current_state.update({
            "status": self.status,
            "door_a": self.door_a,
            "door_b": self.door_b,
            "uv_status": self.uv_status,
        })
        severity = "CRITICAL" if target_state == "INTERLOCK_ALARM" else "INFO"
        return self.emit_event(
            event_type=EVENT_MAP.get(target_state, "PASS_BOX_STATE_CHANGED"),
            source=source,
            previous_state={"status": previous},
            new_state={"status": target_state},
            payload=payload or {},
            severity=severity,
            sample_id=sample_id,
            correlation_id=correlation_id,
        )

    def update_telemetry(self, readings: dict[str, Any]) -> EventRecord:
        self.door_a = readings.get("door_a", self.door_a)
        self.door_b = readings.get("door_b", self.door_b)
        self.uv_status = readings.get("uv_status", self.uv_status)
        if self.interlock_enabled and self.door_a == "open" and self.door_b == "open":
            if self.status != "INTERLOCK_ALARM":
                self.status = "INTERLOCK_ALARM"
                return self.emit_event(
                    event_type="TRANSFER_WINDOW_INTERLOCK_VIOLATED",
                    source="iot_gateway",
                    severity="CRITICAL",
                )
        self.current_state.update({
            "door_a": self.door_a,
            "door_b": self.door_b,
            "uv_status": self.uv_status,
            "status": self.status,
        })
        self.last_telemetry_at = utcnow().isoformat()
        self.updated_at = utcnow().isoformat()
        return self.emit_event(
            event_type="PASS_BOX_TELEMETRY_UPDATED",
            source="iot_gateway",
            new_state=self.current_state.copy(),
        )
