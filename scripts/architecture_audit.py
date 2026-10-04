
"""
Architecture Audit Script — Mini-LIMS Digital Twin Platform
Evaluates: schema consistency, workflow transitions, orphan assets,
undefined states, missing tests, API contracts, configuration completeness.
Produces: architecture-health.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)

BASE = Path(__file__).parent.parent


def load_yaml(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def check_config_files() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    required = ["assets.yaml", "rooms.yaml", "workflows.yaml", "rules.yaml", "thresholds.yaml", "sensors.yaml"]
    for fname in required:
        p = BASE / "config" / fname
        if not p.exists():
            issues.append(f"Missing config file: config/{fname}")
        else:
            try:
                data = load_yaml(p)
                if not data:
                    warnings.append(f"Empty config file: config/{fname}")
            except Exception as e:
                issues.append(f"Invalid YAML in config/{fname}: {e}")
    return issues, warnings


def check_asset_room_references() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    assets_cfg = load_yaml(BASE / "config" / "assets.yaml")
    rooms_cfg = load_yaml(BASE / "config" / "rooms.yaml")
    room_ids = {r["id"] for r in rooms_cfg.get("rooms", [])}
    for asset in assets_cfg.get("assets", []):
        room = asset.get("room")
        if room and room not in room_ids:
            issues.append(f"Asset {asset['id']} references undefined room: {room}")
        if not asset.get("id"):
            issues.append(f"Asset missing 'id' field: {asset}")
        if not asset.get("type"):
            issues.append(f"Asset {asset.get('id', '?')} missing 'type' field")
    return issues, warnings


def check_workflow_transitions() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    wf_cfg = load_yaml(BASE / "config" / "workflows.yaml")
    for wf in wf_cfg.get("workflows", []):
        wf_id = wf.get("id", "?")
        states = set(wf.get("states", []))
        initial = wf.get("initial_state")
        if initial not in states:
            issues.append(f"Workflow {wf_id}: initial_state '{initial}' not in states list")
        reachable = {initial}
        for t in wf.get("transitions", []):
            from_s, to_s = t.get("from"), t.get("to")
            if from_s not in states:
                issues.append(f"Workflow {wf_id}: transition from undefined state '{from_s}'")
            if to_s not in states:
                issues.append(f"Workflow {wf_id}: transition to undefined state '{to_s}'")
            if from_s in reachable:
                reachable.add(to_s)
        unreachable = states - reachable
        for s in unreachable:
            warnings.append(f"Workflow {wf_id}: state '{s}' may be unreachable from initial state")
        # Check for missing error transitions
        has_error = any(t.get("to") == "ERROR" for t in wf.get("transitions", []))
        if not has_error and wf_id not in ("pass_box_transfer",):
            warnings.append(f"Workflow {wf_id}: no ERROR transition defined (missing failure mode)")
    return issues, warnings


def check_rules_completeness() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    rules_cfg = load_yaml(BASE / "config" / "rules.yaml")
    rule_ids = set()
    for rule in rules_cfg.get("rules", []):
        rid = rule.get("rule_id")
        if not rid:
            issues.append("Rule missing 'rule_id' field")
            continue
        if rid in rule_ids:
            issues.append(f"Duplicate rule_id: {rid}")
        rule_ids.add(rid)
        if not rule.get("condition"):
            issues.append(f"Rule {rid}: missing 'condition'")
        if not rule.get("actions"):
            warnings.append(f"Rule {rid}: no actions defined")
        if not rule.get("severity"):
            warnings.append(f"Rule {rid}: no severity defined")
    return issues, warnings


def check_test_coverage() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    test_dirs = {
        "unit": BASE / "tests" / "unit",
        "integration": BASE / "tests" / "integration",
        "simulation": BASE / "tests" / "simulation",
        "regression": BASE / "tests" / "regression",
    }
    for name, path in test_dirs.items():
        if not path.exists():
            warnings.append(f"Test directory missing: tests/{name}/")
            continue
        test_files = list(path.glob("test_*.py"))
        if not test_files:
            warnings.append(f"No test files found in tests/{name}/")
    # Check for specific required test files
    required_tests = [
        "tests/unit/test_incubator_twin.py",
        "tests/unit/test_rules_engine.py",
        "tests/unit/test_workflow_engine.py",
        "tests/simulation/test_scenarios.py",
    ]
    for t in required_tests:
        if not (BASE / t).exists():
            warnings.append(f"Missing required test file: {t}")
    return issues, warnings


def check_api_structure() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    api_main = BASE / "backend" / "api" / "v1" / "main.py"
    if not api_main.exists():
        issues.append("Missing FastAPI main: backend/api/v1/main.py")
    else:
        content = api_main.read_text()
        required_endpoints = ["/api/v1/assets", "/api/v1/samples", "/api/v1/simulation/run", "/api/v1/architecture/health"]
        for ep in required_endpoints:
            if ep not in content:
                warnings.append(f"API endpoint may be missing: {ep}")
    return issues, warnings


def check_twin_core() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    required_files = [
        "twin/entities/base.py",
        "twin/entities/incubator.py",
        "twin/entities/autoclave.py",
        "twin/entities/pass_box.py",
        "twin/registry/asset_registry.py",
        "backend/core/event_engine.py",
        "backend/core/rules_engine.py",
        "backend/core/workflow_engine.py",
        "simulation/scenarios/scenario_engine.py",
    ]
    for f in required_files:
        if not (BASE / f).exists():
            issues.append(f"Missing core file: {f}")
    return issues, warnings


def check_ci_workflows() -> Tuple[List[str], List[str]]:
    issues, warnings = [], []
    required_workflows = ["test.yml", "lint.yml", "architecture-check.yml", "simulation.yml"]
    ci_dir = BASE / ".github" / "workflows"
    if not ci_dir.exists():
        issues.append("Missing .github/workflows/ directory")
        return issues, warnings
    for wf in required_workflows:
        if not (ci_dir / wf).exists():
            warnings.append(f"Missing CI workflow: .github/workflows/{wf}")
    return issues, warnings


def compute_score(all_issues: List[str], all_warnings: List[str], critical_count: int) -> int:
    score = 100
    score -= len(all_issues) * 5
    score -= len(all_warnings) * 2
    score -= critical_count * 15
    return max(0, min(100, score))


def run_audit() -> Dict[str, Any]:
    all_issues: List[str] = []
    all_warnings: List[str] = []
    critical_count = 0
    checks = [
        ("Config Files", check_config_files),
        ("Asset-Room References", check_asset_room_references),
        ("Workflow Transitions", check_workflow_transitions),
        ("Rules Completeness", check_rules_completeness),
        ("Test Coverage", check_test_coverage),
        ("API Structure", check_api_structure),
        ("Twin Core Files", check_twin_core),
        ("CI Workflows", check_ci_workflows),
    ]
    check_results = {}
    for name, fn in checks:
        try:
            issues, warnings = fn()
            all_issues.extend(issues)
            all_warnings.extend(warnings)
            check_results[name] = {"issues": issues, "warnings": warnings}
        except Exception as e:
            all_issues.append(f"Audit check '{name}' failed: {e}")
            check_results[name] = {"issues": [str(e)], "warnings": []}

    score = compute_score(all_issues, all_warnings, critical_count)
    health = {
        "architecture_score": score,
        "issues": len(all_issues),
        "warnings": len(all_warnings),
        "critical": critical_count,
        "checks": check_results,
        "all_issues": all_issues,
        "all_warnings": all_warnings,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    return health


if __name__ == "__main__":
    print("=" * 60)
    print("Mini-LIMS Architecture Audit")
    print("=" * 60)
    health = run_audit()
    out_path = BASE / "architecture-health.json"
    with open(out_path, "w") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)
    print(f"\nArchitecture Score : {health['architecture_score']}/100")
    print(f"Issues             : {health['issues']}")
    print(f"Warnings           : {health['warnings']}")
    print(f"Critical           : {health['critical']}")
    if health["all_issues"]:
        print("\n[ISSUES]")
        for i in health["all_issues"]:
            print(f"  ✗ {i}")
    if health["all_warnings"]:
        print("\n[WARNINGS]")
        for w in health["all_warnings"]:
            print(f"  ⚠ {w}")
    print(f"\nReport saved to: {out_path}")
    sys.exit(1 if health["critical"] > 0 else 0)

