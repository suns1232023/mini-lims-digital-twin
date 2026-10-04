
"""
Unit Tests — Rules Engine
Tests: rule loading, condition evaluation, alarm generation, threshold resolution
"""
import pytest
import tempfile
import yaml
import os
from backend.core.rules_engine import RulesEngine, RuleViolation


SAMPLE_RULES = {
    "rules": [
        {
            "rule_id": "INC_TEMP_HIGH",
            "name": "Incubator Temperature High",
            "asset_types": ["incubator"],
            "condition": "temperature > 40",
            "severity": "ALARM",
            "actions": ["create_alarm", "mark_excursion"],
            "message": "Incubator {asset_id} temperature {temperature}°C exceeds limit",
        },
        {
            "rule_id": "ENV_PRESSURE_ALARM",
            "name": "Clean Room Pressure Alarm",
            "asset_types": ["environmental_sensor"],
            "rooms": ["R-STERILE"],
            "condition": "pressure > -5",
            "severity": "ALARM",
            "actions": ["create_alarm"],
            "message": "Room pressure out of range",
        },
        {
            "rule_id": "PB_INTERLOCK",
            "name": "Pass Box Interlock",
            "asset_types": ["pass_box"],
            "condition": "door_a == 'open' and door_b == 'open'",
            "severity": "CRITICAL",
            "actions": ["create_alarm", "lock_both_doors"],
            "message": "Interlock violation",
        },
    ]
}


@pytest.fixture
def rules_engine():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_RULES, f)
        path = f.name
    engine = RulesEngine(config_path=path)
    yield engine
    os.unlink(path)


class TestRulesEngineLoading:
    def test_loads_rules(self, rules_engine):
        rules = rules_engine.get_rules()
        assert len(rules) == 3

    def test_get_rule_by_id(self, rules_engine):
        rule = rules_engine.get_rule("INC_TEMP_HIGH")
        assert rule is not None
        assert rule["severity"] == "ALARM"

    def test_get_nonexistent_rule(self, rules_engine):
        assert rules_engine.get_rule("NONEXISTENT") is None


class TestRuleEvaluation:
    def test_temperature_alarm_triggered(self, rules_engine):
        violations = rules_engine.evaluate_asset(
            asset_id="INC-01",
            asset_type="incubator",
            room_id="R-CULTURE",
            state={"temperature": 41.0, "status": "INCUBATING"},
            thresholds={},
        )
        assert len(violations) == 1
        assert violations[0].rule_id == "INC_TEMP_HIGH"
        assert violations[0].severity == "ALARM"

    def test_temperature_normal_no_alarm(self, rules_engine):
        violations = rules_engine.evaluate_asset(
            asset_id="INC-01",
            asset_type="incubator",
            room_id="R-CULTURE",
            state={"temperature": 37.0, "status": "INCUBATING"},
            thresholds={},
        )
        assert len(violations) == 0

    def test_pressure_alarm_triggered_correct_room(self, rules_engine):
        violations = rules_engine.evaluate_asset(
            asset_id="ENV-STERILE",
            asset_type="environmental_sensor",
            room_id="R-STERILE",
            state={"pressure": -3.0},
            thresholds={},
        )
        assert len(violations) == 1
        assert violations[0].rule_id == "ENV_PRESSURE_ALARM"

    def test_pressure_alarm_not_triggered_wrong_room(self, rules_engine):
        violations = rules_engine.evaluate_asset(
            asset_id="ENV-OTHER",
            asset_type="environmental_sensor",
            room_id="R-CULTURE",
            state={"pressure": -3.0},
            thresholds={},
        )
        assert len(violations) == 0

    def test_interlock_violation_detected(self, rules_engine):
        violations = rules_engine.evaluate_asset(
            asset_id="PB-01",
            asset_type="pass_box",
            room_id="R-BUFFER-1",
            state={"door_a": "open", "door_b": "open"},
            thresholds={},
        )
        assert len(violations) == 1
        assert violations[0].rule_id == "PB_INTERLOCK"
        assert violations[0].severity == "CRITICAL"
        assert "lock_both_doors" in violations[0].actions

    def test_interlock_not_triggered_one_door(self, rules_engine):
        violations = rules_engine.evaluate_asset(
            asset_id="PB-01",
            asset_type="pass_box",
            room_id="R-BUFFER-1",
            state={"door_a": "open", "door_b": "closed"},
            thresholds={},
        )
        assert len(violations) == 0

    def test_wrong_asset_type_skipped(self, rules_engine):
        violations = rules_engine.evaluate_asset(
            asset_id="AC-01",
            asset_type="autoclave",
            room_id="R-STERILIZE",
            state={"temperature": 41.0},
            thresholds={},
        )
        # INC_TEMP_HIGH only applies to incubators
        assert all(v.rule_id != "INC_TEMP_HIGH" for v in violations)


class TestRuleViolation:
    def test_violation_to_dict(self):
        v = RuleViolation(
            rule_id="TEST_RULE",
            asset_id="INC-01",
            message="Test message",
            severity="ALARM",
            actions=["create_alarm"],
        )
        d = v.to_dict()
        assert d["rule_id"] == "TEST_RULE"
        assert d["severity"] == "ALARM"
        assert "create_alarm" in d["actions"]

