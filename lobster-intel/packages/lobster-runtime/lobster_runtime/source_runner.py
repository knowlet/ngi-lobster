from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .run_once import run_plugin_once_with_config


def _runtime_dir(workspace_dir: str | Path, plugin_id: str) -> Path:
    return Path(workspace_dir) / "lobster-intel" / "data" / "runtime" / "sources" / plugin_id


def run_source_plugin(
    plugin_dir: str | Path,
    workspace_dir: str | Path,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = run_plugin_once_with_config(plugin_dir, workspace_dir, config=config)
    plugin_id = result["plugin"]
    runtime_dir = _runtime_dir(workspace_dir, plugin_id)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    latest_path = runtime_dir / "latest.json"
    snapshot = {
        "schema_version": "v1",
        "plugin": plugin_id,
        "version": result.get("version"),
        "ran_at_utc": result.get("ran_at_utc") or datetime.now(timezone.utc).isoformat(),
        "evidence": result.get("evidence"),
    }
    latest_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    result["runtime_artifact_path"] = str(latest_path)
    return result
