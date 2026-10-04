
"""
Rules Engine — Declarative rule evaluation from rules.yaml.
Rules are testable independently of UI and business logic.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from twin.entities.base import EventRecord


class RuleViolation:
    def __init__(self, rule_id: str, asset_id: str, message: str, severity: str, actions: List[str]):
        self.rule_id = rule_id
        self.asset_id = asset_id
        self.message = message
        self.severity = severity
        self.actions = actions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "asset_id": self.asset_id,
            "message": self.message,
            "severity": self.severity,
            "actions": self.actions,
        }


class RulesEngine:
    """
    Evaluates declarative rules from rules.yaml against asset state.
    Rules are independent of UI — fully testable in isolation.
    """

    def __init__(self, config_path: str = "config/rules.yaml"):
        self._rules: List[Dict[str, Any]] = []
        self._load_rules(Path(config_path))

    def _load_rules(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as f:
            config = yaml.safe_load(f)
        self._rules = config.get("rules", [])

    def evaluate_asset(
        self,
        asset_id: str,
        asset_type: str,
        room_id: Optional[str],
        state: Dict[str, Any],
        thresholds: Dict[str, Any],
    ) -> List[RuleViolation]:
        """Evaluate all applicable rules for an asset. Returns list of violations."""
        violations = []
        for rule in self._rules:
            # Check asset type filter
            asset_types = rule.get("asset_types", [])
            if asset_types and asset_type not in asset_types:
                continue
            # Check room filter
            rooms = rule.get("rooms", [])
            if rooms and room_id not in rooms:
                continue
            # Evaluate condition
            try:
                violation = self._evaluate_condition(
                    rule=rule,
                    asset_id=asset_id,
                    state=state,
                    thresholds=thresholds,
                )
                if violation:
                    violations.append(violation)
            except Exception as e:
                print(f"[RulesEngine] Error evaluating rule {rule.get('rule_id')}: {e}")
        return violations

    def _evaluate_condition(
        self,
        rule: Dict[str, Any],
        asset_id: str,
        state: Dict[str, Any],
        thresholds: Dict[str, Any],
    ) -> Optional[RuleViolation]:
        """Evaluate a single rule condition against asset state."""
        condition = rule.get("condition", "")
        # Build evaluation context
        ctx = {**state, "thresholds": thresholds}
        # Simple threshold evaluations
        result = self._eval_simple(condition, ctx)
        if result:
            msg = rule.get("message", f"Rule {rule['rule_id']} violated for {asset_id}")
            msg = msg.format(asset_id=asset_id, **{k: v for k, v in state.items() if isinstance(v, (int, float, str))})
            return RuleViolation(
                rule_id=rule["rule_id"],
                asset_id=asset_id,
                message=msg,
                severity=rule.get("severity", "WARNING"),
                actions=rule.get("actions", []),
            )
        return None

    def _eval_simple(self, condition: str, ctx: Dict[str, Any]) -> bool:
        """
        Safe condition evaluator.
        Supports: temperature > X, pressure < X, status == 'Y', door == 'open', etc.
        """
        try:
            # Replace threshold references
            condition = self._resolve_thresholds(condition, ctx.get("thresholds", {}))
            # Safe eval with restricted context
            safe_ctx = {k: v for k, v in ctx.items() if k != "thresholds"}
            return bool(eval(condition, {"__builtins__": {}}, safe_ctx))  # noqa: S307
        except Exception:
            return False

    def _resolve_thresholds(self, condition: str, thresholds: Dict[str, Any]) -> str:
        """Replace threshold references like thresholds.temperature.max with actual values."""
        import re
        pattern = r"thresholds\.(\w+)\.(\w+)"
        def replacer(m):
            metric, key = m.group(1), m.group(2)
            val = thresholds.get(metric, {}).get(key)
            return str(val) if val is not None else "None"
        return re.sub(pattern, replacer, condition)

    def get_rules(self) -> List[Dict[str, Any]]:
        return self._rules

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self._rules if r.get("rule_id") == rule_id), None)

