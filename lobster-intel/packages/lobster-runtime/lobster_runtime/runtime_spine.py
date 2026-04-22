from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from lobster_delivery import deliver_heartbeat_payload
from .analyzers import analyze_evidence_artifact


SUPPORTED_DIRECTION_NORMALIZATIONS = {
    ("yes_is_peace", "yes_is_escalation"),
    ("yes_is_escalation", "yes_is_peace"),
}

RUNTIME_SOURCE_PLUGIN_IDS = {
    "official_statements": "official-statements-tracker",
    "watchlist": "watchlist-tracker",
    "polymarket": "polymarket-tracker",
}


@dataclass(slots=True)
class ThesisRuntimeInput:
    thesis_id: str
    workspace_dir: str | Path
    official_statements: dict[str, Any] | None = None
    watchlist: dict[str, Any] | None = None
    polymarket: dict[str, Any] | None = None
    target_registry: list[dict[str, Any]] = field(default_factory=list)
    semantic_frame: str = "generic_thesis_frame"
    probability_direction: str = "yes_is_peace"
    state: str = "ACTIVE_TRUCE"
    now_utc: str | None = None
    schema_version: str = "v1"
    contract_version: str = "ngi_runtime_spine.v1"


@dataclass(slots=True)
class ThesisRuntimeResult:
    thesis_id: str
    run_id: str
    runtime_snapshot: dict[str, Any]
    compare_artifact: dict[str, Any]
    alert_artifact: dict[str, Any]
    delivery_receipt: dict[str, Any]
    paths: dict[str, str]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _stable_run_id(now_utc: str) -> str:
    dt = _parse_iso(now_utc)
    if dt is None:
        raise ValueError(f"invalid run timestamp: {now_utc}")
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _workspace_data_dir(workspace_dir: str | Path) -> Path:
    return Path(workspace_dir) / "lobster-intel" / "data"


def _artifact_path(workspace_dir: str | Path, *parts: str) -> Path:
    path = _workspace_data_dir(workspace_dir).joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _runtime_source_latest_path(workspace_dir: str | Path, source_key: str) -> Path:
    return _workspace_data_dir(workspace_dir) / "runtime" / "sources" / RUNTIME_SOURCE_PLUGIN_IDS[source_key] / "latest.json"


def _validate_thesis_id(thesis_id: str | None) -> str | None:
    if thesis_id is None:
        return None
    if re.fullmatch(r"[A-Za-z0-9_-]+", thesis_id):
        return thesis_id
    raise ValueError(f"unsafe thesis_id: {thesis_id!r}")


def _default_registry_candidates(workspace_dir: str | Path, thesis_id: str | None) -> list[Path]:
    thesis_id = _validate_thesis_id(thesis_id)
    if not thesis_id:
        return []
    registry_root = _workspace_data_dir(workspace_dir) / "runtime" / "thesis-registry"
    return [
        registry_root / f"{thesis_id}.json",
        registry_root / thesis_id / "registry.json",
    ]


