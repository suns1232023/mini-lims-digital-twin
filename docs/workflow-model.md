
# Workflow Model — Mini-LIMS Digital Twin Platform

**Version:** 1.0.0

---

## 1. Design Principles

- Workflows are **state-machine based** — no arbitrary transitions
- Definitions are **configurable via YAML** — not hard-coded
- Every transition is **validated** before execution
- Every action generates an **audit trail event**
- **Blocking conditions** prevent invalid state progression
- **Timeout handlers** escalate stalled workflows

---

## 2. Sample Lifecycle Workflow

```
REGISTERED → RECEIVED → PREPARED → TESTING → INCUBATING → READING → REVIEW → APPROVED → REPORTED → ARCHIVED
                                                                              ↓
                                                                           REJECTED → PREPARED (re-test)
```

### Transition Table

| From | To | Condition | Timeout |
|------|----|-----------|---------|
| REGISTERED | RECEIVED | Sample physically received | 24h |
| RECEIVED | PREPARED | Preparation complete | 4h |
| PREPARED | TESTING | Test method assigned + equipment available | 2h |
| TESTING | INCUBATING | Inoculation complete | 30min |
| INCUBATING | READING | Incubation period elapsed | per method |
| READING | REVIEW | Reading recorded | 2h |
| REVIEW | APPROVED | QA approval | 8h |
| REVIEW | REJECTED | QA rejection | 8h |
| APPROVED | REPORTED | Report generated | 4h |
| REPORTED | ARCHIVED | Retention period set | — |
| REJECTED | PREPARED | Re-test initiated | 24h |

---

## 3. Autoclave Workflow

```
IDLE → LOADING → RUNNING → COOLING → COMPLETED → RELEASED

Failure path:
RUNNING → ERROR → SAFE_STATE → MAINTENANCE → VALIDATION → RELEASED
```

### Transition Table

| From | To | Condition |
|------|----|-----------|
| IDLE | LOADING | Operator initiates load |
| LOADING | RUNNING | Door sealed + cycle selected |
| RUNNING | COOLING | Cycle time elapsed |
| RUNNING | ERROR | Temperature/pressure fault |
| COOLING | COMPLETED | Temperature ≤ 60°C |
| COMPLETED | RELEASED | Operator releases |
| ERROR | SAFE_STATE | Emergency stop confirmed |
| SAFE_STATE | MAINTENANCE | Maintenance team assigned |
| MAINTENANCE | VALIDATION | Repair complete |
| VALIDATION | RELEASED | Validation passed |

---

## 4. Incubator Workflow

```
IDLE → LOADED → INCUBATING → COMPLETED → RELEASED
                    ↓
                  ERROR → SAFE_STATE
```

### Transition Table

| From | To | Condition |
|------|----|-----------|
| IDLE | LOADED | Sample placed |
| LOADED | INCUBATING | Door closed + temp stable |
| INCUBATING | COMPLETED | Incubation period elapsed |
| INCUBATING | ERROR | Temperature excursion > threshold |
| COMPLETED | RELEASED | Sample removed |
| ERROR | SAFE_STATE | Alarm acknowledged |

---

## 5. Pass-Box (Transfer Window) Workflow

```
IDLE → LOCKED → UV_DISINFECTING → OPEN → TRANSFERRING → CLOSED → IDLE

Interlock violation:
OPEN (side A) + OPEN (side B) → INTERLOCK_ALARM
```

---

## 6. Workflow Engine Capabilities

| Capability | Description |
|-----------|-------------|
| Valid transitions | Only defined transitions allowed |
| Invalid transitions | Rejected with WORKFLOW_FAILED event |
| Timeouts | Configurable per step, escalates to alarm |
| Blocking conditions | Equipment unavailable, alarm active |
| Approval gates | QA approval required before APPROVED |
| Recovery paths | Defined for all failure states |
| Audit trail | Every transition logged as immutable event |
| Configuration | Defined in `config/workflows.yaml` |

---

## 7. Workflow Configuration Format

```yaml
# config/workflows.yaml
workflows:
  - id: sample_lifecycle
    name: Sample Lifecycle
    initial_state: REGISTERED
    states:
      - REGISTERED
      - RECEIVED
      - PREPARED
      - TESTING
      - INCUBATING
      - READING
      - REVIEW
      - APPROVED
      - REJECTED
      - REPORTED
      - ARCHIVED
    transitions:
      - from: REGISTERED
        to: RECEIVED
        timeout_hours: 24
        event: SAMPLE_RECEIVED
      - from: RECEIVED
        to: PREPARED
        timeout_hours: 4
        event: SAMPLE_PREPARED
      # ... additional transitions
```

