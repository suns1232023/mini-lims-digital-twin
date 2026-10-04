
# Mini-LIMS Digital Twin Platform — Architecture Document

**Version:** 1.0.0  
**Date:** 2026-10-04  
**Status:** Active  
**Repository:** https://github.com/suns1232023/mini-lims-digital-twin

---

## 1. Executive Summary

This document describes the target architecture for transforming the Mini-LIMS Digital Twin prototype from a single-file interactive visualization into a modular, event-driven, simulation-capable Digital Twin platform for microbiology laboratory management.

**Core Philosophy:**
```
MODEL → GENERATE → TEST → SIMULATE → AUDIT → IMPROVE
```

---

## 2. Architecture Layers

### Layer 1: Presentation Layer
- Vue 3 + TypeScript + Vite
- SVG-based 2D spatial visualization (current)
- Three.js 3D visualization (future Phase 13)
- Tailwind CSS
- Components: DigitalTwinMap, AssetPanel, SamplePanel, WorkflowPanel, AlarmPanel, EventTimeline, SimulationPanel, ArchitectureHealthPanel, EnvironmentPanel
- **UI is observer only — never source of truth**

### Layer 2: Digital Twin Core
- Centralized state engine
- Asset registry with identity, metadata, current state, historical state
- Telemetry ingestion
- Event emission on every state change
- Location and relationship tracking

### Layer 3: LIMS Domain Layer
- Sample lifecycle management (REGISTERED → ARCHIVED)
- Digital thread per sample
- Test method assignment
- Operator and equipment linkage
- Deviation tracking

### Layer 4: Workflow Engine
- State-machine-based workflow definitions
- Valid/invalid transition enforcement
- Timeout handling
- Blocking condition evaluation
- Approval gates
- Recovery paths
- Audit trail generation

### Layer 5: Event Engine
- Event store abstraction (PostgreSQL initially)
- Immutable event records
- Correlation ID tracking
- Event replay capability
- WebSocket broadcast to frontend

### Layer 6: Rules Engine
- Declarative YAML-defined rules
- Threshold evaluation
- Alarm creation
- Sample excursion marking
- QA notification triggers
- Independent testability

### Layer 7: Simulation Engine
- Deterministic scenario execution
- 9 standard scenarios (A–I)
- Event sequence generation
- State transition recording
- Simulation reports
- Regression test generation

### Layer 8: Data Layer
- PostgreSQL: assets, rooms, samples, workflows, events, alarms, audit_logs
- TimescaleDB: high-frequency telemetry (temperature, pressure, humidity)
- Redis: optional real-time state cache

### Layer 9: Integration Layer
- MQTT abstraction (initially backed by simulator)
- REST API v1 (versioned)
- WebSocket for real-time push
- Modbus TCP adapter (future)

### Layer 10: Automated Test Layer
- Pytest (backend unit + integration)
- Vitest (frontend unit)
- Playwright (E2E, if appropriate)
- Simulation regression tests

### Layer 11: Architecture Governance Layer
- `scripts/architecture_audit.py`
- `architecture-health.json`
- Schema consistency checks
- Workflow transition validation
- Missing test detection

### Layer 12: AI-Assisted Improvement Layer
- AI agent interface via `architecture.yaml` + config + test results
- Produces `architecture-proposal.yaml` + `architecture-review.md`
- Human architect approval required before any major change

---

## 3. Key Design Principles

1. **UI is observer only** — business logic never lives in SVG/Vue components
2. **Digital Twin State Engine is source of truth** — all state changes go through it
3. **Every state change emits an event** — full traceability
4. **Configuration over code** — new assets created via YAML, not code changes
5. **Explicit state machines** — no arbitrary UI state variables
6. **Immutable event history** — current_state and event_history are separate
7. **Staged migration** — 13 phases, test after every major change

---

## 4. Directory Structure

```
mini-lims-digital-twin/
├── docs/
│   ├── architecture.md          # This document
│   ├── architecture.yaml        # Machine-readable architecture model
│   ├── data-model.md
│   ├── event-model.md
│   ├── workflow-model.md
│   └── ADR/                     # Architecture Decision Records
├── config/
│   ├── assets.yaml
│   ├── rooms.yaml
│   ├── workflows.yaml
│   ├── rules.yaml
│   ├── thresholds.yaml
│   └── sensors.yaml
├── twin/
│   ├── entities/                # Digital Twin entity definitions
│   ├── schemas/                 # Pydantic schemas
│   ├── states/                  # State machine definitions
│   └── registry/                # Asset registry
├── backend/
│   ├── api/v1/                  # FastAPI versioned routes
│   ├── core/                    # Event engine, workflow engine, rules engine
│   ├── db/                      # SQLAlchemy models
│   └── services/                # Business services
├── simulation/
│   ├── scenarios/               # Scenario A–I definitions
│   ├── generators/              # Data generators
│   ├── sensors/                 # Sensor simulators
│   └── reports/                 # Simulation output reports
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── simulation/
│   └── regression/
├── scripts/
│   └── architecture_audit.py
├── frontend/
│   └── src/
│       └── components/
├── .github/
│   └── workflows/
│       ├── test.yml
│       ├── lint.yml
│       ├── build.yml
│       ├── simulation.yml
│       ├── schema-validation.yml
│       ├── architecture-check.yml
│       └── regression.yml
├── architecture-health.json
├── docker-compose.yml
└── index.html                   # Legacy prototype (preserved)
```

---

## 5. Migration Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Extract domain model | Planned |
| 2 | Create Digital Twin state engine | Planned |
| 3 | Create event engine | Planned |
| 4 | Create workflow engine | Planned |
| 5 | Create configuration-driven model | Planned |
| 6 | Move frontend to Vue/TypeScript | Planned |
| 7 | Add FastAPI | Planned |
| 8 | Add simulation engine | Planned |
| 9 | Add automated tests | Planned |
| 10 | Add GitHub CI | Planned |
| 11 | Add architecture audit | Planned |
| 12 | Add AI architecture feedback interface | Planned |
| 13 | Add Three.js 3D visualization | Planned |

---

## 6. API Contract Summary

```
GET  /api/v1/assets
GET  /api/v1/assets/{id}
GET  /api/v1/assets/{id}/events
GET  /api/v1/assets/{id}/state
GET  /api/v1/samples
GET  /api/v1/samples/{id}
GET  /api/v1/samples/{id}/thread
GET  /api/v1/workflows/{id}
POST /api/v1/simulation/run
GET  /api/v1/simulation/{id}
GET  /api/v1/architecture/health
WS   /ws/twin-state
```

---

## 7. Completion Criteria

The platform is considered successfully transformed when:

- [ ] UI does not contain core business logic
- [ ] Digital Twin state is centralized
- [ ] Events are traceable via correlation_id
- [ ] Rules are configurable via YAML
- [ ] Simulations are reproducible
- [ ] Failures can be simulated (Scenarios A–I)
- [ ] Recovery paths exist for all failure modes
- [ ] Sample digital threads can be reconstructed
- [ ] Automated tests exist for all critical paths
- [ ] GitHub Actions validates the system on every PR
- [ ] Architecture health can be measured
- [ ] Configuration can create new assets without code changes
- [ ] 2D and future 3D interfaces share the same backend state model
- [ ] AI recommendations are generated from actual evidence
- [ ] No major architectural change is automatically accepted without validation
