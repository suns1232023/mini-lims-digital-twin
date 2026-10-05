
"""
Architecture Audit Script — Mini-LIMS Digital Twin Platform
Computes architecture health score dynamically from actual checks.
Score is NEVER hard-coded. Every point is earned or deducted from real checks.
Produces: architecture-health.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)

# Root is the directory containing this script's parent (scripts/../)
ROOT = Path(__file__).parent.parent


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_arch() -> dict:
    return load_yaml(ROOT / "architecture.yaml")


# ── Individual Checks ─────────────────────────────────────────────────────────

def check_architecture_yaml() -> tuple[list[str], list[str], int]:
    """Check architecture.yaml exists and has required sections."""
    issues, warnings = [], []
    score = 0
    arch_path = ROOT / "architecture.yaml"
    if not arch_path.exists():
        issues.append("CRITICAL: architecture.yaml not found — architecture contract missing")
        return issues, warnings, score
    arch = load_arch()
    required_sections = ["version", "project", "domains", "entities", "state_machines",
                         "simulation_scenarios", "quality_gates", "constraints"]
    for section in required_sections:
        if section not in arch:
            warnings.append(f"architecture.yaml missing section: {section!r}")
        else:
            score += 1
    return issues, warnings, score


def check_domain_files() -> tuple[list[str], list[str], int]:
    """Check all required domain files exist."""
    issues, warnings = [], []
    score = 0
    arch = load_arch()
    for domain in arch.get("domains", []):
        domain_id = domain.get("id", "?")
        for required_file in domain.get("required_files", []):
            path = ROOT / required_file
            if path.exists():
                score += 1
            else:
                issues.append(f"Missing required file [{domain_id}]: {required_file}")
    return issues, warnings, score


def check_state_machines() -> tuple[list[str], list[str], int]:
    """Validate state machine definitions: reachability, error paths, transitions."""
    issues, warnings = [], []
    score = 0
    arch = load_arch()
    for machine_id, defn in arch.get("state_machines", {}).items():
        states = set(defn.get("states", []))
        initial = defn.get("initial")
        transitions = defn.get("transitions", [])
        error_states = set(defn.get("error_states", []))

        if not initial:
            issues.append(f"State machine {machine_id!r}: missing initial state")
            continue
        if initial not in states:
            issues.append(f"State machine {machine_id!r}: initial state {initial!r} not in states")
            continue

        # Build reachability via BFS
        allowed: dict[str, list[str]] = {}
        for t in transitions:
            allowed.setdefault(t["from"], []).append(t["to"])
            # Validate states exist
            if t["from"] not in states:
                issues.append(f"State machine {machine_id!r}: transition from undefined state {t['from']!r}")
            if t["to"] not in states:
                issues.append(f"State machine {machine_id!r}: transition to undefined state {t['to']!r}")

        visited: set[str] = set()
        queue = [initial]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for nxt in allowed.get(current, []):
                if nxt not in visited:
                    queue.append(nxt)

        unreachable = states - visited
        for s in unreachable:
            warnings.append(f"State machine {machine_id!r}: state {s!r} is unreachable from initial")

        # Check error transitions exist
        has_error_path = any(t["to"] in error_states for t in transitions)
        if error_states and not has_error_path:
            warnings.append(f"State machine {machine_id!r}: error states defined but no transitions lead to them")
        elif error_states and has_error_path:
            score += 2  # Bonus for having error paths

        score += 1  # Base score for valid state machine
    return issues, warnings, score


def check_contracts() -> tuple[list[str], list[str], int]:
    """Check JSON Schema contracts exist and are valid JSON."""
    issues, warnings = [], []
    score = 0
    arch = load_arch()
    required = arch.get("quality_gates", {}).get("required_contracts", [
        "contracts/asset.json", "contracts/event.json",
        "contracts/sample.json", "contracts/workflow.json", "contracts/simulation.json",
    ])
    for contract_path in required:
        path = ROOT / contract_path
        if not path.exists():
            issues.append(f"Missing contract: {contract_path}")
            continue
        try:
            import json as _json
            data = _json.loads(path.read_text())
            if "$schema" not in data:
                warnings.append(f"Contract {contract_path}: missing $schema field")
            if "required" not in data and data.get("type") == "object":
                warnings.append(f"Contract {contract_path}: no required fields defined")
            score += 2
        except Exception as e:
            issues.append(f"Contract {contract_path}: invalid JSON — {e}")
    return issues, warnings, score


def check_tests() -> tuple[list[str], list[str], int]:
    """Check required test files exist and contain actual test functions."""
    issues, warnings = [], []
    score = 0
    arch = load_arch()
    required_tests = arch.get("quality_gates", {}).get("required_test_files", [
        "tests/unit/test_state_machines.py",
        "tests/unit/test_event_model.py",
        "tests/unit/test_asset_registry.py",
        "tests/simulation/test_scenarios.py",
    ])
    for test_path in required_tests:
        path = ROOT / test_path
        if not path.exists():
            issues.append(f"Missing required test file: {test_path}")
            continue
        content = path.read_text()
        test_count = content.count("def test_")
        if test_count == 0:
            warnings.append(f"Test file {test_path}: no test functions found")
        else:
            score += min(test_count, 5)  # Up to 5 points per test file
    return issues, warnings, score


def check_ci_workflows() -> tuple[list[str], list[str], int]:
    """Check GitHub Actions workflow files exist and have correct structure."""
    issues, warnings = [], []
    score = 0
    arch = load_arch()
    required_workflows = arch.get("quality_gates", {}).get("required_workflows",
        [".github/workflows/test.yml", ".github/workflows/architecture.yml",
         ".github/workflows/simulation.yml", ".github/workflows/build.yml"])
    for wf_path in required_workflows:
        path = ROOT / wf_path
        if not path.exists():
            issues.append(f"Missing CI workflow: {wf_path}")
            continue
        try:
            wf = load_yaml(path)
            if "jobs" not in wf:
                warnings.append(f"Workflow {wf_path}: no jobs defined")
            else:
                score += 2
            # Check for forbidden patterns
            content = path.read_text()
            if "mini-lims-platform" in content:
                issues.append(f"Workflow {wf_path}: contains forbidden path 'mini-lims-platform'")
            if "cache: pip" in content and "cache-dependency-path" not in content:
                warnings.append(f"Workflow {wf_path}: cache: pip without cache-dependency-path")
        except Exception as e:
            warnings.append(f"Workflow {wf_path}: parse error — {e}")
    return issues, warnings, score


def check_no_hardcoded_values() -> tuple[list[str], list[str], int]:
    """Check source files for forbidden patterns."""
    issues, warnings = [], []
    score = 10  # Start with full score, deduct for violations
    forbidden_patterns = [
        ("score = 94", "Hard-coded architecture score"),
        ("score = 100", "Hard-coded architecture score"),
        ("localhost:8000", "Hard-coded localhost URL in source"),
        ("password", "Possible credential in source"),
        ("secret", "Possible secret in source"),
    ]
    source_dirs = [ROOT / "twin", ROOT / "simulation", ROOT / "scripts", ROOT / "backend"]
    for src_dir in source_dirs:
        if not src_dir.exists():
            continue
        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text().lower()
            for pattern, description in forbidden_patterns:
                if pattern.lower() in content and "test" not in str(py_file):
                    issues.append(f"{description} in {py_file.relative_to(ROOT)}")
                    score -= 2
    return issues, warnings, max(0, score)


def check_pyproject_toml() -> tuple[list[str], list[str], int]:
    """Check pyproject.toml exists and has required sections."""
    issues, warnings = [], []
    score = 0
    path = ROOT / "pyproject.toml"
    if not path.exists():
        issues.append("Missing pyproject.toml — dependency management not configured")
        return issues, warnings, score
    content = path.read_text()
    for section in ["[project]", "[tool.ruff]", "[tool.mypy]", "[tool.pytest"]:
        if section in content:
            score += 1
        else:
            warnings.append(f"pyproject.toml missing section: {section}")
    return issues, warnings, score


def check_architecture_constraints() -> tuple[list[str], list[str], int]:
    """Check architecture constraints from architecture.yaml."""
    issues, warnings = [], []
    score = 0
    arch = load_arch()
    constraints = arch.get("constraints", [])
    if not constraints:
        warnings.append("No architecture constraints defined in architecture.yaml")
        return issues, warnings, score
    # Check UI-not-source-of-truth constraint
    frontend_dir = ROOT / "frontend"
    if frontend_dir.exists():
        for py_file in frontend_dir.rglob("*.py"):
            content = py_file.read_text()
            if "business_logic" in content or "state_machine" in content:
                issues.append(f"Possible business logic in frontend: {py_file.relative_to(ROOT)}")
    score += len(constraints)  # Points for having constraints defined
    return issues, warnings, score


# ── Score Computation ─────────────────────────────────────────────────────────

def compute_score(
    all_issues: list[str],
    all_warnings: list[str],
    raw_score: int,
    max_possible: int,
) -> int:
    """Compute final score 0-100 from raw score, issues, and warnings."""
    if max_possible == 0:
        return 0
    base = int((raw_score / max_possible) * 100)
    # Deduct for issues and warnings
    deductions = len(all_issues) * 5 + len(all_warnings) * 2
    final = max(0, min(100, base - deductions))
    return final


# ── Main Audit ────────────────────────────────────────────────────────────────

def run_audit() -> dict[str, Any]:
    all_issues: list[str] = []
    all_warnings: list[str] = []
    raw_score = 0
    max_possible = 0
    check_results: dict[str, Any] = {}

    checks = [
        ("Architecture YAML",       check_architecture_yaml,    20),
        ("Domain Files",            check_domain_files,         30),
        ("State Machines",          check_state_machines,       20),
        ("JSON Contracts",          check_contracts,            15),
        ("Test Coverage",           check_tests,                25),
        ("CI Workflows",            check_ci_workflows,         10),
        ("No Hard-coded Values",    check_no_hardcoded_values,  10),
        ("pyproject.toml",          check_pyproject_toml,        5),
        ("Architecture Constraints",check_architecture_constraints, 5),
    ]

    for name, fn, weight in checks:
        try:
            issues, warnings, score = fn()
            all_issues.extend(issues)
            all_warnings.extend(warnings)
            raw_score += score
            max_possible += weight
            check_results[name] = {
                "issues": issues,
                "warnings": warnings,
                "score": score,
                "weight": weight,
            }
        except Exception as e:
            all_issues.append(f"Audit check {name!r} raised exception: {e}")
            check_results[name] = {"issues": [str(e)], "warnings": [], "score": 0, "weight": weight}
            max_possible += weight

    critical_count = sum(1 for i in all_issues if i.startswith("CRITICAL"))
    final_score = compute_score(all_issues, all_warnings, raw_score, max_possible)

    return {
        "architecture_score": final_score,
        "raw_score": raw_score,
        "max_possible": max_possible,
        "issues": len(all_issues),
        "warnings": len(all_warnings),
        "critical": critical_count,
        "checks": check_results,
        "all_issues": all_issues,
        "all_warnings": all_warnings,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "note": "Score computed dynamically from actual checks — never hard-coded",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Mini-LIMS Architecture Audit")
    print("=" * 60)
    health = run_audit()
    out_path = ROOT / "architecture-health.json"
    with open(out_path, "w") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)
    print(f"\nArchitecture Score : {health['architecture_score']}/100")
    print(f"Raw Score          : {health['raw_score']}/{health['max_possible']}")
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
