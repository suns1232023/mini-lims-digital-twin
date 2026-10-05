
"""
Simulation Tests — All 9 Scenarios (A-I)
Every scenario becomes a regression test.
Tests validate actual simulation behavior, not mocks.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from simulation.scenarios.engine import ScenarioEngine, SimulationReport


@pytest.fixture
def engine():
    return ScenarioEngine()


def assert_valid_report(report: SimulationReport) -> None:
    """Common assertions for all simulation reports."""
    assert report.run_id, "run_id must be set"
    assert report.scenario_id, "scenario_id must be set"
    assert report.scenario_name, "scenario_name must be set"
    assert report.started_at, "started_at must be set"
    assert report.completed_at, "completed_at must be set"
    assert isinstance(report.event_sequence, list)
    assert isinstance(report.state_transitions, list)
    assert isinstance(report.alarms, list)
    assert isinstance(report.final_state, dict)
    # Validate to_dict structure
    d = report.to_dict()
    for key in ["run_id", "scenario_id", "scenario_name", "started_at",
                "completed_at", "passed", "summary", "event_sequence",
                "state_transitions", "alarms", "final_state"]:
        assert key in d, f"Missing key in report dict: {key!r}"
    assert "total_events" in d["summary"]
    assert "total_alarms" in d["summary"]


class TestScenarioA:
    def test_runs_successfully(self, engine):
        report = engine.run("A")
        assert_valid_report(report)
        assert report.passed is True

    def test_no_alarms(self, engine):
        report = engine.run("A")
        assert len(report.alarms) == 0

    def test_has_events(self, engine):
        report = engine.run("A")
        assert len(report.event_sequence) > 0

    def test_has_transitions(self, engine):
        report = engine.run("A")
        assert len(report.state_transitions) > 0

    def test_affects_samples(self, engine):
        report = engine.run("A")
        assert len(report.affected_samples) > 0

    def test_deterministic(self, engine):
        r1 = engine.run("A", seed=42)
        r2 = engine.run("A", seed=42)
        assert len(r1.event_sequence) == len(r2.event_sequence)
        assert len(r1.state_transitions) == len(r2.state_transitions)


class TestScenarioB:
    def test_runs_successfully(self, engine):
        report = engine.run("B")
        assert_valid_report(report)

    def test_creates_alarm(self, engine):
        report = engine.run("B")
        assert len(report.alarms) >= 1

    def test_alarm_severity_is_alarm(self, engine):
        report = engine.run("B")
        alarms = [a for a in report.alarms if a["rule_id"] == "INC_TEMP_HIGH"]
        assert len(alarms) >= 1
        assert alarms[0]["severity"] == "ALARM"

    def test_transitions_to_error(self, engine):
        report = engine.run("B")
        error_transitions = [t for t in report.state_transitions if t["to"] == "ERROR"]
        assert len(error_transitions) >= 1

    def test_has_recovery_path(self, engine):
        report = engine.run("B")
        assert len(report.recovery_path) > 0

    def test_affects_samples(self, engine):
        report = engine.run("B")
        assert len(report.affected_samples) > 0

    def test_custom_temperature_param(self, engine):
        report = engine.run("B", params={"target_temperature": 45.0})
        assert_valid_report(report)
        assert len(report.alarms) >= 1


class TestScenarioC:
    def test_runs_successfully(self, engine):
        report = engine.run("C")
        assert_valid_report(report)

    def test_creates_critical_alarm(self, engine):
        report = engine.run("C")
        critical = [a for a in report.alarms if a["severity"] == "CRITICAL"]
        assert len(critical) >= 1

    def test_interlock_event_generated(self, engine):
        report = engine.run("C")
        event_types = [e["event_type"] for e in report.event_sequence]
        assert "TRANSFER_WINDOW_INTERLOCK_VIOLATED" in event_types

    def test_transitions_to_interlock_alarm(self, engine):
        report = engine.run("C")
        transitions = [t for t in report.state_transitions if t["to"] == "INTERLOCK_ALARM"]
        assert len(transitions) >= 1


class TestScenarioD:
    def test_runs_successfully(self, engine):
        report = engine.run("D")
        assert_valid_report(report)

    def test_creates_critical_alarm(self, engine):
        report = engine.run("D")
        critical = [a for a in report.alarms if a["severity"] == "CRITICAL"]
        assert len(critical) >= 1

    def test_transitions_to_error(self, engine):
        report = engine.run("D")
        error_transitions = [t for t in report.state_transitions if t["to"] == "ERROR"]
        assert len(error_transitions) >= 1

    def test_has_recovery_path(self, engine):
        report = engine.run("D")
        assert "MAINTENANCE" in report.recovery_path or "SAFE_STATE" in report.recovery_path


class TestScenarioE:
    def test_runs_successfully(self, engine):
        report = engine.run("E")
        assert_valid_report(report)

    def test_creates_critical_alarm(self, engine):
        report = engine.run("E")
        critical = [a for a in report.alarms if a["severity"] == "CRITICAL"]
        assert len(critical) >= 1

    def test_sensor_failure_event(self, engine):
        report = engine.run("E")
        event_types = [e["event_type"] for e in report.event_sequence]
        assert "SENSOR_FAILURE" in event_types


class TestScenarioF:
    def test_runs_successfully(self, engine):
        report = engine.run("F")
        assert_valid_report(report)

    def test_creates_alarm(self, engine):
        report = engine.run("F")
        assert len(report.alarms) >= 1

    def test_affects_samples(self, engine):
        report = engine.run("F")
        assert len(report.affected_samples) > 0

    def test_blocks_workflow(self, engine):
        report = engine.run("F")
        blocked = [i for i in report.workflow_impact if i.get("impact") == "WORKFLOW_BLOCKED"]
        assert len(blocked) > 0

    def test_custom_pressure_param(self, engine):
        report = engine.run("F", params={"target_pressure": -1.0})
        assert_valid_report(report)


class TestScenarioG:
    def test_runs_successfully(self, engine):
        report = engine.run("G")
        assert_valid_report(report)

    def test_creates_alarm(self, engine):
        report = engine.run("G")
        assert len(report.alarms) >= 1

    def test_has_recovery_path(self, engine):
        report = engine.run("G")
        assert len(report.recovery_path) > 0


class TestScenarioH:
    def test_runs_successfully(self, engine):
        report = engine.run("H")
        assert_valid_report(report)

    def test_creates_alarm(self, engine):
        report = engine.run("H")
        assert len(report.alarms) >= 1

    def test_blocks_workflow(self, engine):
        report = engine.run("H")
        assert len(report.workflow_impact) > 0


class TestScenarioI:
    def test_runs_successfully(self, engine):
        report = engine.run("I")
        assert_valid_report(report)

    def test_no_active_alarms_after_recovery(self, engine):
        report = engine.run("I")
        assert report.final_state.get("alarms", 0) == 0

    def test_has_recovery_path(self, engine):
        report = engine.run("I")
        assert len(report.recovery_path) > 0

    def test_passed_is_true(self, engine):
        report = engine.run("I")
        assert report.passed is True


class TestUnknownScenario:
    def test_unknown_scenario_handled(self, engine):
        report = engine.run("Z")
        assert report.scenario_id == "Z"
        assert report.passed is False
        d = report.to_dict()
        assert d["run_id"]


class TestAllScenariosRegistered:
    def test_all_nine_scenarios_defined(self, engine):
        assert set(engine.SCENARIOS.keys()) == {"A", "B", "C", "D", "E", "F", "G", "H", "I"}

    def test_all_scenarios_runnable(self, engine):
        for scenario_id in engine.SCENARIOS:
            report = engine.run(scenario_id)
            assert report.completed_at is not None, f"Scenario {scenario_id} did not complete"
