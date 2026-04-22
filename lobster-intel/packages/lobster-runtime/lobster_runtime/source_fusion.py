from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fusion import FusionComputationInput, FusionComputationResult, build_fusion_result

_FIREHOSE_PRIORITY_WEIGHTS = {
    "low": 0.25,
    "medium": 0.5,
    "med": 0.5,
    "normal": 0.5,
    "high": 0.75,
    "urgent": 1.0,
    "critical": 1.0,
    "sev1": 1.0,
}
_FIREHOSE_PEACE_TAGS = {
    "ceasefire",
    "deescalation",
    "diplomacy",
    "humanitarian",
    "negotiation",
    "negotiations",
    "talks",
    "truce",
    "withdrawal",
}
_FIREHOSE_ESCALATION_TAGS = {
    "airstrike",
    "airstrikes",
    "airspace",
    "attack",
    "attacks",
    "conflict",
    "escalation",
    "military",
    "missile",
    "missiles",
    "strike",
    "strikes",
}


@dataclass(slots=True)
class SourceFusionInput:
    official_statements: dict[str, Any] | None
    watchlist: dict[str, Any] | None
    firehose: dict[str, Any] | None
    polymarket: dict[str, Any] | None
    dq_status: str = "pass"
    freshness_status: str = "fresh"
    state: str = "ACTIVE_TRUCE"
    logic_summary: str = "Cross-source fusion from source runtime artifacts"
    target_resolution_mode: str = "source_runtime_fusion"


@dataclass(slots=True)
class SourceFusionArtifacts:
    official_statements_path: Path
    watchlist_path: Path
    firehose_path: Path
    polymarket_path: Path


def _load_artifact(path: Path, *, optional: bool = False) -> dict[str, Any] | None:
    if optional and not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _items(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    evidence = payload.get("evidence") or {}
    items = evidence.get("items") or []
    return items if isinstance(items, list) else []


def _latest_ts(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    return payload.get("ran_at_utc") or ((payload.get("evidence") or {}).get("cursor"))


def _source_run_id(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    run_id = payload.get("run_id")
    if run_id is None:
        return None
    text = str(run_id).strip()
    return text or None


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _latest_item_ts(items: list[dict[str, Any]], field: str) -> str | None:
    latest_value: str | None = None
    latest_dt: datetime | None = None
    for item in items:
        raw_value = item.get(field)
        parsed = _parse_ts(raw_value)
        if parsed is None:
            continue
        if latest_dt is None or parsed > latest_dt:
            latest_dt = parsed
            latest_value = str(raw_value)
    return latest_value


def _official_signal_strength(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    return min(0.4, 0.2 + 0.2 * len(items))


def _watchlist_signal_strength(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    return min(0.4, 0.15 + 0.15 * len(items))


def _market_escalation_probability(item: dict[str, Any] | None) -> float | None:
    if not item:
        return None
    metadata = item.get("metadata") or {}
    yes_probability = metadata.get("yes_probability")
    if yes_probability is None:
        return None
    try:
        yes_probability = float(yes_probability)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, 1.0 - yes_probability))


def _firehose_priority_weight(value: Any) -> float:
    if value in (None, ""):
        return 0.5
    return _FIREHOSE_PRIORITY_WEIGHTS.get(str(value).strip().lower(), 0.5)


def _firehose_tag_polarity(item: dict[str, Any]) -> int:
    values = item.get("tags")
    tags = values if isinstance(values, list) else []
    normalized = {str(tag).strip().lower() for tag in tags if str(tag).strip()}
    peace_hits = len(normalized & _FIREHOSE_PEACE_TAGS)
    escalation_hits = len(normalized & _FIREHOSE_ESCALATION_TAGS)
    if peace_hits > escalation_hits:
        return 1
    if escalation_hits > peace_hits:
        return -1
    return 0


def _firehose_peace_score(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0

    total = 0.0
    for item in items:
        polarity = _firehose_tag_polarity(item)
        priority_weight = _firehose_priority_weight(item.get("priority"))
        total += max(0.0, min(1.0, 0.5 + 0.5 * polarity * priority_weight))
    return total / len(items)


def build_source_fusion_result(inp: SourceFusionInput) -> FusionComputationResult:
    official_items = _items(inp.official_statements)
    watchlist_items = _items(inp.watchlist)
    firehose_items = _items(inp.firehose)
    polymarket_items = _items(inp.polymarket)
    market_item = polymarket_items[0] if polymarket_items else None

    official_strength = _official_signal_strength(official_items)
    watchlist_strength = _watchlist_signal_strength(watchlist_items)
    first_principles_escalation_probability = min(1.0, official_strength + watchlist_strength)
    market_escalation_probability = _market_escalation_probability(market_item)
    firehose_source_run_id = _source_run_id(inp.firehose)
    firehose_latest_event_at_utc = _latest_item_ts(firehose_items, "published_at_utc")
    firehose_latest_collected_at_utc = _latest_item_ts(firehose_items, "collected_at_utc")
    firehose_peace_score = _firehose_peace_score(firehose_items)

    metadata = (market_item or {}).get("metadata") or {}
    source_config = metadata.get("source_config") or {}
    timestamp_utc = max(
        [
            ts
            for ts in [
                _latest_ts(inp.official_statements),
                _latest_ts(inp.watchlist),
                _latest_ts(inp.firehose),
                _latest_ts(inp.polymarket),
            ]
            if ts
        ],
        default=_utcnow(),
    )

    target = {
        "type": "polymarket" if market_item else None,
        "market_id": metadata.get("market_id") or (market_item or {}).get("external_id"),
        "market_slug": metadata.get("slug") or (market_item or {}).get("url"),
        "market_name": source_config.get("label") or (market_item or {}).get("title"),
    }
    target_detail = {
        "platform": "polymarket" if market_item else None,
        "market_id": target["market_id"],
        "market_slug": target["market_slug"],
        "market_question": (market_item or {}).get("title"),
        "market_yes_probability": metadata.get("yes_probability"),
        "market_closed": metadata.get("closed"),
        "market_active": metadata.get("active"),
        "probability_mode": "yes_is_peace",
    }

    return build_fusion_result(
        FusionComputationInput(
            timestamp_utc=timestamp_utc,
            state=inp.state,
            logic_summary=inp.logic_summary,
            target_resolution_mode=inp.target_resolution_mode,
            target=target,
            target_detail=target_detail,
            adsb_count=len(watchlist_items),
            adsb_peace_score=None,
            adsb_used=False,
            firehose_events_analyzed=len(firehose_items),
            firehose_peace_score=firehose_peace_score,
            firehose_source_run_id=firehose_source_run_id,
            firehose_latest_event_at_utc=firehose_latest_event_at_utc,
            firehose_latest_collected_at_utc=firehose_latest_collected_at_utc,
            adsb_weight=0.5,
            firehose_weight=0.5,
            first_principles_probability=max(0.0, min(1.0, 1.0 - first_principles_escalation_probability)),
            first_principles_escalation_probability=first_principles_escalation_probability,
            market_escalation_probability=market_escalation_probability,
            dq_status=inp.dq_status,
            freshness_status=inp.freshness_status,
        )
    )


def load_source_fusion_artifacts(paths: SourceFusionArtifacts) -> SourceFusionInput:
    return SourceFusionInput(
        official_statements=_load_artifact(paths.official_statements_path),
        watchlist=_load_artifact(paths.watchlist_path),
        firehose=_load_artifact(paths.firehose_path, optional=True),
        polymarket=_load_artifact(paths.polymarket_path),
    )
