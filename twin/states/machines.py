
"""
State Machine Definitions — loaded from architecture.yaml.
Every transition is validated. Invalid transitions raise ValueError.
"""
from __future__ import annotations

from typing import Optional
import yaml
from pathlib import Path


class StateMachine:
    """Generic state machine loaded from architecture.yaml."""

    def __init__(self, machine_id: str, definition: dict):
        self.machine_id = machine_id
        self.states: list[str] = definition["states"]
        self.initial: str = definition["initial"]
        self.error_states: list[str] = definition.get("error_states", [])
        # Build transition map: {(from, to): event_type}
        self._transitions: dict[tuple[str, str], str] = {}
        # Build allowed targets: {from_state: [to_states]}
        self._allowed: dict[str, list[str]] = {}
        for t in definition.get("transitions", []):
            key = (t["from"], t["to"])
            self._transitions[key] = t["event"]
            self._allowed.setdefault(t["from"], []).append(t["to"])

    def can_transition(self, from_state: str, to_state: str) -> bool:
        return to_state in self._allowed.get(from_state, [])

    def validate_transition(self, from_state: str, to_state: str) -> str:
        """Returns event_type if valid, raises ValueError if invalid."""
        if not self.can_transition(from_state, to_state):
            allowed = self._allowed.get(from_state, [])
            raise ValueError(
                f"[{self.machine_id}] Invalid transition {from_state!r} → {to_state!r}. "
                f"Allowed from {from_state!r}: {allowed}"
            )
        return self._transitions[(from_state, to_state)]

    def get_allowed_transitions(self, from_state: str) -> list[str]:
        return self._allowed.get(from_state, [])

    def is_error_state(self, state: str) -> bool:
        return state in self.error_states

    def get_all_states(self) -> list[str]:
        return list(self.states)

    def get_reachable_states(self) -> set[str]:
        """BFS from initial state to find all reachable states."""
        visited = set()
        queue = [self.initial]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for next_state in self._allowed.get(current, []):
                if next_state not in visited:
                    queue.append(next_state)
        return visited

    def get_unreachable_states(self) -> list[str]:
        reachable = self.get_reachable_states()
        return [s for s in self.states if s not in reachable]

    def has_error_transitions(self) -> bool:
        """Check if any state has a transition to an error state."""
        for (_, to), _ in self._transitions.items():
            if to in self.error_states:
                return True
        return False


class StateMachineRegistry:
    """Loads all state machines from architecture.yaml."""

    def __init__(self, arch_path: str = "architecture.yaml"):
        self._machines: dict[str, StateMachine] = {}
        self._load(Path(arch_path))

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as f:
            arch = yaml.safe_load(f)
        for machine_id, definition in arch.get("state_machines", {}).items():
            self._machines[machine_id] = StateMachine(machine_id, definition)

    def get(self, machine_id: str) -> Optional[StateMachine]:
        return self._machines.get(machine_id)

    def get_all(self) -> dict[str, StateMachine]:
        return dict(self._machines)

    def validate_transition(self, machine_id: str, from_state: str, to_state: str) -> str:
        machine = self.get(machine_id)
        if not machine:
            raise KeyError(f"State machine {machine_id!r} not found")
        return machine.validate_transition(from_state, to_state)

