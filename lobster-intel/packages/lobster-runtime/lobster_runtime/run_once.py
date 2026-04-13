from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lobster_plugins import PluginContext, load_plugin


def _normalize(value: Any):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    return value


def run_plugin_once(plugin_dir: str | Path, workspace_dir: str | Path) -> dict[str, Any]:
    plugin_dir = Path(plugin_dir)
    workspace_dir = Path(workspace_dir)
    manifest, entrypoints = load_plugin(plugin_dir)
    ctx = PluginContext(
        plugin_id=manifest.id,
        plugin_dir=plugin_dir,
        workspace_dir=workspace_dir,
        now_utc=datetime.now(timezone.utc).isoformat(),
    )
    evidence = _normalize(entrypoints["ingest"](ctx))
    result: dict[str, Any] = {
        "plugin": manifest.id,
        "version": manifest.version,
        "ran_at_utc": ctx.now_utc,
        "evidence": evidence,
    }
    if "compile" in entrypoints:
        compiled = _normalize(entrypoints["compile"](ctx, evidence))
        result["compiled"] = compiled
    if "evaluate" in entrypoints:
        runtime = _normalize(entrypoints["evaluate"](ctx, result.get("evidence"), result.get("compiled")))
        result["runtime"] = runtime
    return result

