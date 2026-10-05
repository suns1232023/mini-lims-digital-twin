
"""
Unit Tests — State Machine Definitions
Tests: valid transitions, invalid transitions, reachability, error paths.
All tests validate actual system behavior, not mocks.
"""
import pytest
import sys
from pathlib import Path

# Ensure root is in path for clean runner
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from twin.states.machines import StateMachine, StateMachineRegistry


INCUBATOR_DEF = {
    "states": ["IDLE", "LOADED", "INCUBATING", "COMPLETED", "RELEASED", "ERROR", "SAFE_STATE"],
    "initial": "IDLE",
    "error_states": ["ERROR", "SAFE_STATE"],
    "transitions": [
        {"from": "IDLE",       "to": "LOADED",     "event": "INCUBATOR_LOADED"},
        {"from": "LOADED",     "to": "INCUBATING", "event": "INCUBATOR_INCUBATION_STARTED"},
        {"from": "LOADED",     "to": "IDLE",       "event": "INCUBATOR_RESET"},
        {"from": "INCUBATING", "to": "COMPLETED",  "event": "INCUBATOR_INCUBATION_COMPLETED"},
        {"from": "INCUBATING", "to": "ERROR",      "event": "INCUBATOR_TEMPERATURE_EXCURSION"},
        {"from": "COMPLETED",  "to": "RELEASED",   "event": "INCUBATOR_RELEASED"},
        {"from": "RELEASED",   "to": "IDLE",       "event": "INCUBATOR_RESET"},
        {"from": "ERROR",      "to": "SAFE_STATE", "event": "INCUBATOR_ALARM_ACKNOWLEDGED"},
        {"from": "SAFE_STATE", "to": "IDLE",       "event": "INCUBATOR_RECOVERED"},
    ],
}

AUTOCLAVE_DEF = {
    "states": ["IDLE", "LOADING", "RUNNING", "COOLING", "COMPLETED", "RELEASED",
               "ERROR", "SAFE_STATE", "MAINTENANCE", "VALIDATION"],
    "initial": "IDLE",
    "error_states": ["ERROR", "SAFE_STATE", "MAINTENANCE", "VALIDATION"],
    "transitions": [
        {"from": "IDLE",        "to": "LOADING",     "event": "AUTOCLAVE_LOADING_STARTED"},
        {"from": "LOADING",     "to": "RUNNING",     "event": "AUTOCLAVE_STARTED"},
        {"from": "LOADING",     "to": "IDLE",        "event": "AUTOCLAVE_RESET"},
        {"from": "RUNNING",     "to": "COOLING",     "event": "AUTOCLAVE_COOLING_STARTED"},
        {"from": "RUNNING",     "to": "ERROR",       "event": "AUTOCLAVE_FAILED"},
        {"from": "COOLING",     "to": "COMPLETED",   "event": "AUTOCLAVE_COMPLETED"},
        {"from": "COMPLETED",   "to": "RELEASED",    "event": "AUTOCLAVE_RELEASED"},
        {"from": "RELEASED",    "to": "IDLE",        "event": "AUTOCLAVE_RESET"},
        {"from": "ERROR",       "to": "SAFE_STATE",  "event": "AUTOCLAVE_SAFE_STATE_ENTERED"},
        {"from": "SAFE_STATE",  "to": "MAINTENANCE", "event": "AUTOCLAVE_MAINTENANCE_STARTED"},
        {"from": "MAINTENANCE", "to": "VALIDATION",  "event": "AUTOCLAVE_VALIDATION_STARTED"},
        {"from": "VALIDATION",  "to": "RELEASED",    "event": "AUTOCLAVE_VALIDATION_PASSED"},
    ],
}

PASS_BOX_DEF = {
    "states": ["IDLE", "LOCKED", "UV_DISINFECTING", "OPEN", "TRANSFERRING", "CLOSED", "INTERLOCK_ALARM"],
    "initial": "IDLE",
    "error_states": ["INTERLOCK_ALARM"],
    "transitions": [
        {"from": "IDLE",            "to": "LOCKED",          "event": "TRANSFER_WINDOW_LOCKED"},
        {"from": "LOCKED",          "to": "UV_DISINFECTING", "event": "TRANSFER_WINDOW_UV_STARTED"},
        {"from": "LOCKED",          "to": "IDLE",            "event": "TRANSFER_WINDOW_RESET"},
        {"from": "UV_DISINFECTING", "to": "OPEN",            "event": "TRANSFER_WINDOW_OPENED"},
        {"from": "OPEN",            "to": "TRANSFERRING",    "event": "SAMPLE_MOVED"},
        {"from": "OPEN",            "to": "INTERLOCK_ALARM", "event": "TRANSFER_WINDOW_INTERLOCK_VIOLATED"},
        {"from": "TRANSFERRING",    "to": "CLOSED",          "event": "TRANSFER_WINDOW_CLOSED"},
        {"from": "CLOSED",          "to": "IDLE",            "event": "TRANSFER_WINDOW_RESET"},
        {"from": "INTERLOCK_ALARM", "to": "IDLE",            "event": "ALARM_ACKNOWLEDGED"},
    ],
}


@pytest.fixture
def incubator_sm():
    return StateMachine("incubator", INCUBATOR_DEF)


