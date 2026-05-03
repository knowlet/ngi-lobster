from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from read_state_field import read_top_level_scalar


FRESHNESS_THRESHOLD_HOURS = 4.0
DIVERGENCE_THRESHOLD_PP = 15.0


def parse_utc_timestamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def compute_freshness_hours(snapshot_at_utc: str, now: datetime | None = None) -> float:
    reference = now or datetime.now(timezone.utc)
    return (reference - parse_utc_timestamp(snapshot_at_utc)).total_seconds() / 3600.0


def load_latest_snapshot_at_utc(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT snapshot_at_utc FROM market_snapshots ORDER BY snapshot_at_utc DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        raise RuntimeError("missing market_snapshots row")
    snapshot_at_utc = str(row[0])
    validate_optional_timestamp(
        snapshot_at_utc,
        "snapshot_at_utc",
        context="market_snapshots",
    )
    return snapshot_at_utc


def read_probability(payload: dict[str, object], key: str, *, context: str) -> float:
    value = payload.get(key)
    if value is None:
        raise RuntimeError(f"missing {context}.{key}")
    return validate_probability(value, key, context=context)


def validate_probability(value: object, key: str, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{context}.{key} must be a JSON number between 0 and 1")
    probability = float(value)
    if probability < 0 or probability > 1:
        raise RuntimeError(f"{context}.{key} must be a JSON number between 0 and 1")
    return probability


def validate_optional_timestamp(value: object, key: str, *, context: str) -> None:
    if value is None or value == "":
        return
    if not isinstance(value, str) or _parse_ts(value) is None:
        raise RuntimeError(f"{context}.{key} must be an ISO-8601 timestamp")


def validate_optional_non_empty_string(value: object, key: str, *, context: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{context}.{key} must be a non-empty string")


def require_non_empty_string(value: object, key: str, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{context}.{key} must be a non-empty string")
    return value


def read_optional_object(payload: dict[str, object], key: str, *, context: str) -> dict[str, object]:
    value = payload.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RuntimeError(f"{context}.{key} must be a JSON object")
    return value


def load_latest_ngi_timestamp_utc(latest_ngi: dict[str, object]) -> str:
    for key in ("timestamp_utc", "generated_at_utc", "created_at_utc", "updated_at_utc", "snapshot_at_utc"):
        value = latest_ngi.get(key)
        if value:
            validate_optional_timestamp(value, key, context="latest_ngi")
            return str(value)
    raise RuntimeError(
        "missing latest_ngi timestamp (expected one of: timestamp_utc, generated_at_utc, created_at_utc, updated_at_utc, snapshot_at_utc)"
    )


def compute_signed_divergence_direction(first_principles_minus_market_pp: float) -> str:
    if first_principles_minus_market_pp > 0:
        return "first_principles_above_market"
    if first_principles_minus_market_pp < 0:
        return "first_principles_below_market"
    return "aligned"


def _as_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
        return None
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _parse_runtime_source_payload(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        raise RuntimeError("missing runtime_source payload")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("runtime_source payload must be a JSON object")
    validate_optional_timestamp(payload.get("ran_at_utc"), "ran_at_utc", context="runtime_source")
    evidence = payload.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, dict):
            raise RuntimeError("runtime_source evidence must be a JSON object")
        if "items" in evidence and not isinstance(evidence["items"], list):
            raise RuntimeError("runtime_source evidence.items must be a list")
        for index, item in enumerate(evidence.get("items") or []):
            if not isinstance(item, dict):
                raise RuntimeError(f"runtime_source evidence.items[{index}] must be a JSON object")
            context = f"runtime_source evidence.items[{index}]"
            validate_optional_non_empty_string(item.get("external_id"), "external_id", context=context)
            validate_optional_non_empty_string(item.get("title"), "title", context=context)
            validate_optional_non_empty_string(item.get("url"), "url", context=context)
            validate_optional_timestamp(item.get("collected_at_utc"), "collected_at_utc", context=context)
            validate_optional_timestamp(item.get("published_at_utc"), "published_at_utc", context=context)
            metadata = item.get("metadata")
            if metadata is not None and not isinstance(metadata, dict):
                raise RuntimeError(
                    f"runtime_source evidence.items[{index}].metadata must be a JSON object"
                )
            source_config = (metadata or {}).get("source_config")
            if source_config is not None and not isinstance(source_config, dict):
                raise RuntimeError(
                    f"runtime_source evidence.items[{index}].metadata.source_config must be a JSON object"
                )
            if metadata is not None:
                metadata_context = f"runtime_source evidence.items[{index}].metadata"
                validate_optional_non_empty_string(
                    metadata.get("market_id"), "market_id", context=metadata_context
                )
                validate_optional_non_empty_string(metadata.get("slug"), "slug", context=metadata_context)
            if source_config is not None:
                validate_optional_non_empty_string(
                    source_config.get("label"),
                    "label",
                    context=f"runtime_source evidence.items[{index}].metadata.source_config",
                )
            yes_probability = (metadata or {}).get("yes_probability")
            if yes_probability is not None:
                validate_probability(
                    yes_probability,
                    "yes_probability",
                    context=f"runtime_source evidence.items[{index}].metadata",
                )
    return payload


def _market_item_rank(item: dict[str, Any]) -> tuple[int, int, int, float]:
    metadata = item.get("metadata") or {}
    accepting_orders = _as_bool(metadata.get("accepting_orders"))
    active = _as_bool(metadata.get("active"))
    closed = _as_bool(metadata.get("closed"))
    latest_dt = _parse_ts(item.get("collected_at_utc")) or _parse_ts(item.get("published_at_utc"))
    latest_ts = latest_dt.timestamp() if latest_dt is not None else float("-inf")
    return (
        1 if accepting_orders is True else 0,
        1 if closed is False else 0,
        1 if active is True else 0,
        latest_ts,
    )


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


def _select_rollover_candidate(
    runtime_source_payload: dict[str, Any] | None,
    *,
    current_market_id: str | None,
) -> dict[str, Any] | None:
    if not runtime_source_payload:
        return None
    evidence = runtime_source_payload.get("evidence") or {}
    items = evidence.get("items") or []
    if not isinstance(items, list):
        return None

    eligible: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") or {}
        market_id = metadata.get("market_id") or item.get("external_id")
        if current_market_id and str(market_id) == str(current_market_id):
            continue
        if _as_bool(metadata.get("closed")) is not False:
            continue
        if _as_bool(metadata.get("accepting_orders")) is not True:
            continue
        eligible.append(item)

    if not eligible:
        return None

    candidate = max(eligible, key=_market_item_rank)
    metadata = candidate.get("metadata") or {}
    source_config = metadata.get("source_config") or {}
    return {
        "market_id": metadata.get("market_id") or candidate.get("external_id"),
        "market_slug": metadata.get("slug") or candidate.get("url"),
        "market_name": source_config.get("label") or candidate.get("title"),
        "market_question": candidate.get("title"),
        "market_yes_probability": metadata.get("yes_probability"),
        "market_closed": _as_bool(metadata.get("closed")),
        "market_active": _as_bool(metadata.get("active")),
        "market_accepting_orders": _as_bool(metadata.get("accepting_orders")),
        "collected_at_utc": candidate.get("collected_at_utc"),
        "published_at_utc": candidate.get("published_at_utc"),
    }


def _describe_rollover_candidate_blocker(
    runtime_source_payload: dict[str, Any] | None,
    *,
    current_market_id: str | None,
    rollover_candidate: dict[str, Any] | None,
) -> str | None:
    if rollover_candidate is not None:
        return None
    if runtime_source_payload is None:
        return "runtime_source_not_provided"

    evidence = runtime_source_payload.get("evidence") or {}
    items = evidence.get("items") or []
    successor_seen = False
    for item in items:
        metadata = item.get("metadata") or {}
        market_id = metadata.get("market_id") or item.get("external_id")
        if current_market_id and str(market_id) == str(current_market_id):
            continue
        successor_seen = True

    if not successor_seen:
        return "no_successor_market"
    return "no_explicit_open_accepting_successor"


def build_summary(
    state_path: Path,
    db_path: Path,
    latest_ngi_path: Path,
    runtime_source_path: Path | None = None,
) -> dict[str, object]:
    dq_status = read_top_level_scalar(state_path, "dq_status")
    latest_snapshot_at_utc = load_latest_snapshot_at_utc(db_path)
    freshness_hours = compute_freshness_hours(latest_snapshot_at_utc)

    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    if not isinstance(latest_ngi, dict):
        raise RuntimeError("latest_ngi payload must be a JSON object")
    latest_ngi_timestamp_utc = load_latest_ngi_timestamp_utc(latest_ngi)
    latest_ngi_age_hours = compute_freshness_hours(latest_ngi_timestamp_utc)
    market_target = read_optional_object(latest_ngi, "market_target", context="latest_ngi")
    target_detail = read_optional_object(latest_ngi, "target_detail", context="latest_ngi")
    validate_optional_non_empty_string(
        market_target.get("market_id"), "market_id", context="latest_ngi.market_target"
    )
    validate_optional_non_empty_string(
        market_target.get("market_name"), "market_name", context="latest_ngi.market_target"
    )
    validate_optional_non_empty_string(
        target_detail.get("market_id"), "market_id", context="latest_ngi.target_detail"
    )
    validate_optional_non_empty_string(
        target_detail.get("market_question"),
        "market_question",
        context="latest_ngi.target_detail",
    )
    first_principles_probability = read_probability(
        latest_ngi, "first_principles_probability", context="latest_ngi"
    )
    market_yes_probability = read_probability(
        target_detail, "market_yes_probability", context="target_detail"
    )
    validate_optional_non_empty_string(
        target_detail.get("probability_mode"), "probability_mode", context="target_detail"
    )
    validate_optional_non_empty_string(
        latest_ngi.get("probability_mode"), "probability_mode", context="latest_ngi"
    )
    probability_mode = (
        target_detail.get("probability_mode") or latest_ngi.get("probability_mode") or "unknown"
    )
    divergence_pp = abs(first_principles_probability - market_yes_probability) * 100.0
    first_principles_minus_market_pp = (first_principles_probability - market_yes_probability) * 100.0
    stale_data = freshness_hours > FRESHNESS_THRESHOLD_HOURS
    latest_ngi_stale = latest_ngi_age_hours > FRESHNESS_THRESHOLD_HOURS
    divergence_blocking = divergence_pp > DIVERGENCE_THRESHOLD_PP
    market_closed = _as_bool(target_detail.get("market_closed"))
    market_accepting_orders = _as_bool(target_detail.get("market_accepting_orders"))
    market_closed_unknown = "market_closed" in target_detail and market_closed is None
    market_accepting_orders_unknown = (
        "market_accepting_orders" in target_detail and market_accepting_orders is None
    )
    closed_target_blocking = (
        market_closed is True
        or market_accepting_orders is False
        or market_closed_unknown
        or market_accepting_orders_unknown
    )
    reselection_required = closed_target_blocking
    runtime_source_payload = _parse_runtime_source_payload(runtime_source_path)
    rollover_candidate = _select_rollover_candidate(
        runtime_source_payload,
        current_market_id=str(market_target.get("market_id") or target_detail.get("market_id") or "") or None,
    )
    rollover_candidate_blocker = None
    if reselection_required:
        rollover_candidate_blocker = _describe_rollover_candidate_blocker(
            runtime_source_payload,
            current_market_id=str(market_target.get("market_id") or target_detail.get("market_id") or "") or None,
            rollover_candidate=rollover_candidate,
        )

    status = "pass"
    blockers: list[str] = []
    if dq_status != "pass":
        status = "fail"
        blockers.append(f"dq_status={dq_status}")
    if stale_data:
        status = "fail"
        blockers.append(f"stale_data={freshness_hours:.2f}h")
    if latest_ngi_stale:
        status = "fail"
        blockers.append(f"latest_ngi_stale={latest_ngi_age_hours:.2f}h")
    if closed_target_blocking:
        status = "fail"
        if market_closed is True:
            blockers.append("market_closed=true")
        if market_accepting_orders is False:
            blockers.append("market_accepting_orders=false")
        if market_closed_unknown:
            blockers.append("market_closed=unknown")
        if market_accepting_orders_unknown:
            blockers.append("market_accepting_orders=unknown")
    if divergence_blocking:
        status = "fail"
        blockers.append(f"divergence_pp={divergence_pp:.2f}")

    runtime_target_id = market_target.get("market_id") or target_detail.get("market_id")
    market_question = target_detail.get("market_question")
    if reselection_required:
        runtime_target_id = require_non_empty_string(
            runtime_target_id,
            "runtime_target_id",
            context="active_target_reselection",
        )
        market_question = require_non_empty_string(
            market_question,
            "market_question",
            context="active_target_reselection",
        )

    active_target_reselection = {
        "runtime_target_id": runtime_target_id,
        "market_question": market_question,
        "reselection_required": reselection_required,
        "next_contract_action": "reselect_active_target" if reselection_required else "keep_active_target",
        "rollover_candidate_blocker": rollover_candidate_blocker,
        "rollover_candidate": rollover_candidate,
    }

    return {
        "status": status,
        "dq_status": dq_status,
        "latest_snapshot_at_utc": latest_snapshot_at_utc,
        "freshness_hours": round(freshness_hours, 4),
        "freshness_threshold_hours": FRESHNESS_THRESHOLD_HOURS,
        "stale_data": stale_data,
        "latest_ngi_timestamp_utc": latest_ngi_timestamp_utc,
        "latest_ngi_age_hours": round(latest_ngi_age_hours, 4),
        "latest_ngi_threshold_hours": FRESHNESS_THRESHOLD_HOURS,
        "latest_ngi_stale": latest_ngi_stale,
        "divergence_pp": round(divergence_pp, 4),
        "divergence_threshold_pp": DIVERGENCE_THRESHOLD_PP,
        "divergence_blocking": divergence_blocking,
        "first_principles_probability": first_principles_probability,
        "market_yes_probability": market_yes_probability,
        "first_principles_minus_market_pp": round(first_principles_minus_market_pp, 4),
        "direction": compute_signed_divergence_direction(first_principles_minus_market_pp),
        "probability_mode": probability_mode,
        "market_target_id": market_target.get("market_id") or target_detail.get("market_id"),
        "market_target_name": market_target.get("market_name") or target_detail.get("market_question"),
        "market_closed": market_closed,
        "market_accepting_orders": market_accepting_orders,
        "closed_target_blocking": closed_target_blocking,
        "reselection_required": reselection_required,
        "next_contract_action": "reselect_active_target" if reselection_required else "keep_active_target",
        "rollover_candidate": rollover_candidate,
        "rollover_candidate_blocker": rollover_candidate_blocker,
        "active_target_reselection": active_target_reselection,
        "blockers": blockers,
    }


def main(argv: list[str]) -> int:
    if len(argv) not in {4, 5}:
        print(
            "usage: verify_runtime_ops_health.py <state.yaml> <intelligence_store.sqlite> <latest_ngi.json> [runtime_source_polymarket.json]",
            file=sys.stderr,
        )
        return 2

    state_path = Path(argv[1])
    db_path = Path(argv[2])
    latest_ngi_path = Path(argv[3])
    runtime_source_path = Path(argv[4]) if len(argv) == 5 else None

    try:
        summary = build_summary(state_path, db_path, latest_ngi_path, runtime_source_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
