
"""
FastAPI Backend — Mini-LIMS Digital Twin Platform
Versioned REST API + WebSocket real-time state broadcast.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from twin.registry.asset_registry import AssetRegistry
from backend.core.event_engine import EventEngine
from backend.core.rules_engine import RulesEngine
from backend.core.workflow_engine import WorkflowEngine
from simulation.scenarios.scenario_engine import ScenarioEngine

# ── Shared state ─────────────────────────────────────────────────
registry = AssetRegistry("config/assets.yaml")
event_engine = EventEngine()
rules_engine = RulesEngine("config/rules.yaml")
workflow_engine = WorkflowEngine("config/workflows.yaml")
scenario_engine = ScenarioEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background simulator tick
    task = asyncio.create_task(_simulator_loop())
    yield
    task.cancel()


app = FastAPI(
    title="Mini-LIMS Digital Twin API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Background simulator ─────────────────────────────────────────
async def _simulator_loop():
    """Simulate sensor readings every 2 seconds."""
    import math, random, time
    tick = 0
    while True:
        await asyncio.sleep(2)
        tick += 1
        t = time.time()
        for asset in registry.get_all():
            readings = {}
            if asset.asset_type == "incubator":
                readings = {
                    "temperature": round(37.0 + math.sin(t * 0.2 + hash(asset.asset_id) % 5) * 0.3 + random.uniform(-0.1, 0.1), 1),
                    "humidity": round(60.0 + random.uniform(-1, 1), 1),
                }
            elif asset.asset_type == "autoclave":
                if asset.status == "RUNNING":
                    readings = {"temperature": round(121.0 + random.uniform(-0.3, 0.3), 1), "pressure": round(1.05 + random.uniform(-0.02, 0.02), 3)}
            elif asset.asset_type == "environmental_sensor":
                base_p = {"ENV-STERILE": -15, "ENV-YANGXING": -12, "ENV-MICROBIO": -10}.get(asset.asset_id, 0)
                readings = {
                    "pressure": round(base_p + math.sin(t * 0.3 + hash(asset.asset_id) % 10) * 1.5 + random.uniform(-0.3, 0.3), 1),
                    "temperature": round(22.0 + random.uniform(-0.1, 0.1), 1),
                    "humidity": round(50.0 + random.uniform(-0.5, 0.5), 1),
                }
            if readings:
                event = registry.update_telemetry(asset.asset_id, readings)
                if event:
                    await event_engine.publish(event)
                    # Evaluate rules
                    thresholds = asset.metadata.extra.get("thresholds", {})
                    violations = rules_engine.evaluate_asset(
                        asset_id=asset.asset_id,
                        asset_type=asset.asset_type,
                        room_id=asset.room_id,
                        state=asset.current_state,
                        thresholds=thresholds,
                    )
                    for v in violations:
                        await event_engine.publish_raw(
                            event_type="ALARM_CREATED",
                            source="rules_engine",
                            asset_id=asset.asset_id,
                            severity=v.severity,
                            payload=v.to_dict(),
                        )


# ── WebSocket ────────────────────────────────────────────────────
@app.websocket("/ws/twin-state")
async def websocket_twin_state(ws: WebSocket):
    await ws.accept()
    q = event_engine.subscribe()
    # Send initial snapshot
    await ws.send_text(json.dumps(registry.snapshot(), ensure_ascii=False))
    try:
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=3.0)
                await ws.send_text(msg)
            except asyncio.TimeoutError:
                # Send heartbeat snapshot every 3s
                await ws.send_text(json.dumps(registry.snapshot(), ensure_ascii=False))
    except WebSocketDisconnect:
        event_engine.unsubscribe(q)


# ── Assets ───────────────────────────────────────────────────────
@app.get("/api/v1/assets", response_model=List[Dict[str, Any]])
async def list_assets():
    return registry.get_summaries()


@app.get("/api/v1/assets/{asset_id}")
async def get_asset(asset_id: str):
    asset = registry.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return asset.get_summary()


@app.get("/api/v1/assets/{asset_id}/events")
async def get_asset_events(asset_id: str, limit: int = 50):
    events = event_engine.get_events(asset_id=asset_id, limit=limit)
    return [e.dict() for e in events]


@app.get("/api/v1/assets/{asset_id}/state")
async def get_asset_state(asset_id: str):
    asset = registry.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return {"asset_id": asset_id, "status": asset.status, "current_state": asset.current_state}


class TransitionRequest(BaseModel):
    target_state: str
    actor: str = "api"
    payload: Optional[Dict[str, Any]] = None


@app.post("/api/v1/assets/{asset_id}/transition")
async def transition_asset(asset_id: str, req: TransitionRequest):
    try:
        event = registry.transition_state(
            asset_id=asset_id,
            target_state=req.target_state,
            source=req.actor,
            payload=req.payload,
        )
        await event_engine.publish(event)
        return {"ok": True, "event_id": event.event_id, "new_state": req.target_state}
    except (ValueError, KeyError, AttributeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Samples ──────────────────────────────────────────────────────
_samples: Dict[str, Dict] = {}
_sample_counter = {"n": 1}


class CreateSampleRequest(BaseModel):
    barcode: Optional[str] = None
    customer_id: Optional[str] = None
    product_id: Optional[str] = None
    batch_id: Optional[str] = None
    test_method_id: Optional[str] = None


@app.post("/api/v1/samples")
async def create_sample(req: CreateSampleRequest):
    sample_id = f"SMP-{_sample_counter['n']:04d}"
    _sample_counter["n"] += 1
    wf = workflow_engine.create_instance("sample_lifecycle", sample_id, "sample")
    sample = {
        "sample_id": sample_id,
        "barcode": req.barcode or sample_id,
        "current_state": "REGISTERED",
        "workflow_instance_id": wf.instance_id,
        "customer_id": req.customer_id,
        "product_id": req.product_id,
        "batch_id": req.batch_id,
        "test_method_id": req.test_method_id,
    }
    _samples[sample_id] = sample
    await event_engine.publish_raw(
        event_type="SAMPLE_REGISTERED",
        source="api",
        asset_id="LIMS",
        sample_id=sample_id,
        payload=sample,
    )
    return sample


@app.get("/api/v1/samples")
async def list_samples():
    return list(_samples.values())


@app.get("/api/v1/samples/{sample_id}")
async def get_sample(sample_id: str):
    s = _samples.get(sample_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
    return s


@app.get("/api/v1/samples/{sample_id}/thread")
async def get_sample_thread(sample_id: str):
    """Return the complete digital thread for a sample."""
    events = event_engine.reconstruct_thread(sample_id)
    return {
        "sample_id": sample_id,
        "sample": _samples.get(sample_id),
        "event_count": len(events),
        "events": [e.dict() for e in events],
    }


# ── Workflows ────────────────────────────────────────────────────
@app.get("/api/v1/workflows")
async def list_workflows():
    return workflow_engine.get_definitions()


@app.get("/api/v1/workflows/{instance_id}")
async def get_workflow_instance(instance_id: str):
    inst = workflow_engine.get_instance(instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Workflow instance {instance_id} not found")
    return inst.to_dict()


# ── Simulation ───────────────────────────────────────────────────
class SimulationRequest(BaseModel):
    scenario_id: str
    params: Optional[Dict[str, Any]] = None


@app.post("/api/v1/simulation/run")
async def run_simulation(req: SimulationRequest):
    if req.scenario_id not in ScenarioEngine.SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario_id}. Valid: {list(ScenarioEngine.SCENARIOS.keys())}")
    report = scenario_engine.run(req.scenario_id, req.params)
    return report.to_dict()


@app.get("/api/v1/simulation/scenarios")
async def list_scenarios():
    return [{"id": k, "name": v} for k, v in ScenarioEngine.SCENARIOS.items()]


# ── Architecture Health ──────────────────────────────────────────
@app.get("/api/v1/architecture/health")
async def get_architecture_health():
    import json
    from pathlib import Path
    health_file = Path("architecture-health.json")
    if health_file.exists():
        return json.loads(health_file.read_text())
    return {"architecture_score": 0, "issues": 0, "warnings": 0, "critical": 0, "note": "Run architecture_audit.py to generate"}


# ── Events ───────────────────────────────────────────────────────
@app.get("/api/v1/events")
async def list_events(limit: int = 100, severity: Optional[str] = None):
    events = event_engine.get_events(severity=severity, limit=limit)
    return [e.dict() for e in events]


@app.get("/")
async def root():
    return {
        "service": "Mini-LIMS Digital Twin API",
        "version": "1.0.0",
        "docs": "/docs",
        "ws": "/ws/twin-state",
    }

