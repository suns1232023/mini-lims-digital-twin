
# ADR-002: Event-Driven Architecture

**Date:** 2026-10-04  
**Status:** Accepted

## Context
State changes in the current prototype are scattered across UI components with no traceability.

## Decision
Every meaningful state change must generate an immutable event stored in PostgreSQL. Events are broadcast via WebSocket. `current_state` and `event_history` are maintained as separate concepts.

## Rationale
- Full audit trail for GMP/regulatory compliance
- Enables simulation replay
- Decouples UI from business logic
- Supports correlation_id-based traceability

## Consequences
- Event table must never allow UPDATE/DELETE
- All business logic must go through the event engine
- UI becomes a pure observer
