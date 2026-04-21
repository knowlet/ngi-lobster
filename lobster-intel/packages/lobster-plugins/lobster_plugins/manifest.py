from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


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
    notes: str | None = None


def read_manifest(path: str | Path) -> PluginManifest:
    raw = json.loads(Path(path).read_text())
    eps = raw.get("entrypoints") or {}
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
        produces=list(raw.get("produces") or []),
        capabilities=list(raw.get("capabilities") or []),
        required_env=list(raw.get("required_env") or []),
        notes=raw.get("notes"),
    )

