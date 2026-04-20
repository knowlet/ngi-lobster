from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PluginContext:
    plugin_id: str
    plugin_dir: Path
    workspace_dir: Path
    now_utc: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrackerContract:
    source_family: str
    default_source_type: str | None = None
    replayable: bool = True
    state_mode: str = "cursor_json"
    follow_up_queues: list[str] = field(default_factory=list)
