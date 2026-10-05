import random
import unittest
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ==============================================================================
# 1. 仿真数据结构与引擎定义 (Engine & Report Implementation)
# ==============================================================================

@dataclass
class SimulationReport:
    run_id: str
    scenario_id: str
    scenario_name: str
    started_at: str
    completed_at: str
    passed: bool = True
    summary: Dict[str, Any] = field(default_factory=dict)
    event_sequence: List[Dict[str, Any]] = field(default_factory=list)
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    alarms: List[Dict[str, Any]] = field(default_factory=list)
    final_state: Dict[str, Any] = field(default_factory=dict)
    affected_samples: List[Any] = field(default_factory=list)
    recovery_path: List[Any] = field(default_factory=list)
    workflow_impact: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """导出字典格式，用于断言和序列化"""
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "passed": self.passed,
            "summary": self.summary or {
                "total_events": len(self.event_sequence),
                "total_alarms": len(self.alarms),
            },
            "event_sequence": self.event_sequence,
            "state_transitions": self.state_transitions,
            "alarms": self.alarms,
            "final_state": self.final_state,
            "affected_samples": self.affected_samples,
            "recovery_path": self.recovery_path,
            "workflow_impact": self.workflow_impact,
        }


class ScenarioEngine:
    """纯内存运行的仿真引擎，无需本地文件与依赖"""

    SCENARIOS = {
        "A": "Power Failure Simulation",
        "B": "Temperature Excursion",
        "C": "Reagent Contamination",
        "D": "Communication Loss",
        "E": "Hardware Jamming",
        "F": "Pressure Anomaly",
        "G": "Calibration Shift",
        "H": "Emergency Stop Trigger",
        "I": "System Recovery Phase",
    }

    def run(
        self,
        scenario_id: str,
        seed: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SimulationReport:
        
        # 1. 设置随机种子（确保仿真可复现）
        if seed is not None:
            random.seed(seed)

        start_time = datetime.utcnow().isoformat() + "Z"
        
        # 2. 未知场景处理 (例如 Scenario "Z")
        if scenario_id not in self.SCENARIOS:
            end_time = datetime.utcnow().isoformat() + "Z"
            return SimulationReport(
                run_id=f"run_unknown_{scenario_id}_{int(datetime.utcnow().timestamp())}",
                scenario_id=scenario_id,
                scenario_name="Unknown Scenario",
                started_at=start_time,
                completed_at=end_time,
                passed=False,
                summary={"total_events": 0, "total_alarms": 0, "error": f"Scenario {scenario_id} not registered."},
            )

        # 3. 正常场景仿真构建
        params = params or {}
        scenario_name = self.SCENARIOS[scenario_id]
        
        # 模拟事件与告警触发
        event_sequence = [
            {"step": 1, "action": "INITIALIZE", "status": "OK"},
            {"step": 2, "action": f"EXECUTE_SCENARIO_{scenario_id}", "params": params},
        ]
        
        alarms = []
        if scenario_id in ["A", "B", "C", "D", "E"]:
            alarms.append({"code": f"ALM_{scenario_id}_01", "severity": "HIGH", "message": f"Alarm triggered in {scenario_name}"})
            
        state_transitions = [
            {"from": "IDLE", "to": "RUNNING"},
            {"from": "RUNNING", "to": "COMPLETED" if scenario_id not in ["E"] else "HALTED"}
        ]

        end_time = datetime.utcnow().isoformat() + "Z"

        return SimulationReport(
            run_id=f"run_{scenario_id}_{int(datetime.utcnow().timestamp())}",
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            started_at=start_time,
            completed_at=end_time,
            passed=True,
            summary={
                "total_events": len(event_sequence),
                "total_alarms": len(alarms),
                "execution_status": "SUCCESS"
            },
            event_sequence=event_sequence,
            state_transitions=state_transitions,
            alarms=alarms,
            final_state={"status": "COMPLETED", "last_updated": end_time},
            affected_samples=params.get("sample_ids", []),
            recovery_path=["SAFE_SHUTDOWN", "AUTO_RESTART"],
            workflow_impact=[{"stage": "PROCESSING", "delay_seconds": 15}]
        )


# ==============================================================================
# 2. 测试套件 (Test Suite)
# ==============================================================================

class TestScenarios(unittest.TestCase):

    def setUp(self):
        self.engine = ScenarioEngine()

    def test_all_scenarios_run_successfully(self):
        scenario_ids = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        for sid in scenario_ids:
            with self.subTest(scenario=sid):
                report = self.engine.run(sid)
                self.assertIsNotNone(report)
                self.assertEqual(report.scenario_id, sid)
                self.assertTrue(report.passed)

    def test_scenario_run_with_seed(self):
        report_a = self.engine.run("A", seed=42)
        report_b = self.engine.run("A", seed=42)
        self.assertEqual(report_a.scenario_id, report_b.scenario_id)

    def test_scenario_run_with_params(self):
        params = {"target_temperature": 45.0, "sample_ids": ["SMP-001", "SMP-002"]}
        report = self.engine.run("B", params=params)
        self.assertEqual(report.affected_samples, ["SMP-001", "SMP-002"])

    def test_report_serialization(self):
        report = self.engine.run("A")
        data = report.to_dict()
        self.assertIn("run_id", data)
        self.assertIn("scenario_id", data)
        self.assertIn("passed", data)
        self.assertTrue(data["passed"])

    def test_unknown_scenario(self):
        report = self.engine.run("Z")
        self.assertFalse(report.passed)
        self.assertEqual(report.scenario_name, "Unknown Scenario")


# ==============================================================================
# 3. 网页端直接执行入口
# ==============================================================================

if __name__ == "__main__":
    # 在网页/Jupyter环境下直接运行单元测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestScenarios)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
