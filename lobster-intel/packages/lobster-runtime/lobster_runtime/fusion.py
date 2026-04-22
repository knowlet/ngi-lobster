from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .service import RuntimeEvaluationInput, evaluate_runtime


@dataclass(slots=True)
class FusionComputationInput:
    timestamp_utc: str
    state: str
    logic_summary: str | None
    target_resolution_mode: str
    target: dict[str, Any] | None
    target_detail: dict[str, Any] | None
    adsb_count: int | None
    adsb_peace_score: float | None
    adsb_used: bool
    firehose_events_analyzed: int
    firehose_peace_score: float
    firehose_source_run_id: str | None
    firehose_latest_event_at_utc: str | None
    firehose_latest_collected_at_utc: str | None
    adsb_weight: float
    firehose_weight: float
    first_principles_probability: float
    first_principles_escalation_probability: float
    market_escalation_probability: float | None
    dq_status: str = "warn"
    freshness_status: str = "unknown"


@dataclass(slots=True)
class FusionComputationResult:
    data: dict[str, Any]
    gap_value: float | None


def build_fusion_result(inp: FusionComputationInput) -> FusionComputationResult:
    runtime = evaluate_runtime(
        RuntimeEvaluationInput(
            snapshot_id=f"ngi:{inp.timestamp_utc}",
            created_at_utc=inp.timestamp_utc,
            state=inp.state,  # type: ignore[arg-type]
            target_market_id=(inp.target or {}).get("market_id"),
            target_market_name=(inp.target or {}).get("market_name") or (inp.target_detail or {}).get("market_question"),
            market_escalation_probability=inp.market_escalation_probability,
            first_principles_escalation_probability=inp.first_principles_escalation_probability,
            dq_status=inp.dq_status,  # type: ignore[arg-type]
            freshness_status=inp.freshness_status,  # type: ignore[arg-type]
        )
    )

    target = inp.target or {}
    result = {
        "timestamp_utc": inp.timestamp_utc,
        "state": inp.state,
        "logic_summary": inp.logic_summary,
        "target_resolution_mode": inp.target_resolution_mode,
        "market_target": {
            "type": target.get("type"),
            "market_id": target.get("market_id"),
            "market_slug": target.get("market_slug"),
            "market_name": target.get("market_name") or (inp.target_detail or {}).get("market_question"),
        },
        "adsb": {
            "count": inp.adsb_count,
            "peace_score": inp.adsb_peace_score,
            "used": inp.adsb_used,
        },
        "firehose": {
            "events_analyzed": inp.firehose_events_analyzed,
            "peace_score": inp.firehose_peace_score,
            "source_run_id": inp.firehose_source_run_id,
            "latest_event_at_utc": inp.firehose_latest_event_at_utc,
            "latest_collected_at_utc": inp.firehose_latest_collected_at_utc,
        },
        "weights": {
            "adsb": inp.adsb_weight,
            "firehose": inp.firehose_weight,
        },
        "first_principles_probability": inp.first_principles_probability,
        "first_principles_escalation_probability": inp.first_principles_escalation_probability,
        "market_escalation_probability": inp.market_escalation_probability,
        "target_detail": inp.target_detail,
        "ngi": runtime.snapshot.ngi,
        "ngi_percentage": runtime.snapshot.ngi * 100 if runtime.snapshot.ngi is not None else None,
        "gap_triggered": runtime.snapshot.gap_triggered,
        "gap_reason": runtime.snapshot.gap_reason,
        "decision": runtime.snapshot.decision,
    }
    return FusionComputationResult(data=result, gap_value=runtime.gap_value)
