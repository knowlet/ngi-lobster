from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .run_once import run_plugin_once_with_config


def normalize_source_plugin_config(plugin_dir: str | Path, config: Any) -> dict[str, Any] | None:
    if config is None:
        return None
    if isinstance(config, dict):
        return config
    if not isinstance(config, list):
        raise TypeError(f"unsupported source plugin config type: {type(config).__name__}")

    plugin_id = Path(plugin_dir).resolve().parent.name if Path(plugin_dir).name == "plugin.py" else Path(plugin_dir).name
    if plugin_id in {"official-statements-tracker", "watchlist-tracker"}:
        return {"feeds": config}
    if plugin_id == "polymarket-tracker":
        return {"markets": config}
    return {"items": config}


def _runtime_dir(workspace_dir: str | Path, plugin_id: str) -> Path:
    return Path(workspace_dir) / "lobster-intel" / "data" / "runtime" / "sources" / plugin_id


def _run_id(ran_at_utc: str) -> str:
    return datetime.fromisoformat(ran_at_utc.replace("Z", "+00:00")).strftime("%Y%m%dT%H%M%SZ")


def run_source_plugin(
    plugin_dir: str | Path,
    workspace_dir: str | Path,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_config = normalize_source_plugin_config(plugin_dir, config)
    result = run_plugin_once_with_config(plugin_dir, workspace_dir, config=normalized_config)
    plugin_id = result["plugin"]
    runtime_dir = _runtime_dir(workspace_dir, plugin_id)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = runtime_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    latest_path = runtime_dir / "latest.json"
    ran_at_utc = result.get("ran_at_utc") or datetime.now(timezone.utc).isoformat()
    run_id = _run_id(ran_at_utc)
    run_path = runs_dir / f"{run_id}.json"
    snapshot = {
        "schema_version": "v1",
        "plugin": plugin_id,
        "version": result.get("version"),
        "run_id": run_id,
        "ran_at_utc": ran_at_utc,
        "evidence": result.get("evidence"),
    }
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
    run_path.write_text(payload)
    latest_path.write_text(payload)
    result["run_id"] = run_id
    result["runtime_artifact_path"] = str(run_path)
    result["latest_runtime_artifact_path"] = str(latest_path)
    result["normalized_config"] = normalized_config
    return result
