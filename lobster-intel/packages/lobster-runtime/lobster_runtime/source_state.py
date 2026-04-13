from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class SourceCursor:
    source_id: str
    cursor: str | None = None
    updated_at_utc: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class SourceState:
    schema_version: str = "v1"
    updated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cursors: dict[str, SourceCursor] = field(default_factory=dict)

    def set_cursor(self, source_id: str, cursor: str | None, metadata: dict | None = None) -> None:
        self.cursors[source_id] = SourceCursor(
            source_id=source_id,
            cursor=cursor,
            updated_at_utc=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self.updated_at_utc = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "updated_at_utc": self.updated_at_utc,
            "cursors": {key: asdict(value) for key, value in self.cursors.items()},
        }


def load_source_state(path: str | Path) -> SourceState:
    p = Path(path)
    if not p.exists():
        return SourceState()
    payload = json.loads(p.read_text())
    state = SourceState(
        schema_version=payload.get("schema_version", "v1"),
        updated_at_utc=payload.get("updated_at_utc") or datetime.now(timezone.utc).isoformat(),
    )
    for source_id, value in (payload.get("cursors") or {}).items():
        state.cursors[source_id] = SourceCursor(
            source_id=source_id,
            cursor=value.get("cursor"),
            updated_at_utc=value.get("updated_at_utc"),
            metadata=value.get("metadata") or {},
        )
    return state


def save_source_state(path: str | Path, state: SourceState) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
    return p
