from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


_SAFE_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _validated_path_component(value: str, *, label: str) -> str:
    if not _SAFE_PATH_COMPONENT.fullmatch(value):
        raise ValueError(f"{label} must be a simple relative path component: {value!r}")
    return value


def _source_runtime_dir(workspace_dir: str | Path, plugin_id: str) -> Path:
    safe_plugin_id = _validated_path_component(plugin_id, label="plugin_id")
    return Path(workspace_dir) / "lobster-intel" / "data" / "runtime" / "sources" / safe_plugin_id


def _source_runs_dir(workspace_dir: str | Path, plugin_id: str) -> Path:
    return _source_runtime_dir(workspace_dir, plugin_id) / "runs"


def _source_run_path(workspace_dir: str | Path, plugin_id: str, run_id: str) -> Path:
    return _source_runs_dir(workspace_dir, plugin_id) / f"{run_id}.json"


def _source_index_path(workspace_dir: str | Path, plugin_id: str) -> Path:
    return _source_runtime_dir(workspace_dir, plugin_id) / "index.sqlite"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = payload.get("evidence") or {}
    items = evidence.get("items") or []
    return items if isinstance(items, list) else []


def _item_view(item: dict[str, Any], ran_at_utc: str | None) -> dict[str, Any]:
    return {
        "source_id": item.get("source_id"),
        "source_type": item.get("source_type"),
        "external_id": item.get("external_id"),
        "title": item.get("title"),
        "url": item.get("url"),
        "published_at_utc": item.get("published_at_utc"),
        "collected_at_utc": item.get("collected_at_utc") or ran_at_utc,
    }


def replay_source_run(workspace_dir: str | Path, plugin_id: str, run_id: str) -> dict[str, Any]:
    artifact_path = _source_run_path(workspace_dir, plugin_id, run_id)
    if not artifact_path.exists():
        raise FileNotFoundError(f"missing source run artifact: {artifact_path}")

    payload = _load_json(artifact_path)
    evidence = payload.get("evidence") or {}
    ran_at_utc = payload.get("ran_at_utc")
    items = [_item_view(item, ran_at_utc) for item in _items(payload)]
    return {
        "plugin": payload.get("plugin") or plugin_id,
        "run_id": payload.get("run_id") or run_id,
        "ran_at_utc": ran_at_utc,
        "artifact_path": str(artifact_path),
        "state_path": evidence.get("state_path"),
        "evidence_item_count": len(items),
        "new_count": evidence.get("new_count"),
        "items": items,
    }


def rebuild_source_index(workspace_dir: str | Path, plugin_id: str) -> dict[str, Any]:
    runs_dir = _source_runs_dir(workspace_dir, plugin_id)
    if not runs_dir.exists():
        raise FileNotFoundError(f"missing source runs directory: {runs_dir}")

    index_path = _source_index_path(workspace_dir, plugin_id)
    if index_path.exists():
        index_path.unlink()

    run_paths = sorted(runs_dir.glob("*.json"))
    run_count = 0
    item_count = 0

    with sqlite3.connect(index_path) as conn:
        conn.execute(
            "create table source_runs (run_id text primary key, plugin text, ran_at_utc text, artifact_path text, evidence_item_count integer, new_count integer, state_path text)"
        )
        conn.execute(
            "create table source_items (item_id text primary key, run_id text, source_id text, external_id text, title text, url text, published_at_utc text, collected_at_utc text, source_type text, artifact_path text)"
        )

        for run_path in run_paths:
            payload = _load_json(run_path)
            evidence = payload.get("evidence") or {}
            run_id = str(payload.get("run_id") or run_path.stem)
            plugin = str(payload.get("plugin") or plugin_id)
            ran_at_utc = payload.get("ran_at_utc")
            state_path = evidence.get("state_path")
            items = _items(payload)

            conn.execute(
                "insert into source_runs (run_id, plugin, ran_at_utc, artifact_path, evidence_item_count, new_count, state_path) values (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    plugin,
                    ran_at_utc,
                    str(run_path),
                    len(items),
                    evidence.get("new_count"),
                    state_path,
                ),
            )
            run_count += 1

            for index, item in enumerate(items):
                external_id = item.get("external_id") or f"item-{index}"
                item_id = f"{run_id}:{item.get('source_id') or plugin}:{external_id}"
                conn.execute(
                    "insert into source_items (item_id, run_id, source_id, external_id, title, url, published_at_utc, collected_at_utc, source_type, artifact_path) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item_id,
                        run_id,
                        item.get("source_id"),
                        external_id,
                        item.get("title"),
                        item.get("url"),
                        item.get("published_at_utc"),
                        item.get("collected_at_utc") or ran_at_utc,
                        item.get("source_type"),
                        str(run_path),
                    ),
                )
                item_count += 1

        conn.commit()

    return {
        "plugin": plugin_id,
        "index_path": str(index_path),
        "run_count": run_count,
        "item_count": item_count,
    }
