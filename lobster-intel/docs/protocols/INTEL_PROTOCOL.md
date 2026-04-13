# INTEL_PROTOCOL

## Goal

Define how evidence, compiled knowledge, runtime state, and delivery interact inside Lobster Intel.

## Core rules

### 1. Evidence is immutable
Raw evidence must not be rewritten in place.

Evidence includes:
- source documents
- screenshots
- OCR text
- Firehose events
- market snapshots
- transcripts
- web captures
- raw report inputs

Permitted operations:
- append
- index
- hash
- annotate externally

Forbidden operations:
- overwrite source content as a summary
- mutate evidence to fit later conclusions

### 2. Compiled knowledge is derived
Wiki pages, summaries, schema, and reusable judgments are compiled artifacts.

Rules:
- must point back to evidence
- must include provenance where material claims are made
- may be updated as understanding improves
- must not be treated as the sole truth in fast-moving situations

### 3. Runtime state is explicit
Runtime state must be stored as structured outputs.

Minimum runtime artifacts:
- current state
- monitor target
- DQ status
- freshness status
- alert state
- drift state
- state transition log

### 4. Delivery is downstream only
Delivery renders decisions. It does not decide truth.

Delivery outputs include:
- heartbeat messages
- Telegram notifications
- morning/evening reports
- agent review summaries

## Provenance rules

Every material judgment should be traceable to one or more of:
- evidence path
- source URL
- runtime artifact
- compiled page
- prior alert id

Recommended fields:
- `source_id`
- `source_path`
- `collected_at`
- `compiled_from`
- `runtime_basis`
- `confidence`

## Confidence rules

- `high`: multi-source or directly validated
- `medium`: plausible, partially validated
- `low`: weak source base, uncertain, or inference-heavy

Low confidence claims should be labeled clearly.

## Drift rules

Drift must be treated as a first-class failure mode.

Minimum drift categories:
1. evidence vs compiled knowledge
2. compiled knowledge vs machine memory
3. runtime state vs target configuration
4. delivered alert vs current runtime truth

Every drift report should include:
- drift type
- affected objects
- severity
- detected_at
- suggested repair action

## State rules

The state machine must be explicit and versioned.

Current target states:
- `PRE_AGREEMENT`
- `ACTIVE_TRUCE`
- `DISPUTED_TRUCE`
- `ESCALATION`

Rules:
- no implicit state transitions
- transitions must be logged
- alerts should name the active state used for evaluation

## Plugin contract rules

Plugins must declare:
- id
- version
- type
- entrypoints
- capabilities required
- artifacts produced

Plugins must not:
- silently mutate evidence
- bypass runtime state recording
- send delivery directly without declared capability

## Required sidecars

The system should maintain auditable sidecars such as:
- `index.md`
- `log.md`
- `schema/entities.json`
- `schema/graph.json`
- `schema/tags.json`
- `runtime/alerts.jsonl`
- `runtime/state_transitions.jsonl`
- `runtime/drift_report.json`

## Operating principle

Ground truth order for fast-moving intelligence:
1. raw/live evidence
2. runtime state derived from evidence
3. compiled knowledge
4. delivery text

If these disagree, the system should prefer the higher layer in that order and emit a drift signal.
