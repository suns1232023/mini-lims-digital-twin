
"""
Simulation Engine — Deterministic scenario execution.
Scenarios A–I as defined in the architecture specification.
"""
from __future__ import annotations

import uuid
import random
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SimulationReport:
    def __init__(self, scenario_id: str, scenario_name: str):
        self.run_id = str(uuid.uuid4())
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.started_at = utcnow()
        self.completed_at: Optional[datetime] = None
        self.event_sequence: List[Dict] = []
        self.state_transitions: List[Dict] = []
        self.alarms: List[Dict] = []
        self.affected_samples: List[str] = []
        self.workflow_impact: List[Dict] = []
        self.recovery_path: List[str] = []
        self.final_state: Dict[str, Any] = {}

    def add_event(self, event_type: str, asset_id: str, payload: Dict = None, severity: str = "INFO"):
        self.event_sequence.append({
            "ts": utcnow().isoformat(),
            "event_type": event_type,
            "asset_id": asset_id,
            "severity": severity,
            "payload": payload or {},
        })

    def add_transition(self, asset_id: str, from_state: str, to_state: str):
        self.state_transitions.append({
            "ts": utcnow().isoformat(),
            "asset_id": asset_id,
            "from": from_state,
            "to": to_state,
        })

    def add_alarm(self, rule_id: str, asset_id: str, message: str, severity: str):
        self.alarms.append({
            "ts": utcnow().isoformat(),
            "rule_id": rule_id,
            "asset_id": asset_id,
            "message": message,
            "severity": severity,
        })

    def finalize(self, final_state: Dict[str, Any]):
        self.completed_at = utcnow()
        self.final_state = final_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "summary": {
                "total_events": len(self.event_sequence),
                "total_transitions": len(self.state_transitions),
                "total_alarms": len(self.alarms),
                "affected_samples": len(self.affected_samples),
            },
            "event_sequence": self.event_sequence,
            "state_transitions": self.state_transitions,
            "alarms": self.alarms,
            "affected_samples": self.affected_samples,
            "workflow_impact": self.workflow_impact,
            "recovery_path": self.recovery_path,
            "final_state": self.final_state,
        }


