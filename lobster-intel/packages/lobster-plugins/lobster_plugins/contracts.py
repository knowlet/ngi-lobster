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

