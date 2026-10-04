
"""
Simulation Tests — All 9 Scenarios (A–I)
Every simulation scenario becomes a regression test.
"""
import pytest
from simulation.scenarios.scenario_engine import ScenarioEngine, SimulationReport


@pytest.fixture
def engine():
    return ScenarioEngine()


def _assert_report_valid(report: SimulationReport):
    """Common assertions for all simulation reports."""
    assert report.run_id
    assert report.scenario_id
    assert report.scenario_name
    assert report.started_at
    assert report.completed_at
    assert isinstance(report.event_sequence, list)
    assert isinstance(report.state_transitions, list)
    assert isinstance(report.alarms, list)
    assert isinstance(report.final_state, dict)


class TestScenarioA:
    def test_normal_operation_runs(self, engine):
        report = engine.run("A")
        _assert_report_valid(report)

    def test_normal_operation_no_alarms(self, engine):
        report = engine.run("A")
        assert len(report.alarms) == 0

    def test_normal_operation_has_events(self, engine):
        report = engine.run("A")
        assert len(report.event_sequence) > 0

    def test_normal_operation_has_transitions(self, engine):
        report = engine.run("A")
        assert len(report.state_transitions) > 0

    def test_normal_operation_affects_samples(self, engine):
        report = engine.run("A")
        assert len(report.affected_samples) > 0


class TestScenarioB:
    def test_temperature_excursion_runs(self, engine):
        report = engine.run("B")
        _assert_report_valid(report)

    def test_temperature_excursion_creates_alarm(self, engine):
        report = engine.run("B")
        assert len(report.alarms) >= 1
        alarm_ids = [a["rule_id"] for a in report.alarms]
        assert "INC_TEMP_HIGH" in alarm_ids

    def test_temperature_excursion_alarm_severity(self, engine):
        report = engine.run("B")
        alarms = [a for a in report.alarms if a["rule_id"] == "INC_TEMP_HIGH"]
        assert alarms[0]["severity"] == "ALARM"

    def test_temperature_excursion_transitions_to_error(self, engine):
        report = engine.run("B")
        transitions = [t for t in report.state_transitions if t["to"] == "ERROR"]
        assert len(transitions) >= 1

    def test_temperature_excursion_has_recovery_path(self, engine):
        report = engine.run("B")
        assert len(report.recovery_path) > 0

    def test_temperature_excursion_affects_samples(self, engine):
        report = engine.run("B")
        assert len(report.affected_samples) > 0

    def test_temperature_excursion_custom_params(self, engine):
        report = engine.run("B", params={"target_temperature": 45.0})
        _assert_report_valid(report)
        assert len(report.alarms) >= 1


class TestScenarioC:
    def test_interlock_violation_runs(self, engine):
        report = engine.run("C")
        _assert_report_valid(report)

    def test_interlock_violation_creates_critical_alarm(self, engine):
        report = engine.run("C")
        critical = [a for a in report.alarms if a["severity"] == "CRITICAL"]
        assert len(critical) >= 1

    def test_interlock_violation_event_type(self, engine):
        report = engine.run("C")
        event_types = [e["event_type"] for e in report.event_sequence]
        assert "TRANSFER_WINDOW_INTERLOCK_VIOLATED" in event_types

    def test_interlock_violation_transitions_to_alarm_state(self, engine):
        report = engine.run("C")
        transitions = [t for t in report.state_transitions if t["to"] == "INTERLOCK_ALARM"]
        assert len(transitions) >= 1


class TestScenarioD:
    def test_autoclave_failure_runs(self, engine):
        report = engine.run("D")
        _assert_report_valid(report)

    def test_autoclave_failure_creates_critical_alarm(self, engine):
        report = engine.run("D")
        critical = [a for a in report.alarms if a["severity"] == "CRITICAL"]
        assert len(critical) >= 1

    def test_autoclave_failure_transitions_to_error(self, engine):
        report = engine.run("D")
        transitions = [t for t in report.state_transitions if t["to"] == "ERROR"]
        assert len(transitions) >= 1

    def test_autoclave_failure_has_recovery_path(self, engine):
        report = engine.run("D")
        assert "MAINTENANCE" in report.recovery_path or "SAFE_STATE" in report.recovery_path


class TestScenarioE:
    def test_sensor_failure_runs(self, engine):
        report = engine.run("E")
        _assert_report_valid(report)

    def test_sensor_failure_creates_critical_alarm(self, engine):
        report = engine.run("E")
        critical = [a for a in report.alarms if a["severity"] == "CRITICAL"]
        assert len(critical) >= 1

    def test_sensor_failure_event_generated(self, engine):
        report = engine.run("E")
        event_types = [e["event_type"] for e in report.event_sequence]
        assert "SENSOR_FAILURE" in event_types


class TestScenarioF:
    def test_environmental_excursion_runs(self, engine):
        report = engine.run("F")
        _assert_report_valid(report)

    def test_environmental_excursion_creates_alarm(self, engine):
        report = engine.run("F")
        assert len(report.alarms) >= 1

    def test_environmental_excursion_affects_samples(self, engine):
        report = engine.run("F")
        assert len(report.affected_samples) > 0

    def test_environmental_excursion_blocks_workflow(self, engine):
        report = engine.run("F")
        impacts = [i for i in report.workflow_impact if i.get("impact") == "WORKFLOW_BLOCKED"]
        assert len(impacts) > 0


class TestScenarioG:
    def test_workflow_timeout_runs(self, engine):
        report = engine.run("G")
        _assert_report_valid(report)

    def test_workflow_timeout_creates_alarm(self, engine):
        report = engine.run("G")
        assert len(report.alarms) >= 1

    def test_workflow_timeout_has_recovery_path(self, engine):
        report = engine.run("G")
        assert len(report.recovery_path) > 0


class TestScenarioH:
    def test_equipment_unavailable_runs(self, engine):
        report = engine.run("H")
        _assert_report_valid(report)

    def test_equipment_unavailable_creates_alarm(self, engine):
        report = engine.run("H")
        assert len(report.alarms) >= 1

    def test_equipment_unavailable_blocks_workflow(self, engine):
        report = engine.run("H")
        assert len(report.workflow_impact) > 0


class TestScenarioI:
    def test_recovery_runs(self, engine):
        report = engine.run("I")
        _assert_report_valid(report)

    def test_recovery_has_no_active_alarms(self, engine):
        report = engine.run("I")
        assert report.final_state.get("alarms", 0) == 0

    def test_recovery_path_defined(self, engine):
        report = engine.run("I")
        assert len(report.recovery_path) > 0


class TestSimulationReport:
    def test_to_dict_complete(self, engine):
        report = engine.run("A")
        d = report.to_dict()
        assert "run_id" in d
        assert "scenario_id" in d
        assert "summary" in d
        assert "event_sequence" in d
        assert "state_transitions" in d
        assert "alarms" in d
        assert "final_state" in d

    def test_unknown_scenario_handled(self, engine):
        report = engine.run("Z")
        assert report.scenario_id == "Z"
        # Should not raise, should produce a report
        d = report.to_dict()
        assert d["run_id"]


