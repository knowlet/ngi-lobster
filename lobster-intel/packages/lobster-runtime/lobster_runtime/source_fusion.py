from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fusion import FusionComputationInput, FusionComputationResult, build_fusion_result


@dataclass(slots=True)
class SourceFusionInput:
    official_statements: dict[str, Any] | None
    watchlist: dict[str, Any] | None
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
    polymarket_path: Path


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


def build_source_fusion_result(inp: SourceFusionInput) -> FusionComputationResult:
    official_items = _items(inp.official_statements)
    watchlist_items = _items(inp.watchlist)
    polymarket_items = _items(inp.polymarket)
    market_item = polymarket_items[0] if polymarket_items else None

    official_strength = _official_signal_strength(official_items)
    watchlist_strength = _watchlist_signal_strength(watchlist_items)
    first_principles_escalation_probability = min(1.0, official_strength + watchlist_strength)
    market_escalation_probability = _market_escalation_probability(market_item)

    metadata = (market_item or {}).get("metadata") or {}
    source_config = metadata.get("source_config") or {}
    timestamp_utc = max(
        [ts for ts in [_latest_ts(inp.official_statements), _latest_ts(inp.watchlist), _latest_ts(inp.polymarket)] if ts],
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
            firehose_events_analyzed=len(official_items),
            firehose_peace_score=0.0,
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
        official_statements=json.loads(paths.official_statements_path.read_text(encoding="utf-8")),
        watchlist=json.loads(paths.watchlist_path.read_text(encoding="utf-8")),
        polymarket=json.loads(paths.polymarket_path.read_text(encoding="utf-8")),
    )
