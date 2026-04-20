from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .contracts import TrackerContract


@dataclass(slots=True)
class PluginEntrypoints:
    ingest: str
    compile: str | None = None
    evaluate: str | None = None


@dataclass(slots=True)
class PluginManifest:
    id: str
    name: str
    version: str
    type: str
    entrypoints: PluginEntrypoints
    produces: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    required_env: list[str] = field(default_factory=list)
    tracker: TrackerContract | None = None
    notes: str | None = None


def _runtime_queue_outputs(produces: list[str]) -> list[str]:
    return [
        value
        for value in produces
        if value.startswith("runtime.") and value.endswith("_queue")
    ]


def _read_tracker_contract(raw: dict[str, Any], produces: list[str]) -> TrackerContract | None:
    tracker_raw = raw.get("tracker")
    runtime_queue_outputs = _runtime_queue_outputs(produces)
    if tracker_raw is None:
        if runtime_queue_outputs:
            raise ValueError("runtime queue outputs require tracker.follow_up_queues")
        return None

    contract = TrackerContract(
        source_family=tracker_raw["source_family"],
        default_source_type=tracker_raw.get("default_source_type"),
        replayable=tracker_raw.get("replayable", True),
        state_mode=tracker_raw.get("state_mode", "cursor_json"),
        follow_up_queues=list(tracker_raw.get("follow_up_queues") or []),
    )
    expected_outputs = {f"runtime.{queue_name}" for queue_name in contract.follow_up_queues}
    missing_outputs = sorted(expected_outputs.difference(produces))
    if missing_outputs:
        raise ValueError(
            f"tracker.follow_up_queues missing produces entries: {missing_outputs}"
        )
    undeclared_outputs = sorted(set(runtime_queue_outputs).difference(expected_outputs))
    if undeclared_outputs:
        raise ValueError(
            f"runtime queue outputs must be declared in tracker.follow_up_queues: {undeclared_outputs}"
        )
    return contract


def read_manifest(path: str | Path) -> PluginManifest:
    raw = json.loads(Path(path).read_text())
    eps = raw.get("entrypoints") or {}
    produces = list(raw.get("produces") or [])
    return PluginManifest(
        id=raw["id"],
        name=raw["name"],
        version=raw["version"],
        type=raw["type"],
        entrypoints=PluginEntrypoints(
            ingest=eps["ingest"],
            compile=eps.get("compile"),
            evaluate=eps.get("evaluate"),
        ),
        produces=produces,
        capabilities=list(raw.get("capabilities") or []),
        required_env=list(raw.get("required_env") or []),
        tracker=_read_tracker_contract(raw, produces),
        notes=raw.get("notes"),
    )
