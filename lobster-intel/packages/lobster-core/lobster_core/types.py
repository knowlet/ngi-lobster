from enum import StrEnum


class RuntimeState(StrEnum):
    PRE_AGREEMENT = "PRE_AGREEMENT"
    ACTIVE_TRUCE = "ACTIVE_TRUCE"
    DISPUTED_TRUCE = "DISPUTED_TRUCE"
    ESCALATION = "ESCALATION"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DriftType(StrEnum):
    EVIDENCE_VS_COMPILED = "evidence_vs_compiled"
    COMPILED_VS_MACHINE_MEMORY = "compiled_vs_machine_memory"
    RUNTIME_VS_TARGET = "runtime_vs_target"
    DELIVERED_VS_RUNTIME = "delivered_vs_runtime"


class AlertDisposition(StrEnum):
    TRIGGERED = "triggered"
    SUPPRESSED = "suppressed"


class DQStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"