class ScenarioEngine:
    """
    Runs deterministic simulation scenarios.
    Each scenario produces: event sequence, state transitions, alarms,
    affected samples, workflow impact, recovery path, final state, report.
    """

    SCENARIOS = {
        "A": "Normal laboratory operation",
        "B": "Incubator temperature excursion",
        "C": "Pass-box interlock violation",
        "D": "Autoclave failure",
        "E": "Sensor failure",
        "F": "Environmental excursion",
        "G": "Sample workflow timeout",
        "H": "Equipment unavailable",
        "I": "Recovery after failure",
    }

    def run(self, scenario_id: str, params: Optional[Dict] = None) -> SimulationReport:
        name = self.SCENARIOS.get(scenario_id, f"Scenario {scenario_id}")
        report = SimulationReport(scenario_id=scenario_id, scenario_name=name)
        params = params or {}
        runner = getattr(self, f"_scenario_{scenario_id.lower()}", self._scenario_unknown)
        runner(report, params)
        return report

    # ── Scenario A: Normal Operation ─────────────────────────────
    def _scenario_a(self, r: SimulationReport, p: Dict):
        r.add_event("INCUBATOR_LOADED", "INC-01", {"sample_id": "SMP-0001"})
        r.add_transition("INC-01", "IDLE", "LOADED")
        r.add_event("INCUBATOR_INCUBATION_STARTED", "INC-01", {"temperature": 37.0})
        r.add_transition("INC-01", "LOADED", "INCUBATING")
        for i in range(5):
            temp = 37.0 + math.sin(i * 0.5) * 0.2
            r.add_event("INCUBATOR_TEMPERATURE_CHANGED", "INC-01", {"temperature": round(temp, 2)})
        r.add_event("INCUBATOR_INCUBATION_COMPLETED", "INC-01")
        r.add_transition("INC-01", "INCUBATING", "COMPLETED")
        r.add_event("AUTOCLAVE_STARTED", "AC-01", {"cycle": "gravity_121C"})
        r.add_transition("AC-01", "IDLE", "RUNNING")
        r.add_event("AUTOCLAVE_COMPLETED", "AC-01", {"cycle_total": 1})
        r.add_transition("AC-01", "RUNNING", "COMPLETED")
        r.affected_samples = ["SMP-0001"]
        r.final_state = {"INC-01": "COMPLETED", "AC-01": "COMPLETED", "all_alarms": 0}
        r.finalize(r.final_state)

    # ── Scenario B: Incubator Temperature Excursion ──────────────
    def _scenario_b(self, r: SimulationReport, p: Dict):
        target_temp = p.get("target_temperature", 42.0)
        r.add_event("INCUBATOR_LOADED", "INC-02", {"sample_id": "SMP-0002"})
        r.add_transition("INC-02", "IDLE", "LOADED")
        r.add_event("INCUBATOR_INCUBATION_STARTED", "INC-02", {"temperature": 37.0})
        r.add_transition("INC-02", "LOADED", "INCUBATING")
        for i in range(3):
            temp = 37.0 + (target_temp - 37.0) * (i + 1) / 3
            r.add_event("INCUBATOR_TEMPERATURE_CHANGED", "INC-02", {"temperature": round(temp, 2)})
        r.add_alarm("INC_TEMP_HIGH", "INC-02", f"Temperature {target_temp}°C exceeds alarm limit 40°C", "ALARM")
        r.add_event("INCUBATOR_TEMPERATURE_EXCURSION", "INC-02", {"temperature": target_temp}, "ALARM")
        r.add_transition("INC-02", "INCUBATING", "ERROR")
        r.affected_samples = ["SMP-0002"]
        r.workflow_impact = [{"sample_id": "SMP-0002", "impact": "WORKFLOW_BLOCKED", "reason": "temperature_excursion"}]
        r.recovery_path = ["ERROR", "SAFE_STATE", "IDLE"]
        r.final_state = {"INC-02": "ERROR", "alarms": 1, "affected_samples": ["SMP-0002"]}
        r.finalize(r.final_state)

    # ── Scenario C: Pass-Box Interlock Violation ─────────────────
    def _scenario_c(self, r: SimulationReport, p: Dict):
        r.add_event("TRANSFER_WINDOW_LOCKED", "PB-01")
        r.add_transition("PB-01", "IDLE", "LOCKED")
        r.add_event("TRANSFER_WINDOW_UV_STARTED", "PB-01")
        r.add_transition("PB-01", "LOCKED", "UV_DISINFECTING")
        r.add_event("TRANSFER_WINDOW_OPENED", "PB-01", {"door": "door_a"})
        r.add_transition("PB-01", "UV_DISINFECTING", "OPEN")
        # Interlock violation: both doors open
        r.add_event("TRANSFER_WINDOW_INTERLOCK_VIOLATED", "PB-01",
                    {"door_a": "open", "door_b": "open"}, "CRITICAL")
        r.add_alarm("PB_INTERLOCK_VIOLATION", "PB-01",
                    "Both doors open simultaneously — interlock violated", "CRITICAL")
        r.add_transition("PB-01", "OPEN", "INTERLOCK_ALARM")
        r.recovery_path = ["INTERLOCK_ALARM", "IDLE"]
        r.final_state = {"PB-01": "INTERLOCK_ALARM", "alarms": 1}
        r.finalize(r.final_state)

    # ── Scenario D: Autoclave Failure ────────────────────────────
    def _scenario_d(self, r: SimulationReport, p: Dict):
        r.add_event("AUTOCLAVE_STARTED", "AC-01", {"temperature": 121.0})
        r.add_transition("AC-01", "IDLE", "RUNNING")
        r.add_event("AUTOCLAVE_TELEMETRY_UPDATED", "AC-01", {"temperature": 121.0, "pressure": 1.05})
        r.add_event("AUTOCLAVE_TELEMETRY_UPDATED", "AC-01", {"temperature": 118.0, "pressure": 0.8})
        r.add_alarm("AC_TEMP_EXCURSION", "AC-01",
                    "Temperature 118°C below sterilization minimum 120°C", "CRITICAL")
        r.add_event("AUTOCLAVE_FAILED", "AC-01", {"temperature": 118.0}, "CRITICAL")
        r.add_transition("AC-01", "RUNNING", "ERROR")
        r.add_event("AUTOCLAVE_SAFE_STATE_ENTERED", "AC-01")
        r.add_transition("AC-01", "ERROR", "SAFE_STATE")
        r.recovery_path = ["ERROR", "SAFE_STATE", "MAINTENANCE", "VALIDATION", "RELEASED"]
        r.final_state = {"AC-01": "SAFE_STATE", "alarms": 1}
        r.finalize(r.final_state)

    # ── Scenario E: Sensor Failure ───────────────────────────────
    def _scenario_e(self, r: SimulationReport, p: Dict):
        r.add_event("TELEMETRY_UPDATED", "ENV-STERILE", {"temperature": 22.0, "pressure": -15.0})
        r.add_event("TELEMETRY_UPDATED", "ENV-STERILE", {"temperature": 22.0, "pressure": -15.0})
        # Sensor stops reporting
        r.add_alarm("SENSOR_FAILURE", "ENV-STERILE",
                    "Sensor ENV-STERILE has not reported for 65s", "CRITICAL")
        r.add_event("SENSOR_FAILURE", "ENV-STERILE", {"last_reading_age_sec": 65}, "CRITICAL")
        r.recovery_path = ["sensor_replaced", "SENSOR_RECOVERED"]
        r.final_state = {"ENV-STERILE": "FAILED", "alarms": 1}
        r.finalize(r.final_state)

    # ── Scenario F: Environmental Excursion ──────────────────────
    def _scenario_f(self, r: SimulationReport, p: Dict):
        target_pressure = p.get("target_pressure", -3.0)
        for pressure in [-15.0, -12.0, -8.0, -5.0, target_pressure]:
            r.add_event("TELEMETRY_UPDATED", "ENV-STERILE", {"pressure": pressure})
        r.add_alarm("ENV_PRESSURE_ALARM", "ENV-STERILE",
                    f"Room R-STERILE pressure {target_pressure} Pa out of range", "ALARM")
        r.add_event("PRESSURE_EXCURSION", "ENV-STERILE", {"pressure": target_pressure}, "ALARM")
        r.affected_samples = ["SMP-0003", "SMP-0004"]
        r.workflow_impact = [
            {"sample_id": s, "impact": "WORKFLOW_BLOCKED", "reason": "environmental_excursion"}
            for s in r.affected_samples
        ]
        r.final_state = {"ENV-STERILE": "ALARM", "alarms": 1, "affected_samples": r.affected_samples}
        r.finalize(r.final_state)

    # ── Scenario G: Sample Workflow Timeout ──────────────────────
    def _scenario_g(self, r: SimulationReport, p: Dict):
        r.add_event("SAMPLE_RECEIVED", "LIMS", {"sample_id": "SMP-0005"})
        r.add_event("SAMPLE_PREPARED", "LIMS", {"sample_id": "SMP-0005"})
        # Timeout: sample stuck in TESTING for > 2h
        r.add_alarm("SAMPLE_WORKFLOW_TIMEOUT", "LIMS",
                    "Sample SMP-0005 in TESTING for 3h (limit: 2h)", "ALARM")
        r.add_event("WORKFLOW_BLOCKED", "LIMS",
                    {"sample_id": "SMP-0005", "state": "TESTING", "age_hours": 3}, "ALARM")
        r.affected_samples = ["SMP-0005"]
        r.recovery_path = ["WORKFLOW_RELEASED", "TESTING", "INCUBATING"]
        r.final_state = {"SMP-0005": "BLOCKED_IN_TESTING", "alarms": 1}
        r.finalize(r.final_state)

    # ── Scenario H: Equipment Unavailable ───────────────────────
    def _scenario_h(self, r: SimulationReport, p: Dict):
        r.add_event("INCUBATOR_INCUBATION_STARTED", "INC-03")
        r.add_transition("INC-03", "IDLE", "INCUBATING")
        # All incubators occupied — new sample cannot be assigned
        r.add_event("WORKFLOW_BLOCKED", "LIMS",
                    {"sample_id": "SMP-0006", "reason": "no_incubator_available"}, "WARNING")
        r.add_alarm("EQUIPMENT_UNAVAILABLE", "LIMS",
                    "No incubator available for SMP-0006", "WARNING")
        r.affected_samples = ["SMP-0006"]
        r.workflow_impact = [{"sample_id": "SMP-0006", "impact": "WORKFLOW_BLOCKED", "reason": "equipment_unavailable"}]
        r.final_state = {"SMP-0006": "BLOCKED_WAITING_EQUIPMENT", "alarms": 1}
        r.finalize(r.final_state)

    # ── Scenario I: Recovery After Failure ───────────────────────
    def _scenario_i(self, r: SimulationReport, p: Dict):
        # Start from ERROR state (result of Scenario B or D)
        r.add_event("INCUBATOR_ALARM_ACKNOWLEDGED", "INC-02", {"operator": "QA-001"})
        r.add_transition("INC-02", "ERROR", "SAFE_STATE")
        r.add_event("INCUBATOR_RECOVERED", "INC-02", {"temperature": 37.0})
        r.add_transition("INC-02", "SAFE_STATE", "IDLE")
        r.add_event("ALARM_RESOLVED", "INC-02", {"rule_id": "INC_TEMP_HIGH"})
        r.add_event("WORKFLOW_RELEASED", "LIMS", {"sample_id": "SMP-0002"})
        r.recovery_path = ["ERROR", "SAFE_STATE", "IDLE", "LOADED", "INCUBATING"]
        r.final_state = {"INC-02": "IDLE", "alarms": 0, "SMP-0002": "WORKFLOW_RELEASED"}
        r.finalize(r.final_state)

    def _scenario_unknown(self, r: SimulationReport, p: Dict):
        r.add_event("SIMULATION_ERROR", "SYSTEM", {"reason": f"Unknown scenario {r.scenario_id}"}, "WARNING")
        r.finalize({"error": "unknown_scenario"})

