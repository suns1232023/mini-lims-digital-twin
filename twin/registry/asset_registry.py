
"""
Asset Registry — Central registry for all Digital Twin entities.
Loads configuration from assets.yaml and creates corresponding twin objects.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from twin.entities.base import DigitalTwinEntity, EventRecord
from twin.entities.incubator import IncubatorTwin
from twin.entities.autoclave import AutoclaveTwin
from twin.entities.pass_box import PassBoxTwin


ENTITY_MAP = {
    "incubator":            IncubatorTwin,
    "autoclave":            AutoclaveTwin,
    "pass_box":             PassBoxTwin,
    "biosafety_cabinet":    DigitalTwinEntity,
    "environmental_sensor": DigitalTwinEntity,
    "workbench":            DigitalTwinEntity,
    "fume_hood":            DigitalTwinEntity,
    "refrigerator":         DigitalTwinEntity,
}


class AssetRegistry:
    """
    Central registry for all Digital Twin entities.
    Source of truth for asset state.
    """

    def __init__(self, config_path: str = "config/assets.yaml"):
        self._assets: Dict[str, DigitalTwinEntity] = {}
        self._event_log: List[EventRecord] = []
        self._config_path = Path(config_path)
        self._load_from_config()

    def _load_from_config(self) -> None:
        if not self._config_path.exists():
            return
        with open(self._config_path) as f:
            config = yaml.safe_load(f)
        for asset_cfg in config.get("assets", []):
            self._create_asset(asset_cfg)

    def _create_asset(self, cfg: Dict[str, Any]) -> DigitalTwinEntity:
        asset_type = cfg["type"]
        entity_class = ENTITY_MAP.get(asset_type, DigitalTwinEntity)
        entity = entity_class(
            asset_id=cfg["id"],
            asset_type=asset_type,
            name=cfg["name"],
            room_id=cfg.get("room"),
        )
        # Store thresholds in metadata
        entity.metadata.extra["thresholds"] = cfg.get("thresholds", {})
        entity.metadata.extra["sensors"] = cfg.get("sensors", [])
        if cfg.get("metadata"):
            for k, v in cfg["metadata"].items():
                setattr(entity.metadata, k, v) if hasattr(entity.metadata, k) else entity.metadata.extra.update({k: v})
        self._assets[entity.asset_id] = entity
        return entity

    # ── Query ────────────────────────────────────────────────────

    def get(self, asset_id: str) -> Optional[DigitalTwinEntity]:
        return self._assets.get(asset_id)

    def get_all(self) -> List[DigitalTwinEntity]:
        return list(self._assets.values())

    def get_by_type(self, asset_type: str) -> List[DigitalTwinEntity]:
        return [a for a in self._assets.values() if a.asset_type == asset_type]

    def get_by_room(self, room_id: str) -> List[DigitalTwinEntity]:
        return [a for a in self._assets.values() if a.room_id == room_id]

    def get_summaries(self) -> List[Dict[str, Any]]:
        return [a.get_summary() for a in self._assets.values()]

    # ── Mutation ─────────────────────────────────────────────────

    def update_telemetry(self, asset_id: str, readings: Dict[str, Any]) -> Optional[EventRecord]:
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
        **kwargs,
    ) -> EventRecord:
        asset = self.get(asset_id)
        if not asset:
            raise KeyError(f"Asset {asset_id} not found in registry")
        if not hasattr(asset, "transition"):
            raise AttributeError(f"Asset {asset_id} does not support state transitions")
        event = asset.transition(target_state, source=source, **kwargs)
        self._event_log.append(event)
        return event

    def get_events(self, asset_id: str, limit: int = 50) -> List[EventRecord]:
        events = [e for e in self._event_log if e.asset_id == asset_id]
        return events[-limit:]

    def get_all_events(self, limit: int = 200) -> List[EventRecord]:
        return self._event_log[-limit:]

    def get_active_alarms(self) -> List[Dict[str, Any]]:
        alarms = []
        for asset in self._assets.values():
            for alarm_id in asset.active_alarm_ids:
                alarms.append({"asset_id": asset.asset_id, "alarm_id": alarm_id})
        return alarms

    # ── Snapshot ─────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Full state snapshot for WebSocket broadcast."""
        from datetime import datetime, timezone
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "assets": self.get_summaries(),
            "active_alarms": self.get_active_alarms(),
            "event_count": len(self._event_log),
        }

