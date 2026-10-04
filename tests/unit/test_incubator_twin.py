
"""
Unit Tests — Incubator Digital Twin
Tests: asset creation, state transitions, invalid transitions, event generation
"""
import pytest
from twin.entities.incubator import IncubatorTwin, VALID_TRANSITIONS


@pytest.fixture
def incubator():
    return IncubatorTwin(
        asset_id="INC-TEST-01",
        name="Test Incubator",
        room_id="R-CULTURE",
        setpoint_temperature=37.0,
    )


class TestIncubatorCreation:
    def test_initial_state(self, incubator):
        assert incubator.asset_id == "INC-TEST-01"
        assert incubator.status == "IDLE"
        assert incubator.asset_type == "incubator"

    def test_initial_temperature_none(self, incubator):
        assert incubator.temperature is None

    def test_room_assigned(self, incubator):
        assert incubator.room_id == "R-CULTURE"


class TestIncubatorStateTransitions:
    def test_idle_to_loaded(self, incubator):
        event = incubator.transition("LOADED")
        assert incubator.status == "LOADED"
        assert event.event_type == "INCUBATOR_LOADED"
        assert event.severity == "INFO"

    def test_loaded_to_incubating(self, incubator):
        incubator.transition("LOADED")
        event = incubator.transition("INCUBATING")
        assert incubator.status == "INCUBATING"
        assert event.event_type == "INCUBATOR_INCUBATION_STARTED"

    def test_incubating_to_completed(self, incubator):
        incubator.transition("LOADED")
        incubator.transition("INCUBATING")
        event = incubator.transition("COMPLETED")
        assert incubator.status == "COMPLETED"
        assert event.event_type == "INCUBATOR_INCUBATION_COMPLETED"

    def test_completed_to_released(self, incubator):
        incubator.transition("LOADED")
        incubator.transition("INCUBATING")
        incubator.transition("COMPLETED")
        event = incubator.transition("RELEASED")
        assert incubator.status == "RELEASED"

    def test_released_to_idle(self, incubator):
        incubator.transition("LOADED")
        incubator.transition("INCUBATING")
        incubator.transition("COMPLETED")
        incubator.transition("RELEASED")
        event = incubator.transition("IDLE")
        assert incubator.status == "IDLE"

    def test_incubating_to_error(self, incubator):
        incubator.transition("LOADED")
        incubator.transition("INCUBATING")
        event = incubator.transition("ERROR")
        assert incubator.status == "ERROR"
        assert event.severity == "ALARM"
        assert event.event_type == "INCUBATOR_TEMPERATURE_EXCURSION"

    def test_error_to_safe_state(self, incubator):
        incubator.transition("LOADED")
        incubator.transition("INCUBATING")
        incubator.transition("ERROR")
        event = incubator.transition("SAFE_STATE")
        assert incubator.status == "SAFE_STATE"
        assert event.severity == "WARNING"


class TestIncubatorInvalidTransitions:
    def test_idle_to_incubating_invalid(self, incubator):
        with pytest.raises(ValueError, match="Invalid transition"):
            incubator.transition("INCUBATING")

    def test_idle_to_completed_invalid(self, incubator):
        with pytest.raises(ValueError, match="Invalid transition"):
            incubator.transition("COMPLETED")

    def test_loaded_to_released_invalid(self, incubator):
        incubator.transition("LOADED")
        with pytest.raises(ValueError, match="Invalid transition"):
            incubator.transition("RELEASED")

    def test_completed_to_incubating_invalid(self, incubator):
        incubator.transition("LOADED")
        incubator.transition("INCUBATING")
        incubator.transition("COMPLETED")
        with pytest.raises(ValueError, match="Invalid transition"):
            incubator.transition("INCUBATING")


class TestIncubatorEventGeneration:
    def test_event_has_required_fields(self, incubator):
        event = incubator.transition("LOADED")
        assert event.event_id
        assert event.timestamp
        assert event.event_type
        assert event.source
        assert event.asset_id == "INC-TEST-01"
        assert event.correlation_id

    def test_event_records_previous_state(self, incubator):
        event = incubator.transition("LOADED")
        assert event.previous_state == {"status": "IDLE"}
        assert event.new_state == {"status": "LOADED"}

    def test_telemetry_update_generates_event(self, incubator):
        event = incubator.update_telemetry({"temperature": 37.2, "humidity": 60.5})
        assert event.event_type == "INCUBATOR_TEMPERATURE_CHANGED"
        assert incubator.temperature == 37.2
        assert incubator.humidity == 60.5

    def test_summary_includes_temperature(self, incubator):
        incubator.update_telemetry({"temperature": 37.5})
        summary = incubator.get_summary()
        assert summary["temperature"] == 37.5
        assert summary["asset_id"] == "INC-TEST-01"


class TestValidTransitionTable:
    def test_all_states_have_transitions(self):
        states = ["IDLE", "LOADED", "INCUBATING", "COMPLETED", "RELEASED", "ERROR", "SAFE_STATE"]
        for state in states:
            assert state in VALID_TRANSITIONS, f"State {state} missing from transition table"

    def test_no_self_transitions(self):
        for state, targets in VALID_TRANSITIONS.items():
            assert state not in targets, f"Self-transition detected for {state}"

