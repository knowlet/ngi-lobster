from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class ObservationDraft:
    event_type: str
    stance: str
    entity_refs: list[str] = field(default_factory=list)
    semantic_tags: list[str] = field(default_factory=list)
    extractive_rationale: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _content_ref_value(content_refs: list[dict[str, Any]], kind: str) -> str | None:
    for ref in content_refs:
        if ref.get("kind") == kind:
            return ref.get("value")
    return None


def _observation_metadata(evidence_artifact: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(evidence_artifact.get("metadata") or {})
    content_refs = evidence_artifact.get("content_refs") or []
    if evidence_artifact.get("source_type") == "prediction_market":
        metadata.setdefault("market_id", evidence_artifact.get("external_id"))
        metadata.setdefault("market_slug", _content_ref_value(content_refs, "url"))
        metadata.setdefault("market_question", _content_ref_value(content_refs, "title"))
    return metadata


def _default_analyzer(evidence_artifact: dict[str, Any]) -> ObservationDraft:
    source_type = evidence_artifact["source_type"]
    return ObservationDraft(
        event_type=source_type,
        stance="escalatory_signal",
        entity_refs=[evidence_artifact["external_id"]],
        semantic_tags=list((_observation_metadata(evidence_artifact).get("semantic_tags") or [])),
        extractive_rationale=_content_ref_value(evidence_artifact.get("content_refs") or [], "title")
        or _content_ref_value(evidence_artifact.get("content_refs") or [], "summary"),
        metadata=_observation_metadata(evidence_artifact),
    )


def _prediction_market_analyzer(evidence_artifact: dict[str, Any]) -> ObservationDraft:
    metadata = _observation_metadata(evidence_artifact)
    return ObservationDraft(
        event_type="market_candidate",
        stance="market_snapshot",
        entity_refs=[metadata.get("market_id")] if metadata.get("market_id") else [evidence_artifact["external_id"]],
        semantic_tags=[
            *list(metadata.get("semantic_tags") or []),
            "market_candidate",
            metadata.get("semantic_frame") or "unknown_semantic_frame",
        ],
        extractive_rationale=_content_ref_value(evidence_artifact.get("content_refs") or [], "title")
        or _content_ref_value(evidence_artifact.get("content_refs") or [], "summary"),
        metadata=metadata,
    )


ANALYZERS_BY_SOURCE_TYPE: dict[str, Callable[[dict[str, Any]], ObservationDraft]] = {
    "prediction_market": _prediction_market_analyzer,
}


def analyze_evidence_artifact(evidence_artifact: dict[str, Any]) -> ObservationDraft:
    source_type = evidence_artifact["source_type"]
    analyzer = ANALYZERS_BY_SOURCE_TYPE.get(source_type, _default_analyzer)
    return analyzer(evidence_artifact)
