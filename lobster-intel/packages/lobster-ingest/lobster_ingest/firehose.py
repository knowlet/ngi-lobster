from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SAFE_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PRIORITY_ORDER = {
    "low": 0,
    "medium": 1,
    "med": 1,
    "normal": 1,
    "high": 2,
    "urgent": 3,
    "critical": 3,
    "sev1": 3,
}


def _validated_path_component(value: str, *, label: str) -> str:
    value = str(value or "")
    if not _SAFE_PATH_COMPONENT.fullmatch(value):
        raise ValueError(f"{label} must be a simple relative path component: {value!r}")
    return value


def _now_utc(value: str | None = None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).isoformat()


def _workspace_source_root(workspace_dir: str | Path, plugin_id: str) -> Path:
    safe_plugin_id = _validated_path_component(plugin_id, label="plugin_id")
    return Path(workspace_dir) / "lobster-intel" / "data" / "runtime" / "sources" / safe_plugin_id


def _relative_path(path: Path, workspace_dir: str | Path) -> str:
    return str(path.relative_to(Path(workspace_dir)))


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_tags(raw_event: dict[str, Any]) -> list[str]:
    values = _first_present(raw_event, "tags", "event_tags")
    if isinstance(values, list):
        return [str(value).strip() for value in values if str(value).strip()]
    if isinstance(values, str):
        return [part.strip() for part in values.split(",") if part.strip()]

    tag = _first_present(raw_event, "tag", "topic")
    if tag in (None, ""):
        return []
    return [str(tag).strip()]


def _normalized_tag_set(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _normalized_priority_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    return _PRIORITY_ORDER.get(text)


def _stable_external_id(raw_event: dict[str, Any]) -> str:
    explicit = _first_present(raw_event, "id", "event_id", "external_id")
    if explicit not in (None, ""):
        return str(explicit)

    fingerprint_fields = {
        "received_at_utc": _first_present(raw_event, "received_at_utc", "received_at", "published_at_utc", "published_at"),
        "title": _first_present(raw_event, "title", "headline"),
        "url": _first_present(raw_event, "url", "link"),
        "summary": _first_present(raw_event, "summary", "text", "body"),
        "tags": _normalize_tags(raw_event),
    }
    digest = hashlib.sha256(json.dumps(fingerprint_fields, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return f"firehose-{digest[:16]}"


def _normalize_event(raw_event: dict[str, Any], *, collected_at_utc: str) -> dict[str, Any]:
    tags = _normalize_tags(raw_event)
    title = _first_present(raw_event, "title", "headline")
    summary = _first_present(raw_event, "summary", "text", "body")
    published_at_utc = _first_present(raw_event, "published_at_utc", "published_at", "received_at_utc", "received_at")
    url = _first_present(raw_event, "url", "link")

    return {
        "source_id": "firehose",
        "source_type": "firehose_event",
        "external_id": _stable_external_id(raw_event),
        "title": title,
        "url": url,
        "published_at_utc": published_at_utc,
        "collected_at_utc": collected_at_utc,
        "tag": tags[0] if tags else None,
        "tags": tags,
        "priority": _first_present(raw_event, "priority", "severity"),
        "summary": summary,
    }


def normalize_firehose_events(
    *,
    workspace_dir: str | Path,
    input_file: str | Path,
    run_id: str,
    now_utc: str | None = None,
    plugin_id: str = "firehose-tracker",
    include_tags: list[str] | None = None,
    min_priority: str | None = None,
) -> dict[str, Any]:
    recorded_at_utc = _now_utc(now_utc)
    input_path = Path(input_file)
    safe_plugin_id = _validated_path_component(plugin_id, label="plugin_id")
    safe_run_id = _validated_path_component(run_id, label="run_id")
    source_root = _workspace_source_root(workspace_dir, safe_plugin_id)
    runs_root = source_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    line_count = 0
    filtered_by_tag = 0
    filtered_by_priority = 0
    include_tag_set = _normalized_tag_set(include_tags)
    min_priority_rank = _normalized_priority_value(min_priority)
    if min_priority and min_priority_rank is None:
        raise ValueError(f"unsupported min_priority: {min_priority!r}")
    for index, raw_line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        line_count += 1
        try:
            raw_event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid Firehose JSON on line {index}: {exc.msg}") from exc
        if not isinstance(raw_event, dict):
            raise ValueError(f"invalid Firehose JSON on line {index}: expected object")
        item = _normalize_event(raw_event, collected_at_utc=recorded_at_utc)
        if include_tag_set and not (_normalized_tag_set(item.get("tags")) & include_tag_set):
            filtered_by_tag += 1
            continue
        item_priority_rank = _normalized_priority_value(item.get("priority"))
        if min_priority_rank is not None and (item_priority_rank is None or item_priority_rank < min_priority_rank):
            filtered_by_priority += 1
            continue
        items.append(item)

    artifact_relpath = Path("lobster-intel") / "data" / "runtime" / "sources" / safe_plugin_id / "runs" / f"{safe_run_id}.json"
    state_relpath = Path("lobster-intel") / "data" / "runtime" / "sources" / safe_plugin_id / "state.json"
    artifact_path = Path(workspace_dir) / artifact_relpath
    latest_path = source_root / "latest.json"
    state_path = Path(workspace_dir) / state_relpath

    payload = {
        "schema_version": "v1",
        "plugin": safe_plugin_id,
        "version": "0.1.0",
        "run_id": safe_run_id,
        "ran_at_utc": recorded_at_utc,
        "evidence": {
            "new_count": len(items),
            "state_path": state_relpath.as_posix(),
            "items": items,
        },
        "normalization": {
            "source_file": str(input_path),
            "line_count": line_count,
            "kept_count": len(items),
            "filtered_count": filtered_by_tag + filtered_by_priority,
            "filtered_by_tag_count": filtered_by_tag,
            "filtered_by_priority_count": filtered_by_priority,
            "include_tags": sorted(include_tag_set),
            "min_priority": str(min_priority).strip().lower() if min_priority_rank is not None else None,
        },
    }
    state_payload = {
        "schema": "lobster.source.firehose_state.v1",
        "plugin": safe_plugin_id,
        "input_file": str(input_path),
        "last_run_id": safe_run_id,
        "last_ran_at_utc": recorded_at_utc,
        "latest_artifact_path": artifact_relpath.as_posix(),
        "line_count": line_count,
        "item_count": len(items),
        "filtered_count": filtered_by_tag + filtered_by_priority,
    }

    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    artifact_path.write_text(encoded, encoding="utf-8")
    latest_path.write_text(encoded, encoding="utf-8")
    state_path.write_text(json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "status": "ok",
        "plugin": safe_plugin_id,
        "run_id": safe_run_id,
        "new_count": len(items),
        "artifact_path": _relative_path(artifact_path, workspace_dir),
        "state_path": _relative_path(state_path, workspace_dir),
        "line_count": line_count,
        "kept_count": len(items),
        "filtered_count": filtered_by_tag + filtered_by_priority,
    }
