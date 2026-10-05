
"""
Asset Registry — Central registry for all Digital Twin entities.
Loads from architecture.yaml. Source of truth for asset state.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Optional

from twin.entities.base import DigitalTwinEntity, EventRecord
from twin.entities.incubator import IncubatorTwin
from twin.entities.autoclave import AutoclaveTwin
from twin.entities.pass_box import PassBoxTwin

ENTITY_MAP: dict[str, type] = {
    "incubator":            IncubatorTwin,
    "autoclave":            AutoclaveTwin,
    "pass_box":             PassBoxTwin,
    "environmental_sensor": DigitalTwinEntity,
    "biosafety_cabinet":    DigitalTwinEntity,
    "workbench":            DigitalTwinEntity,
    "refrigerator":         DigitalTwinEntity,
}


class AssetRegistry:
    """Central registry. Loads assets from architecture.yaml entities section."""

    def __init__(self, arch_path: str = "architecture.yaml"):
        self._assets: dict[str, DigitalTwinEntity] = {}
        self._event_log: list[EventRecord] = []
        self._load(Path(arch_path))

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as f:
            arch = yaml.safe_load(f)
        for entity_cfg in arch.get("entities", []):
            self._create_entity(entity_cfg)

    def _create_entity(self, cfg: dict[str, Any]) -> DigitalTwinEntity:
        asset_type = cfg["type"]
        cls = ENTITY_MAP.get(asset_type, DigitalTwinEntity)
        entity = cls(
            asset_id=cfg["id"],
            asset_type=asset_type,
            name=cfg["name"],
            room_id=cfg.get("room"),
            metadata={
                "thresholds": cfg.get("thresholds", {}),
                "sensors": cfg.get("sensors", []),
                "adjacent_room": cfg.get("adjacent_room"),
            },
        )
        self._assets[entity.asset_id] = entity
        return entity

    # ── Query ────────────────────────────────────────────────────────────────

    def get(self, asset_id: str) -> Optional[DigitalTwinEntity]:
        return self._assets.get(asset_id)

    def get_all(self) -> list[DigitalTwinEntity]:
        return list(self._assets.values())

    def get_by_type(self, asset_type: str) -> list[DigitalTwinEntity]:
        return [a for a in self._assets.values() if a.asset_type == asset_type]

    def get_by_room(self, room_id: str) -> list[DigitalTwinEntity]:
        return [a for a in self._assets.values() if a.room_id == room_id]

    def get_summaries(self) -> list[dict[str, Any]]:
        return [a.get_summary() for a in self._assets.values()]

    def asset_ids(self) -> list[str]:
        return list(self._assets.keys())

    # ── Mutation ─────────────────────────────────────────────────────────────

    def update_telemetry(self, asset_id: str, readings: dict[str, Any]) -> Optional[EventRecord]:
        asset = self.get(asset_id)
        if not asset:
            return None
        event = asset.update_telemetry(readings)
        self._event_log.append(event)
        return event

    def transition_state(
        self,
        asset_id: str,
        target_state: str,
        source: str = "api",
        **kwargs: Any,
    ) -> EventRecord:
        asset = self.get(asset_id)
        if not asset:
            raise KeyError(f"Asset {asset_id!r} not found")
        if not hasattr(asset, "transition"):
            raise AttributeError(f"Asset {asset_id!r} does not support state transitions")
        event = asset.transition(target_state, source=source, **kwargs)
        self._event_log.append(event)
        return event

    def get_events(self, asset_id: str, limit: int = 50) -> list[EventRecord]:
        return [e for e in self._event_log if e.asset_id == asset_id][-limit:]

    def get_all_events(self, limit: int = 500) -> list[EventRecord]:
        return self._event_log[-limit:]

    def snapshot(self) -> dict[str, Any]:
        from twin.entities.base import utcnow
        return {
            "ts": utcnow().isoformat(),
            "assets": self.get_summaries(),
            "event_count": len(self._event_log),
        }

