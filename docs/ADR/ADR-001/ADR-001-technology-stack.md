
# ADR-001: Technology Stack Selection

**Date:** 2026-10-04  
**Status:** Accepted  
**Deciders:** Architecture Team

## Context
The current prototype is a single `index.html` file. We need to select a coherent technology stack for the full platform migration.

## Decision
**Frontend:** Vue 3 + TypeScript + Vite + SVG + Tailwind CSS  
**Backend:** Python + FastAPI + Pydantic + SQLAlchemy  
**Data:** PostgreSQL + TimescaleDB + Redis (optional)  
**Messaging:** MQTT abstraction backed by deterministic simulator initially  
**Testing:** Pytest + Vitest  
**CI:** GitHub Actions  
**Deployment:** Docker + Docker Compose

## Rationale
- Single coherent path avoids NestJS/FastAPI split
- Python ecosystem aligns with scientific/lab domain
- Vue 3 + TypeScript provides type safety without React overhead
- SVG-first avoids premature Three.js complexity
- TimescaleDB extends PostgreSQL — no separate TSDB infrastructure

## Consequences
- Three.js deferred to Phase 13
- Redis is optional — not required for MVP
- Modbus TCP deferred to integration layer
