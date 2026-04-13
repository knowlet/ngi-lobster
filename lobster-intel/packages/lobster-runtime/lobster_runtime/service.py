from __future__ import annotations

from dataclasses import dataclass

from lobster_core import DQStatus, FreshnessStatus, RuntimeSnapshot, RuntimeState


@dataclass(slots=True)
class RuntimeEvaluationInput:
    snapshot_id: str
    created_at_utc: str
    state: RuntimeState | str
    target_market_id: str | None
    target_market_name: str | None
    market_escalation_probability: float | None
    first_principles_escalation_probability: float | None
    dq_status: DQStatus | str
    freshness_status: FreshnessStatus | str


@dataclass(slots=True)
class RuntimeEvaluationResult:
    snapshot: RuntimeSnapshot
    gap_value: float | None


def evaluate_runtime(inp: RuntimeEvaluationInput) -> RuntimeEvaluationResult:
    state = inp.state if isinstance(inp.state, RuntimeState) else RuntimeState(str(inp.state))
    dq_status = inp.dq_status if isinstance(inp.dq_status, DQStatus) else DQStatus(str(inp.dq_status))
    freshness_status = (
        inp.freshness_status
        if isinstance(inp.freshness_status, FreshnessStatus)
        else FreshnessStatus(str(inp.freshness_status))
    )

    gap_value = None
    gap_triggered = False
    gap_reason = None
    decision = "hold"

    if (
        inp.market_escalation_probability is not None
        and inp.first_principles_escalation_probability is not None
    ):
        gap_value = abs(inp.first_principles_escalation_probability - inp.market_escalation_probability)
        gap_triggered = gap_value >= 0.15
        if gap_triggered:
            gap_reason = "material_gap_detected"
            decision = "review_or_alert"

    snapshot = RuntimeSnapshot(
        schema_version="v1",
        snapshot_id=inp.snapshot_id,
        state=state,
        created_at_utc=inp.created_at_utc,
        target_market_id=inp.target_market_id,
        target_market_name=inp.target_market_name,
        target_id=inp.target_market_id,
        target_type="polymarket" if inp.target_market_id else None,
        dq_status=dq_status,
        freshness_status=freshness_status,
        ngi=gap_value,
        gap_triggered=gap_triggered,
        gap_reason=gap_reason,
        decision=decision,
        generated_at_utc=inp.created_at_utc,
        metrics={
            "market_escalation_probability": inp.market_escalation_probability,
            "first_principles_escalation_probability": inp.first_principles_escalation_probability,
        },
    )
    return RuntimeEvaluationResult(snapshot=snapshot, gap_value=gap_value)
