
"""
Event Engine — Centralized event processing and broadcast.
Every meaningful state change must generate an event through this engine.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from twin.entities.base import EventRecord


class EventEngine:
    """
    Central event bus for the Digital Twin platform.
    - Receives events from all sources (IoT, API, workflow engine, rules engine)
    - Stores events immutably
    - Broadcasts to WebSocket subscribers
    - Supports correlation_id-based traceability
    """

    def __init__(self):
        self._store: List[EventRecord] = []
        self._subscribers: Set[asyncio.Queue] = set()
        self._handlers: Dict[str, List[Callable]] = {}

    # ── Event Publishing ─────────────────────────────────────────

    async def publish(self, event: EventRecord) -> None:
        """Publish an event to the store and all subscribers."""
        self._store.append(event)
        await self._broadcast(event)
        await self._dispatch_handlers(event)

    async def publish_raw(
        self,
        event_type: str,
        source: str,
        asset_id: str,
        severity: str = "INFO",
        sample_id: Optional[str] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        payload: Optional[Dict] = None,
        correlation_id: Optional[str] = None,
    ) -> EventRecord:
        """Create and publish an event from raw parameters."""
        event = EventRecord(
            event_type=event_type,
            source=source,
            asset_id=asset_id,
            sample_id=sample_id,
            previous_state=previous_state or {},
            new_state=new_state or {},
            payload=payload or {},
            severity=severity,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )
        await self.publish(event)
        return event

    # ── WebSocket Broadcast ──────────────────────────────────────

    def subscribe(self) -> asyncio.Queue:
        """Register a new WebSocket subscriber. Returns a queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def _broadcast(self, event: EventRecord) -> None:
        """Broadcast event to all WebSocket subscribers."""
        payload = json.dumps({
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "source": event.source,
            "asset_id": event.asset_id,
            "sample_id": event.sample_id,
            "severity": event.severity,
            "new_state": event.new_state,
            "correlation_id": event.correlation_id,
        }, ensure_ascii=False)

        dead = set()
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.add(q)
        self._subscribers -= dead

    # ── Event Handlers ───────────────────────────────────────────

    def on(self, event_type: str, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def _dispatch_handlers(self, event: EventRecord) -> None:
        handlers = self._handlers.get(event.event_type, [])
        handlers += self._handlers.get("*", [])  # wildcard handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"[EventEngine] Handler error for {event.event_type}: {e}")

    # ── Query ────────────────────────────────────────────────────

    def get_events(
        self,
        asset_id: Optional[str] = None,
        sample_id: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[EventRecord]:
        events = self._store
        if asset_id:
            events = [e for e in events if e.asset_id == asset_id]
        if sample_id:
            events = [e for e in events if e.sample_id == sample_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if severity:
            events = [e for e in events if e.severity == severity]
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]
        return events[-limit:]

    def reconstruct_thread(self, sample_id: str) -> List[EventRecord]:
        """Reconstruct the complete digital thread for a sample."""
        return [e for e in self._store if e.sample_id == sample_id]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_events": len(self._store),
            "subscribers": len(self._subscribers),
            "event_types": list({e.event_type for e in self._store}),
        }