def _thesis_pack_search_paths(workspace_dir: str | Path, thesis_id: str) -> list[Path]:
    thesis_id = cast(str, _validate_thesis_id(thesis_id))
    root = Path(workspace_dir) / "lobster-intel"
    return [
        root / "data" / "runtime" / "thesis-packs" / f"{thesis_id}.json",
        root / "examples" / "thesis-packs" / f"{thesis_id}.json",
    ]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json_file(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_registry_payload(path: Path) -> list[dict[str, Any]]:
    payload = _load_json_file(path)
    if not isinstance(payload, list) or any(not isinstance(entry, dict) for entry in payload):
        raise ValueError(f"runtime registry file must contain a JSON list of objects: {path}")
    return cast(list[dict[str, Any]], payload)


def _base_artifact(
    artifact_id: str,
    run_id: str,
    thesis_id: str,
    created_at_utc: str,
    provenance: dict[str, Any],
    *,
    schema_version: str,
    contract_version: str,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "artifact_id": artifact_id,
        "run_id": run_id,
        "thesis_id": thesis_id,
        "created_at_utc": created_at_utc,
        "provenance": provenance,
        "contract_version": contract_version,
    }


def _json_checksum(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _payload_items(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    evidence = payload.get("evidence") or {}
    items = evidence.get("items") or []
    return items if isinstance(items, list) else []


def _payload_latest_ts(payloads: list[dict[str, Any] | None], now_utc: str | None) -> str:
    candidates = [_parse_iso(now_utc)] if now_utc else []
    for payload in payloads:
        candidates.append(_parse_iso((payload or {}).get("ran_at_utc")))
        for item in _payload_items(payload):
            candidates.append(_parse_iso(item.get("collected_at_utc")))
    present = [candidate for candidate in candidates if candidate is not None]
    return max(present).astimezone(timezone.utc).isoformat() if present else _iso_now()


def _source_payloads(inp: ThesisRuntimeInput) -> list[tuple[str, dict[str, Any] | None]]:
    return [
        ("official-statements-tracker", inp.official_statements),
        ("watchlist-tracker", inp.watchlist),
        ("polymarket-tracker", inp.polymarket),
    ]


def load_thesis_runtime_inputs(
    workspace_dir: str | Path,
    *,
    thesis_id: str | None = None,
    official_statements_path: str | Path | None = None,
    watchlist_path: str | Path | None = None,
    polymarket_path: str | Path | None = None,
    registry_file: str | Path | None = None,
) -> dict[str, Any]:
    _validate_thesis_id(thesis_id)
    source_specs = {
        "official_statements": official_statements_path,
        "watchlist": watchlist_path,
        "polymarket": polymarket_path,
    }
    source_payloads: dict[str, dict[str, Any] | None] = {}
    source_resolution: dict[str, dict[str, Any]] = {}

    for source_key, explicit_path in source_specs.items():
        if explicit_path is not None:
            source_path = Path(explicit_path)
            if not source_path.exists():
                raise FileNotFoundError(f"missing runtime source artifact: {source_path}")
            source_resolution[source_key] = {"path": str(source_path), "mode": "explicit", "exists": True}
            source_payloads[source_key] = _load_json_file(source_path)
            continue

        source_path = _runtime_source_latest_path(workspace_dir, source_key)
        if source_path.exists():
            source_resolution[source_key] = {"path": str(source_path), "mode": "discovered", "exists": True}
            source_payloads[source_key] = _load_json_file(source_path)
        else:
            source_resolution[source_key] = {"path": str(source_path), "mode": "missing", "exists": False}
            source_payloads[source_key] = None

    missing_sources = [
        f"{source_key}: {details['path']}"
        for source_key, details in source_resolution.items()
        if not details["exists"]
    ]
    if missing_sources:
        raise FileNotFoundError("missing runtime source artifacts:\n" + "\n".join(missing_sources))

    thesis_pack_payload: dict[str, Any] = {}
    thesis_pack_resolution: dict[str, Any] = {"path": None, "mode": "empty", "exists": False}
    if thesis_id:
        thesis_pack_resolution["mode"] = "missing"
        for thesis_pack_path in _thesis_pack_search_paths(workspace_dir, thesis_id):
            if not thesis_pack_path.exists():
                continue
            payload = _load_json_file(thesis_pack_path)
            if not isinstance(payload, dict):
                continue
            thesis_pack_resolution = {"path": str(thesis_pack_path), "mode": "discovered", "exists": True}
            thesis_pack_payload = payload
            break

    registry_payload: list[dict[str, Any]] = []
    registry_resolution: dict[str, Any] = {"path": None, "mode": "empty", "exists": False}
    if registry_file is not None:
        registry_path = Path(registry_file)
        if not registry_path.exists():
            raise FileNotFoundError(f"missing runtime registry file: {registry_path}")
        registry_resolution = {"path": str(registry_path), "mode": "explicit", "exists": True}
        registry_payload = _load_registry_payload(registry_path)
    else:
        for registry_path in _default_registry_candidates(workspace_dir, thesis_id):
            if not registry_path.exists():
                continue
            registry_resolution = {"path": str(registry_path), "mode": "discovered", "exists": True}
            registry_payload = _load_registry_payload(registry_path)
            break
        if not registry_payload and isinstance(thesis_pack_payload.get("target_registry"), list) and thesis_pack_payload.get("target_registry"):
            registry_payload = cast(list[dict[str, Any]], thesis_pack_payload["target_registry"])
            registry_resolution = {
                "path": thesis_pack_resolution["path"],
                "mode": "thesis_pack_discovered",
                "exists": True,
            }

    return {
        "official_statements": source_payloads["official_statements"],
        "watchlist": source_payloads["watchlist"],
        "polymarket": source_payloads["polymarket"],
        "target_registry": registry_payload,
        "source_resolution": source_resolution,
        "registry_resolution": registry_resolution,
        "thesis_pack_resolution": thesis_pack_resolution,
        "thesis_settings": {
            "semantic_frame": thesis_pack_payload.get("semantic_frame"),
            "probability_direction": thesis_pack_payload.get("probability_direction"),
            "state": thesis_pack_payload.get("state"),
        },
    }


def _build_content_refs(item: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for key in ("title", "summary", "description", "content", "url"):
        value = item.get(key)
        if value:
            refs.append({"kind": key, "value": str(value)})
    return refs


def _source_provenance(
    payload: dict[str, Any] | None,
    item: dict[str, Any],
    source_name: str,
    item_checksum: str,
) -> dict[str, Any]:
    evidence = (payload or {}).get("evidence") or {}
    return {
        "source_ids": [item.get("source_id") or source_name],
        "source_paths": [str(evidence.get("state_path"))] if evidence.get("state_path") else [],
        "source_urls": [item.get("url")] if item.get("url") else [],
        "parent_record_id": (payload or {}).get("run_id") or (payload or {}).get("plugin"),
        "run_id": (payload or {}).get("run_id") or (payload or {}).get("ran_at_utc"),
        "checksum": item_checksum,
    }


def _evidence_artifact_id(thesis_id: str, source_name: str, item: dict[str, Any], index: int) -> str:
    external_id = item.get("external_id") or f"{source_name}-{index}"
    return f"evidence:{thesis_id}:{source_name}:{external_id}"


def _build_evidence_artifacts(inp: ThesisRuntimeInput, run_id: str, created_at_utc: str) -> list[dict[str, Any]]:
    evidence_artifacts: list[dict[str, Any]] = []
    for source_name, payload in _source_payloads(inp):
        for index, item in enumerate(_payload_items(payload)):
            checksum = _json_checksum(item)
            artifact_id = _evidence_artifact_id(inp.thesis_id, source_name, item, index)
            artifact = _base_artifact(
                artifact_id,
                run_id,
                inp.thesis_id,
                created_at_utc,
                _source_provenance(payload, item, source_name, checksum),
                schema_version=inp.schema_version,
                contract_version=inp.contract_version,
            )
            artifact.update(
                {
                    "source_id": item.get("source_id") or source_name,
                    "source_type": item.get("source_type") or source_name,
                    "external_id": item.get("external_id") or f"{source_name}-{index}",
                    "collected_at_utc": item.get("collected_at_utc") or (payload or {}).get("ran_at_utc") or created_at_utc,
                    "published_at_utc": item.get("published_at_utc"),
                    "content_refs": _build_content_refs(item),
                    "checksum": checksum,
                    "cursor_lineage": ((payload or {}).get("evidence") or {}).get("cursor_state")
                    or ((payload or {}).get("evidence") or {}).get("cursors")
                    or ((payload or {}).get("evidence") or {}).get("cursor"),
                    "raw_pointer": (payload or {}).get("run_id")
                    or (payload or {}).get("plugin")
                    or source_name,
                    "metadata": item.get("metadata") or {},
                }
            )
            evidence_artifacts.append(artifact)
    return evidence_artifacts


def _signal_strength(source_type: str) -> float:
    if source_type == "official_statement":
        return 0.45
    if source_type in {"analyst_feed", "analyst_watchlist"}:
        return 0.30
    return 0.0


def _observation_from_evidence(
    evidence_artifact: dict[str, Any],
    *,
    thesis_id: str,
    run_id: str,
    created_at_utc: str,
    schema_version: str,
    contract_version: str,
) -> dict[str, Any]:
    source_type = evidence_artifact["source_type"]
    observation_id = evidence_artifact["artifact_id"].replace("evidence:", "observation:")
    draft = analyze_evidence_artifact(evidence_artifact)
    metadata = draft.metadata
    is_market = draft.event_type == "market_candidate"
    observation = _base_artifact(
        observation_id,
        run_id,
        thesis_id,
        created_at_utc,
        {
            "source_ids": evidence_artifact["provenance"].get("source_ids") or [],
            "source_paths": evidence_artifact["provenance"].get("source_paths") or [],
            "source_urls": evidence_artifact["provenance"].get("source_urls") or [],
            "parent_record_id": evidence_artifact["artifact_id"],
            "run_id": run_id,
            "checksum": evidence_artifact["checksum"],
        },
        schema_version=schema_version,
        contract_version=contract_version,
    )
    observation.update(
        {
            "evidence_refs": [evidence_artifact["artifact_id"]],
            "entity_refs": draft.entity_refs or [evidence_artifact["external_id"]],
            "event_type": draft.event_type,
            "stance": draft.stance,
            "time_window": {
                "start_at_utc": evidence_artifact.get("published_at_utc") or evidence_artifact.get("collected_at_utc"),
                "end_at_utc": evidence_artifact.get("collected_at_utc"),
            },
            "location": metadata.get("location"),
            "semantic_tags": draft.semantic_tags,
            "source_confidence": 0.95 if is_market else _signal_strength(source_type) + 0.25,
            "extractive_rationale": draft.extractive_rationale,
            "metadata": metadata,
        }
    )
    return observation


def _build_observations(inp: ThesisRuntimeInput, run_id: str, created_at_utc: str, evidence_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _observation_from_evidence(
            artifact,
            thesis_id=inp.thesis_id,
            run_id=run_id,
            created_at_utc=created_at_utc,
            schema_version=inp.schema_version,
            contract_version=inp.contract_version,
        )
        for artifact in evidence_artifacts
    ]


def _compute_freshness(observations: list[dict[str, Any]], created_at_utc: str) -> str:
    created = _parse_iso(created_at_utc)
    newest = max(
        [
            dt
            for dt in (
                _parse_iso((observation.get("time_window") or {}).get("end_at_utc"))
                for observation in observations
            )
            if dt is not None
        ],
        default=None,
    )
    if created is None or newest is None:
        return "unknown"
    age_hours = (created - newest).total_seconds() / 3600.0
    return "fresh" if age_hours <= 24 else "stale"


def _build_fusion_artifact(inp: ThesisRuntimeInput, run_id: str, created_at_utc: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    used_observations = [obs for obs in observations if obs["event_type"] != "market_candidate"]
    escalation_probability = min(
        1.0,
        sum(
            _signal_strength(obs["event_type"])
            for obs in used_observations
        ),
    )
    p_ai = escalation_probability if inp.probability_direction == "yes_is_escalation" else max(0.0, 1.0 - escalation_probability)
    confidence = round(min(0.95, 0.45 + 0.2 * len(used_observations)), 2)
    freshness = _compute_freshness(observations, created_at_utc)
    fusion_artifact = _base_artifact(
        f"fusion:{inp.thesis_id}:{run_id}",
        run_id,
        inp.thesis_id,
        created_at_utc,
        {
            "source_ids": sorted(
                {
                    source_id
                    for observation in observations
                    for source_id in observation["provenance"].get("source_ids") or []
                }
            ),
            "source_paths": [],
            "source_urls": [],
            "parent_record_id": None,
            "run_id": run_id,
            "checksum": _json_checksum([observation["artifact_id"] for observation in observations]),
        },
        schema_version=inp.schema_version,
        contract_version=inp.contract_version,
    )
    fusion_artifact.update(
        {
            "used_observation_ids": [observation["artifact_id"] for observation in used_observations],
            "suppressed_observation_ids": [observation["artifact_id"] for observation in observations if observation not in used_observations],
            "P_AI": round(p_ai, 6),
            "escalation_view": {
                "probability": round(escalation_probability, 6),
                "used_observation_count": len(used_observations),
                "summary": f"{len(used_observations)} observations contributed to escalation view",
            },
            "feature_contributions": [
                {
                    "observation_id": observation["artifact_id"],
                    "feature": observation["event_type"],
                    "weight": _signal_strength(observation["event_type"]),
                }
                for observation in used_observations
            ],
            "confidence": confidence,
            "freshness": freshness,
            "dq_status": "pass",
            "semantic_frame": inp.semantic_frame,
            "probability_direction": inp.probability_direction,
        }
    )
    return fusion_artifact


def _market_candidates(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for observation in observations:
        if observation["event_type"] != "market_candidate":
            continue
        metadata = observation.get("metadata") or {}
        candidates.append(
            {
                "market_id": metadata.get("market_id"),
                "market_slug": metadata.get("market_slug") or metadata.get("slug"),
                "market_question": metadata.get("market_question") or observation.get("extractive_rationale"),
                "semantic_frame": metadata.get("semantic_frame"),
                "probability_direction": metadata.get("probability_direction"),
                "market_yes_probability": metadata.get("yes_probability"),
                "active": metadata.get("active"),
                "closed": metadata.get("closed"),
                "source_observation_id": observation["artifact_id"],
            }
        )
    return candidates


def _registry_aliases(entry: dict[str, Any]) -> list[str]:
    aliases = entry.get("aliases") or []
    return [str(alias).lower() for alias in aliases]


def _normalize_match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalized_equals(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return _normalize_match_text(left) == _normalize_match_text(right)


def _candidate_matches_registry_entry(entry: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if entry.get("market_id") and candidate.get("market_id") and entry["market_id"] == candidate["market_id"]:
        return True
    if _normalized_equals(entry.get("market_slug"), candidate.get("market_slug")):
        return True
    if _normalized_equals(entry.get("market_question"), candidate.get("market_question")):
        return True

    candidate_slug = candidate.get("market_slug")
    candidate_question = candidate.get("market_question")
    for alias in _registry_aliases(entry):
        if _normalized_equals(alias, candidate_slug) or _normalized_equals(alias, candidate_question):
            return True
    return False


def _enrich_market_candidate_from_registry(
    candidate: dict[str, Any],
    entry: dict[str, Any],
    inp: ThesisRuntimeInput,
) -> dict[str, Any]:
    enriched = dict(candidate)
    enriched["market_slug"] = enriched.get("market_slug") or entry.get("market_slug")
    enriched["market_question"] = enriched.get("market_question") or entry.get("market_question")
    enriched["semantic_frame"] = enriched.get("semantic_frame") or entry.get("semantic_frame") or inp.semantic_frame
    enriched["probability_direction"] = (
        enriched.get("probability_direction") or entry.get("probability_direction") or inp.probability_direction
    )
    return enriched


def _candidate_matches_runtime_contract(inp: ThesisRuntimeInput, candidate: dict[str, Any]) -> bool:
    candidate_frame = candidate.get("semantic_frame")
    if candidate_frame and candidate_frame != inp.semantic_frame:
        return False

    candidate_direction = candidate.get("probability_direction") or inp.probability_direction
    if candidate_direction == inp.probability_direction:
        return True

    return (inp.probability_direction, candidate_direction) in SUPPORTED_DIRECTION_NORMALIZATIONS


def _select_live_search_fallback(
    inp: ThesisRuntimeInput,
    market_candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    aligned_candidates = [
        candidate
        for candidate in market_candidates
        if candidate.get("market_id")
        and not candidate.get("closed")
        and _candidate_matches_runtime_contract(inp, candidate)
    ]
    if not aligned_candidates:
        return None

    active_candidates = [candidate for candidate in aligned_candidates if candidate.get("active") is not False]
    ranked_candidates = active_candidates or aligned_candidates
    return max(
        ranked_candidates,
        key=lambda candidate: (
            candidate.get("active") is not False,
            candidate.get("market_yes_probability") is not None,
            float(candidate.get("market_yes_probability") or 0.0),
        ),
    )


def resolve_active_target(inp: ThesisRuntimeInput, observations: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    market_candidates = _market_candidates(observations)
    if not market_candidates:
        return None, None
    if not inp.target_registry:
        fallback_candidate = _select_live_search_fallback(inp, market_candidates)
        if fallback_candidate is None:
            return None, market_candidates[0]
        resolved = {
            "market_id": fallback_candidate.get("market_id"),
            "market_slug": fallback_candidate.get("market_slug"),
            "market_question": fallback_candidate.get("market_question"),
            "semantic_frame": fallback_candidate.get("semantic_frame") or inp.semantic_frame,
            "probability_direction": fallback_candidate.get("probability_direction") or inp.probability_direction,
            "resolution_mode": "live_search_fallback",
            "resolver_confidence": 0.75,
            "fallback_used": True,
        }
        return resolved, fallback_candidate

    for entry in inp.target_registry:
        for candidate in market_candidates:
            if _candidate_matches_registry_entry(entry, candidate):
                resolved = {
                    "market_id": entry.get("market_id") or candidate.get("market_id"),
                    "market_slug": entry.get("market_slug") or candidate.get("market_slug"),
                    "market_question": entry.get("market_question") or candidate.get("market_question"),
                    "semantic_frame": entry.get("semantic_frame") or inp.semantic_frame,
                    "probability_direction": entry.get("probability_direction") or inp.probability_direction,
                    "resolution_mode": "registry_first",
                    "resolver_confidence": 1.0,
                    "fallback_used": False,
                }
                return resolved, _enrich_market_candidate_from_registry(candidate, entry, inp)

    return None, market_candidates[0]


def _normalized_market_probability(active_target: dict[str, Any] | None, market_candidate: dict[str, Any] | None) -> float | None:
    if not active_target or not market_candidate:
        return None
    try:
        market_yes_probability = market_candidate.get("market_yes_probability")
        if market_yes_probability is None:
            return None
        market_yes_probability = float(market_yes_probability)
    except (TypeError, ValueError):
        return None

    desired_direction = active_target.get("probability_direction")
    candidate_direction = market_candidate.get("probability_direction") or desired_direction
    if candidate_direction == desired_direction:
        return market_yes_probability
    if (desired_direction, candidate_direction) in SUPPORTED_DIRECTION_NORMALIZATIONS:
        return 1.0 - market_yes_probability
    return None


def compare_targets(
    *,
    active_target: dict[str, Any] | None,
    market_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    runtime_target_id = (active_target or {}).get("market_id")
    market_target_id = (market_candidate or {}).get("market_id")
    fallback_reason_codes: list[str] = []

    if active_target is None:
        return {
            "runtime_target_id": None,
            "market_target_id": market_target_id,
            "semantic_alignment_status": "missing_runtime_target",
            "numeric_alignment_status": "unknown",
            "compare_mode": "suppressed",
            "alignment_confidence": 0.0,
            "fallback_reason_codes": ["runtime_target_missing"],
            "operator_actionable_notes": ["Resolver did not produce an active target."],
            "market_candidate": market_candidate,
        }

    if active_target.get("fallback_used"):
        fallback_reason_codes.append("live_search_fallback")

    if market_candidate is None:
        fallback_reason_codes.append("market_candidate_missing")
        return {
            "runtime_target_id": runtime_target_id,
            "market_target_id": None,
            "semantic_alignment_status": "unknown",
            "numeric_alignment_status": "unknown",
            "compare_mode": "suppressed",
            "alignment_confidence": 0.0,
            "fallback_reason_codes": fallback_reason_codes,
            "operator_actionable_notes": ["No market candidate snapshot was available for compare."],
            "market_candidate": None,
        }

    semantic_alignment_status = (
        "aligned"
        if active_target.get("semantic_frame") == market_candidate.get("semantic_frame")
        else "mismatch"
    )

    numeric_alignment_status = "aligned"
    directions = (
        active_target.get("probability_direction"),
        market_candidate.get("probability_direction"),
    )
    if directions[0] != directions[1]:
        if directions in SUPPORTED_DIRECTION_NORMALIZATIONS:
            numeric_alignment_status = "normalized"
            fallback_reason_codes.append("direction_normalized")
        else:
            numeric_alignment_status = "mismatch"
            fallback_reason_codes.append("numeric_direction_mismatch")

    if runtime_target_id != market_target_id:
        fallback_reason_codes.append("target_identity_mismatch")
        compare_mode = "suppressed"
        alignment_confidence = 0.15
    elif semantic_alignment_status == "mismatch":
        fallback_reason_codes.append("semantic_frame_mismatch")
        compare_mode = "suppressed"
        alignment_confidence = 0.2
    elif numeric_alignment_status == "mismatch":
        compare_mode = "suppressed"
        alignment_confidence = 0.2
    elif fallback_reason_codes:
        compare_mode = "degraded_compare"
        alignment_confidence = 0.75
    else:
        compare_mode = "full_compare"
        alignment_confidence = 1.0

    notes = {
        "full_compare": ["Runtime target and market candidate are fully aligned."],
        "degraded_compare": ["Fallback logic or normalization was required before compare."],
        "suppressed": ["Compare was suppressed because target identity or alignment is unsafe."],
    }[compare_mode]
    return {
        "runtime_target_id": runtime_target_id,
        "market_target_id": market_target_id,
        "semantic_alignment_status": semantic_alignment_status,
        "numeric_alignment_status": numeric_alignment_status,
        "compare_mode": compare_mode,
        "alignment_confidence": alignment_confidence,
        "fallback_reason_codes": fallback_reason_codes,
        "operator_actionable_notes": notes,
        "market_candidate": market_candidate,
    }


def _load_prior_runtime_snapshot(workspace_dir: str | Path, thesis_id: str) -> dict[str, Any] | None:
    latest_path = _workspace_data_dir(workspace_dir) / "runtime" / thesis_id / "latest.json"
    if not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def _alert_severity(ngi_gap: float | None) -> str:
    magnitude = abs(ngi_gap or 0.0)
    if magnitude >= 0.25:
        return "high"
    if magnitude >= 0.10:
        return "medium"
    return "low"


def _decide_alert(
    *,
    inp: ThesisRuntimeInput,
    run_id: str,
    created_at_utc: str,
    runtime_snapshot: dict[str, Any],
    compare_artifact: dict[str, Any],
    prior_runtime_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    confidence_gate = runtime_snapshot["confidence"] >= 0.6
    freshness_gate = runtime_snapshot["freshness"] != "stale"
    dq_gate = runtime_snapshot["dq_status"] != "fail"
    compare_mode = runtime_snapshot["compare_mode"]
    ngi_gap = runtime_snapshot["ngi_gap"]

    if compare_mode == "suppressed":
        should_send = False
        reason_code = (compare_artifact["fallback_reason_codes"] or ["suppressed_compare_mode"])[0]
        novelty_basis = "compare_suppressed"
    elif not (confidence_gate and freshness_gate and dq_gate):
        should_send = False
        reason_code = "delivery_gates_closed"
        novelty_basis = "quality_gated"
    elif prior_runtime_snapshot is None:
        should_send = abs(ngi_gap or 0.0) >= 0.15
        reason_code = "first_run_gap_detected" if should_send else "first_run_below_threshold"
        novelty_basis = "first_run"
    elif (
        (prior_runtime_snapshot.get("active_target") or {}).get("market_id")
        != (runtime_snapshot.get("active_target") or {}).get("market_id")
    ):
        should_send = True
        reason_code = "active_target_changed"
        novelty_basis = "target_changed"
    elif abs((prior_runtime_snapshot.get("ngi_gap") or 0.0) - (ngi_gap or 0.0)) >= 0.10:
        should_send = True
        reason_code = "ngi_gap_changed"
        novelty_basis = "gap_changed"
    else:
        should_send = False
        reason_code = "no_material_change"
        novelty_basis = "unchanged"

    alert_artifact = _base_artifact(
        f"alert:{inp.thesis_id}:{run_id}",
        run_id,
        inp.thesis_id,
        created_at_utc,
        {
            "source_ids": [],
            "source_paths": [],
            "source_urls": [],
            "parent_record_id": compare_artifact["artifact_id"],
            "run_id": run_id,
            "checksum": _json_checksum(compare_artifact["artifact_id"]),
        },
        schema_version=inp.schema_version,
        contract_version=inp.contract_version,
    )
    alert_artifact.update(
        {
            "should_send": should_send,
            "reason_code": reason_code,
            "severity": _alert_severity(ngi_gap),
            "novelty_basis": novelty_basis,
            "compare_mode": compare_mode,
            "confidence_gate": confidence_gate,
            "freshness_gate": freshness_gate,
            "dq_gate": dq_gate,
            "compare_artifact_id": compare_artifact["artifact_id"],
        }
    )
    return alert_artifact


def _delivery_payload(
    *,
    inp: ThesisRuntimeInput,
    run_id: str,
    runtime_snapshot: dict[str, Any],
    alert_artifact: dict[str, Any],
    paths: dict[str, str],
) -> dict[str, Any]:
    return {
        "thesis_id": inp.thesis_id,
        "active_target": runtime_snapshot.get("active_target"),
        "compare_mode": runtime_snapshot.get("compare_mode"),
        "P_AI": runtime_snapshot.get("P_AI"),
        "market_implied_probability": runtime_snapshot.get("market_implied_probability"),
        "ngi_gap": runtime_snapshot.get("ngi_gap"),
        "reason_codes": [alert_artifact["reason_code"]],
        "contract_version": inp.contract_version,
        "run_id": run_id,
        "artifact_links": paths,
    }


def _persist_evidence(workspace_dir: str | Path, thesis_id: str, evidence_artifacts: list[dict[str, Any]]) -> None:
    for artifact in evidence_artifacts:
        path = _artifact_path(workspace_dir, "evidence", thesis_id, artifact["source_id"], f"{artifact['artifact_id']}.json")
        _write_json(path, artifact)


def _persist_observations(workspace_dir: str | Path, thesis_id: str, observations: list[dict[str, Any]]) -> None:
    for observation in observations:
        path = _artifact_path(workspace_dir, "compiled", thesis_id, "observations", f"{observation['artifact_id']}.json")
        _write_json(path, observation)


def _build_runtime_snapshot(
    *,
    inp: ThesisRuntimeInput,
    run_id: str,
    created_at_utc: str,
    fusion_artifact: dict[str, Any],
    active_target: dict[str, Any] | None,
    market_candidate: dict[str, Any] | None,
    compare_artifact: dict[str, Any],
) -> dict[str, Any]:
    market_implied_probability = (
        _normalized_market_probability(active_target, market_candidate)
        if compare_artifact["compare_mode"] != "suppressed"
        else None
    )
    p_ai = fusion_artifact["P_AI"]
    ngi_gap = round(p_ai - market_implied_probability, 6) if market_implied_probability is not None else None
    runtime_snapshot = _base_artifact(
        f"runtime:{inp.thesis_id}:{run_id}",
        run_id,
        inp.thesis_id,
        created_at_utc,
        {
            "source_ids": [],
            "source_paths": [],
            "source_urls": [],
            "parent_record_id": fusion_artifact["artifact_id"],
            "run_id": run_id,
            "checksum": _json_checksum(fusion_artifact["artifact_id"]),
        },
        schema_version=inp.schema_version,
        contract_version=inp.contract_version,
    )
    runtime_snapshot.update(
        {
            "state": inp.state,
            "active_target": active_target,
            "target_resolution_mode": (active_target or {}).get("resolution_mode"),
            "P_AI": p_ai,
            "market_implied_probability": market_implied_probability,
            "compare_mode": compare_artifact["compare_mode"],
            "ngi_gap": ngi_gap,
            "decision_basis": {
                "fusion_artifact_id": fusion_artifact["artifact_id"],
                "compare_artifact_id": compare_artifact["artifact_id"],
                "semantic_frame": inp.semantic_frame,
                "probability_direction": inp.probability_direction,
                "fallback_reason_codes": compare_artifact["fallback_reason_codes"],
            },
            "confidence": fusion_artifact["confidence"],
            "freshness": fusion_artifact["freshness"],
            "dq_status": fusion_artifact["dq_status"],
        }
    )
    return runtime_snapshot


def run_thesis_runtime(inp: ThesisRuntimeInput) -> ThesisRuntimeResult:
    inp.thesis_id = cast(str, _validate_thesis_id(inp.thesis_id))
    created_at_utc = _payload_latest_ts(
        [inp.official_statements, inp.watchlist, inp.polymarket],
        inp.now_utc,
    )
    run_id = _stable_run_id(created_at_utc)
    evidence_artifacts = _build_evidence_artifacts(inp, run_id, created_at_utc)
    observations = _build_observations(inp, run_id, created_at_utc, evidence_artifacts)
    fusion_artifact = _build_fusion_artifact(inp, run_id, created_at_utc, observations)
    active_target, market_candidate = resolve_active_target(inp, observations)
    compare_artifact = _base_artifact(
        f"compare:{inp.thesis_id}:{run_id}",
        run_id,
        inp.thesis_id,
        created_at_utc,
        {
            "source_ids": [],
            "source_paths": [],
            "source_urls": [],
            "parent_record_id": fusion_artifact["artifact_id"],
            "run_id": run_id,
            "checksum": _json_checksum([active_target, market_candidate]),
        },
        schema_version=inp.schema_version,
        contract_version=inp.contract_version,
    )
    compare_artifact.update(compare_targets(active_target=active_target, market_candidate=market_candidate))
    runtime_snapshot = _build_runtime_snapshot(
        inp=inp,
        run_id=run_id,
        created_at_utc=created_at_utc,
        fusion_artifact=fusion_artifact,
        active_target=active_target,
        market_candidate=market_candidate,
        compare_artifact=compare_artifact,
    )
    prior_runtime_snapshot = _load_prior_runtime_snapshot(inp.workspace_dir, inp.thesis_id)
    alert_artifact = _decide_alert(
        inp=inp,
        run_id=run_id,
        created_at_utc=created_at_utc,
        runtime_snapshot=runtime_snapshot,
        compare_artifact=compare_artifact,
        prior_runtime_snapshot=prior_runtime_snapshot,
    )

    runtime_run_path = _artifact_path(inp.workspace_dir, "runtime", inp.thesis_id, "runs", f"{run_id}.json")
    runtime_latest_path = _artifact_path(inp.workspace_dir, "runtime", inp.thesis_id, "latest.json")
    compare_path = _artifact_path(inp.workspace_dir, "runtime", inp.thesis_id, "compare", f"{run_id}.json")
    fusion_path = _artifact_path(inp.workspace_dir, "compiled", inp.thesis_id, "fusion", f"{run_id}.json")
    alert_path = _artifact_path(inp.workspace_dir, "delivery", inp.thesis_id, "alerts", f"{run_id}.json")
    receipt_path = _artifact_path(inp.workspace_dir, "delivery", inp.thesis_id, "receipts", f"{run_id}.json")
    paths = {
        "runtime_run": str(runtime_run_path),
        "runtime_latest": str(runtime_latest_path),
        "compare": str(compare_path),
        "fusion": str(fusion_path),
        "alert": str(alert_path),
        "delivery_receipt": str(receipt_path),
    }

    delivery_payload = _delivery_payload(
        inp=inp,
        run_id=run_id,
        runtime_snapshot=runtime_snapshot,
        alert_artifact=alert_artifact,
        paths=paths,
    )
    delivery_boundary = deliver_heartbeat_payload(delivery_payload, send=alert_artifact["should_send"])
    delivery_receipt = _base_artifact(
        f"receipt:{inp.thesis_id}:{run_id}",
        run_id,
        inp.thesis_id,
        created_at_utc,
        {
            "source_ids": [],
            "source_paths": [],
            "source_urls": [],
            "parent_record_id": alert_artifact["artifact_id"],
            "run_id": run_id,
            "checksum": _json_checksum(delivery_boundary),
        },
        schema_version=inp.schema_version,
        contract_version=inp.contract_version,
    )
    delivery_receipt.update(
        {
            "sink": "openclaw_heartbeat",
            "delivery_status": "delivered" if alert_artifact["should_send"] else "suppressed",
            "dispatch_time_utc": created_at_utc,
            "delivered_at_utc": created_at_utc if alert_artifact["should_send"] else None,
            "sink_receipt_id": delivery_boundary["proof_id"],
            "alert_artifact_id": alert_artifact["artifact_id"],
            "run_id": run_id,
            "boundary_output": delivery_boundary["output"],
            "delivery_proof": delivery_boundary,
        }
    )

    _persist_evidence(inp.workspace_dir, inp.thesis_id, evidence_artifacts)
    _persist_observations(inp.workspace_dir, inp.thesis_id, observations)
    _write_json(fusion_path, fusion_artifact)
    _write_json(compare_path, compare_artifact)
    _write_json(runtime_run_path, runtime_snapshot)
    _write_json(runtime_latest_path, runtime_snapshot)
    _write_json(alert_path, alert_artifact)
    _write_json(receipt_path, delivery_receipt)

    return ThesisRuntimeResult(
        thesis_id=inp.thesis_id,
        run_id=run_id,
        runtime_snapshot=runtime_snapshot,
        compare_artifact=compare_artifact,
        alert_artifact=alert_artifact,
        delivery_receipt=delivery_receipt,
        paths=paths,
    )


def _runtime_root(workspace_dir: str | Path, thesis_id: str) -> Path:
    thesis_id = cast(str, _validate_thesis_id(thesis_id))
    return _workspace_data_dir(workspace_dir) / "runtime" / thesis_id


def replay_compare_from_artifacts(workspace_dir: str | Path, thesis_id: str, run_id: str) -> dict[str, Any]:
    runtime_path = _runtime_root(workspace_dir, thesis_id) / "runs" / f"{run_id}.json"
    compare_path = _runtime_root(workspace_dir, thesis_id) / "compare" / f"{run_id}.json"
    runtime_snapshot = json.loads(runtime_path.read_text(encoding="utf-8"))
    compare_artifact = json.loads(compare_path.read_text(encoding="utf-8"))
    return compare_targets(
        active_target=runtime_snapshot.get("active_target"),
        market_candidate=compare_artifact.get("market_candidate"),
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def trace_run_lineage(workspace_dir: str | Path, thesis_id: str, run_id: str) -> dict[str, list[str]]:
    thesis_id = cast(str, _validate_thesis_id(thesis_id))
    receipt = _load_json(_artifact_path(workspace_dir, "delivery", thesis_id, "receipts", f"{run_id}.json"))
    alert = _load_json(_artifact_path(workspace_dir, "delivery", thesis_id, "alerts", f"{run_id}.json"))
    compare_artifact = _load_json(_artifact_path(workspace_dir, "runtime", thesis_id, "compare", f"{run_id}.json"))
    runtime_snapshot = _load_json(_artifact_path(workspace_dir, "runtime", thesis_id, "runs", f"{run_id}.json"))
    fusion_artifact = _load_json(_artifact_path(workspace_dir, "compiled", thesis_id, "fusion", f"{run_id}.json"))

    observation_ids = fusion_artifact.get("used_observation_ids") or []
    evidence_ids: list[str] = []
    for observation_id in observation_ids:
        observation_path = _artifact_path(workspace_dir, "compiled", thesis_id, "observations", f"{observation_id}.json")
        if observation_path.exists():
            observation = _load_json(observation_path)
            evidence_ids.extend(observation.get("evidence_refs") or [])

    return {
        "receipt_to_alert": [receipt["alert_artifact_id"]],
        "alert_to_compare": [alert["compare_artifact_id"]],
        "compare_to_runtime": [runtime_snapshot["artifact_id"]],
        "runtime_to_fusion": [runtime_snapshot["decision_basis"]["fusion_artifact_id"]],
        "fusion_to_observations": observation_ids,
        "observation_to_evidence": evidence_ids,
        "compare_to_market": [compare_artifact["market_target_id"]] if compare_artifact.get("market_target_id") else [],
    }


def rebuild_runtime_index(workspace_dir: str | Path, thesis_id: str) -> Path:
    thesis_id = cast(str, _validate_thesis_id(thesis_id))
    runtime_dir = _runtime_root(workspace_dir, thesis_id)
    runs_dir = runtime_dir / "runs"
    alerts_dir = _workspace_data_dir(workspace_dir) / "delivery" / thesis_id / "alerts"
    index_path = runtime_dir / "index" / "runtime_spine.sqlite3"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(index_path)
    try:
        with conn:
            conn.execute(
                """
                create table if not exists runtime_runs (
                    run_id text primary key,
                    thesis_id text not null,
                    compare_mode text,
                    should_send integer not null,
                    runtime_path text not null,
                    alert_path text not null
                )
                """
            )
            conn.execute("delete from runtime_runs")
            for runtime_path in sorted(runs_dir.glob("*.json")):
                runtime_snapshot = _load_json(runtime_path)
                run_id = runtime_snapshot["run_id"]
                alert_path = alerts_dir / f"{run_id}.json"
                alert = _load_json(alert_path) if alert_path.exists() else {"should_send": False}
                conn.execute(
                    """
                    insert into runtime_runs (run_id, thesis_id, compare_mode, should_send, runtime_path, alert_path)
                    values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        thesis_id,
                        runtime_snapshot.get("compare_mode"),
                        1 if alert.get("should_send") else 0,
                        str(runtime_path),
                        str(alert_path),
                    ),
                )
    finally:
        conn.close()
    return index_path
