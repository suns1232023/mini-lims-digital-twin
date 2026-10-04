
# Event Model — Mini-LIMS Digital Twin Platform

**Version:** 1.0.0

---

## 1. Event Structure

Every event must contain the following fields:

```json
{
  "event_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "event_type": "INCUBATOR_TEMPERATURE_CHANGED",
  "source": "simulator | iot_gateway | api | workflow_engine | rules_engine",
  "asset_id": "INC-03",
  "sample_id": "SMP-0001",
  "previous_state": { "temperature": 37.0 },
  "new_state": { "temperature": 38.6 },
  "payload": {},
  "severity": "INFO | WARNING | ALARM | CRITICAL",
  "correlation_id": "uuid-v4"
}
```

---

## 2. Event Catalogue

### Equipment Events
| Event Type | Trigger | Severity |
|-----------|---------|----------|
| INCUBATOR_TEMPERATURE_CHANGED | Temp reading changes | INFO/WARNING/ALARM |
| INCUBATOR_LOADED | Sample placed in incubator | INFO |
| INCUBATOR_INCUBATION_STARTED | State → INCUBATING | INFO |
| INCUBATOR_INCUBATION_COMPLETED | State → COMPLETED | INFO |
| INCUBATOR_DOOR_OPENED | Door sensor triggered | WARNING |
| AUTOCLAVE_STARTED | State → RUNNING | INFO |
| AUTOCLAVE_COMPLETED | State → COMPLETED | INFO |
| AUTOCLAVE_FAILED | State → ERROR | CRITICAL |
| AUTOCLAVE_COOLING_STARTED | State → COOLING | INFO |
| TRANSFER_WINDOW_OPENED | Pass-box door opened | INFO |
| TRANSFER_WINDOW_CLOSED | Pass-box door closed | INFO |
| TRANSFER_WINDOW_UV_STARTED | UV disinfection started | INFO |
| TRANSFER_WINDOW_INTERLOCK_VIOLATED | Both doors open simultaneously | CRITICAL |

### Sample Events
| Event Type | Trigger | Severity |
|-----------|---------|----------|
| SAMPLE_REGISTERED | New sample created | INFO |
| SAMPLE_RECEIVED | Sample received at lab | INFO |
| SAMPLE_PREPARED | Sample preparation complete | INFO |
| SAMPLE_MOVED | Sample location changed | INFO |
| SAMPLE_INCUBATION_STARTED | Sample enters incubator | INFO |
| SAMPLE_INCUBATION_COMPLETED | Incubation period complete | INFO |
| SAMPLE_READING_STARTED | Reading/measurement started | INFO |
| SAMPLE_APPROVED | QA approval granted | INFO |
| SAMPLE_REJECTED | QA rejection | WARNING |
| SAMPLE_WORKFLOW_TIMEOUT | Step exceeded time limit | ALARM |

### Alarm Events
| Event Type | Trigger | Severity |
|-----------|---------|----------|
| ALARM_CREATED | Rule condition met | WARNING/ALARM/CRITICAL |
| ALARM_ACKNOWLEDGED | Operator acknowledges | INFO |
| ALARM_RESOLVED | Condition cleared | INFO |
| ALARM_ESCALATED | Unacknowledged timeout | CRITICAL |

### Workflow Events
| Event Type | Trigger | Severity |
|-----------|---------|----------|
| WORKFLOW_STARTED | Workflow instance created | INFO |
| WORKFLOW_STEP_COMPLETED | Step transitions | INFO |
| WORKFLOW_BLOCKED | Blocking condition met | WARNING |
| WORKFLOW_RELEASED | Blocking condition cleared | INFO |
| WORKFLOW_COMPLETED | Final state reached | INFO |
| WORKFLOW_FAILED | Invalid transition attempted | ALARM |

### Environmental Events
| Event Type | Trigger | Severity |
|-----------|---------|----------|
| PRESSURE_EXCURSION | Room pressure out of range | ALARM |
| TEMPERATURE_EXCURSION | Room temp out of range | ALARM |
| HUMIDITY_EXCURSION | Room humidity out of range | WARNING |
| SENSOR_FAILURE | Sensor stops reporting | CRITICAL |
| SENSOR_RECOVERED | Sensor resumes reporting | INFO |

---

## 3. Event Store Design

- Events are **immutable** — never overwritten
- `current_state` and `event_history` are **separate concepts**
- Events are stored in PostgreSQL `events` table
- High-frequency telemetry stored in TimescaleDB `telemetry` hypertable
- Events can be replayed to reconstruct any historical state

---

## 4. Traceability Chain

```
Sample → Event → Equipment → Workflow → Alarm → Operator Action → Final Result
```

All linked via `correlation_id` and `sample_id`.

---

## 5. WebSocket Push

All events are broadcast to connected frontend clients via:
```
WS /ws/twin-state
```

Payload format matches the event structure above.

