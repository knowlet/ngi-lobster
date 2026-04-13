# SCHEMA_CONTRACTS

## Purpose

Define the minimum shared objects all packages should agree on before deeper migration.

## Required core objects

### `EvidenceRecord`
Represents raw or normalized evidence.

Fields:
- `schema_version`
- `record_id`
- `source_id`
- `source_type`
- `created_at_utc`
- `provenance`
- `source_path` or `source_url`
- `collected_at_utc`
- `checksum`
- `metadata`

### `CompiledPage`
Represents a compiled knowledge artifact.

Fields:
- `page_id`
- `title`
- `page_type`
- `compiled_from`
- `confidence`
- `tags`
- `metadata`

### `RuntimeSnapshot`
Represents the runtime state at a given moment.

Fields:
- `schema_version`
- `snapshot_id`
- `state`
- `created_at_utc`
- `target_market_id`
- `target_market_name`
- `target_id`
- `target_type`
- `dq_status`
- `freshness_status`
- `ngi`
- `gap_triggered`
- `gap_reason`
- `decision`
- `generated_at_utc`
- `metrics`

### `AlertRecord`
Represents an alert decision and its delivery basis.

Fields:
- `schema_version`
- `alert_id`
- `alert_type`
- `severity`
- `state`
- `disposition`
- `reason_key`
- `runtime_basis`
- `threshold_value`
- `measured_value`
- `dedupe_key`
- `delivered_to`
- `generated_at_utc`
- `metadata`

### `DriftReport`
Represents detected divergence between layers.

Fields:
- `schema_version`
- `drift_id`
- `drift_type`
- `severity`
- `affected_objects`
- `detected_at_utc`
- `suggested_action`
- `metadata`

### `StateTransition`
Represents a change in runtime state.

Fields:
- `schema_version`
- `transition_id`
- `from_state`
- `to_state`
- `reason`
- `actor`
- `trigger`
- `source_snapshot_id`
- `recorded_at_utc`
- `metadata`

## Enumerations

### Runtime states
- `PRE_AGREEMENT`
- `ACTIVE_TRUCE`
- `DISPUTED_TRUCE`
- `ESCALATION`

### Confidence
- `high`
- `medium`
- `low`

### Drift types
- `evidence_vs_compiled`
- `compiled_vs_machine_memory`
- `runtime_vs_target`
- `delivered_vs_runtime`

### Alert disposition
- `triggered`
- `suppressed`

### DQ status
- `pass`
- `warn`
- `fail`

### Freshness status
- `fresh`
- `stale`
- `unknown`
