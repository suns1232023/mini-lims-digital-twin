
"""
Unit Tests — Workflow Engine
Tests: workflow creation, valid transitions, invalid transitions, blocking, audit trail
"""
import pytest
import tempfile
import yaml
import os
from backend.core.workflow_engine import WorkflowEngine, WorkflowInstance


SAMPLE_WORKFLOWS = {
    "workflows": [
        {
            "id": "sample_lifecycle",
            "name": "Sample Lifecycle",
            "entity_type": "sample",
            "initial_state": "REGISTERED",
            "states": ["REGISTERED", "RECEIVED", "PREPARED", "TESTING", "INCUBATING", "APPROVED", "ARCHIVED", "REJECTED"],
            "transitions": [
                {"from": "REGISTERED", "to": "RECEIVED",  "event": "SAMPLE_RECEIVED",  "timeout_hours": 24},
                {"from": "RECEIVED",   "to": "PREPARED",  "event": "SAMPLE_PREPARED",  "timeout_hours": 4},
                {"from": "PREPARED",   "to": "TESTING",   "event": "SAMPLE_TESTING",   "timeout_hours": 2},
                {"from": "TESTING",    "to": "INCUBATING","event": "SAMPLE_INCUBATING","timeout_hours": 1},
                {"from": "INCUBATING", "to": "APPROVED",  "event": "SAMPLE_APPROVED",  "timeout_hours": 8},
                {"from": "APPROVED",   "to": "ARCHIVED",  "event": "SAMPLE_ARCHIVED",  "timeout_hours": 720},
                {"from": "TESTING",    "to": "REJECTED",  "event": "SAMPLE_REJECTED",  "timeout_hours": 8},
            ],
        }
    ]
}


@pytest.fixture
def workflow_engine():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_WORKFLOWS, f)
        path = f.name
    engine = WorkflowEngine(config_path=path)
    yield engine
    os.unlink(path)


@pytest.fixture
def sample_instance(workflow_engine):
    return workflow_engine.create_instance("sample_lifecycle", "SMP-0001", "sample")


class TestWorkflowCreation:
    def test_create_instance(self, workflow_engine):
        inst = workflow_engine.create_instance("sample_lifecycle", "SMP-0001")
        assert inst.instance_id
        assert inst.current_state == "REGISTERED"
        assert inst.entity_id == "SMP-0001"

    def test_unknown_workflow_raises(self, workflow_engine):
        with pytest.raises(KeyError):
            workflow_engine.create_instance("nonexistent_workflow", "SMP-0001")

    def test_get_definitions(self, workflow_engine):
        defs = workflow_engine.get_definitions()
        assert len(defs) == 1
        assert defs[0]["id"] == "sample_lifecycle"


class TestWorkflowTransitions:
    def test_registered_to_received(self, sample_instance):
        record = sample_instance.transition("RECEIVED", actor="operator-01")
        assert sample_instance.current_state == "RECEIVED"
        assert record["event"] == "SAMPLE_RECEIVED"
        assert record["actor"] == "operator-01"

    def test_full_happy_path(self, sample_instance):
        for state in ["RECEIVED", "PREPARED", "TESTING", "INCUBATING", "APPROVED", "ARCHIVED"]:
            sample_instance.transition(state)
        assert sample_instance.current_state == "ARCHIVED"
        assert sample_instance.completed_at is not None

    def test_rejection_path(self, sample_instance):
        sample_instance.transition("RECEIVED")
        sample_instance.transition("PREPARED")
        sample_instance.transition("TESTING")
        sample_instance.transition("REJECTED")
        assert sample_instance.current_state == "REJECTED"

    def test_history_recorded(self, sample_instance):
        sample_instance.transition("RECEIVED")
        sample_instance.transition("PREPARED")
        assert len(sample_instance.history) == 2
        assert sample_instance.history[0]["from"] == "REGISTERED"
        assert sample_instance.history[0]["to"] == "RECEIVED"


class TestInvalidTransitions:
    def test_skip_state_invalid(self, sample_instance):
        with pytest.raises(ValueError, match="Invalid transition|No transition"):
            sample_instance.transition("TESTING")  # Skip RECEIVED and PREPARED

    def test_backward_transition_invalid(self, sample_instance):
        sample_instance.transition("RECEIVED")
        with pytest.raises(ValueError):
            sample_instance.transition("REGISTERED")

    def test_nonexistent_state_invalid(self, sample_instance):
        with pytest.raises(ValueError):
            sample_instance.transition("NONEXISTENT_STATE")


class TestWorkflowBlocking:
    def test_block_prevents_transition(self, sample_instance):
        sample_instance.block("equipment_unavailable")
        assert sample_instance.blocked is True
        with pytest.raises(ValueError, match="blocked"):
            sample_instance.transition("RECEIVED")

    def test_release_allows_transition(self, sample_instance):
        sample_instance.block("equipment_unavailable")
        sample_instance.release()
        assert sample_instance.blocked is False
        record = sample_instance.transition("RECEIVED")
        assert record["to"] == "RECEIVED"


class TestWorkflowAuditTrail:
    def test_to_dict_complete(self, sample_instance):
        sample_instance.transition("RECEIVED")
        d = sample_instance.to_dict()
        assert d["instance_id"]
        assert d["workflow_id"] == "sample_lifecycle"
        assert d["entity_id"] == "SMP-0001"
        assert d["current_state"] == "RECEIVED"
        assert len(d["history"]) == 1

    def test_timestamps_recorded(self, sample_instance):
        assert sample_instance.started_at is not None
        assert sample_instance.completed_at is None
        for state in ["RECEIVED", "PREPARED", "TESTING", "INCUBATING", "APPROVED", "ARCHIVED"]:
            sample_instance.transition(state)
        assert sample_instance.completed_at is not None