@pytest.fixture
def autoclave_sm():
    return StateMachine("autoclave", AUTOCLAVE_DEF)


@pytest.fixture
def pass_box_sm():
    return StateMachine("pass_box", PASS_BOX_DEF)


class TestIncubatorStateMachine:
    def test_initial_state(self, incubator_sm):
        assert incubator_sm.initial == "IDLE"

    def test_valid_transition_idle_to_loaded(self, incubator_sm):
        event = incubator_sm.validate_transition("IDLE", "LOADED")
        assert event == "INCUBATOR_LOADED"

    def test_valid_transition_loaded_to_incubating(self, incubator_sm):
        event = incubator_sm.validate_transition("LOADED", "INCUBATING")
        assert event == "INCUBATOR_INCUBATION_STARTED"

    def test_valid_transition_incubating_to_error(self, incubator_sm):
        event = incubator_sm.validate_transition("INCUBATING", "ERROR")
        assert event == "INCUBATOR_TEMPERATURE_EXCURSION"

    def test_valid_transition_error_to_safe_state(self, incubator_sm):
        event = incubator_sm.validate_transition("ERROR", "SAFE_STATE")
        assert event == "INCUBATOR_ALARM_ACKNOWLEDGED"

    def test_invalid_transition_idle_to_incubating(self, incubator_sm):
        with pytest.raises(ValueError, match="Invalid transition"):
            incubator_sm.validate_transition("IDLE", "INCUBATING")

    def test_invalid_transition_idle_to_completed(self, incubator_sm):
        with pytest.raises(ValueError, match="Invalid transition"):
            incubator_sm.validate_transition("IDLE", "COMPLETED")

    def test_invalid_transition_loaded_to_released(self, incubator_sm):
        with pytest.raises(ValueError, match="Invalid transition"):
            incubator_sm.validate_transition("LOADED", "RELEASED")

    def test_can_transition_true(self, incubator_sm):
        assert incubator_sm.can_transition("IDLE", "LOADED") is True

    def test_can_transition_false(self, incubator_sm):
        assert incubator_sm.can_transition("IDLE", "COMPLETED") is False

    def test_error_states_identified(self, incubator_sm):
        assert incubator_sm.is_error_state("ERROR") is True
        assert incubator_sm.is_error_state("SAFE_STATE") is True
        assert incubator_sm.is_error_state("IDLE") is False

    def test_has_error_transitions(self, incubator_sm):
        assert incubator_sm.has_error_transitions() is True

    def test_all_states_reachable(self, incubator_sm):
        unreachable = incubator_sm.get_unreachable_states()
        assert unreachable == [], f"Unreachable states found: {unreachable}"

    def test_allowed_transitions_from_idle(self, incubator_sm):
        allowed = incubator_sm.get_allowed_transitions("IDLE")
        assert "LOADED" in allowed

    def test_all_states_present(self, incubator_sm):
        states = incubator_sm.get_all_states()
        assert "IDLE" in states
        assert "ERROR" in states
        assert "SAFE_STATE" in states


class TestAutoclaveStateMachine:
    def test_initial_state(self, autoclave_sm):
        assert autoclave_sm.initial == "IDLE"

    def test_normal_path(self, autoclave_sm):
        path = ["IDLE", "LOADING", "RUNNING", "COOLING", "COMPLETED", "RELEASED", "IDLE"]
        for i in range(len(path) - 1):
            event = autoclave_sm.validate_transition(path[i], path[i + 1])
            assert event  # event type returned

    def test_failure_path(self, autoclave_sm):
        path = ["RUNNING", "ERROR", "SAFE_STATE", "MAINTENANCE", "VALIDATION", "RELEASED"]
        for i in range(len(path) - 1):
            event = autoclave_sm.validate_transition(path[i], path[i + 1])
            assert event

    def test_invalid_skip_transition(self, autoclave_sm):
        with pytest.raises(ValueError):
            autoclave_sm.validate_transition("IDLE", "RUNNING")

    def test_error_states(self, autoclave_sm):
        for state in ["ERROR", "SAFE_STATE", "MAINTENANCE", "VALIDATION"]:
            assert autoclave_sm.is_error_state(state) is True


class TestPassBoxStateMachine:
    def test_interlock_alarm_reachable(self, pass_box_sm):
        event = pass_box_sm.validate_transition("OPEN", "INTERLOCK_ALARM")
        assert event == "TRANSFER_WINDOW_INTERLOCK_VIOLATED"

    def test_interlock_alarm_is_error_state(self, pass_box_sm):
        assert pass_box_sm.is_error_state("INTERLOCK_ALARM") is True

    def test_recovery_from_interlock(self, pass_box_sm):
        event = pass_box_sm.validate_transition("INTERLOCK_ALARM", "IDLE")
        assert event == "ALARM_ACKNOWLEDGED"

    def test_normal_transfer_path(self, pass_box_sm):
        path = ["IDLE", "LOCKED", "UV_DISINFECTING", "OPEN", "TRANSFERRING", "CLOSED", "IDLE"]
        for i in range(len(path) - 1):
            event = pass_box_sm.validate_transition(path[i], path[i + 1])
            assert event

