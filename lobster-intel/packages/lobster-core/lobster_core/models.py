from dataclasses import dataclass, field
from typing import Any

from .types import (
    AlertDisposition,
    ConfidenceLevel,
    DQStatus,
    DriftType,
    FreshnessStatus,
    RuntimeState,
)


@dataclass(slots=True)
class Provenance:
    source_ids: list[str] = field(default_factory=list)
    source_paths: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    parent_record_id: str | None = None
    run_id: str | None = None
    checksum: str | None = None


@dataclass(slots=True)
class EvidenceRecord:
    schema_version: str
    record_id: str
    source_id: str
    source_type: str
    created_at_utc: str
    provenance: Provenance
    source_path: str | None = None
    source_url: str | None = None
    collected_at_utc: str | None = None
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompiledPage:
    schema_version: str
    page_id: str
    title: str
    page_type: str
    updated_at_utc: str | None = None
    compiled_from: list[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeSnapshot:
    schema_version: str
    snapshot_id: str
    state: RuntimeState
    created_at_utc: str
    target_market_id: str | None = None
    target_market_name: str | None = None
    target_id: str | None = None
    target_type: str | None = None
    dq_status: DQStatus = DQStatus.WARN
    freshness_status: FreshnessStatus = FreshnessStatus.UNKNOWN
    ngi: float | None = None
    gap_triggered: bool = False
    gap_reason: str | None = None
    decision: str | None = None
    generated_at_utc: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AlertRecord:
    schema_version: str
    alert_id: str
    alert_type: str
    severity: str
    state: RuntimeState
    disposition: AlertDisposition
    reason_key: str
    runtime_basis: str
    threshold_value: float | None = None
    measured_value: float | None = None
    dedupe_key: str | None = None
    delivered_to: list[str] = field(default_factory=list)
    generated_at_utc: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DriftReport:
    schema_version: str
    drift_id: str
    drift_type: DriftType
    severity: str
    affected_objects: list[str] = field(default_factory=list)
    detected_at_utc: str | None = None
    suggested_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StateTransition:
    schema_version: str
    transition_id: str
    from_state: RuntimeState | None
    to_state: RuntimeState
    reason: str
    actor: str | None = None
    trigger: str | None = None
    source_snapshot_id: str | None = None
    recorded_at_utc: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
