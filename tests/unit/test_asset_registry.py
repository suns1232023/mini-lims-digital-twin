
"""
Unit Tests — Asset Registry
Tests: asset creation from config, telemetry update, state transition, event generation.
"""
import pytest
import sys
import tempfile
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from twin.registry.asset_registry import AssetRegistry
from twin.entities.incubator import IncubatorTwin
from twin.entities.autoclave import AutoclaveTwin
from twin.entities.pass_box import PassBoxTwin


SAMPLE_ARCH = {
    "entities": [
        {
            "id": "INC-TEST",
            "name": "Test Incubator",
            "type": "incubator",
            "room": "R-TEST",
            "sensors": ["temperature", "humidity"],
            "thresholds": {"temperature": {"min": 35.0, "max": 39.0}},
        },
        {
            "id": "AC-TEST",
            "name": "Test Autoclave",
            "type": "autoclave",
            "room": "R-TEST",
            "sensors": ["temperature", "pressure"],
            "thresholds": {},
        },
        {
            "id": "PB-TEST",
            "name": "Test Pass Box",
            "type": "pass_box",
            "room": "R-BUFFER",
            "adjacent_room": "R-STERILE",
            "sensors": ["door_a", "door_b"],
            "thresholds": {},
        },
    ],
    "state_machines": {},
}


@pytest.fixture
def registry():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_ARCH, f)
        path = f.name
    reg = AssetRegistry(arch_path=path)
    yield reg
    Path(path).unlink(missing_ok=True)


class TestAssetRegistryCreation:
    def test_loads_all_entities(self, registry):
        assets = registry.get_all()
        assert len(assets) == 3

    def test_incubator_created_correctly(self, registry):
        asset = registry.get("INC-TEST")
        assert asset is not None
        assert isinstance(asset, IncubatorTwin)
        assert asset.asset_id == "INC-TEST"
        assert asset.room_id == "R-TEST"
        assert asset.status == "IDLE"

    def test_autoclave_created_correctly(self, registry):
        asset = registry.get("AC-TEST")
        assert asset is not None
        assert isinstance(asset, AutoclaveTwin)

    def test_pass_box_created_correctly(self, registry):
        asset = registry.get("PB-TEST")
        assert asset is not None
        assert isinstance(asset, PassBoxTwin)

    def test_get_nonexistent_returns_none(self, registry):
        assert registry.get("NONEXISTENT") is None

    def test_get_by_type(self, registry):
        incubators = registry.get_by_type("incubator")
        assert len(incubators) == 1
        assert incubators[0].asset_id == "INC-TEST"

    def test_get_by_room(self, registry):
        assets = registry.get_by_room("R-TEST")
        assert len(assets) == 2

    def test_asset_ids(self, registry):
        ids = registry.asset_ids()
        assert "INC-TEST" in ids
        assert "AC-TEST" in ids
        assert "PB-TEST" in ids


class TestTelemetryUpdate:
    def test_telemetry_updates_current_state(self, registry):
        event = registry.update_telemetry("INC-TEST", {"temperature": 37.5, "humidity": 60.0})
        assert event is not None
        asset = registry.get("INC-TEST")
        assert asset.current_state.get("temperature") == 37.5

    def test_telemetry_generates_event(self, registry):
        event = registry.update_telemetry("INC-TEST", {"temperature": 37.0})
        assert event.event_type == "INCUBATOR_TEMPERATURE_CHANGED"
        assert event.asset_id == "INC-TEST"

    def test_telemetry_nonexistent_asset_returns_none(self, registry):
        result = registry.update_telemetry("NONEXISTENT", {"temperature": 37.0})
        assert result is None

    def test_telemetry_updates_last_telemetry_at(self, registry):
        registry.update_telemetry("INC-TEST", {"temperature": 37.0})
        asset = registry.get("INC-TEST")
        assert asset.last_telemetry_at is not None


class TestStateTransition:
    def test_valid_transition_incubator(self, registry):
        event = registry.transition_state("INC-TEST", "LOADED", source="test")
        assert event.event_type == "INCUBATOR_LOADED"
        asset = registry.get("INC-TEST")
        assert asset.status == "LOADED"

    def test_invalid_transition_raises(self, registry):
        with pytest.raises(ValueError, match="Invalid transition"):
            registry.transition_state("INC-TEST", "INCUBATING")

    def test_transition_nonexistent_asset_raises(self, registry):
        with pytest.raises(KeyError):
            registry.transition_state("NONEXISTENT", "LOADED")

    def test_transition_event_logged(self, registry):
        registry.transition_state("INC-TEST", "LOADED")
        events = registry.get_events("INC-TEST")
        assert len(events) >= 1
        assert any(e.event_type == "INCUBATOR_LOADED" for e in events)


class TestSnapshot:
    def test_snapshot_structure(self, registry):
        snap = registry.snapshot()
        assert "ts" in snap
        assert "assets" in snap
        assert "event_count" in snap
        assert isinstance(snap["assets"], list)

    def test_snapshot_contains_all_assets(self, registry):
        snap = registry.snapshot()
        ids = [a["asset_id"] for a in snap["assets"]]
        assert "INC-TEST" in ids
        assert "AC-TEST" in ids
