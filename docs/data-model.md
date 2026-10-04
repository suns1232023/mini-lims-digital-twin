
# Data Model — Mini-LIMS Digital Twin Platform

**Version:** 1.0.0

---

## 1. PostgreSQL Schema

### assets
```sql
CREATE TABLE assets (
    id          VARCHAR(32) PRIMARY KEY,   -- e.g. INC-03
    type        VARCHAR(64) NOT NULL,      -- incubator | autoclave | pass_box | ...
    name        VARCHAR(128) NOT NULL,
    room_id     VARCHAR(32) REFERENCES rooms(id),
    current_state JSONB NOT NULL DEFAULT '{}',
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### rooms
```sql
CREATE TABLE rooms (
    id          VARCHAR(32) PRIMARY KEY,   -- e.g. R-01
    name        VARCHAR(128) NOT NULL,
    zone        VARCHAR(32) NOT NULL,      -- clean | buffer | change | support
    bsl_level   VARCHAR(16),
    clean_grade VARCHAR(32),              -- ISO 5 | ISO 7 | ...
    area_sqm    NUMERIC(8,2),
    metadata    JSONB NOT NULL DEFAULT '{}'
);
```

### samples
```sql
CREATE TABLE samples (
    id              VARCHAR(32) PRIMARY KEY,  -- e.g. SMP-0001
    barcode         VARCHAR(64) UNIQUE,
    current_state   VARCHAR(32) NOT NULL DEFAULT 'REGISTERED',
    workflow_id     VARCHAR(32) REFERENCES workflow_instances(id),
    customer_id     VARCHAR(64),
    product_id      VARCHAR(64),
    batch_id        VARCHAR(64),
    test_method_id  VARCHAR(64),
    operator_id     VARCHAR(64),
    equipment_id    VARCHAR(32) REFERENCES assets(id),
    room_id         VARCHAR(32) REFERENCES rooms(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB NOT NULL DEFAULT '{}'
);
```

### events
```sql
CREATE TABLE events (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      VARCHAR(128) NOT NULL,
    source          VARCHAR(64) NOT NULL,
    asset_id        VARCHAR(32),
    sample_id       VARCHAR(32),
    previous_state  JSONB,
    new_state       JSONB,
    payload         JSONB NOT NULL DEFAULT '{}',
    severity        VARCHAR(16) NOT NULL DEFAULT 'INFO',
    correlation_id  UUID NOT NULL
);
-- Immutable: no UPDATE or DELETE allowed on this table
```

### alarms
```sql
CREATE TABLE alarms (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id         VARCHAR(64) NOT NULL,
    asset_id        VARCHAR(32),
    sample_id       VARCHAR(32),
    severity        VARCHAR(16) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(64),
    resolved_at     TIMESTAMPTZ,
    payload         JSONB NOT NULL DEFAULT '{}'
);
```

### workflow_instances
```sql
CREATE TABLE workflow_instances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_def_id VARCHAR(64) NOT NULL,
    entity_type     VARCHAR(32) NOT NULL,  -- sample | asset
    entity_id       VARCHAR(32) NOT NULL,
    current_state   VARCHAR(64) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}'
);
```

### audit_logs
```sql
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor       VARCHAR(64) NOT NULL,
    action      VARCHAR(128) NOT NULL,
    entity_type VARCHAR(32),
    entity_id   VARCHAR(32),
    details     JSONB NOT NULL DEFAULT '{}',
    correlation_id UUID
);
```

---

## 2. TimescaleDB Hypertable (Telemetry)

```sql
CREATE TABLE telemetry (
    time        TIMESTAMPTZ NOT NULL,
    asset_id    VARCHAR(32) NOT NULL,
    metric      VARCHAR(64) NOT NULL,   -- temperature | pressure | humidity | ...
    value       DOUBLE PRECISION NOT NULL,
    unit        VARCHAR(16),
    quality     VARCHAR(16) DEFAULT 'GOOD'
);
SELECT create_hypertable('telemetry', 'time');
CREATE INDEX ON telemetry (asset_id, time DESC);
```

---

## 3. Digital Twin State Schema (Pydantic)

```python
class AssetState(BaseModel):
    asset_id: str
    asset_type: str
    status: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    door: Optional[str] = None
    countdown: Optional[int] = None
    last_event: Optional[str] = None
    updated_at: datetime

class SampleDigitalThread(BaseModel):
    sample_id: str
    current_state: str
    customer_id: Optional[str]
    product_id: Optional[str]
    batch_id: Optional[str]
    test_method_id: Optional[str]
    operator_id: Optional[str]
    equipment_id: Optional[str]
    environmental_conditions: Optional[dict]
    raw_data: Optional[dict]
    deviations: List[dict]
    events: List[EventRecord]
    final_result: Optional[str]
```

---

## 4. Redis Cache Keys (Optional)

```
twin:state:{asset_id}          → current AssetState JSON (TTL: 30s)
twin:alarms:active             → Set of active alarm IDs
twin:ws:clients                → Set of connected WebSocket client IDs
sim:scenario:{scenario_id}     → Simulation run state
```
