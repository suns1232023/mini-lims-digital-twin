
"""
Workflow Engine — State-machine-based workflow execution.
Loads workflow definitions from workflows.yaml.
Every transition is validated. Every action generates an audit event.
"""
from __future__ import annotations

import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowInstance:
    def __init__(self, instance_id: str, workflow_def: Dict, entity_id: str, entity_type: str):
        self.instance_id = instance_id
        self.workflow_def = workflow_def
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.current_state = workflow_def["initial_state"]
        self.started_at = utcnow()
        self.completed_at: Optional[datetime] = None
        self.history: List[Dict[str, Any]] = []
        self.blocked: bool = False
        self.block_reason: Optional[str] = None

    def _find_transition(self, target_state: str) -> Optional[Dict]:
        for t in self.workflow_def.get("transitions", []):
            if t["from"] == self.current_state and t["to"] == target_state:
                return t
        return None

    def can_transition(self, target_state: str) -> tuple[bool, str]:
        t = self._find_transition(target_state)
        if not t:
            return False, f"No transition defined: {self.current_state} → {target_state}"
        if self.blocked:
            return False, f"Workflow blocked: {self.block_reason}"
        return True, "ok"

    def transition(
        self,
        target_state: str,
        actor: str = "system",
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        ok, reason = self.can_transition(target_state)
        if not ok:
            raise ValueError(f"[WorkflowEngine] {reason}")

        t = self._find_transition(target_state)
        previous = self.current_state
        self.current_state = target_state

        record = {
            "ts": utcnow().isoformat(),
            "from": previous,
            "to": target_state,
            "actor": actor,
            "event": t.get("event", "WORKFLOW_STEP_COMPLETED"),
            "payload": payload or {},
        }
        self.history.append(record)

        terminal_states = ["ARCHIVED", "RELEASED", "REJECTED"]
        if target_state in terminal_states:
            self.completed_at = utcnow()

        return record

    def block(self, reason: str) -> None:
        self.blocked = True
        self.block_reason = reason

    def release(self) -> None:
        self.blocked = False
        self.block_reason = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "workflow_id": self.workflow_def["id"],
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "current_state": self.current_state,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "history": self.history,
        }


class WorkflowEngine:
    """
    Manages workflow instances for samples and assets.
    Definitions loaded from config/workflows.yaml.
    """

    def __init__(self, config_path: str = "config/workflows.yaml"):
        self._definitions: Dict[str, Dict] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._load_definitions(Path(config_path))

    def _load_definitions(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as f:
            config = yaml.safe_load(f)
        for wf in config.get("workflows", []):
            self._definitions[wf["id"]] = wf

    def create_instance(
        self,
        workflow_id: str,
        entity_id: str,
        entity_type: str = "sample",
    ) -> WorkflowInstance:
        defn = self._definitions.get(workflow_id)
        if not defn:
            raise KeyError(f"Workflow definition '{workflow_id}' not found")
        instance_id = str(uuid.uuid4())
        instance = WorkflowInstance(
            instance_id=instance_id,
            workflow_def=defn,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        self._instances[instance_id] = instance
        return instance

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        return self._instances.get(instance_id)

    def get_instances_for_entity(self, entity_id: str) -> List[WorkflowInstance]:
        return [i for i in self._instances.values() if i.entity_id == entity_id]

    def transition(
        self,
        instance_id: str,
        target_state: str,
        actor: str = "system",
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        instance = self.get_instance(instance_id)
        if not instance:
            raise KeyError(f"Workflow instance '{instance_id}' not found")
        return instance.transition(target_state, actor=actor, payload=payload)

    def get_all_instances(self) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._instances.values()]

    def get_definitions(self) -> List[Dict]:
        return list(self._definitions.values())

